"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clinics",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("whatsapp_number", sa.String(50), nullable=False),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="Asia/Jerusalem"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("whatsapp_number"),
    )

    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("phone_number", sa.String(50), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("language", sa.String(10), nullable=False, server_default="he"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clinic_id", "phone_number"),
    )

    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("service_key", sa.String(100), nullable=False),
        sa.Column("name_he", sa.String(255), nullable=False),
        sa.Column("name_en", sa.String(255)),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("provider_name", sa.String(255)),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="confirmed"),
        sa.Column("ref_code", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ref_code"),
    )
    op.create_index("idx_appointments_clinic_start", "appointments", ["clinic_id", "start_time"])
    op.create_index("idx_appointments_patient", "appointments", ["patient_id", "status"])

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=False)),
        sa.Column("phone_number", sa.String(50), nullable=False),
        sa.Column("state", sa.String(50), nullable=False, server_default="idle"),
        sa.Column("state_data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("last_message_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_conversations_phone", "conversations", ["clinic_id", "phone_number"])

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_messages_conversation", "messages", ["conversation_id", "created_at"])

    op.create_table(
        "working_hours",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("day_of_week", sa.SmallInteger(), nullable=False),
        sa.Column("open_time", sa.Time(), nullable=False),
        sa.Column("close_time", sa.Time(), nullable=False),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("working_hours")
    op.drop_index("idx_messages_conversation")
    op.drop_table("messages")
    op.drop_index("idx_conversations_phone")
    op.drop_table("conversations")
    op.drop_index("idx_appointments_patient")
    op.drop_index("idx_appointments_clinic_start")
    op.drop_table("appointments")
    op.drop_table("services")
    op.drop_table("patients")
    op.drop_table("clinics")
