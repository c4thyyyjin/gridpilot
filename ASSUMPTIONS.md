# Assumptions

No data was provided, so every number below is either taken from a public source or is an explicit modelling choice.
Each assumption lists **why** we chose it and **what changes if it is wrong** — the judges will ask about both.
All values live in `config.py`, so every assumption can be changed in one place and tested in the sensitivity analysis.

## 1. Scope and goal

| # | Assumption | Why | If wrong |
|---|---|---|---|
| S1 | We model **one AI data center** over a **72-hour horizon** at **1-hour resolution**. | Long enough to include 3 solar cycles and multi-day training jobs; short enough for an exact LP to solve in seconds. | Subhourly simulation requires a revised generator and new validation. It is currently unsupported; the effect on savings has not been established. |
| S2 | **Service quality is required for a valid savings claim.** Inference is not deferred. Strict LPs enforce job deadlines; infeasible windows use a logged penalized fallback. Online heuristic failures are scored as degraded, and savings comparisons containing failures are suppressed. | The problem says "without compromising its service". A schedule that saves money by missing deadlines is not a valid solution. | Arbitrary workloads need not be feasible. Failed cases define limits of the operating envelope; they are not successful savings. |
| S3 | **"Good" = lowest total cost after pricing carbon**: `cost + λ · CO₂`. λ (CNY per tonne CO₂) is a dial, not a fixed answer. | "Cheaper" and "greener" conflict. Instead of hiding that choice, we sweep λ and show **sampled cost/carbon trade-offs**, then recommend a default. | Nothing breaks — a different priority just means a different point on the same curve. |
| S4 | Secondary metrics reported: total cost (CNY), total CO₂ (t), share of demand met by green energy (%), green energy curtailed (MWh), peak grid draw (MW), SLA violations (must be 0). | One number hides trade-offs; these show *where* the savings come from. | — |

## 2. Electricity supply

| # | Assumption | Value | Source / reasoning | If wrong |
|---|---|---|---|---|
| E1 | Grid price follows a **4-level time-of-use (TOU) tariff**. | Critical peak 1.297, peak 1.100, flat 0.687, valley 0.372 CNY/kWh | Scenario price levels attributed to State Grid Henan's July 2025 agent-purchase tariff. The exact customer/voltage row and components have not been independently confirmed in this workspace; treat these as illustrative scenario levels, not an applicable bill. TOU is the common structure in China; most regions use peak / off-peak / valley levels. | A flatter tariff (smaller peak–valley spread) shrinks the money saved by shifting load — tested in sensitivity analysis. |
| E2 | TOU **hours**: valley 00–07 and 12–14, critical peak 19–21, peak 17–19 and 21–22, flat otherwise. | — | Our choice. The midday valley reflects recent Chinese policies that add valley hours around noon when solar is abundant (e.g. Shandong's 11:00–14:00 deep valley, Heilongjiang adding 12:00–14:00). | Different hours move *when* jobs run, not whether scheduling helps. |
| E3 | Grid **carbon intensity varies by hour** around a mean of **0.537 kgCO₂/kWh**: lower at midday, higher in the evening (±20 %). | mean 0.537 | Mean = China's national average power-sector CO₂ factor for 2022 (MEE & NBS, published Dec 2024). The hourly shape is synthetic; research shows China's grid factor varies strongly over time, so a constant value would be unrealistic. | If carbon intensity were flat, carbon savings would come **only** from using more green energy, not from timing. We show this case. |
| E4 | On-site / dedicated **green supply = solar + wind**, with forecast error. | Solar peak 12 MW (bell curve 06–18 h, daily clearness 0.6–1.0); wind mean 3 MW (AR(1) noise) | Synthetic profiles. Sized (and checked in `baseline.py`: ~29 % of facility energy in the baseline, before battery/shifting) so green energy covers roughly 30 % of demand — enough to matter, not enough to run on alone ("cheap but unstable"). | More green capacity → larger benefit from scheduling, because more surplus would otherwise be wasted. |
| E5 | Green energy costs **0.30 CNY/kWh** (contracted price) and emits **0 kgCO₂/kWh** at point of use. | 0.30 | Assumption: cheaper than every modeled grid level, matching "cheap but unstable". | The current green-first LP rejects tariffs where grid price plus the carbon term is below the green rate; such cases require a different dispatch formulation. |
| E6 | **No export to the grid.** Unused green energy is **curtailed** (wasted). | — | Simplifies the model and is common for behind-the-meter supply. | With export allowed, surplus would earn money and storage/shifting would be slightly less valuable. |

## 3. Battery storage (Hithium-type LFP system)

| # | Assumption | Value | Source / reasoning | If wrong |
|---|---|---|---|---|
| B1 | Battery energy / power | 20 MWh / 10 MW (2-hour system) | 2-hour containerised LFP systems (~5 MWh per container) are standard; 4 containers ≈ 20 MWh. | Sensitivity: 0, 10, 20, 40 MWh — shows the value of each extra MWh. |
| B2 | Round-trip efficiency | 90 % (≈ 95 % each way) | Manufacturer figures for utility-scale LFP range from about 88 % to 95 %. We take a middle value. | Lower efficiency makes small price spreads not worth arbitraging. |
| B3 | Allowed state of charge | 10 %–95 %, start = end = 50 % | Protects battery life; equal start/end stops the optimiser "cheating" by draining the battery at the end. | — |
| B4 | Degradation cost | 0.05 CNY per kWh discharged | Assumption that discourages pointless cycling. | If set to 0 the battery cycles more aggressively; savings look slightly higher but less realistic. |

## 4. Computing workload

| # | Assumption | Value | Reasoning | If wrong |
|---|---|---|---|---|
| W1 | IT capacity | 20 MW | A mid-sized AI data center. | Results scale roughly linearly. |
| W2 | Facility power = IT power × **PUE 1.2** (constant) | 1.2 | Uptime Institute 2025: global average PUE 1.54; hyperscalers ~1.10–1.15. New liquid-cooled AI halls sit near the efficient end, so 1.2 is a cautious middle. | Higher PUE changes demand relative to fixed battery and grid limits; percentage savings may change and require sensitivity testing. Temperature-dependent PUE remains outside the model. |
| W3 | **Inference** (serving users): **not deferrable**. Follows a daily curve (low at night, peak in the evening), ≈ 35 % of energy. | — | Users expect instant answers; delaying would break the SLA. | If part of inference could tolerate delay, more flexibility → more savings. |
| W4 | **Training jobs**: deferrable, each has a release time, deadline, total energy and max power. Can pause and resume (checkpointing). ≈ 45 % of energy. | — | Large training runs checkpoint regularly; a few hours of delay usually doesn't matter. | If jobs cannot pause, the problem becomes integer (MILP) — harder but still solvable; savings drop. |
| W5 | **Batch / offline jobs** (evaluation, data processing, embeddings): deadline ≤ 24 h. ≈ 20 % of energy. | — | Most flexible class. | — |
| W6 | Power use is proportional to work done (no idle power, no ramp limits). | — | Keeps the model linear and exact. | Always-on fixed idle power is constant only if independent of scheduling. Controllable idle power or ramp limits can change dispatch and savings; their effect is not assumed negligible. |

## 5. Forecasts

| # | Assumption | Reasoning | If wrong |
|---|---|---|---|
| F1 | The scheduler sees a **forecast** of solar, wind and inference demand; results are scored on the **actual** values (forecast + noise, 10–30 %). Prices are known in advance (fixed tariff). | Real operators never know the future perfectly. This tests whether gains survive forecast error. | If forecasts are much worse, gains shrink; we report how much at each error level. |

## Sources

- State Grid Henan, agent-purchase electricity price table, July 2025: https://pds.gov.cn/upload/files/2025/7/1/2025年7月代理购电价格公示表-水印版.pdf
- China Briefing, China's industrial power rates 2025 (TOU structure): https://www.china-briefing.com/news/china-electricity-prices-industrial-consumers/
- SolarBe, TOU policy update incl. Shandong deep-valley hours: https://en.solarbe.com/news/50015954?lang=en
- SMM, Heilongjiang adding 12:00–14:00 valley: https://www.metal.com/en/newscontent/102993203
- MEE & NBS, 2022 power CO₂ emission factors: https://www.mee.gov.cn/xxgk2018/xxgk/xxgk01/202412/t20241226_1099413.html
- Zhang et al., monthly variability of China's grid emission factors: https://scholar.hit.edu.cn/en/publications/mitigation-drivers-of-chinas-electricity-grid-revealed-by-monthly/
- Uptime Institute Global Data Center Survey 2025 (PUE 1.54), summarised: https://mgrid.org/2025/10/01/uptime-institute-data-center-pue-stagnation-2025-liquid-cooling/
- LFP round-trip efficiency examples: https://ess-news.com/?p=2670 (88 %), https://www.ess-news.com/2025/05/07/canadian-solars-storage-unit-launches-5-mwh-battery/ (up to 95 %)

## Opt-in robustness extensions (limitations 5–7)

`robustness.Policy` optionally removes advance job knowledge, delays inference/
renewable observations, constrains per-job IT-power ramps, and applies an
amortized compute overhead fraction. Defaults preserve the original model. The
robustness suite uses one-hour observation delay, 2 MW/job/hour ramps, and 5%
amortized overhead as illustrative sensitivities, not calibrated measurements.
Useful work is IT energy times work efficiency. Ramp violations in emergency
fallback are penalized and classified degraded. Per-resume overhead and GPU
granularity remain outside this model. Held-out stress profiles are synthetic,
not measured seasons; no real operating traces were supplied. See
`docs/FIX5_7_REVIEW.md`.


## Optional guarded online controller

Guarded robustness policies assume a separate fast executor with current-hour
inference/renewable measurements, even when the optimizer has delayed telemetry.
This is explicit in decision traces and shared with the matched no-battery reference. The executor
uses laxity-based service targets and reserves ramp-down power; battery dispatch is replanned
with current job powers fixed. It is an hourly simulation assumption, not measured
hardware latency. Unknown future jobs remain unavailable. See
`docs/FIX567_GUARD_REVIEW.md` for tradeoffs and remaining limits.


## Renewable load-service attribution

Green share is renewable energy delivered to facility load divided by facility
load energy. Battery charging losses and energy still stored are not counted as
load service. The initial battery is conservatively treated as nonrenewable.
The battery is well mixed: charging mixes before withdrawal within an hourly
slot, discharge serves load before external supply, and surplus external green
charges the battery. Any discharge recycled through charging retains its source
fraction and incurs both efficiencies. Stored green decreases by withdrawn
energy (delivered discharge divided by discharge efficiency), so losses cannot
create renewable energy. The attribution convention changes no dispatch, cost
or CO2. A zero-load case reports zero green share. This is a declared bookkeeping
convention, not a claim about the unobserved origin of the real starting battery.
