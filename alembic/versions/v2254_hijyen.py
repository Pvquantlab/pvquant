"""v2254_hijyen

Revision ID: v2254_hijyen
Revises: v2252_konformal
Create Date: 2026-09-06

v2.254 — Dalga 3.9: veri hijyeni. scada_hourly.kirpma (bool): saat AC tavanında plato — ölçüm GEÇERLİ
kalır (flag 'valid'; karne sayar, tahmin de tavanı modellemeli) ama fizik/rezidüel KALİBRASYONU bu
saatleri dışarıda bırakır (tavanlı güç DC fiziğini yansıtmaz). Şebeke kısıntısı ise flag='kisinti'
ile işaretlenir (silinmez; flag != 'valid' olduğundan kalibrasyon ve karne otomatik dışlar; geri
alınabilir — gece işi her koşuda yeniden değerlendirir).
"""
from alembic import op

revision = "v2254_hijyen"
down_revision = "v2252_konformal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE scada_hourly ADD COLUMN IF NOT EXISTS kirpma boolean NOT NULL DEFAULT false")


def downgrade() -> None:
    op.execute("UPDATE scada_hourly SET flag='valid' WHERE flag='kisinti'")
    op.execute("ALTER TABLE scada_hourly DROP COLUMN IF EXISTS kirpma")
