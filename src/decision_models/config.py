"""实验配置加载与字段校验。"""

from pathlib import Path
from typing import TypedDict

import yaml

REQUIRED_FIELDS = {'model', 'endpoint', 'data', 'output'}
DEFAULT_CONCURRENCY = 4
MAX_CONCURRENCY = 16
DEFAULT_REPEAT = 1


class RunConfig(TypedDict):
    """已通过校验的运行配置。"""

    model: str
    endpoint: str
    data: str | list[str]  # 多个数据文件时与 output 一一对应，便于双语并行
    output: str | list[str]  # repeat 大于 1 时展开为逐轮结果文件路径
    concurrency: int  # 初始并发度；运行中按成败动态调整，上限 MAX_CONCURRENCY
    repeat: int  # 重复运行轮数，每轮写入独立的结果文件


def load_config(path: Path) -> RunConfig:
    """读取配置并校验字段，保留相对于配置目录的路径。"""
    config = yaml.safe_load(path.read_text(encoding='utf-8'))
    optional = {'concurrency', 'repeat'}
    if not isinstance(config, dict) or set(config) - optional != REQUIRED_FIELDS:
        raise ValueError(
            f'配置字段必须为：{sorted(REQUIRED_FIELDS)}，可另加 concurrency、repeat'
        )
    for name in ('model', 'endpoint'):
        value = config[name]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'配置 {name} 必须为非空字符串')
    datas = _paths(config['data'], 'data')
    outputs = _paths(config['output'], 'output')
    if any(Path(name).suffix != '.jsonl' for name in outputs):
        raise ValueError('output 必须为 .jsonl 文件路径')
    if len(datas) > 1 and len(outputs) != len(datas):
        raise ValueError('data 为多个文件时，output 必须为与其等长的列表')
    if len(set(outputs)) != len(outputs):
        raise ValueError('output 路径不得重复')
    config['data'] = datas[0] if len(datas) == 1 else datas
    config['concurrency'] = _concurrency(config.get('concurrency'))
    config['repeat'] = _repeat(config.get('repeat'))
    if config['repeat'] > 1:
        expanded = [
            _repeat_outputs(name, config['repeat'])
            for name in outputs
        ]
        config['output'] = [
            name for names in expanded for name in names
        ]
    else:
        config['output'] = outputs[0] if len(outputs) == 1 else outputs
    return config


def _paths(value: object, name: str) -> list[str]:
    """校验路径字段：单个非空字符串，或全为非空字符串的列表。"""
    if isinstance(value, str) and value.strip():
        return [value]
    if isinstance(value, list) and value:
        items: list[str] = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f'配置 {name} 必须为非空字符串或非空字符串列表')
            items.append(item)
        return items
    raise ValueError(f'配置 {name} 必须为非空字符串或非空字符串列表')


def _concurrency(value: object) -> int:
    """校验初始并发度；未指定时使用默认值，运行中按成败动态调整。"""
    if value is None:
        return DEFAULT_CONCURRENCY
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= MAX_CONCURRENCY
    ):
        raise ValueError(f'配置 concurrency 必须为 1 到 {MAX_CONCURRENCY} 之间的整数')
    return value


def _repeat(value: object) -> int:
    """校验重复运行轮数；未指定时运行一次。"""
    if value is None:
        return DEFAULT_REPEAT
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError('配置 repeat 必须为不小于 1 的整数')
    return value


def _repeat_outputs(output: str, repeat: int) -> list[str]:
    """按轮次展开结果文件路径，序号从 1 开始，如 responses_1.jsonl。"""
    base = Path(output)
    return [
        str(base.with_name(f'{base.stem}_{index}{base.suffix}'))
        for index in range(1, repeat + 1)
    ]
