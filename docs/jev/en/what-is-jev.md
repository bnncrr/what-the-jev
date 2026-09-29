# What Jev Is

Jev is a decision model from TypeSafe, the first of its "System One" models. It
reads natural language but generates no text: given a state and typed questions,
it returns typed answers with calibrated probabilities that code branches on
directly. Model ID `typesafe/jev-1.13`, moving alias `~typesafe/jev-latest`.

## A decision model, not a chat model

| | Chat LLM | Jev |
| --- | --- | --- |
| Input | messages | `state` + `questions` |
| Output | generated tokens | one typed answer per question |
| Shape | parse the text and validate | always one of your options or a probability |
| Uncertainty | implied by the wording | numeric, per answer |
| Media | text, images, audio, video | text only |

Both read natural language; the split is entirely on the output side. Use Jev
when the answer you want fits an enum, a boolean, or a number. Use an LLM when
words are the output. In practice they combine: Jev routes and verifies, the LLM
writes the language.

## Primitives

Three question types, mixable in one request.

| `type` | Asks | Answer fields |
| --- | --- | --- |
| `noul` | Does this condition hold? | `noul` — probability of yes in [0, 1] |
| `choice` | Which one of these options? | `choice`, `probabilities`, `confidence` |
| `score` | Where does this fall on this ordered scale? | `score`, `legend`, `probabilities`, `confidence` |

- `noul` is a Bernoulli check. The probability *is* the answer; there is no
  separate confidence field.
- `choice` picks one of up to 255 named options.
- `score` places the state on an ordered rubric of 2–10 levels, low to high.
  `score` is the probability-weighted mean of the level indices, so it can land
  between levels (1.99 on a three-level rubric sits on the last level).

All questions in a request are answered in parallel against the same state and
cannot see each other's answers. Answers stay inside the options or levels you
supplied.

## Limits

Jev does not do text generation, visible reasoning (no rationale, no chain of
thought), tool calls, conversation, multi-step plans, images/audio/video, exact
arithmetic or date math, or deterministic logic. Keep those in your code or in an
LLM.

Answers stay inside your schema; they can still be wrong. Calibration means a
reported 0.8 is right about 80% of the time across many answers of that kind —
any single answer can be the other 20%.

## Cost and capacity

| Item | Value |
| --- | --- |
| Billing | input tokens only; output tokens are free |
| Price | USD 0.042 per million input tokens |
| Per-call cost | reported in `usage.cost` |
| Context | 32,000 tokens for `state` plus the longest question |
| Input types | string, JSON object, array |
| Weights | proprietary; no published weights or paper |

A three-question ticket call is roughly 450 input tokens, about USD 0.00002.

## Fit

Good at: routing and triage, classification and tagging at scale, gating agent
tool calls on a `noul` threshold, verifying LLM output against policy, ranking
and filtering by score, LLM-as-a-judge.

Weak at: anything whose output is prose, anything needing arithmetic or dates,
anything that should be a database lookup or a regex.
