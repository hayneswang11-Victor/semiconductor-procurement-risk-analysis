import pandas as pd
import numpy as np

def norm(s):
    s=s.astype(float)
    if len(s)<=1 or float(s.max())==float(s.min()):
        return pd.Series(0.5,index=s.index)
    return (s-s.min())/(s.max()-s.min())

def rank_suppliers(g,strategy):
    g=g.copy()
    if strategy=="Lowest Cost":
        g["rank_score"]=norm(g["landed_cost_adj"])
        cap_share=1.0
    elif strategy=="Balanced":
        g["rank_score"]=0.55*norm(g["landed_cost_adj"])+0.45*norm(g["supply_risk_score_0to100"])
        cap_share=0.75
    elif strategy=="Resilience":
        g["rank_score"]=0.30*norm(g["landed_cost_adj"])+0.70*norm(g["supply_risk_score_0to100"])
        cap_share=0.60
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    return g.sort_values(["rank_score","landed_cost_adj"]).reset_index(drop=True),cap_share

def allocate_material(g,demand_qty,strategy):
    g,cap_share=rank_suppliers(g,strategy)
    demand_qty=float(demand_qty)
    used={sid:0.0 for sid in g["supplier_id"]}
    allocations=[]
    remaining=demand_qty

    # pass 1: respect preferred share cap
    for _,r in g.iterrows():
        if remaining<=1e-9:
            break
        cap=float(r["annual_capacity_adj"])
        pref_cap=demand_qty*cap_share
        qty=min(remaining,cap,pref_cap)
        if qty>0:
            used[r["supplier_id"]]+=qty
            allocations.append({
                "supplier_id":r["supplier_id"],
                "qty":qty,
                "cost":float(r["landed_cost_adj"]),
                "risk":float(r["supply_risk_score_0to100"])
            })
            remaining-=qty

    # pass 2: use remaining physical capacity if capped pass left a shortage
    if remaining>1e-9:
        for _,r in g.iterrows():
            if remaining<=1e-9:
                break
            sid=r["supplier_id"]
            spare=max(0.0,float(r["annual_capacity_adj"])-used[sid])
            extra=min(remaining,spare)
            if extra>0:
                used[sid]+=extra
                found=False
                for item in allocations:
                    if item["supplier_id"]==sid:
                        item["qty"]+=extra
                        found=True
                        break
                if not found:
                    allocations.append({
                        "supplier_id":sid,"qty":extra,
                        "cost":float(r["landed_cost_adj"]),
                        "risk":float(r["supply_risk_score_0to100"])
                    })
                remaining-=extra
    return allocations,max(0.0,remaining)
