"""pvquant.db — baglanti + kiraci baglami. RLS'in Python ayagı."""
from __future__ import annotations
import os
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DB_URL = os.environ.get(
    "PVQ_DB_URL",
    "postgresql+psycopg://pvquant:pvquant_dev@localhost:5432/pvquant",
)
engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def tenant_baglami(tenant_id: str):
    """Her is birimi bu blok icinde kosar; RLS bu degiskeni okur.
    KURAL: services/ icindeki her fonksiyon session'i BURADAN alir."""
    s = SessionLocal()
    try:
        s.execute(text("SET LOCAL ROLE pvq_app"))
        s.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tenant_id)})
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


@contextmanager
def sistem_baglami():
    """Tenant'siz isler (login, tenant olusturma). DIKKAT: yalniz
    auth_service ve migration kullanir; baska yerde cagirmak YASAK."""
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
