from pathlib import Path
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
OUT=ROOT/"outputs"

res=pd.read_csv(DATA/"eda_ip_resource_master.csv")

SCENARIOS={
    "Base":(1.00,1.00),
    "Demand +20%":(1.20,1.00),
    "Vendor Price +10%":(1.00,1.10),
    "Project Growth":(1.30,1.05)
}
POLICIES={"Lean":0.90,"Current":1.00,"Buffer":1.15}

rows=[]
for scen,(demand_mult,price_mult) in SCENARIOS.items():
    for policy,unit_mult in POLICIES.items():
        annual_cost=0.0
        coverage_num=0.0
        peak_total=0.0
        uncovered=0
        for _,r in res.iterrows():
            units=max(1,int(np.ceil(r["current_units"]*unit_mult)))
            peak=float(r["peak_concurrent_users"])*demand_mult
            coverage=min(1.0,units/peak) if peak>0 else 1.0
            annual_cost+=units*float(r["annual_fee_cny_per_unit"])*price_mult
            coverage_num+=coverage*peak
            peak_total+=peak
            uncovered+=int(np.ceil(max(0.0,peak-units)))
        rows.append({
            "scenario":scen,
            "policy":policy,
            "annual_license_cost_cny":annual_cost,
            "peak_demand_coverage":coverage_num/peak_total,
            "estimated_uncovered_peak_units":uncovered
        })

out=pd.DataFrame(rows)
out.to_csv(OUT/"eda_ip_scenario_summary.csv",index=False)
print(out.round({"annual_license_cost_cny":0,"peak_demand_coverage":3}).to_string(index=False))
