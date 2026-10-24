"""Opt-in synthetic regression and validation for limitations 5–7.

No data are fitted. Unscreened generator draws retain infeasible cases. Profiles
are stress assumptions, not measured seasons. Main experiment outputs stay intact.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

import numpy as np
import pandas as pd

import config as C
from data import make_scenario
from evaluate import evaluate
from reporting import METRICS, aggregate, paired_comparisons
from robustness import POLICIES, causal_edf_schedule, causal_mpc_schedule

PROFILES = {"typical":(1.0,1.0,1.0), "low_green":(.5,.75,1.0), "high_inference":(.8,1.0,1.35)}


def run_validation(output_dir, *, seeds=range(200,220), quick=False):
    seeds=list(seeds)
    if len(seeds)!=len(set(seeds)) or not seeds or any(s in range(10) or s==42 for s in seeds):
        raise ValueError("use unique held-out seeds, excluding development seeds 0–9 and 42")
    output=Path(output_dir);output.mkdir(parents=True,exist_ok=True)
    profiles={k:PROFILES[k] for k in ("typical","low_green")} if quick else PROFILES
    policies={k:POLICIES[k] for k in ("original","online","combined")} if quick else POLICIES
    rows,summaries,statistics,pairs,traces=[],[],[],[],[]
    batch=0
    for profile,(solar,wind,inference) in profiles.items():
        for name,policy in policies.items():
            print(f"validation: {profile}/{name}, {len(seeds)} seeds",flush=True)
            batch_rows=[]
            for seed in seeds:
                sc=make_scenario(seed,forecast_error=.3,screen_feasibility=False)
                sc.solar_fc*=solar;sc.solar_act*=solar
                sc.wind_fc*=wind;sc.wind_act*=wind
                sc.inference_fc*=inference;sc.inference_act*=inference
                for method,fn in (("baseline",causal_edf_schedule),("MPC",causal_mpc_schedule)):
                    sch=fn(sc,C.GRID_IMPORT_LIMIT_MW,policy=policy) if method=="baseline" else fn(sc,C.LAMBDA_DEFAULT,C.GRID_IMPORT_LIMIT_MW,policy=policy)
                    metrics=evaluate(sc,sch,C.LAMBDA_DEFAULT,
                                     work_efficiency=policy.efficiency,ramp_mw_per_hour=policy.ramp_mw_per_hour)
                    row=dict(batch=batch,profile=profile,policy=name,method=method,seed=seed,
                             source="synthetic_unscreened",generation_attempts=sc.generation_attempts,
                             status=metrics["status"],feasible=metrics["feasible"],
                             **asdict(policy),**{k:metrics[k] for k in METRICS},
                             compute_overhead_mwh=metrics["compute_overhead_mwh"],
                             ramp_violation_events=metrics["ramp_violation_events"],
                             ramp_excess_mwh=metrics["ramp_excess_mwh"])
                    batch_rows.append(row);rows.append(row)
                    if seed==seeds[0]:
                        traces.append(dict(batch=batch,profile=profile,policy=name,method=method,
                                           seed=seed,decisions=sch.info["decision_trace"]))
            for method in ("baseline","MPC"):
                group=[r for r in batch_rows if r["method"]==method]
                summary=aggregate(group)
                summary.update(batch=batch,profile=profile,policy=name,method=method,
                               max_ramp_violation_events=max(r["ramp_violation_events"] for r in group),
                               max_ramp_excess_mwh=max(r["ramp_excess_mwh"] for r in group),
                               mean_compute_overhead_mwh=np.mean([r["compute_overhead_mwh"] for r in group]))
                summaries.append(summary)
            stats,matched=paired_comparisons(batch_rows)
            for frame,target in ((stats,statistics),(matched,pairs)):
                frame["profile"]=profile;frame["policy"]=name;target.extend(frame.to_dict("records"))
            batch+=1
    raw=pd.DataFrame(rows);summary=pd.DataFrame(summaries);stats=pd.DataFrame(statistics)
    raw.to_csv(output/"runs.csv",index=False)
    summary.to_csv(output/"feasibility.csv",index=False)
    stats.to_csv(output/"paired_comparisons.csv",index=False)
    pd.DataFrame(pairs).to_csv(output/"paired_seed_savings.csv",index=False)
    (output/"decision_traces.json").write_text(json.dumps(traces,indent=2))
    manifest=dict(config_snapshot={k:v for k,v in vars(C).items() if k.isupper()},
                  seeds=seeds,profiles=profiles,policies={k:asdict(v) for k,v in policies.items()},
                  forecast_error=.3,generator_feasibility_screen=False,horizon_hours=C.HORIZON_H*C.DT_H,
                  lambda_cny_per_tonne=C.LAMBDA_DEFAULT,grid_limit_mw=C.GRID_IMPORT_LIMIT_MW,
                  selection="unscreened synthetic draws; seeds 100–119 and 200–219 informed development; seeds 220–239 are designated fresh validation; the seeds field identifies this run")
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2))
    cols=["profile","policy","method","feasible_runs","runs","max_sla_violations",
          "max_capacity_violation_hours","max_grid_limit_violation_hours",
          "max_ramp_violation_events","mean_compute_overhead_mwh"]
    typical=summary[(summary.profile=="typical") & (summary.method=="MPC")]
    rates="; ".join(f"{r.policy}: {int(r.feasible_runs)}/{int(r.runs)}" for _,r in typical.iterrows())
    findings=(f"## Important findings\n\nThis study exposes robustness limits, not operational guarantees. "
              f"Typical-profile MPC feasibility: {rates}. "
              f"Overall {int(raw.feasible.sum())}/{len(raw)} method runs were feasible. "
              f"{int(stats.eligible.sum())}/{len(stats)} paired monetary comparisons met the all-pairs-feasible rule. "
              f"These are {len(seeds)} unique synthetic seeds, not {len(raw)} independent seeds.")
    text=["# Synthetic robustness validation",findings,json.dumps(manifest,indent=2),
          "No real operational traces were supplied. Profiles are stress assumptions, not verified seasons. "
          "Each method pair has identical observations, job information and compute assumptions. "
          "Legacy delayed policies have no current-hour protection. Guarded policies explicitly use current telemetry "
          "in a fast safety/service stage; both baseline and MPC receive that same capability. "
          "Guarded policies fix service with a laxity heuristic, shared with the matched no-battery reference; no universal deadline guarantee is claimed. "
          "True battery state is available from commands; price/carbon and exogenous forecasts remain known. "
          "Checkpoint overhead is amortized, not per-resume; GPU units remain continuous. "
          "Approximate pointwise 95% paired Student-t intervals are suppressed for any infeasible pair. "
          "All failed/degraded draws remain in raw records; no feasibility filtering is used.",
          summary[cols].round(3).to_markdown(index=False),"## Paired savings",stats.round(3).to_markdown(index=False)]
    (output/"RESULTS.md").write_text("\n\n".join(text))
    return raw,summary,stats


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick",action="store_true")
    parser.add_argument("--output-dir",type=Path,default=Path("robustness_results"))
    args=parser.parse_args(argv)
    run_validation(args.output_dir,seeds=range(200,202) if args.quick else range(200,220),quick=args.quick)


if __name__=="__main__":main()
