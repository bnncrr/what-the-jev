"""把数据集的乘客记录改写为一段文本描述，另存为 data/dataset.text.json。

在 prepare_data.py 产出的 data/dataset.json 上运行，不改动后者。
两份数据集的 id、问题、判据、真实结局与 metadata 逐字相同，只有 state 的形态不同：
dataset.json 是乘客字段对象加字段注释，本脚本产出的是同一批字段写成的一段文本。
字段与措辞一一对应，不多不少；字段缺失时在句子里写明，等价于 null。

写法参照 household_module_prompt_gen.py：模块级模板 + create_mapping_rules() 对照表，
先把字段解码成占位符的值，再用 str.format 填入模板。

用法：python render_text.py
"""

import json
from pathlib import Path
from typing import Any

PREPARATION = Path(__file__).resolve().parents[1]
SOURCE_PATH = PREPARATION.parent / 'data/dataset.json'
TARGET_PATH = PREPARATION.parent / 'data/dataset.text.json'

TEMPLATE = (
    'The passenger is {NAME}, {AGE_SEX} travelling in {CLASS} class with {COMPANIONS}. '
    'The ticket number is {TICKET}, and the fare paid is {FARE}. {CABIN} {BOARDING}'
)


def create_mapping_rules() -> dict[str, dict[Any, str]]:
    """各字段取值到措辞的对照表。"""
    return {
        'PCLASS': {1: 'first', 2: 'second', 3: 'third'},
        'EMBARKED': {'S': 'Southampton', 'C': 'Cherbourg', 'Q': 'Queenstown'},
    }


def format_number(value: float) -> str:
    """按原值写出数字，整数不带小数点。"""
    return repr(value).removesuffix('.0')


def format_age_sex(age: float | None, sex: str) -> str:
    """写出年龄与性别，年龄缺失写「of unrecorded age」。"""
    if age is None:
        return f'a {sex} of unrecorded age'
    return f'a {format_number(age)}-year-old {sex}'


def format_companions(sibsp: int, parch: int) -> str:
    """写出同行的兄弟姐妹、配偶与父母、子女。"""
    return f'{_format_sibling(sibsp)} and {_format_child(parch)}'


def _format_sibling(count: int) -> str:
    """写出同行的兄弟姐妹或配偶数。"""
    if count == 0:
        return 'no siblings or spouses'
    return f'{count} sibling or spouse' if count == 1 else f'{count} siblings or spouses'


def _format_child(count: int) -> str:
    """写出同行的父母或子女数。"""
    if count == 0:
        return 'no parents or children'
    return f'{count} parent or child' if count == 1 else f'{count} parents or children'


def format_cabin(cabin: str | None) -> str:
    """写出客舱号，缺失写未记录。"""
    if cabin is None:
        return 'No cabin number is recorded.'
    numbers = cabin.split()
    if len(numbers) == 1:
        return f'The cabin number is {numbers[0]}.'
    return f'The cabin numbers are {cabin}.'


def build_values(passenger: dict[str, Any], mappings: dict[str, dict[Any, str]]) -> dict[str, str]:
    """把一条乘客记录解码成模板占位符的值。"""
    fare = passenger['Fare']
    return {
        'NAME': passenger['Name'],
        'AGE_SEX': format_age_sex(passenger['Age'], passenger['Sex']),
        'CLASS': mappings['PCLASS'][passenger['Pclass']],
        'COMPANIONS': format_companions(passenger['SibSp'], passenger['Parch']),
        'TICKET': passenger['Ticket'],
        'FARE': format_number(fare),
        'CABIN': format_cabin(passenger['Cabin']),
        'BOARDING': (
            f"The passenger boarded the ship at {mappings['EMBARKED'][passenger['Embarked']]}."
            if passenger['Embarked'] is not None
            else 'The port of embarkation is not recorded.'
        ),
    }


def render_passenger(passenger: dict[str, Any]) -> str:
    """把一条乘客记录写成一段文本描述。"""
    return TEMPLATE.format(**build_values(passenger, create_mapping_rules()))


def render_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """把一条样本的 state 换成乘客记录的文本描述，其余字段原样保留。"""
    return {
        **sample,
        'input': {
            **sample['input'],
            'state': render_passenger(sample['input']['state']['passenger']),
        },
    }


def load_dataset(path: Path) -> dict[str, Any]:
    """读取数据集。"""
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, value: Any) -> None:
    """写出 JSON，保留非 ASCII 字符与键序。"""
    with path.open('w', encoding='utf-8') as file:
        json.dump(value, file, ensure_ascii=False, indent=2, allow_nan=False)
        file.write('\n')


def main() -> None:
    """改写 state 为文本，另存为文本版数据集。"""
    dataset = load_dataset(SOURCE_PATH)
    samples = [render_sample(sample) for sample in dataset['samples']]
    write_json(TARGET_PATH, {'schema_version': dataset['schema_version'], 'samples': samples})
    print(f'输入 {SOURCE_PATH}：{len(dataset["samples"])} 条')
    print(f'输出 {TARGET_PATH}：{len(samples)} 条')
    print(f'\n{samples[0]["input"]["state"]}')


if __name__ == '__main__':
    main()
