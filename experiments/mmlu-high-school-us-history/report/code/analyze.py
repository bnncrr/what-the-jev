"""Compute summary statistics for the MMLU high-school US history experiment.

Reads the cleaned dataset and the recorded responses, then writes:
  - generated/summary.json : all statistics used in the report
  - generated/numbers.tex  : LaTeX macros so both report versions share numbers
"""

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
EXP = BASE.parent
OUT = BASE / "generated"

PROB_BINS = [
    ("<0.90", 0.0, 0.90),
    ("0.90–0.94", 0.90, 0.95),
    ("0.95–0.98", 0.95, 0.99),
    ("0.99", 0.99, 0.995),
    ("1.00", 0.995, 1.0000001),
]


def wilson_interval(k, n, z=1.959964):
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return center - half, center + half


def main():
    with open(EXP / "data" / "dataset.cleaned.json") as f:
        samples = {s["id"]: s for s in json.load(f)["samples"]}

    responses = {}
    with open(EXP / "result" / "responses.jsonl") as f:
        for line in f:
            r = json.loads(line)
            assert not r.get("error"), f"error response: {r['id']}"
            responses[r["id"]] = r

    assert set(responses) == set(samples), "response ids do not match dataset ids"

    n = len(responses)
    correct = 0
    model_letters = Counter()
    key_letters = Counter()
    input_tokens = output_tokens = 0
    total_cost = 0.0
    prob_rows = []  # (chosen probability, correct)

    for rid, r in responses.items():
        ans = r["response"]["answers"]["answer"]
        choice = ans["choice"]
        key = samples[rid]["reference"]["answer"]["choice"]
        ok = choice == key
        correct += ok
        model_letters[choice] += 1
        key_letters[key] += 1
        usage = r["response"]["usage"]
        input_tokens += usage["input_tokens"]
        output_tokens += usage["output_tokens"]
        total_cost += usage["cost"]
        prob_rows.append((ans["probabilities"][choice], ok))

    ci_low, ci_high = wilson_interval(correct, n)

    bin_stats = []
    for name, lo, hi in PROB_BINS:
        rows = [(p, ok) for p, ok in prob_rows if lo <= p < hi]
        c = sum(ok for _, ok in rows)
        bin_stats.append(
            {"bin": name, "n": len(rows), "correct": c,
             "accuracy": c / len(rows) if rows else None}
        )

    certain = [(p, ok) for p, ok in prob_rows if p >= 0.995]
    uncertain = [(p, ok) for p, ok in prob_rows if p < 0.995]
    prob_correct = [p for p, ok in prob_rows if ok]
    prob_wrong = [p for p, ok in prob_rows if not ok]
    low_bin = bin_stats[0]

    summary = {
        "model": responses[next(iter(responses))]["response"]["model"],
        "n_samples": n,
        "n_correct": correct,
        "accuracy": correct / n,
        "accuracy_ci95": [ci_low, ci_high],
        "random_baseline": 0.25,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_cost_usd": total_cost,
        "letter_distribution": {
            "model": dict(sorted(model_letters.items())),
            "key": dict(sorted(key_letters.items())),
        },
        "chosen_probability": {
            "mean_correct": sum(prob_correct) / len(prob_correct),
            "mean_wrong": sum(prob_wrong) / len(prob_wrong),
            "n_wrong": len(prob_wrong),
            "at_1_00": {
                "n": len(certain),
                "correct": sum(ok for _, ok in certain),
                "accuracy": sum(ok for _, ok in certain) / len(certain),
            },
            "below_1_00": {
                "n": len(uncertain),
                "correct": sum(ok for _, ok in uncertain),
                "accuracy": sum(ok for _, ok in uncertain) / len(uncertain),
            },
            "bins": bin_stats,
        },
    }

    OUT.mkdir(exist_ok=True)
    with open(OUT / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    pct = lambda x: f"{100 * x:.1f}\\%"
    num = lambda x: f"{x:,}"
    macros = {
        "NumSamples": str(n),
        "NumCorrect": str(correct),
        "AccTotal": pct(correct / n),
        "AccCILow": pct(ci_low),
        "AccCIHigh": pct(ci_high),
        "InputTokens": num(input_tokens).replace(",", "\\thinspace"),
        "OutputTokens": num(output_tokens).replace(",", "\\thinspace"),
        "TotalCost": f"{total_cost:.4f}",
        "NCertain": str(len(certain)),
        "PctCertain": pct(len(certain) / n),
        "AccCertain": pct(sum(ok for _, ok in certain) / len(certain)),
        "NUncertain": str(len(uncertain)),
        "AccUncertain": pct(sum(ok for _, ok in uncertain) / len(uncertain)),
        "MeanProbCorrect": f"{sum(prob_correct) / len(prob_correct):.2f}",
        "MeanProbWrong": f"{sum(prob_wrong) / len(prob_wrong):.2f}",
        "NWrong": str(len(prob_wrong)),
        "LowBinN": str(low_bin["n"]),
        "LowBinCorrect": str(low_bin["correct"]),
        "LowBinAcc": pct(low_bin["accuracy"]),
        "ModelLetterA": str(model_letters["A"]),
        "ModelLetterB": str(model_letters["B"]),
        "ModelLetterC": str(model_letters["C"]),
        "ModelLetterD": str(model_letters["D"]),
        "KeyLetterA": str(key_letters["A"]),
        "KeyLetterB": str(key_letters["B"]),
        "KeyLetterC": str(key_letters["C"]),
        "KeyLetterD": str(key_letters["D"]),
    }
    with open(OUT / "numbers.tex", "w") as f:
        for name, value in macros.items():
            f.write(f"\\newcommand{{\\{name}}}{{{value}}}\n")

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
