"""All model parameters in one place. See ASSUMPTIONS.md for sources and reasoning.

Units: power in MW, energy in MWh, price in CNY/kWh, carbon in kgCO2/kWh.
Note: 1 CNY/kWh == 1000 CNY/MWh and 1 kgCO2/kWh == 1 tCO2/MWh.
"""

# --- Simulation --------------------------------------------------------------
HORIZON_H = 72          # S1: hours simulated
DT_H = 1.0              # S1: time step length (hours)
SEED = 42               # random seed so every run is reproducible

# --- Grid tariff (E1, E2) ----------------------------------------------------
PRICE_LEVELS = {        # CNY/kWh, illustrative levels attributed to Henan July 2025; see ASSUMPTIONS.md
    "critical": 1.297,
    "peak": 1.100,
    "flat": 0.687,
    "valley": 0.372,
}
TOU_HOURS = {           # hour of day -> level; anything not listed is "flat"
    **{h: "valley" for h in [0, 1, 2, 3, 4, 5, 6, 12, 13]},
    **{h: "peak" for h in [17, 18, 21]},
    **{h: "critical" for h in [19, 20]},
}

# --- Grid carbon (E3) --------------------------------------------------------
GRID_CO2_MEAN = 0.537   # kgCO2/kWh, China national average 2022 (MEE & NBS)
GRID_CO2_SWING = 0.20   # +/- share of hourly variation (lower midday, higher evening)

# --- Green supply (E4, E5, E6) -----------------------------------------------
SOLAR_PEAK_MW = 12.0
WIND_MEAN_MW = 3.0
GREEN_PRICE = 0.30      # CNY/kWh
GREEN_CO2 = 0.0         # kgCO2/kWh
ALLOW_EXPORT = False    # surplus green energy is curtailed

# --- Battery (B1-B4) ---------------------------------------------------------
BATT_ENERGY_MWH = 20.0
BATT_POWER_MW = 10.0
BATT_EFF_CHARGE = 0.95      # 0.95 * 0.95 ~= 0.90 round trip
BATT_EFF_DISCHARGE = 0.95
BATT_SOC_MIN = 0.10
BATT_SOC_MAX = 0.95
BATT_SOC_START = 0.50       # end SoC must equal start SoC
BATT_DEGRADATION = 0.05     # CNY per kWh discharged

# --- Workload (W1-W6) --------------------------------------------------------
IT_CAPACITY_MW = 20.0
PUE = 1.2
SHARE_INFERENCE = 0.35
SHARE_TRAINING = 0.45
SHARE_BATCH = 0.20
AVG_IT_UTILISATION = 0.70   # average IT load as share of capacity
N_TRAINING_JOBS = 6
N_BATCH_JOBS = 12
BATCH_MAX_DEADLINE_H = 24

# --- Forecast error (F1) -----------------------------------------------------
FORECAST_ERROR_LEVELS = [0.0, 0.10, 0.20, 0.30]

# --- Objective (S3) ----------------------------------------------------------
# Carbon price lambda in CNY per tonne CO2. 0 = pure cost; large = pure carbon.
LAMBDA_SWEEP = [0, 100, 500, 1000, 2000, 5000, 10000, 20000]
LAMBDA_DEFAULT = 100

# --- Scenario shape (data.py) ------------------------------------------------
INFERENCE_NIGHT_FACTOR = 0.55   # inference load at the nightly low, relative to its mean
INFERENCE_EVENING_FACTOR = 1.35 # inference load at the evening peak, relative to its mean
TRAIN_WINDOW_H = (30, 60)       # training job window length (deadline - release), hours
BATCH_WINDOW_H = (6, 24)        # batch job window length, hours
JOB_SLACK = (0.35, 0.60)        # min run time as a share of the window (lower = more flexible)

# --- Grid connection (added step 4) -------------------------------------------
GRID_IMPORT_LIMIT_MW = 26.0     # contracted import capacity (~108 % of max facility load 24 MW); ASSUMPTION, sweep it

# Explicit fallback penalties, shared by the controller and evaluator (CNY/MWh).
PEN_UNMET_CNY_PER_MWH = 100_000.0
PEN_GRID_OVERFLOW_CNY_PER_MWH = 100_000.0

# --- Economics sensitivity assumptions (not vendor quotes or applicable tariffs) ---
GRID_IMPORT_LIMIT_SWEEP_MW = [10.0, 16.0, 20.0, 24.0, 26.0, 28.0, None]
BATT_INSTALLED_COST_SWEEP_CNY_PER_KWH = [500.0, 1000.0, 1500.0]  # all-in installed energy cost
BATT_INSTALLED_POWER_COST_CNY_PER_KW = 0.0  # optional adder; avoid double-counting all-in quotes
BATT_ECONOMIC_LIFE_YEARS = 10
ECON_DISCOUNT_RATE = 0.08
BATT_FIXED_OM_FRACTION_PER_YEAR = 0.015  # excludes throughput wear already in evaluate()
DEMAND_CHARGE_SWEEP_CNY_PER_KW_MONTH = [0.0, 20.0, 40.0]
ECON_HOURS_PER_YEAR = 8760.0  # annualization assumes the simulated block repeats

# Robustness variants: emergency ramp relaxation is reported/penalized, never hidden.
PEN_RAMP_CNY_PER_MWH = 100_000.0
