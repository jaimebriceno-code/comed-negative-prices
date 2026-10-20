"""Agent-based "World 2031" model.

Three scenarios x 10 independent runs. Every run builds a fresh population of
agents from its own random seed:
  * 8 region (government) agents with randomly drawn policy preferences
  * 200 firm agents that decide whether/when to adopt AI
  * 2,400 household agents (skill, job type, income, wealth, sentiment)
and steps them quarterly from 2026Q4 to 2031Q4 (20 quarters) under
scenario-specific constraints and stochastic shocks.

Starting values are stylised late-2026 conditions (high public debt, ~1.45C
warming, tariff fragmentation, rapid AI diffusion, ageing, polarisation). The
model is illustrative: it explores how these pressures interact, not a forecast.
"""
import json
import numpy as np

QUARTERS = 20
RUNS = 10
HH_PER_REGION = 300
FIRMS_PER_REGION = 25

# name, GDP weight, trend growth %/yr, debt %GDP, climate exposure,
# AI readiness, renewable power share, routine-job share, initial unemployment
REGIONS = [
    ("United States", 15, 2.0, 122, 0.35, 0.90, 0.25, 0.35, 0.043),
    ("Europe",        14, 1.0,  88, 0.35, 0.70, 0.47, 0.35, 0.060),
    ("China",         19, 4.0,  95, 0.50, 0.80, 0.36, 0.42, 0.052),
    ("India",          8, 6.3,  82, 0.85, 0.50, 0.24, 0.30, 0.065),
    ("Rest of Asia",  14, 3.8,  70, 0.65, 0.60, 0.25, 0.38, 0.045),
    ("Latin America",  7, 2.2,  75, 0.60, 0.40, 0.62, 0.33, 0.065),
    ("Middle East & N. Africa", 6, 2.8, 55, 0.80, 0.40, 0.08, 0.30, 0.100),
    ("Sub-Saharan Africa",      5, 3.9, 65, 0.90, 0.25, 0.25, 0.25, 0.090),
]

SCENARIOS = {
    "fragmented_drift": dict(
        title="Fragmented Drift",
        blurb="Muddle-through: tariffs and blocs persist, AI diffuses at today's pace, "
              "climate policy lags, debt keeps creeping up.",
        ai_speed=0.030, ai_jump_p=0.03, displacement=0.18,
        tariff_drift=0.004, conflict_p=0.015, energy_vol=0.06,
        disaster_mult=1.0, debt_stress=1.0, green_push=1.0, rate0=3.5),
    "ai_acceleration": dict(
        title="AI Acceleration",
        blurb="Frontier AI and automation scale fast: productivity surges, but routine "
              "white- and blue-collar work is displaced faster than institutions adapt.",
        ai_speed=0.080, ai_jump_p=0.12, displacement=0.50,
        tariff_drift=0.002, conflict_p=0.012, energy_vol=0.07,
        disaster_mult=1.0, debt_stress=0.9, green_push=1.3, rate0=3.5),
    "polycrisis": dict(
        title="Polycrisis Cascade",
        blurb="Compound stress: sovereign-debt strain, escalating trade/security conflict, "
              "energy spikes and more frequent climate disasters feed on each other.",
        ai_speed=0.025, ai_jump_p=0.02, displacement=0.20,
        tariff_drift=0.012, conflict_p=0.06, energy_vol=0.13,
        disaster_mult=1.8, debt_stress=3.0, green_push=0.7, rate0=4.5),
}


def gini(x):
    x = np.sort(np.clip(x, 0, None))
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def run(scn, seed):
    p = SCENARIOS[scn]
    rng = np.random.default_rng(seed)
    R = len(REGIONS)
    w = np.array([r[1] for r in REGIONS], float); w /= w.sum()
    trend = np.array([r[2] for r in REGIONS]) / 400
    debt = np.array([r[3] for r in REGIONS], float)
    expo = np.array([r[4] for r in REGIONS])
    ready = np.array([r[5] for r in REGIONS])
    renew = np.array([r[6] for r in REGIONS])
    routine_share = np.array([r[7] for r in REGIONS])
    gdp = w * 100.0
    trust = rng.uniform(0.45, 0.6, R)

    # Government agents: independent preference draws each run
    gov = dict(
        populism=rng.beta(2, 3, R),       # reacts to unrest with tariffs/transfers
        prudence=rng.beta(3, 2, R),       # reacts to debt with austerity
        green=rng.beta(2.5, 2.5, R) * p["green_push"],
        social=rng.beta(2.5, 2.5, R),     # reskilling / safety-net reflex
    )

    # Firm agents
    F = R * FIRMS_PER_REGION
    f_reg = np.repeat(np.arange(R), FIRMS_PER_REGION)
    f_innov = rng.beta(2, 4, F)
    f_adopt = np.zeros(F)                 # AI adoption level 0..1
    f_export = rng.beta(2, 3, F)          # tariff exposure

    # Household agents
    H = R * HH_PER_REGION
    h_reg = np.repeat(np.arange(R), HH_PER_REGION)
    h_skill = rng.choice([0, 1, 2], H, p=[0.35, 0.45, 0.20])
    h_routine = rng.random(H) < routine_share[h_reg] * (1.25 - 0.35 * h_skill)
    h_emp = rng.random(H) > np.array([r[8] for r in REGIONS])[h_reg]
    h_firm = f_reg.reshape(R, -1)[h_reg, rng.integers(0, FIRMS_PER_REGION, H)]
    h_displaced = np.zeros(H, bool)
    h_wealth = rng.lognormal(0, 1.3, H) * (1 + h_skill)
    h_sent = rng.normal(0, 0.3, H)
    h_protest = np.zeros(H, bool)
    reg_wage = 0.4 + 0.6 * ready
    base_wage = reg_wage[h_reg] * (1 + 0.8 * h_skill) * rng.lognormal(0, 0.45, H)

    ai, temp, energy, tariff = 0.12, 1.45, 100.0, 0.45
    rate, infl = p["rate0"], 3.0
    reskill = np.zeros(R)
    transfer = np.full(R, 0.35)
    events = []
    out = {k: [] for k in ["gdp", "unemp", "gini", "infl", "debt", "unrest", "trust",
                           "ai", "renew", "temp", "emis", "displaced", "energy", "tariff"]}
    prev_inc = None
    emis0 = None

    for q in range(QUARTERS):
        # ---- global shocks
        ai_step = p["ai_speed"] * (1 - ai)
        if rng.random() < p["ai_jump_p"]:
            ai_step += rng.uniform(0.04, 0.09); events.append((q, "AI capability jump"))
        ai = min(1, ai + ai_step)
        e_shock = rng.normal(0, p["energy_vol"]) * 100
        if rng.random() < p["conflict_p"] * (1 + tariff):
            e_shock += rng.uniform(15, 40); tariff += 0.05
            events.append((q, "geopolitical/energy conflict"))
        energy = max(60, energy + e_shock - 0.15 * (energy - 100) - 1.2 * (renew.mean() - 0.3) * 10)
        tariff = np.clip(tariff + p["tariff_drift"] + rng.normal(0, 0.01), 0, 1)

        # ---- firm agents adopt AI
        pressure = 1 + 0.5 * (energy > 115) + 0.3 * tariff
        adopt_p = ai * ready[f_reg] * f_innov * pressure * 0.6
        newly = (rng.random(F) < adopt_p) & (f_adopt < 1)
        gain = np.where(newly, rng.uniform(0.2, 0.5, F), 0)
        f_adopt = np.minimum(1, f_adopt + gain)

        # layoffs of routine workers at newly-adopting firms
        at_risk = h_emp & h_routine & newly[h_firm]
        lay = at_risk & (rng.random(H) < p["displacement"] * gain[h_firm] / 0.35)
        h_emp[lay] = False; h_displaced[lay] = True

        # ---- regional macro
        reg_adopt = np.bincount(f_reg, f_adopt, R) / FIRMS_PER_REGION
        prod = 0.0050 * reg_adopt * (0.5 + ai)            # AI productivity lift / qtr
        tariff_drag = 0.0025 * tariff * (1 + np.bincount(f_reg, f_export, R) / FIRMS_PER_REGION)
        energy_drag = 0.0004 * (energy - 100) / 10 * (1 - renew)
        dis_p = 0.04 * expo * p["disaster_mult"] * (1 + 2 * (temp - 1.4))
        disaster = rng.random(R) < dis_p
        dis_loss = np.where(disaster, rng.uniform(0.005, 0.03, R) * expo, 0)
        for r in np.where(disaster)[0]:
            events.append((q, f"climate disaster: {REGIONS[r][0]}"))
        crisis_p = 0.004 * p["debt_stress"] * np.exp((debt - 100) / 30) * (rate / 3.5) ** 2
        crisis = rng.random(R) < crisis_p
        for r in np.where(crisis)[0]:
            events.append((q, f"debt crisis: {REGIONS[r][0]}"))
        unemp_r = 1 - np.bincount(h_reg, h_emp, R) / HH_PER_REGION
        fiscal = 0.002 * (transfer - 0.35) + 0.001 * reskill
        demand_gap = -0.02 * np.maximum(unemp_r - 0.07, 0)
        growth = (trend + prod - tariff_drag - energy_drag - dis_loss + fiscal + demand_gap
                  - 0.0006 * (rate - 3) - np.where(crisis, rng.uniform(0.02, 0.05, R), 0) - 0.004 * crisis.any()
                  + rng.normal(0, 0.003, R))
        gdp *= 1 + growth

        # ---- government agents decide
        unrest_r = np.bincount(h_reg, h_protest, R) / HH_PER_REGION
        displ_r = np.bincount(h_reg, h_displaced & ~h_emp, R) / HH_PER_REGION
        room = np.clip((130 - debt) / 60, 0, 1)
        tariff += 0.01 * np.sum(w * gov["populism"] * (unrest_r > 0.08))
        transfer = np.clip(transfer + 0.04 * gov["populism"] * (unrest_r > 0.08)
                           + 0.03 * gov["social"] * (displ_r > 0.02) * room
                           - 0.03 * gov["prudence"] * (debt > 110) - 0.05 * crisis, 0.15, 0.8)
        reskill = np.clip(0.9 * reskill + 0.6 * gov["social"] * room * (displ_r > 0.015), 0, 1)
        renew = np.clip(renew + 0.006 * gov["green"] * (0.5 + room) * (1 + 0.5 * (energy > 110))
                        + 0.004 * ai, 0, 0.95)
        deficit = (1.8 + 2.5 * (transfer - 0.35) + 0.8 * reskill + 30 * dis_loss
                   - 0.6 * gov["prudence"] * (debt > 100)) / 4
        debt = debt * (1 + (rate * 0.7 + 1.0) / 400) / (1 + growth + infl / 400) + deficit
        debt = np.where(crisis, debt + rng.uniform(3, 8, R), debt)

        # ---- prices
        infl = (0.6 * infl + 0.4 * (2.2 + 0.05 * e_shock + 40 * p["tariff_drift"]
                                     + 3 * (transfer.mean() - 0.35) - 8 * prod.mean() * 4)
                + rng.normal(0, 0.25))
        rate = np.clip(0.8 * rate + 0.2 * (1.0 + 1.3 * infl), 0.5, 9)

        # ---- labour market: separations and hiring
        sep = h_emp & (rng.random(H) < 0.012 + 0.6 * np.maximum(-growth, 0)[h_reg])
        h_emp[sep] = False
        find = (0.22 * (1 + 30 * np.maximum(growth, 0))[h_reg] * (0.7 + 0.25 * h_skill)
                * (1 + 0.8 * reskill[h_reg]) * np.where(h_displaced, 0.55, 1))
        hired = ~h_emp & (rng.random(H) < find)
        h_emp[hired] = True
        h_firm[hired] = f_reg.reshape(R, -1)[h_reg[hired], rng.integers(0, FIRMS_PER_REGION, hired.sum())]
        retrain = hired & h_displaced & (rng.random(H) < 0.4 + 0.5 * reskill[h_reg])
        h_routine[retrain] = False
        h_displaced[hired & ~h_routine] = False

        # ---- incomes, wealth, sentiment
        premium = 1 + 0.9 * ai * reg_adopt[h_reg] * (h_skill == 2) - 0.25 * ai * h_routine
        wage = base_wage * premium * (gdp / (w * 100))[h_reg] ** 0.6
        ret = 0.01 + 0.012 * ai * reg_adopt[h_reg] - 0.01 * crisis[h_reg]
        h_wealth = h_wealth * (1 + ret) + np.where(h_emp, 0.05 * wage, -0.02 * h_wealth)
        h_wealth = np.maximum(h_wealth, 0)
        income = np.where(h_emp, wage, transfer[h_reg] * wage) + 0.04 * h_wealth
        chg = 0 if prev_inc is None else np.clip(income / prev_inc - 1, -0.5, 0.5)
        prev_inc = income
        target = (3 * chg - 0.08 * max(infl - 2.5, 0) - 0.5 * (~h_emp) - 0.4 * h_displaced
                  + 0.6 * (trust[h_reg] - 0.5) - 0.3 * disaster[h_reg] - 0.3 * crisis[h_reg])
        h_sent = 0.75 * h_sent + 0.25 * target + rng.normal(0, 0.08, H)
        contagion = unrest_r[h_reg]
        h_protest = (h_sent < -0.25) & (rng.random(H) < 0.25 + 2.5 * contagion)
        unrest_r = np.bincount(h_reg, h_protest, R) / HH_PER_REGION
        trust = np.clip(trust + 0.3 * (growth - trend) - 0.05 * (unrest_r - 0.05)
                        - 0.04 * crisis + 0.01 * (transfer - 0.35) + rng.normal(0, 0.005, R), 0.05, 0.95)

        # ---- climate
        emis = float(np.sum(gdp * (1 - renew) * (1 - 0.1 * ai)))
        emis0 = emis0 or emis
        temp += 0.0065 * (emis / emis0) + rng.normal(0, 0.004)

        out["gdp"].append(float(gdp.sum()))
        out["unemp"].append(float(1 - h_emp.mean()) * 100)
        out["gini"].append(gini(income))
        out["infl"].append(float(infl))
        out["debt"].append(float(np.sum(debt * w)))
        out["unrest"].append(float(h_protest.mean()) * 100)
        out["trust"].append(float(np.sum(trust * w)) * 100)
        out["ai"].append(float(f_adopt.mean()) * 100)
        out["renew"].append(float(np.sum(renew * w)) * 100)
        out["temp"].append(float(temp))
        out["emis"].append(emis / emis0 * 100)
        out["displaced"].append(float((h_displaced & ~h_emp).mean()) * 100)
        out["energy"].append(float(energy))
        out["tariff"].append(float(tariff) * 100)

    snapshot = dict(
        emp=h_emp.tolist(), displaced=h_displaced.tolist(), protest=h_protest.tolist(),
        skill=h_skill.tolist(), region=h_reg.tolist(), income=income.tolist(),
        region_unrest=(np.bincount(h_reg, h_protest, R) / HH_PER_REGION * 100).tolist(),
        region_unemp=((1 - np.bincount(h_reg, h_emp, R) / HH_PER_REGION) * 100).tolist(),
        region_debt=debt.tolist(), region_gdp_growth=((gdp / (w * 100)) ** (4 / QUARTERS) * 100 - 100).tolist(),
    )
    return dict(series=out, events=events, snapshot=snapshot,
                gov=dict((k, v.tolist()) for k, v in gov.items()))


def main():
    results = {}
    for i, scn in enumerate(SCENARIOS):
        results[scn] = [run(scn, seed=1000 * (i + 1) + k) for k in range(RUNS)]
    with open("results.json", "w") as fh:
        json.dump(results, fh)


if __name__ == "__main__":
    main()
