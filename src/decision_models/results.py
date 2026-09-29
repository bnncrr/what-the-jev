"""JSONL 结果持久化、历史记录校验及续跑文件保护。"""

import fcntl
import json
import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from http.client import HTTPException as HTTPException
from pathlib import Path
from typing import Any, BinaryIO, TextIO

from jsonschema import Draft202012Validator

from .client import Transport as Transport
from .client import request_sample as request_sample
from .json_utils import JSONValue as JSONValue
from .json_utils import load_validator, loads, validate

SCHEMA = Path(__file__).resolve().parents[2] / 'schema/result.schema.json'
logger = logging.getLogger(__name__)


def drop_failed(path: Path) -> set[str]:
    """删除失败记录并返回重新排队的样本 ID；调用方须持有输出文件锁。

    上一次运行留下的失败记录在下一次运行时重新请求；本次运行内产生的
    失败记录仍保留在结果里，留待下次运行处理。
    """
    if not path.exists():
        return set()
    kept: list[str] = []
    failed: set[str] = set()
    with path.open(encoding='utf-8') as file:
        for line in file:
            record = loads(line)
            if record['error'] is None:
                kept.append(line)
            else:
                failed.add(record['id'])
    if failed:
        path.write_text(''.join(kept), encoding='utf-8')
    return failed


def write_result(file: TextIO, result: dict[str, Any]) -> None:
    """每完成一条就写入并刷新，保留已完成请求。"""
    file.write(json.dumps(result, ensure_ascii=False, allow_nan=False) + '\n')
    file.flush()


@contextmanager
def locked_output(path: Path) -> Iterator[None]:
    """独占结果文件，锁覆盖历史扫描、尾部修复和追加写入。"""
    with path.open('a+b') as file:
        try:
            fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError(f'结果文件正被其他运行使用：{path}') from exc
        try:
            yield
        finally:
            fcntl.flock(file.fileno(), fcntl.LOCK_UN)


def load_recorded_ids(path: Path) -> set[str]:
    """校验历史记录并修复末尾残行；调用方须持有输出文件锁。"""
    if not path.exists():
        return set()
    validator = load_validator(SCHEMA)
    with path.open('r+b') as file:
        recorded, truncate_at, needs_newline = _scan_records(file, validator)
        if truncate_at is not None:
            file.truncate(truncate_at)
            logger.warning('已截断结果文件末尾残行：%s', path)
        elif needs_newline:
            file.write(b'\n')
            logger.info('已补齐结果文件末尾换行：%s', path)
    return recorded


def _scan_records(
    file: BinaryIO, validator: Draft202012Validator
) -> tuple[set[str], int | None, bool]:
    """逐行校验记录，返回已记录 ID 和待执行的尾部修复信息。"""
    recorded: set[str] = set()
    offset = 0
    needs_newline = False
    for number, raw in enumerate(file, start=1):
        record = _parse_record(raw, number, validator)
        if record is None:
            return recorded, offset, False
        sample_id = record['id']
        if sample_id in recorded:
            raise ValueError(f'结果文件第 {number} 行重复样本 ID：{sample_id}')
        recorded.add(sample_id)
        offset += len(raw)
        needs_newline = not raw.endswith(b'\n')
    return recorded, None, needs_newline


def _parse_record(
    raw: bytes, number: int, validator: Draft202012Validator
) -> dict[str, Any] | None:
    """解码并校验单行记录，仅在未换行的末尾残行可修复时返回 None。"""
    terminated = raw.endswith(b'\n')
    label = f'结果文件第 {number} 行格式错误'
    try:
        record = loads(raw.decode('utf-8'))
    except UnicodeDecodeError as exc:
        if (
            not terminated
            and exc.reason == 'unexpected end of data'
            and exc.end == len(raw)
        ):
            return None
        raise ValueError(f'{label}：无效 UTF-8') from exc
    except json.JSONDecodeError as exc:
        if not terminated and _is_truncated_json(exc):
            return None
        raise ValueError(f'{label}：无效 JSON') from exc
    except ValueError as exc:
        raise ValueError(f'{label}：{exc}') from exc
    validate(record, validator, label)
    return record


def _is_truncated_json(error: json.JSONDecodeError) -> bool:
    """识别记录末尾尚未写完的 JSON token，拒绝明确的语法损坏。"""
    text = error.doc.rstrip()
    if not text.lstrip().startswith('{'):
        return False
    if error.msg.startswith('Unterminated string'):
        return True
    if error.pos >= len(text):
        return True
    tail = text[error.pos :]
    if error.msg == 'Expecting value':
        return tail in {
            'n',
            'nu',
            'nul',
            't',
            'tr',
            'tru',
            'f',
            'fa',
            'fal',
            'fals',
            '-',
        }
    if error.msg == "Expecting ',' delimiter":
        return tail in {'.', 'e', 'E', 'e+', 'e-', 'E+', 'E-'}
    if error.msg == 'Invalid \\uXXXX escape':
        return re.fullmatch(r'u[0-9a-fA-F]{0,3}', tail) is not None
    return False
