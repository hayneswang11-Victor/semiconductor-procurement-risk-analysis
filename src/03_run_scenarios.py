from pathlib import Path
import pandas as pd
import numpy as np
from allocation import allocate_material

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
OUT=ROOT/'outputs'
FX={'CNY':1.0,'JPY':0.049,'KRW':0.0052,'SGD':5.35,'USD':7.15,'EUR':7.75}

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

SCENARIOS={
    'Base':{'demand':1.00,'price':1.00,'capacity':1.00,'lead':1.00,'fx_foreign':1.00},
    'Demand Surge':{'demand':1.20,'price':1.00,'capacity':1.00,'lead':1.00,'fx_foreign':1.00},
    'Cost Pressure':{'demand':1.00,'price':1.10,'capacity':1.00,'lead':1.00,'fx_foreign':1.00},
    'Supply Disruption':{'demand':1.00,'price':1.00,'capacity':0.70,'lead':1.25,'fx_foreign':1.00},
    'FX Shock':{'demand':1.00,'price':1.00,'capacity':1.00,'lead':1.00,'fx_foreign':1.08},
}
STRATEGIES=['Lowest Cost','Balanced','Resilience']

detail=[]
summary=[]
for scen_name,p in SCENARIOS.items():
    scen=base.copy()
    scen['annual_capacity_adj']=scen['monthly_capacity']*12*p['capacity']
    foreign=(scen['currency']!='CNY').astype(float)
    scen['landed_cost_adj']=scen['base_landed_cost_cny']*p['price']*(1+foreign*(p['fx_foreign']-1))
    scen['lead_time_adj']=scen['lead_time_days']*p['lead']

    for strategy in STRATEGIES:
        total_cost=0.0
        risk_cost_num=0.0
        hhis=[]
        material_coverages=[]
        material_shortages=[]
        for mid,g in scen.groupby('material_id'):
            d=float(annual_demand[mid])*p['demand']
            allocs,shortage=allocate_material(g,d,strategy)
            supplied=sum(x['qty'] for x in allocs)
            coverage=supplied/d if d else np.nan
            shortage_rate=max(0.0,1-coverage)
            material_coverages.append(coverage)
            material_shortages.append(shortage_rate)
            if supplied>0:
                shares=np.array([x['qty']/supplied for x in allocs])
                hhis.append(float((shares**2).sum()))
            for x in allocs:
                line_cost=x['qty']*x['cost']
                total_cost+=line_cost
                risk_cost_num+=line_cost*x['risk']
                detail.append({
                    'scenario':scen_name,'strategy':strategy,'material_id':mid,
                    'supplier_id':x['supplier_id'],'allocated_qty':x['qty'],
                    'material_demand_qty':d,'material_coverage':coverage,
                    'landed_cost_cny':x['cost'],'risk_score_0to100':x['risk'],
                    'shortage_qty_material':shortage
                })
        summary.append({
            'scenario':scen_name,
            'strategy':strategy,
            'annual_procurement_cost_cny':total_cost,
            'avg_material_coverage':float(np.mean(material_coverages)),
            'avg_material_shortage_rate':float(np.mean(material_shortages)),
            'materials_with_shortage':int(sum(s>1e-9 for s in material_shortages)),
            'max_material_shortage_rate':float(max(material_shortages)),
            'cost_weighted_supply_risk_0to100':risk_cost_num/total_cost if total_cost else np.nan,
            'avg_supplier_concentration_hhi':float(np.mean(hhis)) if hhis else np.nan
        })

pd.DataFrame(detail).to_csv(OUT/'scenario_allocation_detail.csv',index=False)
summary_df=pd.DataFrame(summary)
summary_df.to_csv(OUT/'scenario_strategy_summary.csv',index=False)
print(summary_df.round(4).to_string(index=False))
