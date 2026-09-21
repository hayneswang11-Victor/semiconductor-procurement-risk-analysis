from pathlib import Path
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
OUT=ROOT/"outputs"
OUT.mkdir(exist_ok=True)
FX={"CNY":1.0,"JPY":0.049,"KRW":0.0052,"SGD":5.35,"USD":7.15,"EUR":7.75}

supplier=pd.read_csv(DATA/"supplier_master.csv")
quote=pd.read_csv(DATA/"quotation.csv")
demand=pd.read_csv(DATA/"demand_forecast.csv")
hist=pd.read_csv(DATA/"procurement_history.csv")

base=supplier.merge(quote,on=["supplier_id","material_id","currency"],how="left",suffixes=("","_q"))
base["fx_to_cny"]=base["currency"].map(FX)
base["landed_cost_cny"]=(base["unit_price"]+base["freight_per_unit"])*base["fx_to_cny"]

hist_perf=hist.groupby(["supplier_id","material_id"]).agg(
    hist_po_count=("po_id","count"),
    hist_order_qty=("ordered_qty","sum"),
    hist_otd=("delivered_on_time","mean"),
    avg_actual_lead=("actual_lead_time_days","mean"),
    quality_incident_rate=("quality_incident","mean")
).reset_index()
base=base.merge(hist_perf,on=["supplier_id","material_id"],how="left")

annual=demand.groupby("material_id")["base_demand"].sum().rename("annual_demand")
base=base.join(annual,on="material_id")
base["annual_capacity"]=base["monthly_capacity"]*12
base["capacity_coverage"]=base["annual_capacity"]/base["annual_demand"]

def minmax(s):
    s=s.astype(float)
    if float(s.max())==float(s.min()):
        return pd.Series(0.5,index=s.index)
    return (s-s.min())/(s.max()-s.min())

base["r_cost"]=base.groupby("material_id")["landed_cost_cny"].transform(minmax)
base["r_lead"]=base.groupby("material_id")["lead_time_days"].transform(minmax)
base["r_otd"]=1-base["otd_rate"]
base["r_quality"]=base.groupby("material_id")["quality_ppm"].transform(minmax)
base["r_capacity"]=(1/base["capacity_coverage"].clip(lower=0.2)).clip(upper=2.0)/2.0
base["r_single"]=(base["single_source_risk_1to5"]-1)/4
base["r_geo"]=(base["geopolitical_risk_1to5"]-1)/4

weights={"r_lead":0.18,"r_otd":0.20,"r_quality":0.18,"r_capacity":0.20,"r_single":0.12,"r_geo":0.12}
base["supply_risk_score_0to100"]=100*sum(base[k]*w for k,w in weights.items())
base["balanced_score"]=0.55*base["r_cost"]+0.45*(base["supply_risk_score_0to100"]/100)

cols=["supplier_id","supplier_name","material_id","material_name","region","currency",
      "landed_cost_cny","lead_time_days","monthly_capacity","annual_capacity","annual_demand",
      "capacity_coverage","quality_ppm","otd_rate","hist_otd","quality_incident_rate",
      "supply_risk_score_0to100","balanced_score"]
base[cols].sort_values(["material_id","balanced_score"]).to_csv(OUT/"supplier_metrics.csv",index=False)

ms=base.groupby("material_id").agg(
    supplier_count=("supplier_id","nunique"),
    min_landed_cost_cny=("landed_cost_cny","min"),
    median_landed_cost_cny=("landed_cost_cny","median"),
    avg_supply_risk=("supply_risk_score_0to100","mean"),
    total_annual_capacity=("annual_capacity","sum"),
    annual_demand=("annual_demand","first")
).reset_index()
ms["capacity_buffer_ratio"]=ms["total_annual_capacity"]/ms["annual_demand"]
ms.to_csv(OUT/"material_summary.csv",index=False)
print("Wrote supplier_metrics.csv and material_summary.csv")
