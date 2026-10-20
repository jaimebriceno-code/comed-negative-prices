"""Aggregate the 30 independent AI-agent runs (llm_runs/*.json) into a summary and a chart."""
import glob
import json
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from visualize import SCN_COLOR, INK, INK2, SURF, GRID  # noqa: F401  (also applies rcParams)
from model import SCENARIOS

METRICS = [
    ("world_real_gdp_growth_avg_pct_2027_2031", "World GDP growth, % per year"),
    ("global_unemployment_peak_pct", "Peak global unemployment, %"),
    ("global_public_debt_pct_gdp_2031", "Global public debt 2031, % GDP"),
    ("us_public_debt_pct_gdp_2031", "US public debt 2031, % GDP"),
    ("inflation_peak_pct_g20_avg", "Peak G20 inflation, %"),
    ("social_unrest_0_100", "Social unrest (2026 = 35)"),
    ("trust_in_institutions_0_100", "Trust in institutions (2026 = 40)"),
    ("firms_using_ai_pct_2031", "Firms using AI 2031, %"),
    ("jobs_displaced_by_ai_millions_cumulative", "Jobs displaced by AI, millions"),
    ("trade_fragmentation_0_100", "Trade fragmentation (2026 = 45)"),
    ("renewable_share_electricity_pct_2031", "Renewables, % of electricity"),
    ("warming_2031_c", "Warming 2031, °C"),
]


def load():
    runs = {s: [] for s in SCENARIOS}
    for f in sorted(glob.glob("llm_runs/*.json")):
        d = json.load(open(f))
        runs[d["scenario"]].append(d)
    return runs


def main():
    runs = load()
    summary = {}
    for s, rs in runs.items():
        m = {}
        for k, _ in METRICS:
            v = np.array([float(r["metrics_2031"][k]) for r in rs])
            m[k] = dict(median=float(np.median(v)), min=float(v.min()), max=float(v.max()), values=v.tolist())
        ineq = {}
        for r in rs:
            ineq[r["metrics_2031"]["income_inequality_change"]] = ineq.get(r["metrics_2031"]["income_inequality_change"], 0) + 1
        summary[s] = dict(n=len(rs), metrics=m, inequality=ineq,
                          conflicts=float(np.median([r["metrics_2031"]["major_new_conflicts"] for r in rs])),
                          debt_crises=float(np.median([r["metrics_2031"]["sovereign_debt_crises"] for r in rs])),
                          headlines=[r["headline"] for r in rs],
                          wildcards=[r["wildcard"] for r in rs],
                          images=[r["image_description"] for r in rs],
                          winners=[w for r in rs for w in r["winners"]],
                          losers=[w for r in rs for w in r["losers"]])
    json.dump(summary, open("agents_summary.json", "w"), indent=1)

    fig, axs = plt.subplots(3, 4, figsize=(15, 9.5))
    fig.suptitle("30 independent AI agents: each dot is one agent's 2031 outcome, bar = median",
                 x=0.06, ha="left", fontsize=14, fontweight="bold")
    names = [SCENARIOS[s]["title"] for s in SCENARIOS]
    for ax, (k, lab) in zip(axs.flat, METRICS):
        for i, s in enumerate(SCENARIOS):
            v = np.array(summary[s]["metrics"][k]["values"])
            jitter = np.linspace(-0.22, 0.22, len(v)) if len(v) > 1 else np.zeros(len(v))
            ax.scatter(np.full(len(v), i) + jitter, v, s=30, color=SCN_COLOR[s], edgecolor=SURF, lw=1, zorder=3)
            med = np.median(v)
            ax.plot([i - 0.32, i + 0.32], [med, med], color=INK, lw=2, zorder=4)
        ax.set_xticks(range(len(names)), [n.split()[0] for n in names])
        ax.set_title(lab, loc="left")
        ax.grid(axis="x", visible=False)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    os.makedirs("img", exist_ok=True)
    fig.savefig("img/agents_outcomes.png", dpi=130)
    print(json.dumps({s: {k: round(v["median"], 2) for k, v in summary[s]["metrics"].items()} for s in summary}, indent=1))


if __name__ == "__main__":
    main()
