"""added tha backend side of dashboard website

Revision ID: 0672fe820aef
Revises: 5bf1fdaf1a2e
Create Date: 2026-06-27 20:35:27.436683

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0672fe820aef"
down_revision: Union[str, None] = "5bf1fdaf1a2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # ── Step 1: Create ENUMs with checkfirst=True (safe if already exist) ────
    # create_type=False on columns below stops SQLAlchemy auto-creating them again

    postgresql.ENUM("admin", "livreur", name="store_user_role").create(
        bind, checkfirst=True
    )
    postgresql.ENUM(
        "not_called",
        "call1",
        "call2",
        "call3",
        "no_answer",
        "unreachable",
        "confirmed_by_phone",
        "cancelled_by_phone",
        name="calling_status",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "not_shipped",
        "shipped",
        "delivered",
        "returned",
        name="delivery_status",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "pending",
        "confirmed",
        "shipped",
        "delivered",
        "cancelled",
        name="order_status",
    ).create(bind, checkfirst=True)

    # ── Step 2: Create store_users (create_type=False prevents double-create) ─

    op.create_table(
        "store_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=True),
        sa.Column(
            "role",
            postgresql.ENUM(
                "admin", "livreur", name="store_user_role", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_store_users_email"), "store_users", ["email"], unique=True)
    op.create_index(op.f("ix_store_users_id"), "store_users", ["id"], unique=False)

    # ── Step 3: Add new columns to ecommerce_orders ───────────────────────────

    op.add_column(
        "ecommerce_orders",
        sa.Column(
            "calling_status",
            postgresql.ENUM(
                "not_called",
                "call1",
                "call2",
                "call3",
                "no_answer",
                "unreachable",
                "confirmed_by_phone",
                "cancelled_by_phone",
                name="calling_status",
                create_type=False,
            ),
            nullable=False,
            server_default="not_called",
        ),
    )

    op.add_column(
        "ecommerce_orders",
        sa.Column(
            "delivery_status",
            postgresql.ENUM(
                "not_shipped",
                "shipped",
                "delivered",
                "returned",
                name="delivery_status",
                create_type=False,
            ),
            nullable=False,
            server_default="not_shipped",
        ),
    )

    op.add_column(
        "ecommerce_orders",
        sa.Column(
            "livreur_notes",
            sa.String(length=1000),
            nullable=True,
        ),
    )

    op.add_column(
        "ecommerce_orders",
        sa.Column(
            "assigned_livreur_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "ecommerce_orders",
        sa.Column(
            "is_hidden_from_livreurs",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # ── Step 4: Convert status VARCHAR → order_status ENUM ───────────────────

    op.alter_column(
        "ecommerce_orders",
        "status",
        existing_type=sa.VARCHAR(length=30),
        type_=postgresql.ENUM(
            "pending",
            "confirmed",
            "shipped",
            "delivered",
            "cancelled",
            name="order_status",
            create_type=False,
        ),
        existing_nullable=False,
        postgresql_using="status::order_status",
    )

    # ── Step 5: Widen notes VARCHAR(500) → VARCHAR(1000) ─────────────────────

    op.alter_column(
        "ecommerce_orders",
        "notes",
        existing_type=sa.VARCHAR(length=500),
        type_=sa.String(length=1000),
        existing_nullable=True,
    )

    # ── Step 6: Indexes & FK ──────────────────────────────────────────────────

    op.create_index(
        op.f("ix_ecommerce_orders_assigned_livreur_id"),
        "ecommerce_orders",
        ["assigned_livreur_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ecommerce_orders_calling_status"),
        "ecommerce_orders",
        ["calling_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ecommerce_orders_delivery_status"),
        "ecommerce_orders",
        ["delivery_status"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_ecommerce_orders_store_users",
        "ecommerce_orders",
        "store_users",
        ["assigned_livreur_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_constraint(
        "fk_ecommerce_orders_store_users", "ecommerce_orders", type_="foreignkey"
    )
    op.drop_index(
        op.f("ix_ecommerce_orders_delivery_status"), table_name="ecommerce_orders"
    )
    op.drop_index(
        op.f("ix_ecommerce_orders_calling_status"), table_name="ecommerce_orders"
    )
    op.drop_index(
        op.f("ix_ecommerce_orders_assigned_livreur_id"), table_name="ecommerce_orders"
    )

    op.alter_column(
        "ecommerce_orders",
        "notes",
        existing_type=sa.String(length=1000),
        type_=sa.VARCHAR(length=500),
        existing_nullable=True,
    )

    op.alter_column(
        "ecommerce_orders",
        "status",
        existing_type=postgresql.ENUM(
            "pending",
            "confirmed",
            "shipped",
            "delivered",
            "cancelled",
            name="order_status",
            create_type=False,
        ),
        type_=sa.VARCHAR(length=30),
        existing_nullable=False,
        postgresql_using="status::varchar",
    )

    op.drop_column("ecommerce_orders", "is_hidden_from_livreurs")
    op.drop_column("ecommerce_orders", "assigned_livreur_id")
    op.drop_column("ecommerce_orders", "livreur_notes")
    op.drop_column("ecommerce_orders", "delivery_status")
    op.drop_column("ecommerce_orders", "calling_status")

    op.drop_index(op.f("ix_store_users_id"), table_name="store_users")
    op.drop_index(op.f("ix_store_users_email"), table_name="store_users")
    op.drop_table("store_users")

    # Drop enums last (columns using them are already gone)
    postgresql.ENUM(name="order_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="delivery_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="calling_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="store_user_role").drop(bind, checkfirst=True)
