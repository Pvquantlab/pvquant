"""aktif tekillik — calibrations/ml_models parca-tekil indeks

v2.163: coklu-aktif yarisi DB katinda imkansizlasir; sorgular ayrica
ORDER BY created_at DESC ile deterministik (en yeni kazanir).

Revision ID: v2163_aktif_tekillik
Revises: v2103_report_tables
"""
from alembic import op

revision = "v2163_aktif_tekillik"
down_revision = "v2103_report_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE UNIQUE INDEX uq_calibrations_aktif
        ON calibrations(plant_id) WHERE active;
    CREATE UNIQUE INDEX uq_ml_models_aktif
        ON ml_models(plant_id) WHERE active;
    """)


def downgrade() -> None:
    op.execute("""
    DROP INDEX IF EXISTS uq_calibrations_aktif;
    DROP INDEX IF EXISTS uq_ml_models_aktif;
    """)
