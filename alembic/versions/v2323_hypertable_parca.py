"""v2323_hypertable_parca

Revision ID: v2323_hypertable_parca
Revises: v2299_users_aktif
Create Date: 2026-09-15

v2.323 — hypertable parça vergisi: ilk şema scada_hourly ve forecast_values'u
7 günlük zaman parçası × 8 uzam bölmesi (plant_id) ile kurmuştu. Sonuç: 19,7k
satırlık scada_hourly 1304 alt tabloya bölündü ve HER sorguda planlayıcı 1304
çocuğu tek tek değerlendirir oldu (ölçüldü: çalışma 95 ms, PLANLAMA 736 ms —
/v1/portfoy'un ~950 ms'sinin kaynağı; forecast_values de haftada 8 parça
büyüyordu). Saatlik veri için doğru ölçek: uzam bölmesi YOK, 1 yıllık parça
(~8760 satır/parça/santral). İki tablo da aynı iskelet+veri+kural korunarak
yeniden kurulur: kolonlar/varsayılanlar/PK LIKE ile birebir, FK + zorunlu RLS
politikası + pvq_app yetkileri elle yeniden bağlanır (scada'da DELETE v2.298
kararı, forecast_values'ta yok). Kopya tek işlemde — yarım durum kalmaz.
"""
from alembic import op

revision = "v2323_hypertable_parca"
down_revision = "v2299_users_aktif"
branch_labels = None
depends_on = None


def _yeniden_kur(tablo: str, fk_sql: str, pvq_app_yetki: str, parca: str) -> None:
    op.execute(f"""
    CREATE TABLE {tablo}_yeni (LIKE {tablo}
      INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES);
    SELECT create_hypertable('{tablo}_yeni', 'ts_utc',
      chunk_time_interval => INTERVAL '{parca}');
    INSERT INTO {tablo}_yeni SELECT * FROM {tablo};
    DROP TABLE {tablo};
    ALTER TABLE {tablo}_yeni RENAME TO {tablo};
    {fk_sql}
    ALTER TABLE {tablo} ENABLE ROW LEVEL SECURITY;
    ALTER TABLE {tablo} FORCE ROW LEVEL SECURITY;
    CREATE POLICY p_{tablo} ON {tablo}
      USING (tenant_id = current_setting('app.tenant_id')::uuid)
      WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
    GRANT {pvq_app_yetki} ON {tablo} TO pvq_app;
    """)


def upgrade() -> None:
    _yeniden_kur(
        "scada_hourly",
        "ALTER TABLE scada_hourly ADD FOREIGN KEY (plant_id) REFERENCES plants(id);",
        "SELECT, INSERT, UPDATE, DELETE",   # DELETE: v2.298 "veriniz sizindir"
        "1 year")
    _yeniden_kur(
        "forecast_values",
        "ALTER TABLE forecast_values ADD FOREIGN KEY (run_id) REFERENCES forecast_runs(id);",
        "SELECT, INSERT, UPDATE",
        "1 year")


def downgrade() -> None:
    # İlk şemanın düzenine dönüş (7 gün × 8 uzam bölmesi) — aynı yöntem, ters yön.
    for tablo, fk, yetki in (
        ("scada_hourly",
         "ALTER TABLE scada_hourly ADD FOREIGN KEY (plant_id) REFERENCES plants(id);",
         "SELECT, INSERT, UPDATE, DELETE"),
        ("forecast_values",
         "ALTER TABLE forecast_values ADD FOREIGN KEY (run_id) REFERENCES forecast_runs(id);",
         "SELECT, INSERT, UPDATE"),
    ):
        op.execute(f"""
        CREATE TABLE {tablo}_eski (LIKE {tablo}
          INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES);
        SELECT create_hypertable('{tablo}_eski', 'ts_utc',
          partitioning_column => 'plant_id', number_partitions => 8);
        INSERT INTO {tablo}_eski SELECT * FROM {tablo};
        DROP TABLE {tablo};
        ALTER TABLE {tablo}_eski RENAME TO {tablo};
        {fk}
        ALTER TABLE {tablo} ENABLE ROW LEVEL SECURITY;
        ALTER TABLE {tablo} FORCE ROW LEVEL SECURITY;
        CREATE POLICY p_{tablo} ON {tablo}
          USING (tenant_id = current_setting('app.tenant_id')::uuid)
          WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
        GRANT {yetki} ON {tablo} TO pvq_app;
        """)
