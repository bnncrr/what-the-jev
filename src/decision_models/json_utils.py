"""JSON 数值、字段唯一性与 schema 校验。"""

import json
import math
from collections.abc import Iterable
from pathlib import Path
from typing import Any, NoReturn, TypeAlias

from jsonschema import Draft202012Validator

JSONValue: TypeAlias = (
    str | int | float | bool | None | list['JSONValue'] | dict[str, 'JSONValue']
)


def reject_constant(value: str) -> NoReturn:
    """拒绝 JSON 标准之外的 NaN 和 Infinity。"""
    raise ValueError(f'非法 JSON 数值：{value}')


def unique_keys(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    """拒绝重复字段，避免静默丢失输入。"""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'重复 JSON 字段：{key}')
        result[key] = value
    return result


def _finite_float(value: str) -> float:
    """解析可用有限浮点数表示的 JSON 数值。"""
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f'JSON 数值超出浮点范围：{value}')
    return number


def loads(text: str) -> Any:
    """解析 JSON，拒绝重复字段和无法安全序列化的数值。"""
    return json.loads(
        text,
        parse_constant=reject_constant,
        parse_float=_finite_float,
        object_pairs_hook=unique_keys,
    )


def load_validator(path: Path) -> Draft202012Validator:
    """从本地 schema 创建校验器。"""
    return Draft202012Validator(loads(path.read_text(encoding='utf-8')))


def validate(data: Any, validator: Draft202012Validator, label: str) -> None:
    """校验数据并在首个错误中包含字段位置。"""
    error = next(validator.iter_errors(data), None)
    if error is not None:
        location = '.'.join(str(part) for part in error.absolute_path) or '$'
        raise ValueError(f'{label} {location}: {error.message}')
