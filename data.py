"""Scenario generator: builds one synthetic 72 h data-center scenario.

Conventions (shared by every scheduler and by evaluate.py):
  * Arrays have length T = HORIZON_H, index t = hour t .. t+1.
  * Power in MW, energy in MWh.
  * Job power / energy / max_power are in *IT* MW (facility = IT * PUE).
  * inference_* arrays are in *IT* MW too.
  * green_* arrays are facility-side MW (solar + wind).
"""
from dataclasses import dataclass, field
import numpy as np
import config as C


@dataclass
class Job:
    id: str
    kind: str            # "training" or "batch"
    release: int         # first hour the job may run
    deadline: int        # job must be finished by the END of hour deadline-1 (exclusive)
    energy_mwh: float    # total IT energy needed
    max_power_mw: float  # max IT power while running


@dataclass
class Scenario:
    T: int
    price: np.ndarray          # CNY/kWh
    grid_co2: np.ndarray       # kgCO2/kWh  (== tCO2/MWh)
    solar_fc: np.ndarray
    wind_fc: np.ndarray
    solar_act: np.ndarray
    wind_act: np.ndarray
    inference_fc: np.ndarray   # IT MW
    inference_act: np.ndarray  # IT MW
    jobs: list = field(default_factory=list)
    forecast_error: float = 0.0
    seed: int = 0
    generation_attempts: int = 1
    generation_screened: bool = True

    @property
    def green_fc(self):
        return self.solar_fc + self.wind_fc

    @property
    def green_act(self):
        return self.solar_act + self.wind_act


def _tou_price(T):
    hours = np.arange(T) % 24
    return np.array([C.PRICE_LEVELS[C.TOU_HOURS.get(int(h), "flat")] for h in hours])


def _grid_co2(T):
    h = (np.arange(T) % 24) + 0.5
    shape = -0.7 * np.cos(2 * np.pi * (h - 13) / 24) + 0.6 * np.exp(-(((h - 20) / 2.5) ** 2))
    one_day = shape[:24]
    shape = (shape - one_day.mean()) / np.abs(one_day - one_day.mean()).max()
    return C.GRID_CO2_MEAN * (1 + C.GRID_CO2_SWING * shape)


def _ar1(rng, n, phi=0.8):
    x = np.zeros(n)
    e = rng.standard_normal(n) * np.sqrt(1 - phi ** 2)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


def _green(rng, T):
    h = (np.arange(T) % 24) + 0.5
    bell = np.where((h >= 6) & (h <= 18), np.sin(np.pi * (h - 6) / 12), 0.0)
    days = int(np.ceil(T / 24))
    clearness = np.repeat(rng.uniform(0.6, 1.0, days), 24)[:T]   # cloudy vs clear days
    solar = C.SOLAR_PEAK_MW * bell * clearness
    wind = np.clip(C.WIND_MEAN_MW * (1 + 0.6 * _ar1(rng, T, 0.9)), 0, 2.5 * C.WIND_MEAN_MW)
    return solar, wind


def _inference_it(T):
    """Daily curve: night low, evening peak, scaled so mean = SHARE_INFERENCE * mean IT load."""
    h = (np.arange(T) % 24) + 0.5
    curve = 1 + 0.45 * np.sin(2 * np.pi * (h - 14) / 24)          # peaks ~20h, low ~8h
    lo, hi = C.INFERENCE_NIGHT_FACTOR, C.INFERENCE_EVENING_FACTOR
    curve = lo + (curve - curve.min()) / (curve.max() - curve.min()) * (hi - lo)
    mean_it = C.SHARE_INFERENCE * C.AVG_IT_UTILISATION * C.IT_CAPACITY_MW
    return mean_it * curve / curve.mean()


def _split(rng, total, n):
    w = rng.uniform(0.5, 1.5, n)
    return total * w / w.sum()


def _make_jobs(rng, T):
    mean_it = C.AVG_IT_UTILISATION * C.IT_CAPACITY_MW
    jobs = []
    specs = [("training", C.N_TRAINING_JOBS, C.SHARE_TRAINING, C.TRAIN_WINDOW_H, "T"),
             ("batch", C.N_BATCH_JOBS, C.SHARE_BATCH, C.BATCH_WINDOW_H, "B")]
    for kind, n, share, (wlo, whi), tag in specs:
        energies = _split(rng, share * mean_it * T, n)
        for i, e in enumerate(energies):
            win = int(rng.integers(wlo, whi + 1))
            if kind == "batch":
                win = min(win, C.BATCH_MAX_DEADLINE_H)
            rel = int(rng.integers(0, max(1, T - win)))
            dl = min(T, rel + win)
            win = dl - rel
            run_h = rng.uniform(*C.JOB_SLACK) * win          # hours needed at max power
            jobs.append(Job(f"{tag}{i+1}", kind, rel, dl, float(e), float(e / max(run_h, 1.0))))
    return jobs


def check_feasible(sc: Scenario):
    """Necessary condition: for every [a,b), energy of jobs whose window lies inside [a,b)
    fits in the spare IT capacity there. Also each job can finish on its own."""
    spare = np.maximum(C.IT_CAPACITY_MW - sc.inference_fc, 0)
    spare = np.minimum(spare, C.IT_CAPACITY_MW - sc.inference_act.clip(max=C.IT_CAPACITY_MW))
    for j in sc.jobs:
        if j.energy_mwh > j.max_power_mw * (j.deadline - j.release) + 1e-9:
            return False
    pts = sorted({j.release for j in sc.jobs} | {j.deadline for j in sc.jobs})
    for a in pts:
        for b in pts:
            if b <= a:
                continue
            need = sum(j.energy_mwh for j in sc.jobs if j.release >= a and j.deadline <= b)
            if need > spare[a:b].sum() * 0.9:   # keep 10 % margin so the problem is not razor-tight
                return False
    return True


def make_scenario(seed=C.SEED, forecast_error=0.0, *, screen_feasibility=True) -> Scenario:
    if C.DT_H != 1.0:
        raise ValueError(
            f"DT_H={C.DT_H}: scenario generation and feasibility screening assume "
            "hourly resolution (DT_H=1). Other step sizes make the screening "
            "unreliable; use DT_H=1. Subhourly scenario generation is unsupported."
        )
    T = C.HORIZON_H
    for attempt in range(500):
        rng = np.random.default_rng(seed * 1000 + attempt)
        solar_fc, wind_fc = _green(rng, T)
        inf_fc = _inference_it(T)
        jobs = _make_jobs(rng, T)
        # Actual = forecast * (1 + smooth noise). With forecast_error = 0, actual == forecast.
        nrng = np.random.default_rng(seed + 7919)
        e = forecast_error
        solar_act = np.clip(solar_fc * (1 + e * _ar1(nrng, T, 0.8)), 0, None)
        wind_act = np.clip(wind_fc * (1 + e * _ar1(nrng, T, 0.8)), 0, None)
        inf_act = np.clip(inf_fc * (1 + 0.5 * e * _ar1(nrng, T, 0.8)), 0, None)
        sc = Scenario(T, _tou_price(T), _grid_co2(T), solar_fc, wind_fc,
                      solar_act, wind_act, inf_fc, inf_act, jobs, forecast_error, seed)
        sc.generation_attempts = attempt + 1
        sc.generation_screened = bool(screen_feasibility)
        if not screen_feasibility or check_feasible(sc):
            return sc
    raise RuntimeError("could not generate a feasible scenario; loosen config")
