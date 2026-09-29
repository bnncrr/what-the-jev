"""实验运行编排、动态并发调度、进度显示与结果汇总。"""

import logging
import os
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from queue import Empty, Queue
from typing import Any, TextIO

from tqdm import tqdm

from .client import Transport, predict
from .config import DEFAULT_CONCURRENCY as DEFAULT_CONCURRENCY
from .config import MAX_CONCURRENCY as MAX_CONCURRENCY
from .config import REQUIRED_FIELDS as REQUIRED_FIELDS
from .config import RunConfig
from .config import _concurrency as _concurrency
from .config import load_config as load_config
from .data import load_dataset
from .results import (
    drop_failed,
    load_recorded_ids,
    locked_output,
    request_sample,
    write_result,
)

logger = logging.getLogger(__name__)


def run(config_path: str | Path, transport: Transport = predict) -> Path | list[Path]:
    """校验输入并请求尚未记录的样本；多数据逐对运行，repeat 大于 1 时逐轮运行。"""
    path = Path(config_path).resolve()
    logger.info('加载配置文件: %s', path)
    config = load_config(path)
    api_key = os.environ.get('OPENROUTER_API_KEY', '').strip()
    if not api_key:
        raise ValueError('需要设置 OPENROUTER_API_KEY。')
    datas = [config['data']] if isinstance(config['data'], str) else config['data']
    configured = config['output']
    outputs = [configured] if isinstance(configured, str) else configured
    repeat = config['repeat']
    results: list[Path] = []
    for data_index, data_name in enumerate(datas):
        samples = load_dataset(path.parent / data_name)
        # output 已按 data 顺序再按轮次展开：单 data 时全部轮次属于它
        if len(datas) == 1:
            names = outputs
        else:
            names = outputs[data_index * repeat : (data_index + 1) * repeat]
        if len(datas) > 1:
            logger.info('数据 %d/%d：%s', data_index + 1, len(datas), data_name)
        for index, name in enumerate(names, start=1):
            if len(names) > 1:
                logger.info('轮次 %d/%d', index, len(names))
            output = (path.parent / name).resolve()
            results.append(_run_once(samples, config, api_key, transport, output))
    return results[0] if isinstance(configured, str) else results


def _run_once(
    samples: list[dict[str, Any]],
    config: RunConfig,
    api_key: str,
    transport: Transport,
    output: Path,
) -> Path:
    """对单个结果文件执行一轮完整运行，返回结果路径。"""
    output.parent.mkdir(parents=True, exist_ok=True)
    with locked_output(output):
        pending = _pending_samples(samples, output)
        skipped = len(samples) - len(pending)
        completed, failed = 0, 0
        if pending:
            completed, failed = _process(pending, config, api_key, transport, output)
    logger.info('结果：%s', output)
    logger.info('汇总：完成 %d，失败 %d，跳过 %d', completed, failed, skipped)
    return output


def _pending_samples(
    samples: list[dict[str, Any]], output: Path
) -> list[dict[str, Any]]:
    """校验历史、清理失败记录并筛选待请求样本；调用方须持有输出文件锁。"""
    recorded = load_recorded_ids(output)
    requeued = drop_failed(output)
    if requeued:
        logger.info('重试：清理失败记录 %d 条，重新排队', len(requeued))
    recorded -= requeued
    pending = [sample for sample in samples if sample['id'] not in recorded]
    if recorded:
        logger.info(
            '续跑：已有 %d 条记录，跳过 %d 条，待请求 %d 条',
            len(recorded),
            len(samples) - len(pending),
            len(pending),
        )
    return pending


def _process(
    samples: list[dict[str, Any]],
    config: RunConfig,
    api_key: str,
    transport: Transport,
    output: Path,
) -> tuple[int, int]:
    """按完成顺序写入结果；并发上限成功加一、失败减半，中断时停止提交并收尾。"""
    completed, failed = 0, 0
    ceiling = min(MAX_CONCURRENCY, len(samples))
    limit = min(config['concurrency'], ceiling)
    if not limit:
        return completed, failed
    remaining = iter(samples)
    finished: Queue[Future[dict[str, Any]]] = Queue()
    pending: set[Future[dict[str, Any]]] = set()
    bar = tqdm(total=len(samples), unit='条', disable=None)

    with output.open('a', encoding='utf-8') as file:
        pool = ThreadPoolExecutor(max_workers=ceiling)
        writable = True
        current: Future[dict[str, Any]] | None = None

        def submit_next() -> bool:
            """有剩余样本时提交一个并登记完成通知；样本耗尽返回 False。"""
            sample = next(remaining, None)
            if sample is None:
                return False
            future = pool.submit(
                _request,
                sample,
                config,
                api_key,
                transport,
            )
            pending.add(future)
            future.add_done_callback(finished.put)
            return True

        def refill() -> None:
            """按当前并发上限补足在途请求。"""
            while len(pending) < limit and submit_next():
                pass

        try:
            refill()
            while pending:
                current = finished.get()
                result = current.result()
                writable = False
                success = _save_result(file, result)
                pending.remove(current)
                current = None
                writable = True
                completed += int(success)
                failed += int(not success)
                limit = _adjust_limit(limit, ceiling, success)
                _report_progress(bar, result, failed, limit)
                refill()
        except BaseException:
            logger.warning('运行中断，停止提交并等待在途请求结束')
            for future in pending:
                future.cancel()
            pool.shutdown(wait=True, cancel_futures=True)
            if writable:
                _save_finished(file, finished, pending, current)
            else:
                logger.error('结果写入未完成，停止追加以保留可恢复的文件尾部')
            raise
        finally:
            pool.shutdown(wait=True, cancel_futures=True)
            bar.close()
    return completed, failed


def _report_progress(
    bar: tqdm, result: dict[str, Any], failed: int, limit: int
) -> None:
    """根据进度条显示状态记录样本日志，并更新完成进度和统计。"""
    error = result['error']
    if error is None:
        if bar.disable:
            logger.info('%s: 完成', result['id'])
    else:
        logger.warning(
            '%s: 失败，类型=%s，HTTP 状态=%s',
            result['id'],
            error['type'],
            error.get('status', '-'),
        )
    bar.update(1)
    bar.set_postfix({'失败': failed, '并发': limit})


def _adjust_limit(limit: int, ceiling: int, success: bool) -> int:
    """AIMD 调整并发上限：成功加一爬升，失败减半退让，夹在 1 与 ceiling 之间。"""
    if success:
        return min(ceiling, limit + 1)
    return max(1, limit // 2)


def _save_result(file: TextIO, result: dict[str, Any]) -> bool:
    """持久化一条结果并返回是否成功；进度与日志由调用方更新。"""
    write_result(file, result)
    return result['error'] is None


def _save_finished(
    file: TextIO,
    finished: Queue[Future[dict[str, Any]]],
    pending: set[Future[dict[str, Any]]],
    current: Future[dict[str, Any]] | None = None,
) -> None:
    """线程池停止后保存剩余结果，清理失败不遮蔽原始异常。"""
    while pending:
        if current is not None:
            future, current = current, None
        else:
            try:
                future = finished.get_nowait()
            except Empty:
                # 中断可能发生在完成通知出队与赋值之间。
                future = next(iter(pending))
        if future not in pending:
            continue
        pending.remove(future)
        if future.cancelled():
            continue
        if future.exception() is not None:
            logger.error('在途请求异常退出，未获得可记录的结果')
            continue
        try:
            _save_result(file, future.result())
        except Exception:
            logger.exception('保存剩余结果失败，停止追加')
            break


def _request(
    sample: dict[str, Any],
    config: RunConfig,
    api_key: str,
    transport: Transport,
) -> dict[str, Any]:
    """构造单轮请求；worker 仅负责请求，不接触结果文件。"""
    payload = {'model': config['model'], **sample['input']}
    return request_sample(
        sample['id'],
        payload,
        api_key,
        config['endpoint'],
        transport,
    )
