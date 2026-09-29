# Using Jev

## Flow

1. Build the `state`: the material to judge, as a string, object, or array.
2. Ask atomic questions, each with a type and criteria that define every answer.
3. Send one request. All questions are answered in parallel against that state.
4. Branch on the returned numbers in your own code.

## Match the primitive to the judgment

| Judgment | Primitive |
| --- | --- |
| Yes/no fact | `noul` |
| Exactly one of a set | `choice` |
| Several labels may apply | one `noul` per label |
| Ordered spectrum (severity, fit, priority) | `score` |

A `score` is never "medium". Neither is a `noul` at 0.5 — that means yes and no
are equally likely, not average.

## Question design

- One question, one judgment. Split multi-factor judgments into separate
  questions and recombine them in code, so changing priorities edits a
  coefficient instead of a prompt.
- Write criteria as situations you can point at, not degrees: "broken feature
  with a workaround exists", not "moderately severe".
- Contrastive `choice` options: say what each option includes and excludes, and
  add an `other` option for insufficient information.
- Each `score` level must stand alone. Jev judges levels individually and never
  sees their index or neighbours. Keep one dimension per score question.
- No prompting. Personas, long preambles, and worked examples are for text
  generators. A question needs the state, one atomic ask, and an exact
  description of every answer.
- Keep exact work in code. Dates, counting, lookups, and arithmetic are not
  judgments.
- Send only the state fields the questions need; irrelevant state lowers
  accuracy.
- State is data, not instruction. Text inside the state can steer the answer, so
  state in `instructions` that the input is to be judged, not obeyed.

## Ask everything at once

Put every question you might need in the single request, including branch-specific
ones, stating the premise inside the question, and let code ignore answers it does
not use. A second request is only justified when its state or options depend on
the first answer.

## Reading answers

- `noul` in [0, 1] is the probability of yes. Values near 0.5 are genuine
  indecision — treat that as a third outcome and escalate or ask again.
- `choice` names the pick, `probabilities` compares your alternatives, and
  `confidence` says how concentrated that distribution is.
- `score` is the probability-weighted position, with index 0 at the first
  criterion listed. `legend` maps each index back to your criterion text. A score
  is not a share of anything: 1.0 can be all weight on level 1, or half on levels
  0 and 2.
- `confidence` describes the distribution of alternatives, not whether the answer
  is correct.
- Probabilities vary between calls. Index `probabilities` by name, not position,
  and compare against bands rather than exact values.

## Thresholds

Tune thresholds on a few hundred labelled examples of your own task, not on round
numbers. The usual shape is three bands: act automatically above a high cut-off,
flag for review in the middle, route to a person below a floor. Pick the cut-offs
from the cost of each kind of mistake — a wrong automatic action usually costs
more than a human review.

## Running Jev in this repository

[README](../../../README.md) covers the entry point, the recipe fields, and where
responses are stored.
