"""Generate report figures from generated/summary.json.

Produces one figure per language:
  figures/fig_prob_zh.pdf / fig_prob_en.pdf
    Sample counts and accuracy by chosen-probability bin.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent.parent
FIG = BASE / "figures"
SC_OTF = BASE / "generated" / "fonts" / "NotoSansCJKsc-Regular.otf"
SYSTEM_TTC = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")

COLOR_CORRECT = "#4878a8"
COLOR_WRONG = "#d1605e"


def ensure_sc_font():
    """Extract the SC face from the system Noto CJK collection (cached)."""
    if SC_OTF.exists():
        return
    from fontTools.ttLib import TTCollection

    for face in TTCollection(str(SYSTEM_TTC)).fonts:
        name = face["name"].getDebugName(16) or face["name"].getDebugName(1)
        if name == "Noto Sans CJK SC":
            SC_OTF.parent.mkdir(parents=True, exist_ok=True)
            face.save(str(SC_OTF))
            return
    raise RuntimeError(f"Noto Sans CJK SC not found in {SYSTEM_TTC}")

LABELS = {
    "zh": {
        "xlabel": "所选概率",
        "ylabel": "题目数",
        "correct": "答对",
        "wrong": "答错",
        "acc": "准确率",
        "n": "n",
    },
    "en": {
        "xlabel": "Chosen probability",
        "ylabel": "Questions",
        "correct": "Correct",
        "wrong": "Wrong",
        "acc": "Accuracy",
        "n": "n",
    },
}


def draw(lang):
    with open(BASE / "generated" / "summary.json") as f:
        summary = json.load(f)
    bins = summary["chosen_probability"]["bins"]
    t = LABELS[lang]

    if lang == "zh":
        ensure_sc_font()
        fm.fontManager.addfont(str(SC_OTF))
        plt.rcParams["font.family"] = ["Noto Sans CJK SC"]
    else:
        plt.rcParams["font.family"] = ["DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    names = [b["bin"] for b in bins]
    correct = [b["correct"] for b in bins]
    wrong = [b["n"] - b["correct"] for b in bins]
    total = [b["n"] for b in bins]
    acc = [100 * b["accuracy"] for b in bins]

    x = range(len(bins))
    fig, ax = plt.subplots(figsize=(3.3, 2.5))
    ax.bar(x, correct, width=0.62, color=COLOR_CORRECT, label=t["correct"])
    ax.bar(x, wrong, width=0.62, bottom=correct, color=COLOR_WRONG,
           label=t["wrong"])

    for i in x:
        ax.text(i, total[i] + 4, f"{acc[i]:.0f}%", ha="center",
                va="bottom", fontsize=7.5)

    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{name}\n{t['n']}={tot}" for name, tot in
                        zip(names, total)], fontsize=7.2)
    ax.tick_params(axis="x", length=0)
    ax.tick_params(axis="y", labelsize=7.5)
    ax.set_xlabel(t["xlabel"], fontsize=8.5, labelpad=6)
    ax.set_ylabel(t["ylabel"], fontsize=8.5)
    ax.set_ylim(0, 160)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=7.5, loc="upper left",
              handlelength=1.1, handleheight=0.9)

    fig.tight_layout(pad=0.4)
    FIG.mkdir(exist_ok=True)
    fig.savefig(FIG / f"fig_prob_{lang}.pdf")
    plt.close(fig)


if __name__ == "__main__":
    draw("zh")
    draw("en")
    print("figures written to", FIG)
