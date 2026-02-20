from __future__ import annotations

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RoadSegment(Base):
    __tablename__ = "road_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    geometry: Mapped[str] = mapped_column(String, nullable=False)
    length: Mapped[float] = mapped_column(Float, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    free_flow_speed: Mapped[float] = mapped_column(Float, nullable=False)
    road_type: Mapped[str] = mapped_column(String, nullable=False)


class SegmentLiveState(Base):
    __tablename__ = "segment_live_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    segment_id: Mapped[int] = mapped_column(ForeignKey("road_segments.id"), index=True)
    timestamp: Mapped[DateTime] = mapped_column(DateTime, index=True)
    vehicle_count: Mapped[int] = mapped_column(Integer)
    avg_speed: Mapped[float] = mapped_column(Float)
    congestion_index: Mapped[float] = mapped_column(Float)


class SegmentFeature(Base):
    __tablename__ = "segment_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    segment_id: Mapped[int] = mapped_column(ForeignKey("road_segments.id"), index=True)
    timestamp: Mapped[DateTime] = mapped_column(DateTime, index=True)
    hour: Mapped[int] = mapped_column(Integer)
    day_of_week: Mapped[int] = mapped_column(Integer)
    lag_1: Mapped[float] = mapped_column(Float)
    lag_3: Mapped[float] = mapped_column(Float)
    lag_6: Mapped[float] = mapped_column(Float)
    rolling_mean_15: Mapped[float] = mapped_column(Float)
    rolling_mean_60: Mapped[float] = mapped_column(Float)
    capacity_ratio: Mapped[float] = mapped_column(Float)
    incident_flag: Mapped[int] = mapped_column(Integer)


class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    segment_id: Mapped[int] = mapped_column(ForeignKey("road_segments.id"), index=True)
    timestamp: Mapped[DateTime] = mapped_column(DateTime, index=True)
    predicted_congestion: Mapped[float] = mapped_column(Float)
    confidence_lower: Mapped[float] = mapped_column(Float)
    confidence_upper: Mapped[float] = mapped_column(Float)
