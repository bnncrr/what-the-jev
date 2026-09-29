"""下载 Hugging Face GPQA leaderboard 聚合结果，保存为最新快照。

数据源是 Hub 的聚合接口，由各模型仓库的 .eval_results/ 与社区 PR 汇总而成，
内容随时间变化、无法固定 revision。固定写到 leaderboard-latest.json，重跑即
覆盖，始终只保留最新一份；历史版本由 git 记录。

eval.yaml 定义了 diamond、main、extended 三个任务。接口不带 task_id 时返回
diamond 的结果（已与 ?task_id=diamond 全量比对一致）；按任务切换用查询参数
?task_id=diamond|main|extended，当前各任务收录数约为 111、7、0。
"""

import json
from pathlib import Path
from typing import Any
from urllib.request import urlopen

URL = 'https://huggingface.co/api/datasets/Idavidrein/gpqa/leaderboard'
PREPARATION = Path(__file__).resolve().parents[1]
RAW_PATH = PREPARATION / 'raw/leaderboard-latest.json'
EXPECTED_FIELDS = {'modelId', 'value'}


def fetch_leaderboard() -> list[dict[str, Any]]:
    """下载 leaderboard 聚合 JSON，核对基本结构。"""
    with urlopen(URL, timeout=60) as response:
        data = json.load(response)
    if not isinstance(data, list) or not data:
        raise ValueError(f'leaderboard 响应异常：{type(data).__name__}')
    bad = [index for index, row in enumerate(data) if not EXPECTED_FIELDS <= set(row)]
    if bad:
        raise ValueError(f'第 {bad[:3]} 条记录缺少必填字段')
    return data


def write_json(path: Path, value: Any) -> None:
    """写出 JSON，保留非 ASCII 字符与键序。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as file:
        json.dump(value, file, ensure_ascii=False, indent=2, allow_nan=False)
        file.write('\n')


def main() -> None:
    """下载并覆盖写出最新快照。"""
    rows = fetch_leaderboard()
    write_json(RAW_PATH, rows)
    print(f'leaderboard {len(rows)} 条：{RAW_PATH}')


if __name__ == '__main__':
    main()
