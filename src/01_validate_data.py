from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/"data"

required = {
    "supplier_master.csv":["supplier_id","material_id","region","currency","lead_time_days","monthly_capacity","quality_ppm","otd_rate"],
    "quotation.csv":["supplier_id","material_id","currency","unit_price","freight_per_unit"],
    "demand_forecast.csv":["month","material_id","base_demand","upside_demand","downside_demand"],
    "procurement_history.csv":["po_id","month","supplier_id","material_id","ordered_qty","actual_lead_time_days"],
    "risk_events.csv":["scenario","impact_type","multiplier"],
    "eda_ip_resource_master.csv":["resource_id","resource_name","current_units","annual_fee_cny_per_unit","peak_concurrent_users"],
    "eda_ip_team_demand.csv":["team_id","resource_id","engineer_count","expected_peak_usage_factor"],
}
errors=[]
for fname,cols in required.items():
    p=DATA/fname
    if not p.exists():
        errors.append(f"Missing file: {fname}")
        continue
    df=pd.read_csv(p)
    missing=[c for c in cols if c not in df.columns]
    if missing:
        errors.append(f"{fname}: missing columns {missing}")
    if "synthetic_flag" in df.columns and not df["synthetic_flag"].fillna(False).astype(bool).all():
        errors.append(f"{fname}: synthetic_flag must be True for all rows")

supplier=pd.read_csv(DATA/"supplier_master.csv")
if supplier.duplicated(["supplier_id","material_id"]).any():
    errors.append("Duplicate supplier_id + material_id in supplier_master")
if not supplier["otd_rate"].between(0,1).all():
    errors.append("OTD outside [0,1]")
if (supplier["monthly_capacity"]<=0).any():
    errors.append("Non-positive capacity")

demand=pd.read_csv(DATA/"demand_forecast.csv")
if (demand[["base_demand","upside_demand","downside_demand"]]<=0).any().any():
    errors.append("Non-positive demand")
if not (demand["upside_demand"]>=demand["base_demand"]).all():
    errors.append("Upside demand below base")
if not (demand["downside_demand"]<=demand["base_demand"]).all():
    errors.append("Downside demand above base")

if errors:
    print("VALIDATION FAILED")
    for e in errors:
        print(" -",e)
    raise SystemExit(1)

print("VALIDATION PASSED")
for fname in required:
    df=pd.read_csv(DATA/fname)
    print(f"{fname}: {len(df)} rows")
