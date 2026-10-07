import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class ChangeType(str, enum.Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MODIFIED = "MODIFIED"
    UNCHANGED = "UNCHANGED"


class Severity(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ReviewStatus(str, enum.Enum):
    UNREVIEWED = "UNREVIEWED"
    CONFIRMED = "CONFIRMED"
    DISMISSED = "DISMISSED"


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    owner_user_id: Mapped[str] = mapped_column(String(200), index=True)
    plan: Mapped[str] = mapped_column(String(20), default="FREE")
    subscription_status: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    workspace = relationship("Workspace")


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(200), index=True)
    feedback_type: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(Text)
    screen: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    version_label: Mapped[str] = mapped_column(String(80))
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    source_hash: Mapped[str] = mapped_column(String(64))
    mapping_json: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30), default="COMPLETE")


class RequirementSnapshot(Base):
    __tablename__ = "requirement_snapshots"
    __table_args__ = (
        UniqueConstraint("import_batch_id", "external_id", name="uq_snapshot_import_external"),
        Index("ix_snapshot_project_external", "project_id", "external_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), index=True)
    import_batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("import_batches.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(120), index=True)
    requirement_type: Mapped[str] = mapped_column(String(120), default="")
    title: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(120), default="")
    parent_external_id: Mapped[str | None] = mapped_column(String(120))
    related_external_ids: Mapped[list] = mapped_column(JSONB, default=list)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    owner: Mapped[str | None] = mapped_column(String(200))
    normalized_text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    source_row_number: Mapped[int] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Comparison(Base):
    __tablename__ = "comparisons"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), index=True)
    baseline_import_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("import_batches.id"))
    comparison_import_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("import_batches.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(30), default="COMPLETE")
    summary_json: Mapped[dict] = mapped_column(JSONB, default=dict)


class RequirementChange(Base):
    __tablename__ = "requirement_changes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comparison_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("comparisons.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(120), index=True)
    change_type: Mapped[ChangeType] = mapped_column(Enum(ChangeType))
    old_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("requirement_snapshots.id"))
    new_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("requirement_snapshots.id"))
    changed_fields: Mapped[dict] = mapped_column(JSONB, default=dict)
    text_diff: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    old_snapshot = relationship("RequirementSnapshot", foreign_keys=[old_snapshot_id])
    new_snapshot = relationship("RequirementSnapshot", foreign_keys=[new_snapshot_id])


class ImpactFinding(Base):
    __tablename__ = "impact_findings"
    __table_args__ = (Index("ix_finding_change_review", "requirement_change_id", "review_status"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requirement_change_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("requirement_changes.id"), index=True)
    impacted_requirement_external_id: Mapped[str] = mapped_column(String(120), index=True)
    severity: Mapped[Severity] = mapped_column(Enum(Severity))
    confidence: Mapped[float] = mapped_column(Float)
    impact_score: Mapped[int] = mapped_column(Integer)
    detection_method: Mapped[str] = mapped_column(String(200))
    reason: Mapped[str] = mapped_column(Text)
    relationship_type: Mapped[str] = mapped_column(String(120))
    review_status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus), default=ReviewStatus.UNREVIEWED)
    reviewer_note: Mapped[str | None] = mapped_column(Text)
    manually_adjusted_severity: Mapped[Severity | None] = mapped_column(Enum(Severity))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    change = relationship("RequirementChange")
