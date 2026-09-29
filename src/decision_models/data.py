"""最终输入数据的读取与校验。"""

from pathlib import Path
from typing import Any

from .json_utils import load_validator, loads, validate
from .json_utils import reject_constant as reject_constant
from .json_utils import unique_keys as unique_keys

SCHEMA = Path(__file__).resolve().parents[2] / 'schema/dataset.schema.json'


def load_dataset(path: str | Path) -> list[dict[str, Any]]:
    """校验完整数据集后返回样本，不读取原始材料。"""
    data = loads(Path(path).read_text(encoding='utf-8'))
    validate(data, load_validator(SCHEMA), '数据格式错误')
    ids = set()
    for sample in data['samples']:
        if sample['id'] in ids:
            raise ValueError(f'重复样本 ID：{sample["id"]}')
        ids.add(sample['id'])
    return data['samples']
