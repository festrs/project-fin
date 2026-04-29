"""Float → Numeric for monetary and quantitative columns.

Revision ID: a3f9c2d1e8b0
Revises:
Create Date: 2026-04-26

"""
from alembic import op
import sqlalchemy as sa

revision = "a3f9c2d1e8b0"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.alter_column(
            "quantity",
            existing_type=sa.Float(),
            type_=sa.Numeric(19, 8),
            existing_nullable=True,
        )

    with op.batch_alter_table("stock_splits") as batch_op:
        batch_op.alter_column(
            "from_factor",
            existing_type=sa.Float(),
            type_=sa.Numeric(19, 8),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "to_factor",
            existing_type=sa.Float(),
            type_=sa.Numeric(19, 8),
            existing_nullable=False,
        )

    with op.batch_alter_table("asset_classes") as batch_op:
        batch_op.alter_column(
            "target_weight",
            existing_type=sa.Float(),
            type_=sa.Numeric(7, 4),
            existing_nullable=True,
        )

    with op.batch_alter_table("asset_weights") as batch_op:
        batch_op.alter_column(
            "target_weight",
            existing_type=sa.Float(),
            type_=sa.Numeric(7, 4),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("asset_weights") as batch_op:
        batch_op.alter_column(
            "target_weight",
            existing_type=sa.Numeric(7, 4),
            type_=sa.Float(),
            existing_nullable=True,
        )

    with op.batch_alter_table("asset_classes") as batch_op:
        batch_op.alter_column(
            "target_weight",
            existing_type=sa.Numeric(7, 4),
            type_=sa.Float(),
            existing_nullable=True,
        )

    with op.batch_alter_table("stock_splits") as batch_op:
        batch_op.alter_column(
            "to_factor",
            existing_type=sa.Numeric(19, 8),
            type_=sa.Float(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "from_factor",
            existing_type=sa.Numeric(19, 8),
            type_=sa.Float(),
            existing_nullable=False,
        )

    with op.batch_alter_table("transactions") as batch_op:
        batch_op.alter_column(
            "quantity",
            existing_type=sa.Numeric(19, 8),
            type_=sa.Float(),
            existing_nullable=True,
        )
