"""Build the shareable World 2031 page (world2031.html) from both simulation methods."""
import html
import json
import numpy as np

agents = json.load(open("agents_summary.json"))
abm = json.load(open("results.json"))
runs = {}
for s in agents:
    runs[s] = [json.load(open(f"llm_runs/{s}_{k:02d}.json")) for k in range(1, 11)]

E = html.escape
ORDER = ["fragmented_drift", "ai_acceleration", "polycrisis"]
TITLE = {"fragmented_drift": "Fragmented Drift", "ai_acceleration": "AI Acceleration", "polycrisis": "Polycrisis Cascade"}
KEY = {"fragmented_drift": "s1", "ai_acceleration": "s2", "polycrisis": "s3"}
PREMISE = {
    "fragmented_drift": "Muddle-through. Tariffs and blocs persist and edge higher, AI spreads at today's pace, climate policy lags, debt creeps up.",
    "ai_acceleration": "Frontier AI and agentic automation scale much faster than expected. Productivity surges; routine office and factory work is displaced faster than institutions adapt.",
    "polycrisis": "Compound stress. Bond-market strain, trade and security conflict, energy spikes and climate disasters feed on each other.",
}
BULLETS = {
    "fragmented_drift": [
        "Growth holds but stays slow: 2.3% a year in the model, 2.6% from the agents. Nobody has the fiscal room to lift it.",
        "Public debt rises 7–8 points of GDP in both methods. The US ends near 130–133%.",
        "Frontier economies in Africa and South Asia default (median 4 crises per agent run). Japanese and US bond-auction scares recur but are contained.",
        "Trade settles into two loose blocs, with India, the Gulf and Mexico acting as connector economies. Fragmentation goes from 45 to about 53–56.",
        "AI reaches about 31% of firms. Gains concentrate in large firms while entry-level office jobs thin out (about 38 million displaced).",
        "Inequality rises in all 20 runs. Trust slips from 40 to 35 and unrest climbs from 35 to 44.",
        "Renewables pass 42% of power, yet warming still reaches about 1.58 °C.",
    ],
    "ai_acceleration": [
        "This is the richest world: growth is 2.6% a year in the model and 3.6% from the agents, the highest of the three.",
        "Jobs take a J-shaped hit. Unemployment peaks around 2029–30 (7.2% globally per the agents; 9.6% in the model's sample, worst run 14%), then recovers.",
        "Agents estimate 140–215 million jobs displaced by AI, about five times the other scenarios. Junior professional hiring largely disappears.",
        "Electricity becomes the binding constraint. Data-centre demand pushes up power bills and peak inflation reaches 4.6%.",
        "Every agent run ends with inequality rising sharply. Governments respond with automation or compute taxes and wage insurance.",
        "Services-export economies such as the Philippines, India's back-office hubs and Kenya lose their growth model.",
        "Unrest is high (58) and trust low (31) despite strong growth. 'Humans first' politics spreads.",
    ],
    "polycrisis": [
        "This is the weakest and angriest world: growth is 1.3% a year in the model and 1.9% from the agents. US and European output stagnates.",
        "Debt jumps about 14 points of GDP in both methods. Bond revolts end in financial repression: central banks cap long yields and inflation erodes the debt.",
        "In most agent runs a Gulf or Hormuz oil shock drives inflation to a 7.2% peak, the highest of the three scenarios.",
        "Sovereign crises cluster: about 9 per agent run, and every model run has at least one. Climate disasters hit governments that have no fiscal room left.",
        "Trade barriers reach about 75–83 out of 100. In 6 of 10 agent runs, a Chinese customs quarantine of Taiwan or its outlying islands halts chip exports.",
        "Unrest reaches 65 and trust falls to 28, a generational low. In the model's worst run, 18% of households protest.",
        "One recurring silver lining: Europe ends more fiscally integrated and better armed.",
    ],
}


def med(s, k):
    return agents[s]["metrics"][k]["median"]


def abm_end(s, k):
    return float(np.median([r["series"][k][-1] for r in abm[s]]))


def abm_cagr(s):
    return ((abm_end(s, "gdp") / 100) ** 0.2 - 1) * 100


rows = [
    ("World GDP growth, % a year", lambda s: f"{abm_cagr(s):.1f}", lambda s: f"{med(s, 'world_real_gdp_growth_avg_pct_2027_2031'):.1f}"),
    ("Public debt change, pts of GDP", lambda s: f"+{abm_end(s, 'debt') - 87.3:.0f}", lambda s: f"+{med(s, 'global_public_debt_pct_gdp_2031') - 95:.0f}"),
    ("Peak unemployment, %", lambda s: f"{np.median([max(r['series']['unemp']) for r in abm[s]]):.1f}", lambda s: f"{med(s, 'global_unemployment_peak_pct'):.1f}"),
    ("Firms using AI by 2031, %", lambda s: f"{abm_end(s, 'ai'):.0f}", lambda s: f"{med(s, 'firms_using_ai_pct_2031'):.0f}"),
    ("Trade fragmentation (2026 = 45)", lambda s: f"{abm_end(s, 'tariff'):.0f}", lambda s: f"{med(s, 'trade_fragmentation_0_100'):.0f}"),
    ("Renewables, % of power", lambda s: f"{abm_end(s, 'renew'):.0f}", lambda s: f"{med(s, 'renewable_share_electricity_pct_2031'):.0f}"),
    ("Warming by 2031, °C", lambda s: f"{abm_end(s, 'temp'):.2f}", lambda s: f"{med(s, 'warming_2031_c'):.2f}"),
]


def table():
    head = "".join(f'<th scope="col" class="{KEY[s]}"><span class="dot"></span>{TITLE[s]}</th>' for s in ORDER)
    body = []
    for lab, fa, fb in rows:
        cells = "".join(f'<td><span class="v">{fa(s)}</span><span class="v ag">{fb(s)}</span></td>' for s in ORDER)
        body.append(f'<tr><th scope="row">{lab}</th>{cells}</tr>')
    return f'''<div class="tablewrap"><table>
<thead><tr><th scope="col">2031 outcome <span class="legend"><span class="v">model</span><span class="v ag">AI agents</span></span></th>{head}</tr></thead>
<tbody>{"".join(body)}</tbody></table></div>'''


def scenario(s, i):
    rs = runs[s]
    heads = "".join(f"<li>{E(r['headline'])}</li>" for r in rs)
    wild = "".join(f"<li>{E(r['wildcard'])}</li>" for r in rs[:5])
    post = "".join(f"<blockquote>{E(r['image_description'])}<cite>Agent run {r['run']}</cite></blockquote>" for r in rs[:3])
    mid = sorted(rs, key=lambda r: r["metrics_2031"]["world_real_gdp_growth_avg_pct_2027_2031"])[5]
    win = "".join(f"<li>{E(w)}</li>" for w in mid["winners"][:3])
    lose = "".join(f"<li>{E(w)}</li>" for w in mid["losers"][:3])
    bullets = "".join(f"<li>{E(b)}</li>" for b in BULLETS[s])
    return f'''
<section class="scn {KEY[s]}" id="{s.replace('_', '-')}">
  <header class="scn-head">
    <p class="eyebrow">Scenario {i}</p>
    <h2>{TITLE[s]}</h2>
    <p class="premise">{E(PREMISE[s])}</p>
  </header>
  <div class="scn-grid">
    <figure class="scene"><img src="img/{s}_scene.png" alt="Illustrated 2031 street scene for {TITLE[s]}, drawn from the model's median outcomes" loading="lazy" width="1033" height="696"></figure>
    <div class="report">
      <h3>What 2031 looks like</h3>
      <ul class="bul">{bullets}</ul>
    </div>
  </div>
  <div class="three">
    <div><h3>Ten agents' headlines</h3><ol class="heads">{heads}</ol></div>
    <div><h3>Who gains, who loses <small>(median agent run)</small></h3>
      <p class="tag up">Gain</p><ul class="wl">{win}</ul>
      <p class="tag down">Lose</p><ul class="wl">{lose}</ul>
      <h3>Wildcards the agents drew</h3><ul class="wl">{wild}</ul></div>
    <div><h3>Postcards from 2031</h3>{post}</div>
  </div>
  <details><summary>Model dashboard: all 10 runs, 12 indicators, 2,400 households</summary>
    <img src="img/{s}_dashboard.png" alt="Dashboard of 10 agent-based model runs for {TITLE[s]}" loading="lazy">
  </details>
</section>'''


CSS = """
/* Layout: one reading column, wide figures; scenario colour carried by a token per section */
:root{
  --bg:#f3f4f1; --surface:#ffffff; --ink:#14171c; --ink2:#4a4f57; --muted:#7a7f86; --rule:#d9dbd6;
  --s1:#2a78d6; --s2:#eb6834; --s3:#169c6c; --up:#1f7a4a; --down:#b23b3a;
  --display:"Archivo",system-ui,sans-serif; --body:"IBM Plex Sans",system-ui,sans-serif; --mono:"IBM Plex Mono",ui-monospace,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#121417; --surface:#1b1e22; --ink:#eceef0; --ink2:#b7bcc3; --muted:#8a9099; --rule:#2e3238;
  --s1:#3987e5; --s2:#f07a48; --s3:#1fb684; --up:#4fbf86; --down:#ef7473; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#121417; --surface:#1b1e22; --ink:#eceef0; --ink2:#b7bcc3; --muted:#8a9099; --rule:#2e3238;
  --s1:#3987e5; --s2:#f07a48; --s3:#1fb684; --up:#4fbf86; --down:#ef7473; color-scheme:dark}
body{background:var(--bg);color:var(--ink);font:16px/1.6 var(--body)}
.wrap{max-width:1120px;margin:0 auto;padding-block:40px 64px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:56px}
h1,h2,h3{font-family:var(--display);text-wrap:balance;margin:0}
h1{font-size:clamp(2.6rem,7vw,4.6rem);line-height:.95;font-weight:800;letter-spacing:-.02em}
h1 span{display:block;font-weight:500;color:var(--ink2);font-size:.42em;letter-spacing:0;margin-top:14px;line-height:1.25}
h2{font-size:clamp(1.8rem,4vw,2.5rem);font-weight:800;letter-spacing:-.01em}
h3{font-size:1rem;font-weight:700;margin-bottom:10px}
h3 small{font-weight:400;color:var(--muted)}
p{margin:0}
.lede{max-width:68ch;color:var(--ink2);font-size:1.08rem}
.stats{display:flex;flex-wrap:wrap;gap:10px 28px;font-family:var(--mono);font-size:.85rem;color:var(--ink2)}
.stats b{color:var(--ink);font-weight:600}
.hero{display:grid;gap:20px}
.eyebrow{font-family:var(--mono);font-size:.78rem;letter-spacing:.08em;text-transform:uppercase;color:var(--accent,var(--muted))}
nav{display:flex;flex-wrap:wrap;gap:8px}
nav a{font:600 .9rem var(--body);color:var(--ink);text-decoration:none;border:1px solid var(--rule);border-radius:999px;padding:6px 14px;display:flex;align-items:center;gap:8px;background:var(--surface)}
nav a:hover,nav a:focus-visible{border-color:var(--ink2);outline:none}
.dot{width:10px;height:10px;border-radius:50%;background:var(--accent);display:inline-block;flex:none}
.s1{--accent:var(--s1)} .s2{--accent:var(--s2)} .s3{--accent:var(--s3)}
.tablewrap{overflow-x:auto;border:1px solid var(--rule);border-radius:10px;background:var(--surface)}
table{border-collapse:collapse;width:100%;min-width:640px;font-variant-numeric:tabular-nums}
th,td{padding:12px 16px;text-align:left;border-bottom:1px solid var(--rule);vertical-align:baseline}
tbody tr:last-child th,tbody tr:last-child td{border-bottom:0}
thead th{font:600 .85rem var(--body);color:var(--ink2)}
thead th.s1,thead th.s2,thead th.s3{color:var(--ink)} thead th .dot{margin-right:8px}
tbody th{font-weight:500;color:var(--ink2);font-size:.92rem}
.v{font-family:var(--mono);font-size:.95rem;display:inline-block;min-width:3.6em}
.v.ag{color:var(--ink2);font-weight:600}
td .v.ag::before,.legend .v.ag::before{content:"/";color:var(--muted);margin-right:.5em;font-weight:400}
.legend{display:block;font-weight:400;color:var(--muted);margin-top:2px}
.legend .v{font-size:.78rem;min-width:0;margin-right:.5em}
.note{font-size:.85rem;color:var(--muted);max-width:80ch}
figure{margin:0}
img{max-width:100%;height:auto;display:block;border-radius:8px}
.wide img{border:1px solid var(--rule)}
figcaption{font-size:.85rem;color:var(--muted);margin-top:8px;max-width:80ch}
.scn{display:grid;gap:28px;border-top:3px solid var(--accent);padding-top:28px}
.scn-head{display:grid;gap:8px}
.premise{color:var(--ink2);max-width:70ch}
.scn-grid{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:32px;align-items:start}
.scene img{border:1px solid var(--rule)}
.bul{margin:0;padding-left:1.1em;display:grid;gap:8px}
.bul li::marker{color:var(--accent)}
.three{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:32px}
.heads{margin:0;padding-left:1.6em;display:grid;gap:6px;font-size:.92rem;color:var(--ink2)}
.heads li::marker{font-family:var(--mono);font-size:.8rem;color:var(--muted)}
.wl{margin:0 0 16px;padding-left:1.1em;display:grid;gap:4px;font-size:.92rem;color:var(--ink2)}
.tag{font:600 .72rem var(--mono);letter-spacing:.08em;text-transform:uppercase;margin-bottom:4px}
.tag.up{color:var(--up)} .tag.up::before{content:"▲ "} .tag.down{color:var(--down)} .tag.down::before{content:"▼ "}
blockquote{margin:0 0 14px;padding:12px 14px;background:var(--surface);border:1px solid var(--rule);border-radius:8px;font-size:.92rem;color:var(--ink2);font-style:italic}
cite{display:block;font:normal .75rem var(--mono);color:var(--muted);margin-top:6px}
details{border:1px solid var(--rule);border-radius:8px;background:var(--surface)}
summary{cursor:pointer;padding:12px 16px;font-weight:600}
summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
details img{border-radius:0 0 8px 8px}
.findings{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px 40px}
.finding h3{margin-bottom:4px}
.finding p{color:var(--ink2);font-size:.95rem}
.caveat{background:var(--surface);border:1px solid var(--rule);border-radius:10px;padding:20px;display:grid;gap:10px}
.caveat p{color:var(--ink2);max-width:80ch}
.method{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:32px}
.method p,.method li{color:var(--ink2);font-size:.95rem}
.method ul{margin:8px 0 0;padding-left:1.1em;display:grid;gap:4px}
footer{font-size:.85rem;color:var(--muted)}
@media (max-width:860px){.scn-grid,.three,.findings,.method{grid-template-columns:minmax(0,1fr)}}
"""

FINDINGS = [
    ("Debt is the binding constraint", "Both methods add 6–15 points of GDP to public debt by 2031. In every scenario, the runs that go badly are the ones where governments had no fiscal room when a shock arrived."),
    ("Inequality rises everywhere", "All 30 AI agents and all 30 model runs end with higher inequality. The scenario changes only how fast it rises; it is fastest under AI Acceleration."),
    ("AI cuts both ways", "AI Acceleration is the fastest-growing and the most unequal world, with five times the job displacement of the other scenarios and the angriest politics relative to its prosperity."),
    ("Warming is locked in", "Every run lands between 1.56 and 1.62 °C. Over five years, policy changes who pays for climate damage, not how much warming happens."),
    ("The Global South grows fastest and is hit hardest", "India and Africa lead growth in the model, but they also absorb most climate disasters and frontier defaults. AI hollows out services-export models."),
    ("Trust erodes even when growth holds", "Trust in institutions falls in all three agent scenarios: to 35, 31 and 28 from 40. Unrest rises even in the richest world."),
]


def page():
    secs = "".join(scenario(s, i + 1) for i, s in enumerate(ORDER))
    nav = "".join(f'<a href="#{s.replace("_", "-")}" class="{KEY[s]}"><span class="dot"></span>{TITLE[s]}</a>' for s in ORDER)
    finds = "".join(f'<div class="finding"><h3>{E(t)}</h3><p>{E(b)}</p></div>' for t, b in FINDINGS)
    return f'''<title>World 2031 Futures</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700;800&family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap">
<style>{CSS}</style>
<main class="wrap">
<header class="hero">
  <p class="eyebrow">Scenario simulations · October 2026 → December 2031</p>
  <h1>World 2031<span>Three futures under today's economic and social constraints</span></h1>
  <p class="lede">Each scenario was run 10 times by two independent methods. The first is an agent-based model in which every run builds a new population of governments, firms and households and hits it with random shocks. The second is 10 separate AI agents per scenario, each reasoning year by year through one plausible path without seeing the others.</p>
  <div class="stats"><span><b>60</b> runs</span><span><b>30</b> model worlds × 2,600 agents</span><span><b>30</b> independent AI analysts</span><span><b>20</b> quarters each</span></div>
  <nav aria-label="Scenarios">{nav}</nav>
</header>

<section aria-labelledby="cmp" style="display:grid;gap:16px">
  <h2 id="cmp">The three worlds side by side</h2>
  {table()}
  <p class="note">Medians of 10 runs per method. Debt is shown as change from 2026, because the model tracks 8 regions starting at 87% of GDP while the agents used the global figure of about 95%.</p>
</section>

<figure class="wide"><img src="img/comparison.png" alt="Model medians and 10th–90th percentile bands for nine indicators across the three scenarios" loading="lazy">
<figcaption>Agent-based model: median and 10th–90th percentile band across 10 runs per scenario, quarterly, 2027–2031.</figcaption></figure>

{secs}

<section aria-labelledby="ff" style="display:grid;gap:24px">
  <h2 id="ff">What holds across all 60 runs</h2>
  <div class="findings">{finds}</div>
</section>

<figure class="wide"><img src="img/agents_outcomes.png" alt="Each AI agent's 2031 estimate for 12 indicators, by scenario" loading="lazy">
<figcaption>Each dot is one AI agent's estimate for 2031. Bars mark the median.</figcaption></figure>

<aside class="caveat" aria-labelledby="cv">
  <h3 id="cv">How far to trust the spread</h3>
  <p>The 10 AI agents in each scenario never saw each other's work, but they converged closely. All ten AI Acceleration agents put growth at 3.6–3.7%. Eight of ten drew the same kind of wildcard: autonomous AI agents interacting until a market or payment system froze. Six of ten Polycrisis agents chose a Chinese customs quarantine of Taiwan or its outlying islands. Copies of one model share the same priors, so their spread understates real uncertainty.</p>
  <p>The agent-based model's random shocks produce much wider tails, such as one Polycrisis run with almost no growth and 18% of households protesting. Read the agents' answers as the most coherent story for each scenario and the model's bands as the range of outcomes.</p>
</aside>

<section class="method" aria-labelledby="mm">
  <div><h2 id="mm" style="font-size:1.5rem;margin-bottom:10px">Method</h2>
    <p><b>Agent-based model.</b> Each run draws:</p>
    <ul><li>8 regional governments with random preferences for populism, fiscal prudence, green investment and social policy</li>
    <li>200 firms deciding when to adopt AI</li>
    <li>2,400 households with skills, jobs, wealth, sentiment and protest that spreads within regions</li></ul>
    <p style="margin-top:10px">Shocks: AI capability jumps, conflicts and energy spikes, climate disasters that grow with warming, and debt crises that grow with debt and interest rates.</p></div>
  <div><h2 style="font-size:1.5rem;margin-bottom:10px">&nbsp;</h2>
    <p><b>AI agents.</b> Every agent received the same October 2026 starting conditions and scenario premise. Each was told to simulate one coherent path year by year, without averaging toward a consensus, and to report a fixed set of metrics, a timeline, winners and losers, and one wildcard.</p>
    <p style="margin-top:10px">Starting conditions: global public debt about 95% of GDP, warming about 1.45 °C, renewables at a third of electricity, tariffs at multi-decade highs, early AI diffusion, ageing populations, low trust.</p></div>
</section>
<footer>These are illustrative scenarios, not forecasts.</footer>
</main>'''


open("world2031.html", "w").write(page())
print("ok")
