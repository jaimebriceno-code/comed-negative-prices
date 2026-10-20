"""Render images and the bullet-point report from results.json."""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
from model import SCENARIOS, REGIONS, QUARTERS, RUNS

SURF, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0"
SCN_COLOR = {"fragmented_drift": "#2a78d6", "ai_acceleration": "#eb6834", "polycrisis": "#1baf7a"}
EMP, DISP, UNEMP = "#2a78d6", "#eb6834", "#8a8984"
plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold",
})
YEARS = 2026.75 + np.arange(1, QUARTERS + 1) / 4

METRICS = [  # key, label, unit
    ("gdp", "World output (2026 = 100)", ""),
    ("unemp", "Unemployment rate", "%"),
    ("gini", "Income inequality (Gini)", ""),
    ("debt", "Public debt, % of GDP", "%"),
    ("unrest", "Households protesting", "%"),
    ("trust", "Trust in institutions (0-100)", ""),
    ("ai", "Firms' AI adoption", "%"),
    ("displaced", "AI-displaced & jobless", "%"),
    ("tariff", "Trade barriers (0-100)", ""),
    ("infl", "Inflation", "%"),
    ("renew", "Renewable power share", "%"),
    ("temp", "Warming (°C vs 1850-1900)", ""),
]

res = json.load(open("results.json"))


def arr(scn, key):
    return np.array([r["series"][key] for r in res[scn]])


def median_run(scn):
    g = arr(scn, "gdp")[:, -1]
    return int(np.argsort(g)[len(g) // 2])


def fan(ax, scn, key, label, unit, color):
    a = arr(scn, key)
    for row in a:
        ax.plot(YEARS, row, color=color, alpha=0.22, lw=1)
    ax.fill_between(YEARS, np.percentile(a, 10, 0), np.percentile(a, 90, 0), color=color, alpha=0.12, lw=0)
    med = np.median(a, 0)
    ax.plot(YEARS, med, color=color, lw=2)
    ax.annotate(f"{med[-1]:.2f}{unit}" if key in ("gini", "temp") else f"{med[-1]:.1f}{unit}",
                (YEARS[-1], med[-1]), xytext=(4, 0), textcoords="offset points",
                va="center", fontsize=8, color=INK)
    ax.set_title(label, loc="left")
    ax.set_xlim(YEARS[0], YEARS[-1] + 0.9)
    ax.set_xticks([2027, 2029, 2031])


def scenario_dashboard(scn):
    p, c = SCENARIOS[scn], SCN_COLOR[scn]
    fig = plt.figure(figsize=(15, 10.5))
    gs = fig.add_gridspec(4, 6, height_ratios=[1, 1, 1, 1.25], hspace=0.55, wspace=0.45)
    fig.suptitle(f"{p['title']}: the world in 2031, 10 independent agent runs",
                 x=0.06, ha="left", fontsize=15, fontweight="bold")
    fig.text(0.06, 0.935, p["blurb"] + "   Thin lines = individual runs, band = 10th to 90th percentile, bold = median.",
             fontsize=9, color=INK2)
    for i, (k, lab, u) in enumerate(METRICS):
        fan(fig.add_subplot(gs[i // 4, i % 4]), scn, k, lab, u, c)
    # Region panel (median run)
    snap = res[scn][median_run(scn)]["snapshot"]
    names = [r[0].replace("Middle East & N. Africa", "MENA").replace("Sub-Saharan Africa", "SS Africa")
             .replace("Latin America", "LatAm").replace("Rest of Asia", "Rest Asia").replace("United States", "US")
             for r in REGIONS]
    ax = fig.add_subplot(gs[0:3, 4:6])
    y = np.arange(len(names))[::-1]
    ax.barh(y + 0.2, snap["region_unemp"], height=0.36, color=c, label="Unemployment %")
    ax.barh(y - 0.2, snap["region_unrest"], height=0.36, color=INK2, label="Protesting %")
    for yi, u, d, g in zip(y, snap["region_unemp"], snap["region_debt"], snap["region_gdp_growth"]):
        ax.text(max(u, 0) + 0.3, yi + 0.2, f"growth {g:+.1f}%/yr · debt {d:.0f}%", va="center", fontsize=7.5, color=INK2)
    ax.set_yticks(y, names)
    ax.set_xlim(0, max(max(snap["region_unemp"]), max(snap["region_unrest"])) * 2.1)
    ax.set_title("Regional state in 2031 (median run)", loc="left")
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    ax.grid(axis="y", visible=False)
    # Household agents snapshot
    ax = fig.add_subplot(gs[3, :])
    emp, disp, prot = (np.array(snap[k]) for k in ("emp", "displaced", "protest"))
    reg = np.array(snap["region"])
    rgb = {k: matplotlib.colors.to_rgb(v) for k, v in (("e", EMP), ("d", DISP), ("u", UNEMP), ("s", SURF))}
    rows, cols_per = 10, 30
    img = np.ones((rows, len(REGIONS) * (cols_per + 2), 3)) * rgb["s"]
    px, py = [], []
    for r in range(len(REGIONS)):
        idx = np.where(reg == r)[0]
        idx = idx[np.lexsort((~prot[idx], ~(disp[idx] & ~emp[idx]), emp[idx]))]
        for j, h in enumerate(idx):
            yy, xx = j // cols_per, r * (cols_per + 2) + j % cols_per
            img[yy, xx] = rgb["e"] if emp[h] else (rgb["d"] if disp[h] else rgb["u"])
            if prot[h]:
                px.append(xx); py.append(yy)
    ax.imshow(img, aspect="auto", interpolation="nearest", extent=(-0.5, img.shape[1] - 0.5, rows - 0.5, -0.5))
    ax.scatter(px, py, s=7, color=INK, lw=0)
    for x0 in np.arange(-0.5, img.shape[1], 1):
        ax.axvline(x0, color=SURF, lw=0.6)
    for y0 in np.arange(-0.5, rows, 1):
        ax.axhline(y0, color=SURF, lw=0.6)
    for r, n in enumerate(names):
        ax.text(r * (cols_per + 2) + cols_per / 2 - 0.5, rows + 0.4, n, ha="center", va="top", fontsize=8, color=INK2)
    ax.set_ylim(rows + 1.6, -0.6); ax.axis("off")
    ax.set_title("2,400 household agents in 2031 (median run). Each square is one household.", loc="left")
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], marker="s", ls="", color=EMP, label="Employed"),
                       Line2D([], [], marker="s", ls="", color=DISP, label="Displaced by AI, jobless"),
                       Line2D([], [], marker="s", ls="", color=UNEMP, label="Unemployed, other causes"),
                       Line2D([], [], marker="o", ls="", color=INK, ms=3, label="Protesting (dot)")],
              loc="upper right", bbox_to_anchor=(1, 1.25), ncol=4, frameon=False, fontsize=8)
    fig.savefig(f"img/{scn}_dashboard.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def comparison():
    keys = ["gdp", "unemp", "gini", "debt", "unrest", "trust", "ai", "tariff", "renew"]
    lab = {k: (l, u) for k, l, u in METRICS}
    fig, axs = plt.subplots(3, 3, figsize=(14, 10))
    fig.suptitle("Three futures compared: median of 10 runs, band = 10th to 90th percentile",
                 x=0.06, ha="left", fontsize=14, fontweight="bold")
    for ax, k in zip(axs.flat, keys):
        for scn in SCENARIOS:
            a, c = arr(scn, k), SCN_COLOR[scn]
            ax.fill_between(YEARS, np.percentile(a, 10, 0), np.percentile(a, 90, 0), color=c, alpha=0.13, lw=0)
            ax.plot(YEARS, np.median(a, 0), color=c, lw=2, label=SCENARIOS[scn]["title"])
        ax.set_title(lab[k][0], loc="left"); ax.set_xticks([2027, 2029, 2031])
    axs[0, 0].legend(frameon=False, fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig("img/comparison.png", dpi=130)
    plt.close(fig)


def postcard(scn):
    """Stylised 2031 street scene whose features are driven by the median outcomes."""
    m = {k: float(np.median(arr(scn, k)[:, -1])) for k, _, _ in METRICS}
    rng = np.random.default_rng(7)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis("off")
    haze = np.clip((m["temp"] - 1.5) * 4 + (100 - m["renew"] * 1.6) / 100 + m["tariff"] / 200, 0, 1)
    sky_top = np.array([0.42, 0.66, 0.92]) * (1 - haze) + np.array([0.72, 0.62, 0.52]) * haze
    for i in range(60):
        t = i / 60
        ax.add_patch(Rectangle((0, i), 100, 1, color=tuple(sky_top * (1 - t) + np.array([0.98, 0.95, 0.88]) * t), lw=0))
    ax.add_patch(Circle((85, 50), 4, color="#f6c453" if haze < 0.5 else "#e09a5a", lw=0))
    # skyline: height ~ output, lit windows ~ employment
    n_bld, x = 14, 2
    emp_rate = 1 - m["unemp"] / 100
    for b in range(n_bld):
        wdt = rng.uniform(4, 6.5); h = rng.uniform(12, 30) * (m["gdp"] / 110)
        ax.add_patch(Rectangle((x, 8), wdt, h, color="#3c4555", lw=0))
        for wy in np.arange(10, 8 + h - 2, 2.4):
            for wx in np.arange(x + 0.8, x + wdt - 1, 1.6):
                lit = rng.random() < emp_rate - 0.15
                ax.add_patch(Rectangle((wx, wy), 0.8, 1.2, color="#ffd970" if lit else "#262c36", lw=0))
        x += wdt + rng.uniform(0.5, 2)
    # ground
    ax.add_patch(Rectangle((0, 0), 100, 8, color="#7b8a6a" if m["temp"] < 1.6 else "#a89a6a", lw=0))
    # energy: solar panels vs smokestacks
    n_solar, n_stack = int(m["renew"] / 6), int((100 - m["renew"]) / 14)
    for i in range(n_solar):
        sx = 4 + i * 4.5
        ax.add_patch(Polygon([(sx, 1), (sx + 3.5, 1), (sx + 3, 3.5), (sx + 0.5, 3.5)], color="#2a5fa8", lw=0))
    for i in range(n_stack):
        sx = 60 + i * 5
        ax.add_patch(Rectangle((sx, 8), 1.6, 14, color="#5b5b5b", lw=0))
        for k in range(5):
            ax.add_patch(Circle((sx + 0.8 + k * 1.2, 23 + k * 1.6), 1 + k * 0.4, color="#9a9a9a", alpha=0.35, lw=0))
    # robots ~ AI adoption
    for i in range(int(m["ai"] / 5)):
        rx = 3 + i * 3.6
        ax.add_patch(Rectangle((rx, 5.6), 1.6, 1.8, color="#c8d0da", lw=0))
        ax.add_patch(Circle((rx + 0.8, 8.0), 0.55, color="#c8d0da", lw=0))
    # crowd ~ unrest
    for i in range(int(m["unrest"] * 4)):
        cx = 40 + rng.uniform(-14, 14)
        ax.add_patch(Circle((cx, 4.8), 0.5, color="#e34948", lw=0))
        ax.plot([cx, cx], [5.3, 7.3], color=INK, lw=0.7)
        ax.add_patch(Rectangle((cx - 0.6, 7.1), 1.2, 0.7, color=SURF, lw=0))
    # trade wall ~ fragmentation
    wall_h = m["tariff"] / 2.5
    ax.add_patch(Rectangle((97, 8), 2.5, wall_h, color="#7a3b2e", lw=0))
    ax.text(2, 57, f"{SCENARIOS[scn]['title']} · 2031", fontsize=16, fontweight="bold", color=INK)
    ax.text(2, 53.5, f"output {m['gdp']:.0f} · jobless {m['unemp']:.1f}% · protesting {m['unrest']:.1f}% · "
            f"AI firms {m['ai']:.0f}% · renewables {m['renew']:.0f}% · +{m['temp']:.2f}°C",
            fontsize=9, color=INK)
    fig.text(0.13, 0.06, "Illustrative scene driven by median model outputs: building height = output, lit windows = employment, "
            "robots = AI adoption,\nred figures = protest, solar/smokestacks = energy mix, sky haze = warming & fragmentation, "
            "red wall (right) = trade barriers.", fontsize=7, color=INK2, va="top")
    fig.savefig(f"img/{scn}_scene.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    import os
    os.makedirs("img", exist_ok=True)
    for s in SCENARIOS:
        scenario_dashboard(s)
        postcard(s)
    comparison()
