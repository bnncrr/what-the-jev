"""清理数据集：剔出材料与设问不对应的题，另存为 data/dataset.cleaned.json。

在 prepare_data.py 产出的 data/dataset.json 上运行，不改动后者。实验与报告用的是
本脚本产出的数据集，config.yaml 的 data 字段指向它。

剔除判据：逐题比对材料（state 中设问之前的部分，含材料末尾的出处）与设问所指对象。
设问指向的材料内容不在所给材料之内，或材料与设问互不相干，即为材料与设问不对应。
按此判据分两层：

    第 1 层：按题面无法作答——设问指向所引文件、节选序号、图表或作者，而这些内容
            不在所给材料之内，或材料与选项分属两道题；
    第 2 层：材料与设问互不相干——设问可独立作答，但所给材料不构成该题的判断依据。

逐题层级与理由记在 EXCLUDED_ITEMS。剔出的题不写进产出的数据集，实验中不留其副本。

用法：python clean_data.py
"""

import json
from pathlib import Path
from typing import Any

SUBJECT = 'high_school_us_history'
DATA_DIR = Path(__file__).resolve().parents[2] / 'data'
SOURCE_PATH = DATA_DIR / 'dataset.json'
CLEANED_PATH = DATA_DIR / 'dataset.cleaned.json'

# 题号后缀 → (层级, 理由)。理由只记可从题面直接核对的事实：设问指向的材料内容及其有无。
EXCLUDED_ITEMS = {
    '0018': (1, '材料第三段只留出处「U.S. Representative John Conyers, … Hearing Before '
                'the Committee on the Judiciary … 1993」，正文缺失，而设问专指该段所举的 '
                '“Wounded Knee”。'),
    '0022': (1, '材料为 Col. Samuel Thomas 1865 年的国会证词，设问问的是 Hamilton 在 '
                'Federalist #15 中认定的问题来源，而材料中没有 Federalist #15。'),
    '0033': (2, '材料为马丁·路德·金 1963 年《伯明翰狱中书信》，设问问的是 Susan B. Anthony '
                '对哪一修正案获批有影响，与材料没有对应关系。'),
    '0044': (1, '材料为 Col. Samuel Thomas 1865 年的证词，设问问的是 Hamilton 为应对 '
                'Federalist #15 所指问题提出的方案，而材料中没有 Federalist #15。'),
    '0049': (2, '材料为 Susan B. Anthony 1873 年的演说，设问问的是哪一法案「不是」为管制'
                '工业家的财富与权力而设，与材料没有对应关系。'),
    '0071': (1, '材料为马丁·路德·金 1963 年《伯明翰狱中书信》，设问中「written here by '
                'Susan B. Anthony」的 here 指材料，而材料并非 Anthony 所写。'),
    '0097': (2, '材料为 Benjamin Franklin 1766 年关于《印花税法》的质询陈述，设问问的是 '
                'Jackson 的政策后来被哪一法案改变，与材料没有对应关系。'),
    '0105': (1, '材料为马丁·路德·金 1963 年《伯明翰狱中书信》，设问问的是 Susan B. Anthony '
                '的诉求依据的是哪一文件，而材料中没有 Anthony 的文本。'),
    '0115': (2, '材料为 Andrew Jackson 1832 年否决合众国银行续期法案的咨文，设问问的是 '
                '1824 年大选为何成为总统政治的转折点，与材料没有对应关系。'),
    '0116': (2, '材料与 0018 同源，第三段只留 Conyers 1993 年听证会的出处、正文缺失；'
                '设问问的是三段引文整体支持哪一推断，缺一段仍可作答，但材料不完整。'),
    '0117': (1, '材料标注为马丁·路德·金 1963 年《伯明翰狱中书信》，设问却称「this passage '
                'by Susan B. Anthony」。按设问所指 Anthony 的语境标准答案成立，按实际材料'
                '模型所选也有依据，考查对象无法确定。'),
    '0119': (1, '材料为 Susan B. Anthony 1873 年的演说，设问问的是「this cartoon」中对 '
                'Andrew Carnegie 的批评，而材料中没有漫画。'),
    '0127': (1, '材料为 Benjamin Franklin 1766 年关于《印花税法》的陈述，设问「The policy '
                'described most immediately led to」的四个选项却全部关于印第安人迁移，'
                '材料与选项分属两题。'),
    '0130': (1, '材料为 Col. Samuel Thomas 1865 年的证词，设问问的是何种情绪促成了 '
                'Federalist #15 中的看法，而材料中没有 Federalist #15。'),
    '0171': (1, '材料为 Susan B. Anthony 1873 年的演说，设问中「another common criticism of '
                'Andrew Carnegie」的 another 指向上一题的漫画，该漫画与 Carnegie 均不在'
                '材料之内。'),
    '0176': (1, '材料为 Andrew Jackson 1829 年关于印第安人迁移的咨文，设问问的是从该引文'
                '可以推断马丁·路德·金的努力如何，问的是材料中没有的 1950 年代民权运动。'),
}


def full_id(suffix: str) -> str:
    """把题号后缀（如 0018）写成数据集里的完整 id。"""
    return f'{SUBJECT}-{suffix}'


def load_dataset(path: Path) -> dict[str, Any]:
    """读取数据集。"""
    return json.loads(path.read_text(encoding='utf-8'))


def drop_excluded(dataset: dict[str, Any]) -> dict[str, Any]:
    """按 EXCLUDED_ITEMS 剔出材料与设问不对应的题，返回留下的数据集。

    清单与数据集必须一一对上：清单里的题号都要在数据集中出现，不能被静默忽略。
    """
    excluded = {full_id(suffix) for suffix in EXCLUDED_ITEMS}
    missing = excluded - {sample['id'] for sample in dataset['samples']}
    if missing:
        raise ValueError(
            f'输入数据集里没有这些题号：{sorted(missing)}；'
            '它可能已经清理过，或不是 prepare_data.py 的产出。'
        )
    kept = [sample for sample in dataset['samples'] if sample['id'] not in excluded]
    return {'schema_version': dataset['schema_version'], 'samples': kept}


def write_json(path: Path, value: Any) -> None:
    """写出 JSON，保留非 ASCII 字符与键序。"""
    with path.open('w', encoding='utf-8') as file:
        json.dump(value, file, ensure_ascii=False, indent=2, allow_nan=False)
        file.write('\n')


def main() -> None:
    """清理数据集，另存为清理后的数据集。"""
    dataset = load_dataset(SOURCE_PATH)
    cleaned = drop_excluded(dataset)
    write_json(CLEANED_PATH, cleaned)
    by_tier: dict[int, list[str]] = {}
    for suffix, (tier, _) in EXCLUDED_ITEMS.items():
        by_tier.setdefault(tier, []).append(suffix)
    print(f'输入 {SOURCE_PATH}：{len(dataset["samples"])} 条')
    print(f'剔出 {len(EXCLUDED_ITEMS)} 条：{" ".join(sorted(EXCLUDED_ITEMS))}')
    for tier in sorted(by_tier):
        print(f'  第 {tier} 层 {len(by_tier[tier])} 条：{" ".join(sorted(by_tier[tier]))}')
    print(f'输出 {CLEANED_PATH}：{len(cleaned["samples"])} 条')


if __name__ == '__main__':
    main()
