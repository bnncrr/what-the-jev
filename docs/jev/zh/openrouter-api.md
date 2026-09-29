# OpenRouter Decisions API

OpenRouter 上的 Jev。两个接口面共用同一个 OpenRouter API key，计入同一账户，无需 TypeSafe 账号、候补名单或单独注册。密钥只保留在服务端。

以下内容于 2026-09-26 依据 Jev 1.13（`typesafe/jev-1.13-20260917`）核对。

## 两个接口面

| 接口面 | 地址 | 用途 |
| --- | --- | --- |
| Decisions API | `POST https://openrouter.ai/api/alpha/decisions` | 任意语言直接发 HTTP，或使用 OpenRouter 决策 SDK |
| System One API | `POST https://openrouter.ai/api/v1/systemone` | 官方 TypeSafe JS/Python SDK，base URL 设为 `https://openrouter.ai/api` |

两者共用同一个 key 与计费。

```
POST https://openrouter.ai/api/alpha/decisions
Authorization: Bearer $OPENROUTER_API_KEY
Content-Type: application/json
```

模型 ID：`typesafe/jev-1.13`，或别名 `~typesafe/jev-latest`。响应会回显带日期的快照，如 `typesafe/jev-1.13-20260917`。当阈值针对某个具体版本调过时，固定使用带版本的 ID。

## 请求

必填字段：`model`、`state`、`questions`。

```json
{
  "model": "~typesafe/jev-latest",
  "state": {"ticket": "同一笔订单被扣款两次。"},
  "questions": {
    "category": {"type": "choice", "instructions": "按诉求分类。",
      "criteria": {"billing": "扣款或退款。", "other": "其他。"}},
    "refund": {"type": "noul", "instructions": "是否要求退款？",
      "criteria": {"true": "明确要求。", "false": "没有要求。"}},
    "urgency": {"type": "score", "instructions": "按影响判断。",
      "criteria": ["可以等待。", "近期处理。", "立即处理。"]}
  }
}
```

| 字段 | 类型 | 必填 |
| --- | --- | --- |
| `model` | 字符串 | 是 |
| `state` | 字符串、对象或数组 | 是 |
| `questions` | 对象，问题名 → 问题 | 是 |
| `provider` | 对象，路由偏好 | 否 |
| `session_id` | 字符串，≤ 256 字符，用于关联同组请求 | 否 |
| `user` | 字符串，≤ 256 字符 | 否 |
| `trace` | 对象，可观测性元数据 | 否 |

各问题类型：

| `type` | `instructions` | `criteria` |
| --- | --- | --- |
| `choice` | 必填；字符串、对象或数组 | 对象：选项名 → 说明（字符串、对象、数组或 null） |
| `noul` | 必填 | 含 `true` 与 `false` 两个键的对象，值为字符串、对象或数组。OpenRouter 参考中列为可选，仅用于描述 |
| `score` | 必填 | 数组，至少一项；由低到高排列 |

问题名自定义，`answers` 使用同样的键返回。

## 响应

```json
{
  "id": "gen-dec-1790015143-AIaTutprXsJ5EwohRSjb",
  "model": "typesafe/jev-1.13-20260917",
  "provider": "TypeSafe",
  "answers": {
    "category": {"type": "choice", "choice": "billing", "confidence": 0.67,
      "probabilities": {"billing": 0.78, "other": 0.22}},
    "refund": {"type": "noul", "noul": 0.96},
    "urgency": {"type": "score", "score": 1.99, "confidence": 0.99,
      "probabilities": {"0": 0, "1": 0, "2": 1},
      "legend": {"0": "可以等待。", "1": "近期处理。", "2": "立即处理。"}}
  },
  "usage": {"input_tokens": 476, "output_tokens": 70, "cost": 1.9992e-05}
}
```

| 答案 | 必有 | 可选 |
| --- | --- | --- |
| `choice` | `type`、`choice` | `confidence`、`probabilities` |
| `noul` | `type`、`noul` | — |
| `score` | `type`、`score` | `confidence`、`probabilities`、`legend` |

`probabilities` 的键在 `choice` 中是选项名，在 `score` 中是字符串形式的等级索引，值之和为 1。`legend` 把每个等级索引映射回判定标准文本。各数值含义见[读取答案](using-jev.md#读取答案)。

## 错误

错误返回 `{"error": {"code", "message", "metadata?"}}`。

| 状态码 | 含义 |
| --- | --- |
| 400 | 参数非法或格式错误 |
| 401 | 密钥缺失或无效 |
| 402 | 余额或配额不足 |
| 403 | 已认证但无权限 |
| 404 | 资源不存在 |
| 413 | 请求体超出大小限制 |
| 429 | 触发限流 |
| 500 | 服务端异常 |
| 502 / 503 | 上游或供应商故障 |
| 524 / 529 | 供应商超时或过载 |

## SDK

- `curl`、`requests` 或任意 HTTP 客户端，如上。
- OpenRouter 决策 SDK：TypeScript、Python、Go。
- 官方 TypeSafe SDK：把 JS 或 Python SDK 的 `base_url` 指向 `https://openrouter.ai/api` 即可。

## 费用

输入 token 计费，输出 token 免费。每百万输入 token 0.042 美元；`usage.cost` 为该次调用费用（美元）。一次三问题的工单调用约 0.00002 美元。
