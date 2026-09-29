"""通过配置路径启动单轮决策实验。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))

from decision_models.logger import configure_logging  # noqa: E402
from decision_models.runner import run  # noqa: E402

CONFIG = ROOT / 'example/ticket-triage/config.yaml'


def main() -> None:
    """直接改 CONFIG，或提供一个实验配置路径。"""
    if len(sys.argv) > 2:
        raise SystemExit('用法：python run.py [config.yaml]')
    configure_logging()
    run(sys.argv[1] if len(sys.argv) == 2 else CONFIG)


if __name__ == '__main__':
    main()
