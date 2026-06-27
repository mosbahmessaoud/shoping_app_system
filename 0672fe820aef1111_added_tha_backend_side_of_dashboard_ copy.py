# """added tha backend side of dashboard website

# Revision ID: 0672fe820aef
# Revises: 5bf1fdaf1a2e
# Create Date: 2026-06-27 20:35:27.436683

# """
# from typing import Sequence, Union
# from alembic import op
# import sqlalchemy as sa

# revision: str = "0672fe820aef"
# down_revision: Union[str, None] = "5bf1fdaf1a2e"
# branch_labels: Union[str, Sequence[str], None] = None
# depends_on: Union[str, Sequence[str], None] = None


# def _enum_exists(conn, name: str) -> bool:
#     result = conn.execute(
#         sa.text("SELECT 1 FROM pg_type WHERE typname = :name"),
#         {"name": name},
#     )
#     return result.fetchone() is not None


# def upgrade() -> None:
#     conn = op.get_bind()

#     # ── 1. Create enum types only if they don't exist ────────────────────────
#     if not _enum_exists(conn, "store_user_role"):
#         conn.execute(sa.text("CREATE TYPE store_user_role AS ENUM ('admin', 'livreur')"))

#     if not _enum_exists(conn, "calling_status"):
#         conn.execute(sa.text("""
#             CREATE TYPE calling_status AS ENUM (
#                 'not_called', 'call1', 'call2', 'call3',
#                 'no_answer', 'unreachable',
#                 'confirmed_by_phone', 'cancelled_by_phone'
#             )
#         """))

#     if not _enum_exists(conn, "delivery_status"):
#         conn.execute(sa.text("""
#             CREATE TYPE delivery_status AS ENUM (
#                 'not_shipped', 'shipped', 'delivered', 'returned'
#             )
#         """))

#     if not _enum_exists(conn, "order_status"):
#         conn.execute(sa.text("""
#             CREATE TYPE order_status AS ENUM (
#                 'pending', 'confirmed', 'shipped', 'delivered', 'cancelled'
#             )
#         """))

#     # ── 2. Create store_users table ───────────────────────────────────────────
#     conn.execute(sa.text("""
#         CREATE TABLE IF NOT EXISTS store_users (
#             id            SERIAL PRIMARY KEY,
#             full_name     VARCHAR(150)    NOT NULL,
#             email         VARCHAR(255)    NOT NULL UNIQUE,
#             password_hash VARCHAR(255)    NOT NULL,
#             phone_number  VARCHAR(20),
#             role          store_user_role NOT NULL DEFAULT 'livreur',
#             is_active     BOOLEAN         NOT NULL DEFAULT TRUE,
#             created_at    TIMESTAMPTZ              DEFAULT now(),
#             updated_at    TIMESTAMPTZ
#         )
#     """))

#     # Indexes (IF NOT EXISTS supported for indexes in all modern PG)
#     conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_store_users_id    ON store_users (id)"))
#     conn.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_store_users_email ON store_users (email)"))

#     # ── 3. Add new columns to ecommerce_orders (one at a time, safely) ───────
#     # Check each column before adding to make the migration re-runnable
#     def column_exists(table: str, column: str) -> bool:
#         r = conn.execute(sa.text(
#             "SELECT 1 FROM information_schema.columns "
#             "WHERE table_name = :t AND column_name = :c"
#         ), {"t": table, "c": column})
#         return r.fetchone() is not None

#     if not column_exists("ecommerce_orders", "calling_status"):
#         conn.execute(sa.text(
#             "ALTER TABLE ecommerce_orders "
#             "ADD COLUMN calling_status calling_status NOT NULL DEFAULT 'not_called'"
#         ))

#     if not column_exists("ecommerce_orders", "delivery_status"):
#         conn.execute(sa.text(
#             "ALTER TABLE ecommerce_orders "
#             "ADD COLUMN delivery_status delivery_status NOT NULL DEFAULT 'not_shipped'"
#         ))

#     if not column_exists("ecommerce_orders", "livreur_notes"):
#         conn.execute(sa.text(
#             "ALTER TABLE ecommerce_orders ADD COLUMN livreur_notes VARCHAR(1000)"
#         ))

#     if not column_exists("ecommerce_orders", "assigned_livreur_id"):
#         conn.execute(sa.text(
#             "ALTER TABLE ecommerce_orders ADD COLUMN assigned_livreur_id INTEGER"
#         ))

#     if not column_exists("ecommerce_orders", "is_hidden_from_livreurs"):
#         conn.execute(sa.text(
#             "ALTER TABLE ecommerce_orders "
#             "ADD COLUMN is_hidden_from_livreurs BOOLEAN NOT NULL DEFAULT FALSE"
#         ))

#     # ── 4. Convert status VARCHAR → order_status enum ─────────────────────────
#     # Check current type first — skip if already an enum
#     r = conn.execute(sa.text(
#         "SELECT data_type FROM information_schema.columns "
#         "WHERE table_name = 'ecommerce_orders' AND column_name = 'status'"
#     ))
#     row = r.fetchone()
#     if row and row[0] == "character varying":
#         conn.execute(sa.text(
#             "ALTER TABLE ecommerce_orders "
#             "ALTER COLUMN status TYPE order_status USING status::order_status"
#         ))

#     # ── 5. Expand notes 500 → 1000 ────────────────────────────────────────────
#     conn.execute(sa.text(
#         "ALTER TABLE ecommerce_orders ALTER COLUMN notes TYPE VARCHAR(1000)"
#     ))

#     # ── 6. Indexes on new columns ─────────────────────────────────────────────
#     conn.execute(sa.text(
#         "CREATE INDEX IF NOT EXISTS ix_ecommerce_orders_assigned_livreur_id "
#         "ON ecommerce_orders (assigned_livreur_id)"
#     ))
#     conn.execute(sa.text(
#         "CREATE INDEX IF NOT EXISTS ix_ecommerce_orders_calling_status "
#         "ON ecommerce_orders (calling_status)"
#     ))
#     conn.execute(sa.text(
#         "CREATE INDEX IF NOT EXISTS ix_ecommerce_orders_delivery_status "
#         "ON ecommerce_orders (delivery_status)"
#     ))

#     # ── 7. Foreign key ────────────────────────────────────────────────────────
#     # Check if FK already exists before creating
#     r = conn.execute(sa.text(
#         "SELECT 1 FROM information_schema.table_constraints "
#         "WHERE constraint_name = 'fk_ecommerce_orders_store_users'"
#     ))
#     if not r.fetchone():
#         op.create_foreign_key(
#             "fk_ecommerce_orders_store_users",
#             "ecommerce_orders", "store_users",
#             ["assigned_livreur_id"], ["id"],
#             ondelete="SET NULL",
#         )


# def downgrade() -> None:
#     conn = op.get_bind()

#     op.drop_constraint("fk_ecommerce_orders_store_users", "ecommerce_orders", type_="foreignkey")

#     conn.execute(sa.text("DROP INDEX IF EXISTS ix_ecommerce_orders_delivery_status"))
#     conn.execute(sa.text("DROP INDEX IF EXISTS ix_ecommerce_orders_calling_status"))
#     conn.execute(sa.text("DROP INDEX IF EXISTS ix_ecommerce_orders_assigned_livreur_id"))

#     # Revert status enum → varchar
#     conn.execute(sa.text(
#         "ALTER TABLE ecommerce_orders "
#         "ALTER COLUMN status TYPE VARCHAR(30) USING status::text"
#     ))

#     # Revert notes 1000 → 500
#     conn.execute(sa.text(
#         "ALTER TABLE ecommerce_orders ALTER COLUMN notes TYPE VARCHAR(500)"
#     ))

#     conn.execute(sa.text("""
#         ALTER TABLE ecommerce_orders
#             DROP COLUMN IF EXISTS is_hidden_from_livreurs,
#             DROP COLUMN IF EXISTS assigned_livreur_id,
#             DROP COLUMN IF EXISTS livreur_notes,
#             DROP COLUMN IF EXISTS delivery_status,
#             DROP COLUMN IF EXISTS calling_status
#     """))

#     conn.execute(sa.text("DROP INDEX IF EXISTS ix_store_users_email"))
#     conn.execute(sa.text("DROP INDEX IF EXISTS ix_store_users_id"))
#     conn.execute(sa.text("DROP TABLE IF EXISTS store_users"))

#     conn.execute(sa.text("DROP TYPE IF EXISTS order_status"))
#     conn.execute(sa.text("DROP TYPE IF EXISTS delivery_status"))
#     conn.execute(sa.text("DROP TYPE IF EXISTS calling_status"))
#     conn.execute(sa.text("DROP TYPE IF EXISTS store_user_role"))
