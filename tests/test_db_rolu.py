"""25.10 v2.488 (denetim Y1) — uygulama DB rolü: PVQ_DB_URL pvq_api ise süper kullanıcı DEĞİL, BYPASSRLS var, pvq_app'e geçebilir;
kiracı bağlamında RLS yine devrede (test_rls_izolasyon ile birlikte). Yerel geliştirmede pvquant ile koşuluyorsa rol sınaması atlanır,
yetki sınaması (pvq_api rolü var, üyelik var) yine koşar."""
import os
import pytest
from sqlalchemy import text

from pvquant.db import sistem_baglami, tenant_baglami


def _kullanici() -> str:
    with sistem_baglami() as s:
        return s.execute(text("SELECT current_user")).scalar()


def test_pvq_api_rolu_ve_yetkileri_var():
    with sistem_baglami() as s:
        r = s.execute(text("SELECT rolsuper, rolbypassrls, rolcanlogin, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname='pvq_api'")).first()
        assert r is not None, "pvq_api rolü yok (alembic head v2488 koşmadı)"
        assert (bool(r.rolsuper), bool(r.rolbypassrls), bool(r.rolcanlogin), bool(r.rolcreaterole), bool(r.rolcreatedb)) == (False, True, True, False, False)
        assert s.execute(text("SELECT pg_has_role('pvq_api', 'pvq_app', 'MEMBER')")).scalar() is True
        # her tabloya DML ve dizilere kullanım
        eksik = s.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' "
            "AND NOT has_table_privilege('pvq_api', quote_ident(table_name), 'SELECT, INSERT, UPDATE, DELETE')")).scalars().all()
        assert eksik == [], f"pvq_api yetkisi eksik tablolar: {eksik}"
        # iki adım: planlayıcı has_sequence_privilege'i relkind süzgecinden önce değerlendirebiliyor («… is not a sequence»)
        diziler = s.execute(text("SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                                 "WHERE n.nspname = 'public' AND c.relkind = 'S'")).scalars().all()
        eksik_dizi = [d for d in diziler if not s.execute(text("SELECT has_sequence_privilege('pvq_api', :d, 'USAGE')"), {"d": f"public.{d}"}).scalar()]
        assert eksik_dizi == []


@pytest.mark.skipif("pvq_api" not in os.environ.get("PVQ_DB_URL", ""), reason="yerel: pvquant ile koşuyor")
def test_uygulama_super_kullanici_degil():
    assert _kullanici() == "pvq_api"
    with sistem_baglami() as s:
        r = s.execute(text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")).first()
        assert (bool(r.rolsuper), bool(r.rolbypassrls)) == (False, True)
        # süper kullanıcıya özgü işler reddedilir
        with pytest.raises(Exception):
            s.execute(text("COPY (SELECT 1) TO PROGRAM 'true'"))
    with sistem_baglami() as s:
        with pytest.raises(Exception):
            s.execute(text("CREATE ROLE sizinti_denemesi"))
    # kiracı bağlamı pvq_app'e geçer; orada BYPASSRLS yoktur
    with tenant_baglami("00000000-0000-0000-0000-000000000001") as s:
        assert s.execute(text("SELECT current_user")).scalar() == "pvq_app"
        assert s.execute(text("SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user")).scalar() is False
