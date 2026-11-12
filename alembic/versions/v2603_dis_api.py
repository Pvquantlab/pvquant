"""v2.603 (Faz 4 paketi F4-I, Stage 11 kurumsal API) — `api_keys.plant_ids`: anahtarın santral kapsamı.

NULL = kiracının tüm santralleri (eski davranış); dolu dizi = yalnız listelenen santraller (dış API uçları 403 `santral_kapsam_disi` döner,
santral listesi süzülür). Kapsam sözlüğü (`ext/platform/api_anahtar.KAPSAMLAR`) üç yeni kapsam alır: veri_kalitesi:oku, portfoy:oku, finans:oku
(kodda; şemada kapsamlar jsonb listesi olduğundan göç gerekmez).

Revision ID: v2603_dis_api
Revises: v2602_denetim
"""
from alembic import op

revision = "v2603_dis_api"
down_revision = "v2602_denetim"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS plant_ids UUID[]")


def downgrade() -> None:
    op.execute("ALTER TABLE api_keys DROP COLUMN IF EXISTS plant_ids")
