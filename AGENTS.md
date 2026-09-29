# AGENTS.md

本仓库用 `decision-models` 框架对 Jev 决策模型跑单轮决策实验：给定数据集逐样本请求，保存完整响应，再据此写报告。

## 知识来源

| 内容 | 位置 |
| --- | --- |
| Jev 是什么、回答方式、能力边界、计费 | `docs/jev/zh/what-is-jev.md` |
| 提问设计、答案读取、阈值 | `docs/jev/zh/using-jev.md` |
| 请求与响应字段、错误码 | `docs/jev/zh/openrouter-api.md` |
| 实验 README 写法 | `.claude/rules/experiment-readme.md` |
| 报告写法 | `.claude/rules/report-content.md` |

`docs/jev/en/` 是同一组文档的英文版。

## 代码架构

入口为 `run.py`，主体在 `src/decision_models/`。

| 模块 | 职责 |
| --- | --- |
| `run.py` | 命令行入口：`python run.py [config.yaml]`，省略参数时用 `example/ticket-triage/config.yaml` |
| `config.py` | 读取并校验 `config.yaml` |
| `data.py` | 按 `schema/dataset.schema.json` 校验数据集，返回样本列表 |
| `client.py` | 发送一次 HTTP POST，返回状态码与响应文本；不解析业务答案，不重试 |
| `results.py` | 结果文件的加锁、追加、历史记录校验与尾部残行修复 |
| `runner.py` | 编排：并发调度、写入结果、进度与汇总 |
| `json_utils.py` | 严格 JSON 解析（拒绝重复字段与 NaN/Infinity）与 schema 校验 |
| `logger.py` | 命令行日志初始化 |

数据流：`config.yaml` → `data/dataset.json` → 逐样本 POST `endpoint` → `result/*.jsonl`。

## 配置

`config.yaml` 字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `model` | 是 | 模型 ID，如 `typesafe/jev-1.13` |
| `endpoint` | 是 | 请求地址，如 `https://openrouter.ai/api/alpha/decisions` |
| `data` | 是 | 数据集路径，相对配置文件所在目录；可为路径列表（如双语 `dataset_zh.json` 与 `dataset_en.json`），此时与 `output` 列表一一对应 |
| `output` | 是 | 结果路径，必须以 `.jsonl` 结尾，相对配置文件所在目录；`data` 为列表时必须为与其等长的列表，路径不得重复 |
| `concurrency` | 否 | 初始并发度，取 1 到 16，默认 4 |
| `repeat` | 否 | 重复轮数，不小于 1，默认 1；大于 1 时结果写为 `responses_1.jsonl`、`responses_2.jsonl` 等 |

配置字段多于或少于上述集合即报错：必填四项必须齐全，可选项只能加 `concurrency` 与 `repeat`。

`OPENROUTER_API_KEY` 从环境变量读取，未设置时报错。

## 运行

```bash
export OPENROUTER_API_KEY='<key>'
python run.py experiments/<name>/config.yaml
```

- 一条样本每轮只请求一次；重跑时已成功的记录跳过。
- 上一次运行留下的失败记录在下次运行时清理并重新请求；本次运行内的失败记录留在结果文件里。
- 结果文件被其他运行占用时报错退出。
- 并发度按成功加一、失败减半调整，上限 16。
- 中断时停止提交新请求，等待在途请求写入，文件尾部保持可续跑。

## 数据与结果格式

`data/dataset.json`（`schema/dataset.schema.json`）：

- 顶层只有 `schema_version`（固定为 `1`）与 `samples`。
- 每个样本含 `id`（非空字符串，数据集内唯一）与 `input`；`input` 含 `state` 与 `questions`。
- `questions` 是问题名到问题对象的映射，每个问题的 `type` 取 `noul`、`choice`、`score`。`type` 为 `choice` 时必须给出 `instructions` 与 `criteria`。
- 样本可另有 `reference` 与 `metadata`。

发往 `endpoint` 的请求体由 `model` 与样本的 `input` 合并而成；`id`、`reference`、`metadata` 不发送。

`result/*.jsonl`（`schema/result.schema.json`）：每行一条 `{"id": ..., "response": ..., "error": ...}`。`response` 是 `endpoint` 返回的完整 JSON，未经解析改写；`error` 为 `null` 或 `{"type": ..., "message": ...}`，`type` 取 `network`、`http`、`invalid_json`，`http` 另带 `status`。

## 目录约定

```
experiments/<name>/          正式实验
example/<name>/              带 README 的小样本示例
├── config.yaml              运行配置
├── data/dataset.json        送入模型的样本
├── preparation/             原始数据与准备脚本，可缺省
│   ├── raw/                 下载的原始数据
│   └── code/                清洗与构造脚本
├── result/responses.jsonl   结果
└── report/                  报告，可缺省
```

`docs/jev/` 是 Jev 知识库，`.claude/rules/` 是写作规范。`.file/` 是本地工作区，不入库。

## 测试

```bash
PYTHONPATH=src python -m pytest tests
```

覆盖配置校验、并发调度、结果文件校验与尾部修复、日志初始化。
