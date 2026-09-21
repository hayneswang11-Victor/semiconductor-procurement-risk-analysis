from pathlib import Path
import pandas as pd
import numpy as np
from allocation import allocate_material

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
OUT=ROOT/'outputs'
FX={'CNY':1.0,'JPY':0.049,'KRW':0.0052,'SGD':5.35,'USD':7.15,'EUR':7.75}
RNG=np.random.default_rng(20260921)
N_SIM=600
STRATEGIES=['Lowest Cost','Balanced','Resilience']

supplier=pd.read_csv(DATA/'supplier_master.csv')
quote=pd.read_csv(DATA/'quotation.csv')
demand=pd.read_csv(DATA/'demand_forecast.csv')
metrics=pd.read_csv(OUT/'supplier_metrics.csv')
base=supplier.merge(quote,on=['supplier_id','material_id','currency'],how='left',suffixes=('','_q'))
base['fx_to_cny']=base['currency'].map(FX)
base['base_landed_cost_cny']=(base['unit_price']+base['freight_per_unit'])*base['fx_to_cny']
base=base.merge(metrics[['supplier_id','material_id','supply_risk_score_0to100']],
                on=['supplier_id','material_id'],how='left')
annual_demand=demand.groupby('material_id')['base_demand'].sum().to_dict()

records=[]
for sim in range(1,N_SIM+1):
    demand_mult=float(np.clip(RNG.normal(1.0,0.09),0.78,1.32))
    price_mult=float(np.clip(RNG.normal(1.0,0.05),0.85,1.25))
    fx_mult=float(np.clip(RNG.normal(1.0,0.035),0.90,1.15))
    cap_noise=np.clip(RNG.normal(1.0,0.10,size=len(base)),0.70,1.25)

    simdf=base.copy()
    foreign=(simdf['currency']!='CNY').astype(float)
    simdf['landed_cost_adj']=simdf['base_landed_cost_cny']*price_mult*(1+foreign*(fx_mult-1))
    simdf['annual_capacity_adj']=simdf['monthly_capacity']*12*cap_noise

    fail_prob=0.015+0.075*(simdf['supply_risk_score_0to100']/100.0)
    fail_draw=RNG.random(len(simdf))<fail_prob.to_numpy()
    realized_factor=np.ones(len(simdf))
    if fail_draw.any():
        realized_factor[fail_draw]=RNG.uniform(0.25,0.75,size=fail_draw.sum())
    simdf['realized_delivery_factor']=realized_factor
    factor_map=simdf.set_index('supplier_id')['realized_delivery_factor'].to_dict()

    for strategy in STRATEGIES:
        total_cost=0.0
        risk_cost_num=0.0
        material_shortages=[]
        for mid,g in simdf.groupby('material_id'):
            d=float(annual_demand[mid])*demand_mult
            allocs,_=allocate_material(g,d,strategy)
            realized=0.0
            for x in allocs:
                line_cost=x['qty']*x['cost']
                total_cost+=line_cost
                risk_cost_num+=line_cost*x['risk']
                realized+=x['qty']*factor_map[x['supplier_id']]
            material_shortages.append(max(0.0,1-realized/d))
        records.append({
            'simulation':sim,
            'strategy':strategy,
            'annual_cost_cny':total_cost,
            'avg_material_shortage_rate':float(np.mean(material_shortages)),
            'max_material_shortage_rate':float(max(material_shortages)),
            'any_material_shortage':int(any(s>1e-9 for s in material_shortages)),
            'cost_weighted_risk':risk_cost_num/total_cost if total_cost else np.nan
        })

mc=pd.DataFrame(records)
mc.to_csv(OUT/'monte_carlo_detail.csv',index=False)
summary=mc.groupby('strategy').agg(
    mean_cost_cny=('annual_cost_cny','mean'),
    p50_cost_cny=('annual_cost_cny','median'),
    p90_cost_cny=('annual_cost_cny',lambda s:s.quantile(0.90)),
    mean_avg_material_shortage_rate=('avg_material_shortage_rate','mean'),
    any_material_shortage_probability=('any_material_shortage','mean'),
    p90_max_material_shortage_rate=('max_material_shortage_rate',lambda s:s.quantile(0.90)),
    mean_cost_weighted_risk=('cost_weighted_risk','mean')
).reset_index()
summary.to_csv(OUT/'monte_carlo_strategy_summary.csv',index=False)
print(summary.round(4).to_string(index=False))
