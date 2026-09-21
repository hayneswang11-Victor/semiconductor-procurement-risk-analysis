from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
RNG = np.random.default_rng(20260921)

materials = [
    ("M001","Silicon Wafer","wafer",780.0,3600),
    ("M002","Photoresist","liter",430.0,2900),
    ("M003","Process Gas","cylinder",520.0,780),
    ("M004","CMP Slurry","liter",115.0,6200),
    ("M005","PVD Target","piece",8600.0,110),
    ("M006","Packaging Substrate","piece",42.0,185000),
    ("M007","Lead Frame","kpcs",68.0,210),
    ("M008","Specialty Chemical","liter",155.0,5400),
]
regions = [("CN","CNY"),("JP","JPY"),("KR","KRW"),("SG","SGD"),("US","USD"),("DE","EUR")]
fx_to_cny = {"CNY":1.0,"JPY":0.049,"KRW":0.0052,"SGD":5.35,"USD":7.15,"EUR":7.75}

supplier_rows, quote_rows = [], []
sid_no = 1
for mid,mname,uom,base_cost,base_demand in materials:
    selected = RNG.choice(len(regions), size=3, replace=False)
    for idx in selected:
        region,currency = regions[idx]
        sid = f"S{sid_no:03d}"
        sid_no += 1
        lead = int(RNG.integers(18,70))
        capacity = int(base_demand * RNG.uniform(0.55,1.05))
        quality_ppm = int(RNG.integers(35,320))
        otd = round(float(RNG.uniform(0.88,0.995)),4)
        single_risk = int(RNG.integers(1,6))
        geo_base = {"CN":1,"JP":2,"KR":2,"SG":1,"US":3,"DE":2}[region]
        geo_risk = min(5, geo_base + int(RNG.integers(0,2)))
        supplier_rows.append({
            "supplier_id":sid,
            "supplier_name":f"Supplier_{sid}_{region}",
            "material_id":mid,
            "material_name":mname,
            "uom":uom,
            "region":region,
            "currency":currency,
            "lead_time_days":lead,
            "monthly_capacity":capacity,
            "quality_ppm":quality_ppm,
            "otd_rate":otd,
            "payment_terms_days":int(RNG.choice([30,45,60,90])),
            "single_source_risk_1to5":single_risk,
            "geopolitical_risk_1to5":geo_risk,
            "qualification_status":str(RNG.choice(["Qualified","Qualified","Qualified","Conditional"])),
            "synthetic_flag":True,
        })
        cny_cost = base_cost * RNG.uniform(0.88,1.14)
        unit_price = cny_cost / fx_to_cny[currency]
        freight = cny_cost * RNG.uniform(0.006,0.025) / fx_to_cny[currency]
        quote_rows.append({
            "supplier_id":sid,
            "material_id":mid,
            "currency":currency,
            "unit_price":round(unit_price,4),
            "freight_per_unit":round(freight,4),
            "discount_threshold_qty":int(base_demand*RNG.uniform(0.5,1.2)),
            "discount_rate":round(float(RNG.uniform(0.01,0.06)),4),
            "quote_valid_from":"2026-01-01",
            "quote_valid_to":"2026-12-31",
            "synthetic_flag":True,
        })

supplier_master = pd.DataFrame(supplier_rows)
quotation = pd.DataFrame(quote_rows)
supplier_master.to_csv(DATA/"supplier_master.csv", index=False)
quotation.to_csv(DATA/"quotation.csv", index=False)

months = pd.period_range("2026-01","2026-12",freq="M")
dem_rows = []
base_demand_map = {mid:base_demand for mid,_,_,_,base_demand in materials}
name_map = {mid:(mname,uom) for mid,mname,uom,_,_ in materials}
for mid,mname,uom,_,base_demand in materials:
    for i,period in enumerate(months):
        seasonality = 1 + 0.06*np.sin(2*np.pi*i/12)
        demand = max(1, int(base_demand*seasonality*RNG.normal(1.0,0.035)))
        dem_rows.append({
            "month":str(period),
            "material_id":mid,
            "material_name":mname,
            "uom":uom,
            "base_demand":demand,
            "upside_demand":int(round(demand*1.20)),
            "downside_demand":int(round(demand*0.85)),
            "synthetic_flag":True,
        })
demand = pd.DataFrame(dem_rows)
demand.to_csv(DATA/"demand_forecast.csv", index=False)

# Synthetic procurement history
hist_rows = []
po_no = 1
for _,drow in demand.iterrows():
    mid = drow["material_id"]
    monthly_demand = float(drow["base_demand"])
    sup = supplier_master[supplier_master["material_id"]==mid].merge(
        quotation[quotation["material_id"]==mid],
        on=["supplier_id","material_id","currency"], how="left", suffixes=("","_q")
    )
    sup["landed_cny"] = (sup["unit_price"]+sup["freight_per_unit"])*sup["currency"].map(fx_to_cny)
    sup["pref"] = sup["landed_cny"].rank(method="first") + 0.6*(-sup["otd_rate"]).rank(method="first")
    sup = sup.sort_values("pref")
    shares = np.array([0.52,0.31,0.17])[:len(sup)]
    shares = shares/shares.sum()
    for share,(_,r) in zip(shares,sup.iterrows()):
        qty = max(1,int(round(monthly_demand*share*RNG.uniform(0.95,1.05))))
        promised = int(r["lead_time_days"])
        actual = max(1,int(round(promised*RNG.normal(1.0,0.12))))
        hist_rows.append({
            "po_id":f"PO{po_no:05d}",
            "month":drow["month"],
            "supplier_id":r["supplier_id"],
            "material_id":mid,
            "ordered_qty":qty,
            "unit_price":round(float(r["unit_price"]*RNG.normal(1.0,0.025)),4),
            "currency":r["currency"],
            "promised_lead_time_days":promised,
            "actual_lead_time_days":actual,
            "delivered_on_time":int(actual<=promised*1.05),
            "quality_incident":int(RNG.random()<min(0.15,float(r["quality_ppm"])/2000)),
            "synthetic_flag":True,
        })
        po_no += 1
pd.DataFrame(hist_rows).to_csv(DATA/"procurement_history.csv", index=False)

risk_events = pd.DataFrame([
    ["EVT01","Base","All","none",1.00,"Normal planning baseline",True],
    ["EVT02","Demand Surge","All","demand",1.20,"Demand +20% across materials",True],
    ["EVT03","Cost Pressure","All","price",1.10,"Supplier price +10%",True],
    ["EVT04","Supply Disruption","All","capacity",0.70,"Available capacity -30%, lead time +25%",True],
    ["EVT05","FX Shock","Foreign suppliers","fx",1.08,"Non-CNY landed cost +8%",True],
], columns=["event_id","scenario","scope","impact_type","multiplier","description","synthetic_flag"])
risk_events.to_csv(DATA/"risk_events.csv", index=False)

eda = pd.DataFrame([
    ["E001","TCAD Suite A","EDA Tool","Floating",42,168000,32,25,0.94,True],
    ["E002","Digital Implementation Suite B","EDA Tool","Floating",55,132000,47,36,0.91,True],
    ["E003","Analog/RF Suite C","EDA Tool","Floating",30,148000,24,18,0.89,True],
    ["E004","Verification IP Bundle D","IP License","Project",12,265000,10,7,0.86,True],
], columns=["resource_id","resource_name","resource_type","license_type","current_units","annual_fee_cny_per_unit","peak_concurrent_users","avg_concurrent_users","renewal_probability","synthetic_flag"])
eda.to_csv(DATA/"eda_ip_resource_master.csv", index=False)

team = pd.DataFrame([
    ["T01","Device Modeling",18,"E001",0.80,True],
    ["T02","Digital Design",44,"E002",0.85,True],
    ["T03","Analog Design",22,"E003",0.75,True],
    ["T04","Verification",36,"E004",0.60,True],
], columns=["team_id","team_name","engineer_count","resource_id","expected_peak_usage_factor","synthetic_flag"])
team.to_csv(DATA/"eda_ip_team_demand.csv", index=False)

print("Created synthetic datasets:", len(supplier_master), "supplier-material rows,", len(demand), "monthly demand rows.")
