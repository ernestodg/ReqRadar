"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-05
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    change_type = postgresql.ENUM("ADDED", "REMOVED", "MODIFIED", "UNCHANGED", name="changetype", create_type=False)
    severity = postgresql.ENUM("HIGH", "MEDIUM", "LOW", name="severity", create_type=False)
    review = postgresql.ENUM("UNREVIEWED", "CONFIRMED", "DISMISSED", name="reviewstatus", create_type=False)
    postgresql.ENUM("ADDED", "REMOVED", "MODIFIED", "UNCHANGED", name="changetype").create(op.get_bind(), checkfirst=True)
    postgresql.ENUM("HIGH", "MEDIUM", "LOW", name="severity").create(op.get_bind(), checkfirst=True)
    postgresql.ENUM("UNREVIEWED", "CONFIRMED", "DISMISSED", name="reviewstatus").create(op.get_bind(), checkfirst=True)
    op.create_table("workspaces", sa.Column("id", sa.UUID(), primary_key=True), sa.Column("name", sa.String(200), nullable=False), sa.Column("owner_user_id", sa.String(200), nullable=False), sa.Column("plan", sa.String(20), nullable=False), sa.Column("subscription_status", sa.String(50)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_workspaces_owner_user_id", "workspaces", ["owner_user_id"])
    op.create_table("projects", sa.Column("id", sa.UUID(), primary_key=True), sa.Column("workspace_id", sa.UUID(), sa.ForeignKey("workspaces.id"), nullable=False), sa.Column("name", sa.String(200), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_projects_workspace_id", "projects", ["workspace_id"])
    op.create_table("import_batches", sa.Column("id", sa.UUID(), primary_key=True), sa.Column("project_id", sa.UUID(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("filename", sa.String(255), nullable=False), sa.Column("version_label", sa.String(80), nullable=False), sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("row_count", sa.Integer(), nullable=False), sa.Column("source_hash", sa.String(64), nullable=False), sa.Column("mapping_json", postgresql.JSONB(), nullable=False), sa.Column("status", sa.String(30), nullable=False))
    op.create_index("ix_import_batches_project_id", "import_batches", ["project_id"])
    op.create_table("requirement_snapshots", sa.Column("id", sa.UUID(), primary_key=True), sa.Column("project_id", sa.UUID(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("import_batch_id", sa.UUID(), sa.ForeignKey("import_batches.id"), nullable=False), sa.Column("external_id", sa.String(120), nullable=False), sa.Column("requirement_type", sa.String(120), nullable=False), sa.Column("title", sa.Text(), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("status", sa.String(120), nullable=False), sa.Column("parent_external_id", sa.String(120)), sa.Column("related_external_ids", postgresql.JSONB(), nullable=False), sa.Column("tags", postgresql.JSONB(), nullable=False), sa.Column("owner", sa.String(200)), sa.Column("normalized_text", sa.Text(), nullable=False), sa.Column("content_hash", sa.String(64), nullable=False), sa.Column("source_row_number", sa.Integer(), nullable=False), sa.Column("metadata_json", postgresql.JSONB(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.UniqueConstraint("import_batch_id", "external_id", name="uq_snapshot_import_external"))
    op.create_index("ix_requirement_snapshots_import_batch_id", "requirement_snapshots", ["import_batch_id"])
    op.create_index("ix_requirement_snapshots_project_id", "requirement_snapshots", ["project_id"])
    op.create_index("ix_requirement_snapshots_external_id", "requirement_snapshots", ["external_id"])
    op.create_index("ix_requirement_snapshots_content_hash", "requirement_snapshots", ["content_hash"])
    op.create_index("ix_snapshot_project_external", "requirement_snapshots", ["project_id", "external_id"])
    op.create_table("comparisons", sa.Column("id", sa.UUID(), primary_key=True), sa.Column("project_id", sa.UUID(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("baseline_import_id", sa.UUID(), sa.ForeignKey("import_batches.id"), nullable=False), sa.Column("comparison_import_id", sa.UUID(), sa.ForeignKey("import_batches.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("status", sa.String(30), nullable=False), sa.Column("summary_json", postgresql.JSONB(), nullable=False))
    op.create_index("ix_comparisons_project_id", "comparisons", ["project_id"])
    op.create_table("requirement_changes", sa.Column("id", sa.UUID(), primary_key=True), sa.Column("comparison_id", sa.UUID(), sa.ForeignKey("comparisons.id"), nullable=False), sa.Column("external_id", sa.String(120), nullable=False), sa.Column("change_type", change_type, nullable=False), sa.Column("old_snapshot_id", sa.UUID(), sa.ForeignKey("requirement_snapshots.id")), sa.Column("new_snapshot_id", sa.UUID(), sa.ForeignKey("requirement_snapshots.id")), sa.Column("changed_fields", postgresql.JSONB(), nullable=False), sa.Column("text_diff", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_requirement_changes_comparison_id", "requirement_changes", ["comparison_id"])
    op.create_index("ix_requirement_changes_external_id", "requirement_changes", ["external_id"])
    op.create_table("impact_findings", sa.Column("id", sa.UUID(), primary_key=True), sa.Column("requirement_change_id", sa.UUID(), sa.ForeignKey("requirement_changes.id"), nullable=False), sa.Column("impacted_requirement_external_id", sa.String(120), nullable=False), sa.Column("severity", severity, nullable=False), sa.Column("confidence", sa.Float(), nullable=False), sa.Column("impact_score", sa.Integer(), nullable=False), sa.Column("detection_method", sa.String(200), nullable=False), sa.Column("reason", sa.Text(), nullable=False), sa.Column("relationship_type", sa.String(120), nullable=False), sa.Column("review_status", review, nullable=False), sa.Column("reviewer_note", sa.Text()), sa.Column("manually_adjusted_severity", severity), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_impact_findings_requirement_change_id", "impact_findings", ["requirement_change_id"])
    op.create_index("ix_impact_findings_impacted_requirement_external_id", "impact_findings", ["impacted_requirement_external_id"])
    op.create_index("ix_finding_change_review", "impact_findings", ["requirement_change_id", "review_status"])


def downgrade() -> None:
    op.drop_table("impact_findings")
    op.drop_table("requirement_changes")
    op.drop_table("comparisons")
    op.drop_table("requirement_snapshots")
    op.drop_table("import_batches")
    op.drop_table("projects")
    op.drop_table("workspaces")
    postgresql.ENUM(name="reviewstatus").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="severity").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="changetype").drop(op.get_bind(), checkfirst=True)
