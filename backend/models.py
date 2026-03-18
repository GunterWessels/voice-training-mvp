import uuid
from datetime import datetime, date
from typing import Optional
from decimal import Decimal
from sqlalchemy import String, Boolean, Integer, Text, DateTime, Numeric, BigInteger, Date, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from backend.db import Base


class Division(Base):
    __tablename__ = "divisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Cohort(Base):
    __tablename__ = "cohorts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    division_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    cohort_token: Mapped[Optional[str]] = mapped_column(Text, unique=True, nullable=True)
    celebrations_enabled: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    first_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(Text, nullable=False, default='rep')
    cohort_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    division_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    division_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    product_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    persona_id: Mapped[str] = mapped_column(Text, nullable=False)
    arc: Mapped[dict] = mapped_column(JSONB, nullable=False)
    celebration_triggers: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    cartridge_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    cof_map: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    argument_rubrics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    grading_criteria: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    methodology: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    preset: Mapped[Optional[str]] = mapped_column(Text, default='full_practice')
    status: Mapped[Optional[str]] = mapped_column(Text, default='active')
    arc_stage_reached: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    speaker: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    arc_stage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Completion(Base):
    __tablename__ = "completions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    cof_clinical: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cof_operational: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cof_financial: Mapped[bool] = mapped_column(Boolean, nullable=False)
    arc_stage_reached: Mapped[int] = mapped_column(Integer, nullable=False)
    cert_issued: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    cert_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lms_export_ready: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    dimension_scores: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class MeteringEvent(Base):
    __tablename__ = "metering_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    cohort_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    division_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    call_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tokens_in: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    tokens_out: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class PracticeSeries(Base):
    __tablename__ = "practice_series"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_to_cohort_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    assigned_to_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class PracticeSeriesItem(Base):
    __tablename__ = "practice_series_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    series_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    product_id: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    section: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_doc: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    approved_claim: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    keywords: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
