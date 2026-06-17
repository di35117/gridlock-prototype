import logging
import pulp
from sqlalchemy import text
from database import engine

logger = logging.getLogger(__name__)

async def get_tactical_plan(corridor: str, risk_level: str) -> dict:
    """Provides data-grounded station assignments and tier-based barricading."""
    # 1. Fetch historical stations
    query = text("""
        SELECT police_station FROM station_corridor_mapping
        WHERE corridor ILIKE :corridor
    """)
    async with engine.connect() as conn:
        result = await conn.execute(query, {"corridor": corridor})
        rows = result.fetchall()
        
    stations = [row.police_station for row in rows if row.police_station]
    if not stations:
        stations = ["Nearest available station (No historical mapping)"]

    # 2. Derive resource tiers based on risk (since we don't have exact historical officer counts)
    tier_mapping = {
        "Low": {"tier": "Tier 3 (Standard Patrol)", "barricades": 5},
        "Medium": {"tier": "Tier 2 (Reinforced)", "barricades": 15},
        "High": {"tier": "Tier 1 (Major Deployment)", "barricades": 40},
        "Critical": {"tier": "Tier 0 (Maximum Mobilization)", "barricades": 100}
    }
    
    plan = tier_mapping.get(risk_level, tier_mapping["Medium"])

    return {
        "primary_stations": stations,
        "manpower_tier": plan["tier"],
        "recommended_barricade_count": plan["barricades"]
    }

async def optimize_manpower(total_officers: int, demands: dict[str, int], risks: dict[str, float]) -> dict:
    """
    Uses Linear Programming to optimally distribute limited officers across multiple events.
    Objective: Maximize risk-weighted officer deployment.
    """
    logger.info("Running PuLP Linear Optimization for manpower allocation...")
    
    # Define the Linear Programming problem
    prob = pulp.LpProblem("Police_Deployment_Optimization", pulp.LpMaximize)

    # Variables: How many officers to assign to each event
    events = list(demands.keys())
    allocations = pulp.LpVariable.dicts("assign", events, lowBound=0, cat='Integer')

    # Objective Function: Maximize (Officers Assigned * Event Risk Score)
    # This ensures higher risk events get priority for officers
    prob += pulp.lpSum([allocations[e] * risks.get(e, 1.0) for e in events]), "Total_Risk_Weighted_Deployment"

    # Constraint 1: We cannot assign more officers than we have available
    prob += pulp.lpSum([allocations[e] for e in events]) <= total_officers, "Total_Manpower_Constraint"

    # Constraint 2: We cannot assign more officers to an event than it demands
    for e in events:
        prob += allocations[e] <= demands[e], f"Demand_Constraint_{e}"

    # Solve the problem
    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    results = {}
    total_assigned = 0
    for e in events:
        assigned = int(allocations[e].varValue) if allocations[e].varValue else 0
        results[e] = assigned
        total_assigned += assigned

    unmet_demand = sum(demands.values()) - total_assigned

    return {
        "allocations": results,
        "unmet_demand": unmet_demand,
        "optimization_status": pulp.LpStatus[prob.status]
    }