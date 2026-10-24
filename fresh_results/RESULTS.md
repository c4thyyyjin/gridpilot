# Synthetic robustness validation

## Important findings

This study exposes robustness limits, not operational guarantees. Typical-profile MPC feasibility: original: 19/20; online: 12/20; delayed_online: 0/20; ramp_online: 12/20; overhead_online: 10/20; combined: 0/20; guarded_online: 20/20; guarded_delayed: 20/20; guarded_combined: 19/20. Overall 655/1080 method runs were feasible. 18/81 paired monetary comparisons met the all-pairs-feasible rule. These are 20 unique synthetic seeds, not 1080 independent seeds.

{
  "config_snapshot": {
    "HORIZON_H": 72,
    "DT_H": 1.0,
    "SEED": 42,
    "PRICE_LEVELS": {
      "critical": 1.297,
      "peak": 1.1,
      "flat": 0.687,
      "valley": 0.372
    },
    "TOU_HOURS": {
      "0": "valley",
      "1": "valley",
      "2": "valley",
      "3": "valley",
      "4": "valley",
      "5": "valley",
      "6": "valley",
      "12": "valley",
      "13": "valley",
      "17": "peak",
      "18": "peak",
      "21": "peak",
      "19": "critical",
      "20": "critical"
    },
    "GRID_CO2_MEAN": 0.537,
    "GRID_CO2_SWING": 0.2,
    "SOLAR_PEAK_MW": 12.0,
    "WIND_MEAN_MW": 3.0,
    "GREEN_PRICE": 0.3,
    "GREEN_CO2": 0.0,
    "ALLOW_EXPORT": false,
    "BATT_ENERGY_MWH": 20.0,
    "BATT_POWER_MW": 10.0,
    "BATT_EFF_CHARGE": 0.95,
    "BATT_EFF_DISCHARGE": 0.95,
    "BATT_SOC_MIN": 0.1,
    "BATT_SOC_MAX": 0.95,
    "BATT_SOC_START": 0.5,
    "BATT_DEGRADATION": 0.05,
    "IT_CAPACITY_MW": 20.0,
    "PUE": 1.2,
    "SHARE_INFERENCE": 0.35,
    "SHARE_TRAINING": 0.45,
    "SHARE_BATCH": 0.2,
    "AVG_IT_UTILISATION": 0.7,
    "N_TRAINING_JOBS": 6,
    "N_BATCH_JOBS": 12,
    "BATCH_MAX_DEADLINE_H": 24,
    "FORECAST_ERROR_LEVELS": [
      0.0,
      0.1,
      0.2,
      0.3
    ],
    "LAMBDA_SWEEP": [
      0,
      100,
      500,
      1000,
      2000,
      5000,
      10000,
      20000
    ],
    "LAMBDA_DEFAULT": 100,
    "INFERENCE_NIGHT_FACTOR": 0.55,
    "INFERENCE_EVENING_FACTOR": 1.35,
    "TRAIN_WINDOW_H": [
      30,
      60
    ],
    "BATCH_WINDOW_H": [
      6,
      24
    ],
    "JOB_SLACK": [
      0.35,
      0.6
    ],
    "GRID_IMPORT_LIMIT_MW": 26.0,
    "PEN_UNMET_CNY_PER_MWH": 100000.0,
    "PEN_GRID_OVERFLOW_CNY_PER_MWH": 100000.0,
    "GRID_IMPORT_LIMIT_SWEEP_MW": [
      10.0,
      16.0,
      20.0,
      24.0,
      26.0,
      28.0,
      null
    ],
    "BATT_INSTALLED_COST_SWEEP_CNY_PER_KWH": [
      500.0,
      1000.0,
      1500.0
    ],
    "BATT_INSTALLED_POWER_COST_CNY_PER_KW": 0.0,
    "BATT_ECONOMIC_LIFE_YEARS": 10,
    "ECON_DISCOUNT_RATE": 0.08,
    "BATT_FIXED_OM_FRACTION_PER_YEAR": 0.015,
    "DEMAND_CHARGE_SWEEP_CNY_PER_KW_MONTH": [
      0.0,
      20.0,
      40.0
    ],
    "ECON_HOURS_PER_YEAR": 8760.0,
    "PEN_RAMP_CNY_PER_MWH": 100000.0
  },
  "seeds": [
    220,
    221,
    222,
    223,
    224,
    225,
    226,
    227,
    228,
    229,
    230,
    231,
    232,
    233,
    234,
    235,
    236,
    237,
    238,
    239
  ],
  "profiles": {
    "typical": [
      1.0,
      1.0,
      1.0
    ],
    "low_green": [
      0.5,
      0.75,
      1.0
    ],
    "high_inference": [
      0.8,
      1.0,
      1.35
    ]
  },
  "policies": {
    "original": {
      "observation_delay_h": 0,
      "advance_job_knowledge": true,
      "checkpoint_overhead_fraction": 0.0,
      "ramp_mw_per_hour": null,
      "service_guard": false,
      "fast_safety": false
    },
    "online": {
      "observation_delay_h": 0,
      "advance_job_knowledge": false,
      "checkpoint_overhead_fraction": 0.0,
      "ramp_mw_per_hour": null,
      "service_guard": false,
      "fast_safety": false
    },
    "delayed_online": {
      "observation_delay_h": 1,
      "advance_job_knowledge": false,
      "checkpoint_overhead_fraction": 0.0,
      "ramp_mw_per_hour": null,
      "service_guard": false,
      "fast_safety": false
    },
    "ramp_online": {
      "observation_delay_h": 0,
      "advance_job_knowledge": false,
      "checkpoint_overhead_fraction": 0.0,
      "ramp_mw_per_hour": 2.0,
      "service_guard": false,
      "fast_safety": false
    },
    "overhead_online": {
      "observation_delay_h": 0,
      "advance_job_knowledge": false,
      "checkpoint_overhead_fraction": 0.05,
      "ramp_mw_per_hour": null,
      "service_guard": false,
      "fast_safety": false
    },
    "combined": {
      "observation_delay_h": 1,
      "advance_job_knowledge": false,
      "checkpoint_overhead_fraction": 0.05,
      "ramp_mw_per_hour": 2.0,
      "service_guard": false,
      "fast_safety": false
    },
    "guarded_online": {
      "observation_delay_h": 0,
      "advance_job_knowledge": false,
      "checkpoint_overhead_fraction": 0.0,
      "ramp_mw_per_hour": null,
      "service_guard": true,
      "fast_safety": true
    },
    "guarded_delayed": {
      "observation_delay_h": 1,
      "advance_job_knowledge": false,
      "checkpoint_overhead_fraction": 0.0,
      "ramp_mw_per_hour": null,
      "service_guard": true,
      "fast_safety": true
    },
    "guarded_combined": {
      "observation_delay_h": 1,
      "advance_job_knowledge": false,
      "checkpoint_overhead_fraction": 0.05,
      "ramp_mw_per_hour": 2.0,
      "service_guard": true,
      "fast_safety": true
    }
  },
  "forecast_error": 0.3,
  "generator_feasibility_screen": false,
  "horizon_hours": 72.0,
  "lambda_cny_per_tonne": 100,
  "grid_limit_mw": 26.0,
  "selection": "unscreened synthetic draws; seeds 100\u2013119 and 200\u2013219 informed development; seeds 220\u2013239 are designated fresh validation; the seeds field identifies this run"
}

No real operational traces were supplied. Profiles are stress assumptions, not verified seasons. Each method pair has identical observations, job information and compute assumptions. Legacy delayed policies have no current-hour protection. Guarded policies explicitly use current telemetry in a fast safety/service stage; both baseline and MPC receive that same capability. Guarded policies fix service with a laxity heuristic, shared with the matched no-battery reference; no universal deadline guarantee is claimed. True battery state is available from commands; price/carbon and exogenous forecasts remain known. Checkpoint overhead is amortized, not per-resume; GPU units remain continuous. Approximate pointwise 95% paired Student-t intervals are suppressed for any infeasible pair. All failed/degraded draws remain in raw records; no feasibility filtering is used.

| profile        | policy           | method   |   feasible_runs |   runs |   max_sla_violations |   max_capacity_violation_hours |   max_grid_limit_violation_hours |   max_ramp_violation_events |   mean_compute_overhead_mwh |
|:---------------|:-----------------|:---------|----------------:|-------:|---------------------:|-------------------------------:|---------------------------------:|----------------------------:|----------------------------:|
| typical        | original         | baseline |              19 |     20 |                    1 |                              0 |                                0 |                           0 |                       0     |
| typical        | original         | MPC      |              19 |     20 |                    1 |                              0 |                                0 |                           0 |                       0     |
| typical        | online           | baseline |              19 |     20 |                    1 |                              0 |                                0 |                           0 |                       0     |
| typical        | online           | MPC      |              12 |     20 |                    6 |                              0 |                                0 |                           0 |                       0     |
| typical        | delayed_online   | baseline |               0 |     20 |                    1 |                             18 |                                0 |                           0 |                       0     |
| typical        | delayed_online   | MPC      |               0 |     20 |                    7 |                             20 |                                7 |                           0 |                       0     |
| typical        | ramp_online      | baseline |               4 |     20 |                    1 |                              0 |                                0 |                           5 |                       0     |
| typical        | ramp_online      | MPC      |              12 |     20 |                    7 |                              0 |                                0 |                           1 |                       0     |
| typical        | overhead_online  | baseline |              18 |     20 |                    1 |                              0 |                                0 |                           0 |                      34.468 |
| typical        | overhead_online  | MPC      |              10 |     20 |                    8 |                              0 |                                0 |                           0 |                      34.119 |
| typical        | combined         | baseline |               0 |     20 |                    1 |                             20 |                                0 |                           5 |                      34.447 |
| typical        | combined         | MPC      |               0 |     20 |                    9 |                             21 |                                7 |                           1 |                      34.134 |
| typical        | guarded_online   | baseline |              20 |     20 |                    0 |                              0 |                                0 |                           0 |                       0     |
| typical        | guarded_online   | MPC      |              20 |     20 |                    0 |                              0 |                                0 |                           0 |                       0     |
| typical        | guarded_delayed  | baseline |              20 |     20 |                    0 |                              0 |                                0 |                           0 |                       0     |
| typical        | guarded_delayed  | MPC      |              20 |     20 |                    0 |                              0 |                                0 |                           0 |                       0     |
| typical        | guarded_combined | baseline |              19 |     20 |                    1 |                              0 |                                0 |                           0 |                      34.478 |
| typical        | guarded_combined | MPC      |              19 |     20 |                    1 |                              0 |                                0 |                           0 |                      34.478 |
| low_green      | original         | baseline |              19 |     20 |                    1 |                              0 |                                0 |                           0 |                       0     |
| low_green      | original         | MPC      |              19 |     20 |                    1 |                              0 |                                0 |                           0 |                       0     |
| low_green      | online           | baseline |              19 |     20 |                    1 |                              0 |                                0 |                           0 |                       0     |
| low_green      | online           | MPC      |              13 |     20 |                    6 |                              0 |                                0 |                           0 |                       0     |
| low_green      | delayed_online   | baseline |               0 |     20 |                    1 |                             18 |                                0 |                           0 |                       0     |
| low_green      | delayed_online   | MPC      |               0 |     20 |                    6 |                             20 |                               10 |                           0 |                       0     |
| low_green      | ramp_online      | baseline |               4 |     20 |                    1 |                              0 |                                0 |                           5 |                       0     |
| low_green      | ramp_online      | MPC      |              12 |     20 |                    8 |                              0 |                                0 |                           1 |                       0     |
| low_green      | overhead_online  | baseline |              18 |     20 |                    1 |                              0 |                                0 |                           0 |                      34.468 |
| low_green      | overhead_online  | MPC      |              10 |     20 |                   10 |                              0 |                                0 |                           0 |                      34.128 |
| low_green      | combined         | baseline |               0 |     20 |                    1 |                             20 |                                0 |                           5 |                      34.447 |
| low_green      | combined         | MPC      |               0 |     20 |                    9 |                             20 |                               10 |                           1 |                      34.156 |
| low_green      | guarded_online   | baseline |              20 |     20 |                    0 |                              0 |                                0 |                           0 |                       0     |
| low_green      | guarded_online   | MPC      |              20 |     20 |                    0 |                              0 |                                0 |                           0 |                       0     |
| low_green      | guarded_delayed  | baseline |              20 |     20 |                    0 |                              0 |                                0 |                           0 |                       0     |
| low_green      | guarded_delayed  | MPC      |              20 |     20 |                    0 |                              0 |                                0 |                           0 |                       0     |
| low_green      | guarded_combined | baseline |              19 |     20 |                    1 |                              0 |                                0 |                           0 |                      34.478 |
| low_green      | guarded_combined | MPC      |              19 |     20 |                    1 |                              0 |                                0 |                           0 |                      34.478 |
| high_inference | original         | baseline |              14 |     20 |                    1 |                              0 |                                0 |                           0 |                       0     |
| high_inference | original         | MPC      |              14 |     20 |                    3 |                              0 |                                0 |                           0 |                       0     |
| high_inference | online           | baseline |              14 |     20 |                    1 |                              0 |                                0 |                           0 |                       0     |
| high_inference | online           | MPC      |               7 |     20 |                   10 |                              0 |                                0 |                           0 |                       0     |
| high_inference | delayed_online   | baseline |               0 |     20 |                    1 |                             22 |                                1 |                           0 |                       0     |
| high_inference | delayed_online   | MPC      |               0 |     20 |                    9 |                             24 |                                7 |                           0 |                       0     |
| high_inference | ramp_online      | baseline |               1 |     20 |                    1 |                              0 |                                0 |                           4 |                       0     |
| high_inference | ramp_online      | MPC      |               8 |     20 |                    8 |                              0 |                                0 |                           1 |                       0     |
| high_inference | overhead_online  | baseline |              10 |     20 |                    2 |                              0 |                                0 |                           0 |                      34.195 |
| high_inference | overhead_online  | MPC      |               6 |     20 |                   11 |                              0 |                                0 |                           0 |                      33.384 |
| high_inference | combined         | baseline |               0 |     20 |                    2 |                             24 |                                1 |                           5 |                      34.131 |
| high_inference | combined         | MPC      |               0 |     20 |                   13 |                             25 |                                7 |                           2 |                      33.374 |
| high_inference | guarded_online   | baseline |              20 |     20 |                    0 |                              0 |                                0 |                           0 |                       0     |
| high_inference | guarded_online   | MPC      |              20 |     20 |                    0 |                              0 |                                0 |                           0 |                       0     |
| high_inference | guarded_delayed  | baseline |              20 |     20 |                    0 |                              0 |                                0 |                           0 |                       0     |
| high_inference | guarded_delayed  | MPC      |              20 |     20 |                    0 |                              0 |                                0 |                           0 |                       0     |
| high_inference | guarded_combined | baseline |              19 |     20 |                    1 |                              0 |                                0 |                           0 |                      34.478 |
| high_inference | guarded_combined | MPC      |              19 |     20 |                    1 |                              0 |                                0 |                           0 |                      34.478 |

## Paired savings

|   batch | method   | metric    |   n_pairs |   n_feasible_pairs | eligible   |   confidence | status          | ci_status   | percentage_status   |   saving_mean |   saving_ci_low |   saving_ci_high |   gain_pct_mean |   gain_pct_ci_low |   gain_pct_ci_high | profile        | policy           |
|--------:|:---------|:----------|----------:|-------------------:|:-----------|-------------:|:----------------|:------------|:--------------------|--------------:|----------------:|-----------------:|----------------:|------------------:|-------------------:|:---------------|:-----------------|
|       0 | MPC      | objective |        20 |                 18 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | original         |
|       0 | MPC      | cost_cny  |        20 |                 18 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | original         |
|       0 | MPC      | co2_t     |        20 |                 18 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | original         |
|       1 | MPC      | objective |        20 |                 12 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | online           |
|       1 | MPC      | cost_cny  |        20 |                 12 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | online           |
|       1 | MPC      | co2_t     |        20 |                 12 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | online           |
|       2 | MPC      | objective |        20 |                  0 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | delayed_online   |
|       2 | MPC      | cost_cny  |        20 |                  0 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | delayed_online   |
|       2 | MPC      | co2_t     |        20 |                  0 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | delayed_online   |
|       3 | MPC      | objective |        20 |                  2 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | ramp_online      |
|       3 | MPC      | cost_cny  |        20 |                  2 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | ramp_online      |
|       3 | MPC      | co2_t     |        20 |                  2 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | ramp_online      |
|       4 | MPC      | objective |        20 |                 10 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | overhead_online  |
|       4 | MPC      | cost_cny  |        20 |                 10 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | overhead_online  |
|       4 | MPC      | co2_t     |        20 |                 10 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | overhead_online  |
|       5 | MPC      | objective |        20 |                  0 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | combined         |
|       5 | MPC      | cost_cny  |        20 |                  0 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | combined         |
|       5 | MPC      | co2_t     |        20 |                  0 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | combined         |
|       6 | MPC      | objective |        20 |                 20 | True       |         0.95 | feasible        | available   | defined             |     37499.1   |       36086.8   |        38911.3   |           5.034 |             4.881 |              5.188 | typical        | guarded_online   |
|       6 | MPC      | cost_cny  |        20 |                 20 | True       |         0.95 | feasible        | available   | defined             |     36186.2   |       34844.2   |        37528.1   |           5.177 |             5.025 |              5.329 | typical        | guarded_online   |
|       6 | MPC      | co2_t     |        20 |                 20 | True       |         0.95 | feasible        | available   | defined             |        13.129 |          11.32  |           14.938 |           2.861 |             2.464 |              3.257 | typical        | guarded_online   |
|       7 | MPC      | objective |        20 |                 20 | True       |         0.95 | feasible        | available   | defined             |     37499.1   |       36086.8   |        38911.3   |           5.034 |             4.881 |              5.188 | typical        | guarded_delayed  |
|       7 | MPC      | cost_cny  |        20 |                 20 | True       |         0.95 | feasible        | available   | defined             |     36186.2   |       34844.2   |        37528.1   |           5.177 |             5.025 |              5.329 | typical        | guarded_delayed  |
|       7 | MPC      | co2_t     |        20 |                 20 | True       |         0.95 | feasible        | available   | defined             |        13.129 |          11.32  |           14.938 |           2.861 |             2.464 |              3.257 | typical        | guarded_delayed  |
|       8 | MPC      | objective |        20 |                 19 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | guarded_combined |
|       8 | MPC      | cost_cny  |        20 |                 19 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | guarded_combined |
|       8 | MPC      | co2_t     |        20 |                 19 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | typical        | guarded_combined |
|       9 | MPC      | objective |        20 |                 18 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | original         |
|       9 | MPC      | cost_cny  |        20 |                 18 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | original         |
|       9 | MPC      | co2_t     |        20 |                 18 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | original         |
|      10 | MPC      | objective |        20 |                 13 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | online           |
|      10 | MPC      | cost_cny  |        20 |                 13 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | online           |
|      10 | MPC      | co2_t     |        20 |                 13 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | online           |
|      11 | MPC      | objective |        20 |                  0 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | delayed_online   |
|      11 | MPC      | cost_cny  |        20 |                  0 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | delayed_online   |
|      11 | MPC      | co2_t     |        20 |                  0 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | delayed_online   |
|      12 | MPC      | objective |        20 |                  2 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | ramp_online      |
|      12 | MPC      | cost_cny  |        20 |                  2 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | ramp_online      |
|      12 | MPC      | co2_t     |        20 |                  2 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | ramp_online      |
|      13 | MPC      | objective |        20 |                 10 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | overhead_online  |
|      13 | MPC      | cost_cny  |        20 |                 10 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | overhead_online  |
|      13 | MPC      | co2_t     |        20 |                 10 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | overhead_online  |
|      14 | MPC      | objective |        20 |                  0 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | combined         |
|      14 | MPC      | cost_cny  |        20 |                  0 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | combined         |
|      14 | MPC      | co2_t     |        20 |                  0 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | combined         |
|      15 | MPC      | objective |        20 |                 20 | True       |         0.95 | feasible        | available   | defined             |     40518.5   |       39231.6   |        41805.5   |           5.088 |             4.947 |              5.229 | low_green      | guarded_online   |
|      15 | MPC      | cost_cny  |        20 |                 20 | True       |         0.95 | feasible        | available   | defined             |     39859.4   |       38575.1   |        41143.6   |           5.358 |             5.209 |              5.507 | low_green      | guarded_online   |
|      15 | MPC      | co2_t     |        20 |                 20 | True       |         0.95 | feasible        | available   | defined             |         6.591 |           5.587 |            7.596 |           1.259 |             1.066 |              1.453 | low_green      | guarded_online   |
|      16 | MPC      | objective |        20 |                 20 | True       |         0.95 | feasible        | available   | defined             |     40518.5   |       39231.6   |        41805.5   |           5.088 |             4.947 |              5.229 | low_green      | guarded_delayed  |
|      16 | MPC      | cost_cny  |        20 |                 20 | True       |         0.95 | feasible        | available   | defined             |     39859.4   |       38575.1   |        41143.6   |           5.358 |             5.209 |              5.507 | low_green      | guarded_delayed  |
|      16 | MPC      | co2_t     |        20 |                 20 | True       |         0.95 | feasible        | available   | defined             |         6.591 |           5.587 |            7.596 |           1.259 |             1.066 |              1.453 | low_green      | guarded_delayed  |
|      17 | MPC      | objective |        20 |                 19 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | guarded_combined |
|      17 | MPC      | cost_cny  |        20 |                 19 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | guarded_combined |
|      17 | MPC      | co2_t     |        20 |                 19 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | low_green      | guarded_combined |
|      18 | MPC      | objective |        20 |                 11 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | original         |
|      18 | MPC      | cost_cny  |        20 |                 11 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | original         |
|      18 | MPC      | co2_t     |        20 |                 11 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | original         |
|      19 | MPC      | objective |        20 |                  5 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | online           |
|      19 | MPC      | cost_cny  |        20 |                  5 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | online           |
|      19 | MPC      | co2_t     |        20 |                  5 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | online           |
|      20 | MPC      | objective |        20 |                  0 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | delayed_online   |
|      20 | MPC      | cost_cny  |        20 |                  0 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | delayed_online   |
|      20 | MPC      | co2_t     |        20 |                  0 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | delayed_online   |
|      21 | MPC      | objective |        20 |                  1 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | ramp_online      |
|      21 | MPC      | cost_cny  |        20 |                  1 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | ramp_online      |
|      21 | MPC      | co2_t     |        20 |                  1 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | ramp_online      |
|      22 | MPC      | objective |        20 |                  4 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | overhead_online  |
|      22 | MPC      | cost_cny  |        20 |                  4 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | overhead_online  |
|      22 | MPC      | co2_t     |        20 |                  4 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | overhead_online  |
|      23 | MPC      | objective |        20 |                  0 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | combined         |
|      23 | MPC      | cost_cny  |        20 |                  0 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | combined         |
|      23 | MPC      | co2_t     |        20 |                  0 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | combined         |
|      24 | MPC      | objective |        20 |                 20 | True       |         0.95 | feasible        | available   | defined             |     41876.8   |       40613.3   |        43140.2   |           4.922 |             4.809 |              5.035 | high_inference | guarded_online   |
|      24 | MPC      | cost_cny  |        20 |                 20 | True       |         0.95 | feasible        | available   | defined             |     41127.4   |       39864.7   |        42390.1   |           5.168 |             5.049 |              5.287 | high_inference | guarded_online   |
|      24 | MPC      | co2_t     |        20 |                 20 | True       |         0.95 | feasible        | available   | defined             |         7.494 |           6.286 |            8.701 |           1.361 |             1.145 |              1.578 | high_inference | guarded_online   |
|      25 | MPC      | objective |        20 |                 20 | True       |         0.95 | feasible        | available   | defined             |     41876.8   |       40613.3   |        43140.2   |           4.922 |             4.809 |              5.035 | high_inference | guarded_delayed  |
|      25 | MPC      | cost_cny  |        20 |                 20 | True       |         0.95 | feasible        | available   | defined             |     41127.4   |       39864.7   |        42390.1   |           5.168 |             5.049 |              5.287 | high_inference | guarded_delayed  |
|      25 | MPC      | co2_t     |        20 |                 20 | True       |         0.95 | feasible        | available   | defined             |         7.494 |           6.286 |            8.701 |           1.361 |             1.145 |              1.578 | high_inference | guarded_delayed  |
|      26 | MPC      | objective |        20 |                 19 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | guarded_combined |
|      26 | MPC      | cost_cny  |        20 |                 19 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | guarded_combined |
|      26 | MPC      | co2_t     |        20 |                 19 | False      |         0.95 | infeasible_runs | ineligible  | defined             |       nan     |         nan     |          nan     |         nan     |           nan     |            nan     | high_inference | guarded_combined |