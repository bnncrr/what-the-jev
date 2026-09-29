# OpenRouter Decisions API

Jev on OpenRouter. One OpenRouter API key for both surfaces, billed to the same
account; no TypeSafe account, waitlist, or separate signup. Keep the key
server-side.

Verified against Jev 1.13 (`typesafe/jev-1.13-20260917`) on 2026-09-26.

## Surfaces

| Surface | Endpoint | Use |
| --- | --- | --- |
| Decisions API | `POST https://openrouter.ai/api/alpha/decisions` | plain HTTP from any language, or the OpenRouter decision SDKs |
| System One API | `POST https://openrouter.ai/api/v1/systemone` | the official TypeSafe JS/Python SDK, base URL `https://openrouter.ai/api` |

The two surfaces are the same key and the same billing.

```
POST https://openrouter.ai/api/alpha/decisions
Authorization: Bearer $OPENROUTER_API_KEY
Content-Type: application/json
```

Model IDs: `typesafe/jev-1.13` or the alias `~typesafe/jev-latest`. Responses
echo a dated snapshot such as `typesafe/jev-1.13-20260917`. Pin the versioned ID
when thresholds are tuned to one release.

## Request

Required fields: `model`, `state`, `questions`.

```json
{
  "model": "~typesafe/jev-latest",
  "state": {"ticket": "Charged twice for one order."},
  "questions": {
    "category": {"type": "choice", "instructions": "Classify the request.",
      "criteria": {"billing": "Charge or refund.", "other": "Anything else."}},
    "refund": {"type": "noul", "instructions": "Is a refund demanded?",
      "criteria": {"true": "Explicit request.", "false": "None."}},
    "urgency": {"type": "score", "instructions": "Judge impact.",
      "criteria": ["Can wait.", "Handle soon.", "Act now."]}
  }
}
```

| Field | Type | Required |
| --- | --- | --- |
| `model` | string | yes |
| `state` | string, object, or array | yes |
| `questions` | object, question name → question | yes |
| `provider` | object, routing preferences | no |
| `session_id` | string, ≤ 256 chars, groups related requests | no |
| `user` | string, ≤ 256 chars | no |
| `trace` | object, observability metadata | no |

Per question type:

| `type` | `instructions` | `criteria` |
| --- | --- | --- |
| `choice` | required; string, object, or array | object: option key → description (string, object, array, or null) |
| `noul` | required | object with `true` and `false` keys, each string, object, or array. Listed as optional in the OpenRouter reference; description only |
| `score` | required | array, at least one item; ordered low → high |

Question names are yours; `answers` is keyed by the same names.

## Response

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
      "legend": {"0": "Can wait.", "1": "Handle soon.", "2": "Act now."}}
  },
  "usage": {"input_tokens": 476, "output_tokens": 70, "cost": 1.9992e-05}
}
```

| Answer | Required | Optional |
| --- | --- | --- |
| `choice` | `type`, `choice` | `confidence`, `probabilities` |
| `noul` | `type`, `noul` | — |
| `score` | `type`, `score` | `confidence`, `probabilities`, `legend` |

`probabilities` keys are option names for `choice` and level indices as strings
for `score`; the values sum to 1. `legend` maps each level index back to your
criterion text. See [Reading answers](using-jev.md#reading-answers) for what the
numbers mean.

## Errors

Errors return `{"error": {"code", "message", "metadata?"}}`.

| Status | Meaning |
| --- | --- |
| 400 | invalid or malformed parameters |
| 401 | missing or invalid key |
| 402 | insufficient credits or quota |
| 403 | authenticated but not permitted |
| 404 | not found |
| 413 | payload exceeds size limits |
| 429 | rate limit exceeded |
| 500 | unexpected server error |
| 502 / 503 | upstream or provider failure |
| 524 / 529 | provider timeout or overloaded |

## SDKs

- `curl`, `requests`, or any HTTP client, as above.
- OpenRouter decision SDKs: TypeScript, Python, Go.
- Official TypeSafe SDKs: point the JS or Python SDK at OpenRouter with
  `base_url = "https://openrouter.ai/api"`.

## Cost

Input tokens are billed, output tokens are free. USD 0.042 per million input
tokens; `usage.cost` is the cost of that call in USD. A three-question ticket
call costs about USD 0.00002.
