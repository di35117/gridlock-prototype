from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, Text, Index, BigInteger
)
from database import Base


class Incident(Base):
    """Raw ASTRAM incident data — all 8,173 rows from the CSV."""
    __tablename__ = "incidents"

    id = Column(String(50), primary_key=True)          
    event_type       = Column(String(50),  index=True)            
    event_cause      = Column(String(100), index=True)            
    start_datetime   = Column(DateTime,    nullable=True)
    resolved_datetime = Column(DateTime,   nullable=True)
    closed_datetime  = Column(DateTime,    nullable=True)
    priority         = Column(String(20),  index=True)            
    requires_road_closure = Column(Boolean, default=False)
    status           = Column(String(50),  nullable=True)
    corridor         = Column(String(150), index=True)
    zone             = Column(String(100), nullable=True)
    police_station   = Column(String(150), nullable=True)
    junction         = Column(String(250), nullable=True)
    address          = Column(Text,        nullable=True)
    description      = Column(Text,        nullable=True)
    
    # NEW: Added Vehicle Type for the ML model
    veh_type         = Column(String(100), nullable=True)
    
    latitude         = Column(Float,       nullable=True)
    longitude        = Column(Float,       nullable=True)
    assigned_to_police_id = Column(String(100), nullable=True)
    closed_by_id     = Column(String(100), nullable=True)
    direction        = Column(String(250), nullable=True)
    route_path       = Column(Text,        nullable=True)

    # Derived — computed at load time
    hour_of_day      = Column(Integer, nullable=True)   
    day_of_week      = Column(Integer, nullable=True)   
    time_to_close_hours = Column(Float, nullable=True)

    __table_args__ = (
        Index("idx_inc_corridor_hour",  "corridor",    "hour_of_day"),
        Index("idx_inc_cause_corridor", "event_cause", "corridor"),
        Index("idx_inc_priority_cause", "priority",    "event_cause"),
    )


class CorridorRiskProfile(Base):
    __tablename__ = "corridor_risk_profiles"

    corridor              = Column(String(150), primary_key=True)
    total_incidents       = Column(Integer, default=0)
    road_closures         = Column(Integer, default=0)
    closure_rate          = Column(Float,   default=0.0)   
    high_priority_count   = Column(Integer, default=0)
    high_priority_rate    = Column(Float,   default=0.0)   
    event_incidents       = Column(Integer, default=0)     
    construction_incidents = Column(Integer, default=0)
    congestion_incidents  = Column(Integer, default=0)
    avg_hourly_baseline   = Column(Float,   default=0.0)   
    std_hourly_baseline   = Column(Float,   default=0.0)   
    risk_score            = Column(Float,   default=0.0)   


class StationCorridorMapping(Base):
    __tablename__ = "station_corridor_mapping"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    corridor       = Column(String(150), index=True)
    police_station = Column(String(150))
    incident_count = Column(Integer, default=0)   
    event_count    = Column(Integer, default=0)   
    is_primary     = Column(Boolean, default=False)  


class EventCauseStat(Base):
    __tablename__ = "event_cause_stats"

    event_cause               = Column(String(100), primary_key=True)
    n_incidents               = Column(Integer, default=0)
    closure_rate              = Column(Float,   default=0.0)   
    high_priority_rate        = Column(Float,   default=0.0)   
    median_time_to_close_hours = Column(Float,  nullable=True)
    severity_tier             = Column(Integer, default=1)