"""v2299_users_aktif

Revision ID: v2299_users_aktif
Revises: v2298_scada_delete
Create Date: 2026-09-08

v2.299 — ekip yönetimi: kullanıcı pasifleştirilebilsin (silmek yerine — denetim izi ve atamalar korunur).
Pasif kullanıcı oturum açamaz; son etkin yönetici pasifleştirilemez/düşürülemez (servis kuralı).
"""
from alembic import op

revision = "v2299_users_aktif"
down_revision = "v2298_scada_delete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS aktif boolean NOT NULL DEFAULT true")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS aktif")
