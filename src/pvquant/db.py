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
    """Tenant'siz isler (login, tenant olusturma). DIKKAT: yalniz auth_service, migration ve kimliksiz
    ucların ÖZETLE (SHA-256) tek satır araması kullanır (edge_service toplayıcı anahtarı, bulut_oauth_service
    durum değeri): arama sonucu hemen kiracı bağlamına geçilir, başka sorgu bu bağlamda yapılmaz.
    Bunun dışında çağırmak YASAK (10.11.2026 güncellemesi)."""
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


@contextmanager
def platform_baglami(aktor_id: str):
    """24.10 Faz 1 — PLATFORM (PVQuant personeli) işleri: kiracılar arası, RLS dışı (uygulama kullanıcısı), ADLI ve İZLİ.
    sistem_baglami'nden farkı: çağıran bir platform aktörü bildirmek ZORUNDADIR (app.platform_aktor oturum değişkeni) ve
    her platform ucu denetim_izi'ne yazar (denetim_service.kaydet). Kiracı verisini OKURKEN mümkünse tenant_baglami(id)
    tercih edilir — RLS devrede kalır, yalnız kiracı kimliği platformdan gelir. Yalnız apps/api/yonetim.py ve
    platform_service kullanır."""
    if not aktor_id:
        raise ValueError("platform_baglami: aktör zorunlu")
    s = SessionLocal()
    try:
        s.execute(text("SELECT set_config('app.platform_aktor', :a, true)"), {"a": str(aktor_id)})
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


_bakim_sessionmaker = None


def _bakim_oturumu():
    global _bakim_sessionmaker
    url = os.environ.get("PVQ_BAKIM_DB_URL")
    if not url:
        return SessionLocal()
    if _bakim_sessionmaker is None:
        _bakim_sessionmaker = sessionmaker(bind=create_engine(url, pool_pre_ping=True), expire_on_commit=False)
    return _bakim_sessionmaker()


@contextmanager
def bakim_baglami():
    """v2.597 (Faz 4 F4-B): tahmin arşivi BAKIM bağlamı — forecast_runs/forecast_values üzerindeki değişmezlik tetikleyicisi
    yalnız bu bağlamda (app.arsiv_bakim='1') UPDATE/DELETE'e izin verir. Üretim kodu çağırmaz; göç, bakım betikleri
    (scripts/seed_sentetik.py) ve test fixture temizlikleri kullanır. Kiracı bağlamı yok (sahip rolü), RLS devre dışı.
    v2.606: PVQ_BAKIM_DB_URL tanımlıysa (CI: tam takım pvq_api rolüyle koşar, bakım ise DB sahibiyle) o bağlantı kullanılır;
    yoksa PVQ_DB_URL (yerelde zaten sahip). pvq_api/pvq_app'ten UPDATE/DELETE yetkisi şemada kaldırıldığı için bakım sahip ister."""
    s = _bakim_oturumu()
    try:
        s.execute(text("SELECT set_config('app.arsiv_bakim', '1', true)"))
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
