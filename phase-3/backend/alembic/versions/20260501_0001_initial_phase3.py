"""Initial Phase 3 product tables.

Revision ID: 20260501_0001
Revises:
Create Date: 2026-05-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260501_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "report_quota",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("plan", sa.String(length=32), nullable=False),
        sa.Column("reports_used_this_month", sa.Integer(), nullable=False),
        sa.Column("reports_limit", sa.Integer(), nullable=True),
        sa.Column("period_reset_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "applicants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("dsa_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("income", sa.Float(), nullable=False),
        sa.Column("credit_amount", sa.Float(), nullable=False),
        sa.Column("annuity", sa.Float(), nullable=False),
        sa.Column("employment_years", sa.Float(), nullable=False),
        sa.Column("age_years", sa.Float(), nullable=False),
        sa.Column("family_size", sa.Integer(), nullable=False),
        sa.Column("education", sa.String(length=128), nullable=False),
        sa.Column("income_type", sa.String(length=128), nullable=False),
        sa.Column("housing_type", sa.String(length=128), nullable=False),
        sa.Column("occupation", sa.String(length=128), nullable=True),
        sa.Column("family_status", sa.String(length=128), nullable=False),
        sa.Column("feature_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("risk_class", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("shap_top_features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("final_report", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("processing_steps", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dsa_decision", sa.String(length=32), nullable=True),
        sa.Column("lender_outcome", sa.String(length=32), nullable=True),
        sa.Column("lender_name", sa.String(length=255), nullable=True),
        sa.Column("outcome_logged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("include_in_training", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_applicants_dsa_created", "applicants", ["dsa_user_id", "created_at"])

    op.create_table(
        "model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("training_sample_count", sa.Integer(), nullable=True),
        sa.Column("roc_auc", sa.Float(), nullable=True),
        sa.Column("recall", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.UniqueConstraint("version", name="uq_model_versions_version"),
    )

    op.create_table(
        "training_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("triggered_by", sa.String(length=32), nullable=False),
        sa.Column("new_labels_used", sa.Integer(), nullable=True),
        sa.Column("base_model_version", sa.String(length=64), nullable=True),
        sa.Column("output_model_version", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("training_runs")
    op.drop_table("model_versions")
    op.drop_index("ix_applicants_dsa_created", table_name="applicants")
    op.drop_table("applicants")
    op.drop_table("report_quota")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
