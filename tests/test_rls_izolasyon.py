"""RLS sizinti testi: iki tenant birbirinin verisini goremez."""
import uuid
import pytest
from sqlalchemy import text
from pvquant.db import sistem_baglami, tenant_baglami


@pytest.fixture
def iki_tenant():
    """Iki tenant + iki santral olustur, ID'leri dondur."""
    a_id = str(uuid.uuid4())
    b_id = str(uuid.uuid4())
    a_plant = str(uuid.uuid4())
    b_plant = str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name) VALUES(:i, 'A'), (:j, 'B')"),
                  {"i": a_id, "j": b_id})
    with tenant_baglami(a_id) as s:
        s.execute(text(
            "INSERT INTO plants(id, tenant_id, name, lat, lon, tz, capacity_kwp) "
            "VALUES(:pid, :tid, 'A-plant', 37.0, 32.0, 'Europe/Istanbul', 1000)"),
            {"pid": a_plant, "tid": a_id})
    with tenant_baglami(b_id) as s:
        s.execute(text(
            "INSERT INTO plants(id, tenant_id, name, lat, lon, tz, capacity_kwp) "
            "VALUES(:pid, :tid, 'B-plant', 39.0, 35.0, 'Europe/Istanbul', 2000)"),
            {"pid": b_plant, "tid": b_id})
    yield {"a": a_id, "b": b_id, "a_plant": a_plant, "b_plant": b_plant}
    # Temizlik: sistem baglamiyla sil
    with sistem_baglami() as s:
        s.execute(text("DELETE FROM plants WHERE tenant_id IN (:a, :b)"),
                  {"a": a_id, "b": b_id})
        s.execute(text("DELETE FROM tenants WHERE id IN (:a, :b)"),
                  {"a": a_id, "b": b_id})


def test_a_yalniz_kendini_gorur(iki_tenant):
    """Tenant A bagliginda YALNIZ A'nin santrali gorunur."""
    with tenant_baglami(iki_tenant["a"]) as s:
        rows = s.execute(text("SELECT id FROM plants")).fetchall()
    assert len(rows) == 1
    assert str(rows[0][0]) == iki_tenant["a_plant"]


def test_b_yalniz_kendini_gorur(iki_tenant):
    """Tenant B bagliginda YALNIZ B'nin santrali gorunur."""
    with tenant_baglami(iki_tenant["b"]) as s:
        rows = s.execute(text("SELECT id FROM plants")).fetchall()
    assert len(rows) == 1
    assert str(rows[0][0]) == iki_tenant["b_plant"]


def test_a_baginda_b_ye_insert_yasak(iki_tenant):
    """Tenant A bagliginda B'nin tenant_id'siyle INSERT etmek RLS ile reddedilir."""
    from sqlalchemy.exc import DatabaseError
    with pytest.raises(DatabaseError):
        with tenant_baglami(iki_tenant["a"]) as s:
            s.execute(text(
                "INSERT INTO plants(tenant_id, name, lat, lon, tz, capacity_kwp) "
                "VALUES(:tid, 'sizinti', 0, 0, 'UTC', 1)"),
                {"tid": iki_tenant["b"]})
