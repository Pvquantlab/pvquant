"""Faz 9 (14.11.2026) — E alanı: rol × kiracı × kaynak × işlem yetki matrisi (çekirdeğe dokunmaz; yalnız uçları ve DB rollerini sınar).

Bölüm 1 (DB'siz): uç envanteri bekçisi (kimliksiz uç listesi sabit), viewer → her yazma ucunda 403, editor → her admin ucunda 403,
  platform/müşteri jeton kapsamı ayrımı, temsil jetonunun yazma ve yan etkili GET davranışı, iec104 nokta tablosu ucu (Ş18).
Bölüm 2 (DB; PVQ_DB_URL test DB — CI düzeni pvq_api rolü): kiracı A yöneticisi, kiracı B'nin santral/portföy kimlikleriyle müşteri uçlarının
  TAMAMINI dolaşır: hiçbir yanıtta B'nin işaret adı/kiracı kimliği görünmez; yazma uçları B'nin santralini değiştiremez. Dış API anahtarı:
  kapsam × santral kapsamı × kiracı. DB rol düzeyi: pvq_app bağlamından RLS'siz tablolara erişim (K3 şüphelerinin K1 sınaması), pvq_api'nin
  «değiştirilemez» tablolardaki tekil UPDATE/DELETE yetkileri.
Ham matris FAZ9_CIKTI ortam değişkeni verilirse oraya CSV olarak yazılır (07_Guvenlik_Testleri.md, guvenlik_matrisi.csv).
Ölçüt bağları: E-Z1 kiracılar arası sızıntı yok · E-Z2 rol kapısı · E-Z3 API anahtarı kapsamı · E-Z4 kimliksiz uç listesi · E-B1 DB savunma derinliği.
Koşu: PVQ_DB_URL=<test DB> PYTHONPATH=src .venv/bin/python3 -m pytest -q -p no:cacheprovider tests/test_faz9_guvenlik_matrisi.py
"""
from __future__ import annotations

import csv
import io
import os
import re
import uuid
from collections.abc import Iterator

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici

CIKTI = os.environ.get("FAZ9_CIKTI")


# ------------------------------------------------------------------------------------------------ envanter yardımcıları
def tum_uclar() -> Iterator[APIRoute]:
    for x in api_main.app.routes:
        if isinstance(x, APIRoute):
            yield x
        elif type(x).__name__ == "_IncludedRouter":          # FastAPI 0.138: include_router tembel sarmalayıcı
            for r in x.original_router.routes:
                if isinstance(r, APIRoute):
                    yield r


def _agac(dep, out: set[str]) -> set[str]:
    for d in dep.dependencies:
        out.add(getattr(d.call, "__qualname__", str(d.call)))
        _agac(d, out)
    return out


def kapi_turu(r: APIRoute) -> str:
    s = _agac(r.dependant, set())
    if any("platform_yetkisi" in z for z in s):
        return "platform"
    if any("api_anahtari" in z for z in s):
        return "api_anahtari"
    if any("toplayici_anahtari" in z for z in s):
        return "toplayici"
    if any("yonetici_yetkisi" in z for z in s):
        return "admin"
    if any("yazma_yetkisi" in z for z in s):
        return "editor"
    if any("gecerli_kullanici" in z for z in s):
        return "viewer"
    return "kimliksiz"


KIMLIKSIZ_BEKLENEN = {
    ("POST", "/v1/auth/login"), ("POST", "/v1/yonetim/giris"), ("GET", "/v1/dogrulama"), ("POST", "/v1/vitrin/basvuru"),
    ("POST", "/v1/parola-sifirla-istek"), ("POST", "/v1/parola-sifirla"), ("GET", "/v1/bulut/oauth/{saglayici}/geri-donus"),
    ("GET", "/v1/healthz"), ("GET", "/v1/readyz"), ("GET", "/v1/report/json-schema"),   # readyz: Faz 9 P8 (F9-F01)
}
# viewer'ın yazabildiği (belgeli) müşteri uçları: kendi hesabı + Ş13
VIEWER_YAZMA_BELGELI = {
    "/v1/oturum/yenile", "/v1/parola", "/v1/iki-adim/baslat", "/v1/iki-adim/dogrula", "/v1/iki-adim", "/v1/iki-adim/kapat",
    "/v1/iki-adim/kurtarma-kodlari", "/v1/iki-adim/kurtarma-yenile", "/v1/plants/{plant_id}/alarmlar/{alarm_id}/okundu", "/v1/plants/{plant_id}/fizik-terimleri/onizle",
    "/v1/plants/{plant_id}/scada/preview",
}


def _yontem_yol(r: APIRoute):
    for m in sorted(r.methods):
        yield m, r.path


def _sahte_yol(path: str, degerler: dict[str, str]) -> str:
    return re.sub(r"{(\w+)(?::\w+)?}", lambda m: degerler.get(m.group(1), str(uuid.uuid4())), path)


def _yaz_csv(ad: str, satirlar: list[dict]) -> None:
    if not CIKTI or not satirlar:
        return
    os.makedirs(CIKTI, exist_ok=True)
    with open(os.path.join(CIKTI, ad), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(satirlar[0].keys()))
        w.writeheader()
        w.writerows(satirlar)


@pytest.fixture(autouse=True)
def _temiz():
    yield
    api_main.app.dependency_overrides.clear()


def _rol(rol: str, tenant: str = "t-faz9", sub: str = "u-faz9"):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": sub, "tenant_id": tenant, "role": rol, "exp": 0}


# ================================================================================================ Bölüm 1 — DB'siz
def test_uc_envanteri_sayilari_ve_kimliksiz_liste_sabit():
    """E-Z4: her uç bir kimlik kapısının arkasında; kimliksiz uç kümesi tam olarak belgelenen 9 uç. Yeni kimliksiz uç eklenirse kırmızı."""
    sayac: dict[str, int] = {}
    kimliksiz = set()
    satirlar = []
    for r in tum_uclar():
        if str(getattr(r, "path", "")).startswith("/v1/_test/"):   # tam takımda başka test modülü (test_abonelik_kapilari_v2609) sınama rotası ekler; envantere girmez
            continue
        k = kapi_turu(r)
        for m, p in _yontem_yol(r):
            sayac[k] = sayac.get(k, 0) + 1
            satirlar.append({"yontem": m, "yol": p, "kapi": k})
            if k == "kimliksiz":
                kimliksiz.add((m, p))
    _yaz_csv("uc_kapilari.csv", satirlar)
    assert kimliksiz == KIMLIKSIZ_BEKLENEN
    assert sum(sayac.values()) == 253   # 247 + /v1/readyz (P8) + GET /eak (v2.640) + POST alarm-kurallari/deneme (v2.641) + PUT /santral-sinifi (C1) + POST /yonetim/iki-adim/kurtarma-yenile + /yeniden-kur (A3, platform kapısı)
    assert sayac.get("api_anahtari") == 16 and sayac.get("toplayici") == 1 and sayac.get("platform") == 37   # A3 (21.11): +2 platform ucu (kurtarma-yenile, yeniden-kur)


def _gecersiz_govde_istegi(c: TestClient, m: str, yol: str):
    return c.request(m, yol, json={}, headers={"Authorization": "Bearer x"})


def test_viewer_her_yazma_ucunda_403():
    """E-Z2: viewer rolü, `yazma_yetkisi`/`yonetici_yetkisi` kapılı HER yazma ucunda (POST/PUT/PATCH/DELETE) 403 alır (gövde doğrulamasından
    önce). Kapısız müşteri yazma uçları yalnız belgelenen listeyle (kendi hesabı + Ş13) sınırlı."""
    c = TestClient(api_main.app, raise_server_exceptions=False)
    _rol("viewer")
    sonuc, kapisiz_yazma = [], set()
    for r in tum_uclar():
        k = kapi_turu(r)
        for m, p in _yontem_yol(r):
            if m not in ("POST", "PUT", "PATCH", "DELETE") or k not in ("viewer", "editor", "admin"):
                continue
            if k == "viewer":
                kapisiz_yazma.add(p)
                continue
            kod = _gecersiz_govde_istegi(c, m, _sahte_yol(p, {})).status_code
            sonuc.append({"rol": "viewer", "yontem": m, "yol": p, "kapi": k, "http": kod})
    _yaz_csv("viewer_yazma.csv", sonuc)
    hatali = [s for s in sonuc if s["http"] != 403]
    assert not hatali, hatali
    assert kapisiz_yazma <= VIEWER_YAZMA_BELGELI, sorted(kapisiz_yazma - VIEWER_YAZMA_BELGELI)


def test_editor_admin_uclarinda_403():
    """E-Z2: editor, `yonetici_yetkisi` kapılı her uçta (okuma dâhil) 403 alır."""
    c = TestClient(api_main.app, raise_server_exceptions=False)
    _rol("editor")
    sonuc = []
    for r in tum_uclar():
        if kapi_turu(r) != "admin":
            continue
        for m, p in _yontem_yol(r):
            kod = _gecersiz_govde_istegi(c, m, _sahte_yol(p, {})).status_code
            sonuc.append({"rol": "editor", "yontem": m, "yol": p, "http": kod})
    _yaz_csv("editor_admin.csv", sonuc)
    assert sonuc and all(s["http"] == 403 for s in sonuc), [s for s in sonuc if s["http"] != 403]


def _jeton(monkeypatch, **iddia) -> str:
    import datetime as dt

    import jwt as _jwt

    from pvquant.services import auth_service as au
    monkeypatch.setenv("PVQ_JWT_SECRET", "faz9-test-sirri-0123456789abcdef")
    g = {"sub": "u1", "tenant_id": "t1", "role": "admin", "exp": dt.datetime.now(dt.UTC) + dt.timedelta(hours=1)}
    g.update(iddia)
    return "Bearer " + _jwt.encode(g, au._sir(), algorithm="HS256")


def test_platform_ve_musteri_jeton_kapsamlari_karismaz(monkeypatch):
    """E-Z2: platform jetonu müşteri ucunda 403; müşteri jetonu platform ucunda 403 (gerçek bağımlılıklar, DB çağrısı yok)."""
    c = TestClient(api_main.app, raise_server_exceptions=False)
    plat = _jeton(monkeypatch, kapsam="platform", sub="p1")
    assert c.get("/v1/plants", headers={"Authorization": plat}).status_code == 403
    mus = _jeton(monkeypatch)
    assert c.get("/v1/yonetim/kiracilar", headers={"Authorization": mus}).status_code == 403
    assert c.get("/v1/plants", headers={"Authorization": "Bearer bozuk"}).status_code == 401
    assert c.get("/v1/plants").status_code in (401, 422)


def test_temsil_jetonu_yazamaz_ama_yan_etkili_kgup_get_acik(monkeypatch):
    """E-Z2 + Ş1 (K3 → K1): temsil (kimliğe bürünme) jetonu POST'ta 403 ve /report, /scada/disa GET'lerinde 403. Ancak
    `GET /v1/plants/{id}/kgup?fmt=csv` (arşive yeni sürüm YAZAN GET) kapıdan geçer — bulgu F9-E05; bu test mevcut davranışı belgeler."""
    from pvquant.services import platform_service
    monkeypatch.setattr(platform_service, "oturum_durumu", lambda s: {"aktif": True, "sv": 0, "rol": "sahip", "email": "x"})
    monkeypatch.setattr(platform_service, "kiraci_durumu", lambda t: "active")
    j = _jeton(monkeypatch, temsil="p1", sub="p1", role="viewer")

    class _R:
        def __init__(self, method, path):
            self.method = method
            self.url = type("U", (), {"path": path})()
    with pytest.raises(Exception) as e:
        gecerli_kullanici(_R("POST", "/v1/plants/x/olaylar"), j)
    assert e.value.status_code == 403
    for p in ("/v1/plants/x/report", "/v1/plants/x/scada/disa"):
        with pytest.raises(Exception) as e:
            gecerli_kullanici(_R("GET", p), j)
        assert e.value.status_code == 403
    assert gecerli_kullanici(_R("GET", "/v1/plants/x/kgup"), j)["role"] == "viewer"   # F9-E05: yan etkili GET temsile açık


def test_iec104_nokta_tablosu_basarili_yolda_200(monkeypatch):
    """Ş18 / F9-E09 (P17) — DÜZELTİLDİ: uç gövdesi `datetime.now(timezone.utc)` kullanıyordu ama ad içe aktarılmamıştı → başarılı yolda
    NameError/500. Artık fonksiyon içi içe aktarma; geçerli tablo ve iec104 veri yolu ile 200 ve tablo özeti döner."""
    from pvquant.services import iec104_nokta_service, plant_service
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "params_json": {"veri_yolu": {"tur": "iec104"}}})
    monkeypatch.setattr(plant_service, "params_birlestir", lambda *a, **k: None)
    monkeypatch.setattr(iec104_nokta_service, "csv_den", lambda metin: [{"ioa": 1, "alan": "guc_kw", "carpan": 1.0}])
    monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: None)
    _rol("editor")
    c = TestClient(api_main.app, raise_server_exceptions=False)
    r = c.post("/v1/plants/p1/veri-yolu/iec104-nokta-tablosu", files={"dosya": ("t.csv", io.BytesIO(b"ioa,alan,carpan\n1,guc_kw,1\n"), "text/csv")})
    assert r.status_code == 200, r.text
    assert r.json()["n"] == 1 and r.json()["alanlar"] == ["guc_kw"]


# ================================================================================================ Bölüm 2 — DB
def _db_var() -> bool:
    try:
        from sqlalchemy import text

        from pvquant.db import sistem_baglami
        with sistem_baglami() as s:
            s.execute(text("SELECT 1"))
        return True
    except Exception: 
        return False


db = pytest.mark.skipif(not _db_var(), reason="test DB yok (PVQ_DB_URL)")


@pytest.fixture(scope="module")
def iki_kiraci():
    """Sentetik iki kiracı: A (iki santral), B (bir santral + portföy + kullanıcı). Benzersiz işaretler yanıtlarda aranır."""
    from sqlalchemy import text

    from pvquant.db import sistem_baglami, tenant_baglami
    iz = uuid.uuid4().hex[:10]
    a, b = str(uuid.uuid4()), str(uuid.uuid4())
    a1, a2, b1 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    bport, bkul = str(uuid.uuid4()), str(uuid.uuid4())
    isaret = f"FAZ9GIZLI{iz}"
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name) VALUES(:a, :an), (:b, :bn)"), {"a": a, "an": f"faz9-A-{iz}", "b": b, "bn": f"{isaret}-kiraci"})
        s.execute(text("INSERT INTO users(id, tenant_id, email, pw_hash, role) VALUES(:u, :t, :e, 'x', 'admin')"),
                  {"u": bkul, "t": b, "e": f"{isaret.lower()}@ornek.invalid"})
    with tenant_baglami(a) as s:
        for pid, ad in ((a1, "faz9-A1"), (a2, "faz9-A2")):
            s.execute(text("INSERT INTO plants(id, tenant_id, name, lat, lon, tz, capacity_kwp) VALUES(:p, :t, :n, 37.9, 32.5, 'Europe/Istanbul', 1000)"),
                      {"p": pid, "t": a, "n": ad})
    with tenant_baglami(b) as s:
        s.execute(text("INSERT INTO plants(id, tenant_id, name, lat, lon, tz, capacity_kwp) VALUES(:p, :t, :n, 38.1, 33.1, 'Europe/Istanbul', 2345)"),
                  {"p": b1, "t": b, "n": f"{isaret}-santral"})
        s.execute(text("INSERT INTO portfoy(id, tenant_id, ad, tur, gecerli_bas) VALUES(:i, :t, :n, 'ozel', '2026-01-01')"),
                  {"i": bport, "t": b, "n": f"{isaret}-portfoy"})
    yield {"a": a, "b": b, "a1": a1, "a2": a2, "b1": b1, "bport": bport, "bkul": bkul, "isaret": isaret}
    # temizlik en iyi çaba: değişmez tablolarda (denetim_izi vb.) satır kalabilir — test DB, benzersiz işaretli
    from pvquant.db import bakim_baglami
    for ctx in (bakim_baglami, sistem_baglami):
        try:
            with ctx() as s:
                s.execute(text("DELETE FROM api_keys WHERE tenant_id IN (:a, :b)"), {"a": a, "b": b})
                s.execute(text("DELETE FROM portfoy WHERE tenant_id IN (:a, :b)"), {"a": a, "b": b})
                s.execute(text("DELETE FROM plants WHERE tenant_id IN (:a, :b)"), {"a": a, "b": b})
                s.execute(text("DELETE FROM users WHERE tenant_id IN (:a, :b)"), {"a": a, "b": b})
                s.execute(text("DELETE FROM tenants WHERE id IN (:a, :b)"), {"a": a, "b": b})
            break
        except Exception: 
            continue


def _b_santral_anlik(k) -> tuple:
    from sqlalchemy import text

    from pvquant.db import tenant_baglami
    with tenant_baglami(k["b"]) as s:
        r = s.execute(text("SELECT name, capacity_kwp, lat, lon, COALESCE(params_json::text,'') FROM plants WHERE id=:p"), {"p": k["b1"]}).first()
    return tuple(r) if r else None


@db
def test_kiracilar_arasi_tum_musteri_uclari(iki_kiraci):
    """E-Z1 (çekirdek ölçüt): kiracı A yöneticisi (admin — en geniş müşteri rolü), B'nin santral/portföy kimlikleriyle HER müşteri ucunu çağırır.
    Geçme koşulu: (i) hiçbir yanıt gövdesinde B'nin işareti ya da kiracı kimliği yok; (ii) B'nin santral satırı değişmez; (iii) yol parametresi
    B nesnesi olan uçlarda 2xx yanıt, işaret içermiyorsa bile ayrıca listelenir (servis RLS'ine dayanan «boş 200», Ş16)."""
    k = iki_kiraci
    once = _b_santral_anlik(k)
    _rol("admin", tenant=k["a"], sub=str(uuid.uuid4()))
    c = TestClient(api_main.app, raise_server_exceptions=False)
    yol_deg = {"plant_id": k["b1"], "portfoy_id": k["bport"], "pid": k["b1"], "uid": k["bkul"], "tid": k["b"]}
    satirlar, sizinti, bos200 = [], [], []
    for r in tum_uclar():
        if kapi_turu(r) not in ("viewer", "editor", "admin"):
            continue
        for m, p in _yontem_yol(r):
            if "{" not in p and m != "GET":
                continue          # B nesnesine dokunmayan yazmalar matrisin konusu değil (A'nın kendi verisi)
            yol = _sahte_yol(p, yol_deg)
            try:
                y = c.request(m, yol, json={})
                kod, govde = y.status_code, y.text
            except Exception as e: 
                kod, govde = -1, repr(e)
            b_nesne = any(x in p for x in ("{plant_id}", "{portfoy_id}", "{pid}", "{uid}", "{tid}"))
            sizdi = k["isaret"] in govde or k["isaret"].lower() in govde or k["b"] in govde
            satirlar.append({"rol": "admin(A)", "kaynak_kiraci": "B" if b_nesne else "A(liste)", "yontem": m, "yol": p, "http": kod,
                             "sizinti": int(sizdi), "boyut": len(govde)})
            if sizdi:
                sizinti.append((m, p, kod))
            if b_nesne and 200 <= kod < 300:
                bos200.append((m, p, kod))
    _yaz_csv("kiracilar_arasi.csv", satirlar)
    assert not sizinti, f"KRİTİK sızıntı: {sizinti}"
    assert _b_santral_anlik(k) == once, "B santrali A bağlamından değişti"
    # bilgi: B nesnesiyle 2xx dönen uçlar (içerik B'yi göstermiyor; ayrı satırda raporlanır)
    print(f"\nB nesnesiyle 2xx dönen uç sayısı: {len(bos200)} / {sum(1 for s in satirlar if s['kaynak_kiraci'] == 'B')}")
    for x in bos200:
        print("  2xx:", x)


@db
def test_dis_api_anahtar_kapsam_matrisi(iki_kiraci):
    """E-Z3: A kiracısının tek kapsamlı anahtarları 16 dış uçta: doğru kapsam dışında 403; santral kapsamı (plant_ids=[A1]) ile A2'ye erişim
    reddedilir; A anahtarıyla B santrali hiçbir kapsamda B verisi döndürmez; geçersiz/iptal anahtar 401."""
    from pvquant.services import api_anahtar_service as aas
    k = iki_kiraci
    # kapsam: uç → beklenen kapsam (uclar.csv'den; bağımlılık kapanışından okunur)
    def _kapsam(r: APIRoute) -> str | None:
        for d in r.dependant.dependencies:
            cl = getattr(d.call, "__closure__", None) or ()
            for h in cl:
                v = h.cell_contents
                if isinstance(v, str) and ":" in v:
                    return v
        return None
    uclar = [(m, r.path, _kapsam(r)) for r in tum_uclar() if kapi_turu(r) == "api_anahtari" for m in r.methods]
    assert len(uclar) == 16 and all(u[2] for u in uclar), uclar
    kapsamlar = sorted({u[2] for u in uclar})
    anahtarlar = {kp: aas.uret(k["a"], f"faz9-{kp}", [kp])["anahtar"] for kp in kapsamlar}
    sinirli = aas.uret(k["a"], "faz9-sinirli", kapsamlar, plant_ids=[k["a1"]])["anahtar"]
    iptal = aas.uret(k["a"], "faz9-iptal", kapsamlar)
    aas.iptal(k["a"], iptal["id"])
    c = TestClient(api_main.app, raise_server_exceptions=False)

    def _istek(m, p, degerler, anahtar):
        """Girdi doğrulaması kapsam denetiminden önce koştuğu için (422) zorunlu girdiler geçerli verilir: tahmin-arsivi `hedef`, uretim-dosyasi dosya."""
        ek: dict = {"json": {}}
        if p.endswith("/tahmin-arsivi"):
            ek = {"params": {"hedef": "2026-11-01T10:00:00Z"}}
        elif p.endswith("/uretim-dosyasi"):
            ek = {"files": {"dosya": ("u.csv", io.BytesIO(b"ts,kw\n2026-11-01T10:00:00Z,1\n"), "text/csv")}}
        return c.request(m, _sahte_yol(p, degerler), headers={"X-API-Key": anahtar}, **ek)
    satir, hatali = [], []
    for m, p, kp in uclar:
        for kps, anh in anahtarlar.items():
            y = _istek(m, p, {"plant_id": k["a1"], "portfoy_id": str(uuid.uuid4())}, anh)
            beklenen_red = kps != kp
            satir.append({"uc": f"{m} {p}", "gereken": kp, "anahtar_kapsami": kps, "hedef": "A1", "http": y.status_code})
            if beklenen_red and y.status_code != 403:
                hatali.append(("kapsam", m, p, kps, y.status_code))
        if "{plant_id}" in p:
            y = _istek(m, p, {"plant_id": k["a2"]}, sinirli)
            satir.append({"uc": f"{m} {p}", "gereken": kp, "anahtar_kapsami": "tum+plant_ids=[A1]", "hedef": "A2", "http": y.status_code})
            if y.status_code not in (403, 404):
                hatali.append(("santral_kapsami", m, p, y.status_code))
            y = _istek(m, p, {"plant_id": k["b1"]}, anahtarlar[kp])
            satir.append({"uc": f"{m} {p}", "gereken": kp, "anahtar_kapsami": kp, "hedef": "B1", "http": y.status_code})
            if k["isaret"] in y.text or k["b"] in y.text or 200 <= y.status_code < 300:
                hatali.append(("kiraci", m, p, y.status_code))
        y = c.request(m, _sahte_yol(p, {"plant_id": k["a1"]}), headers={"X-API-Key": iptal["anahtar"]}, json={})
        satir.append({"uc": f"{m} {p}", "gereken": kp, "anahtar_kapsami": "iptal", "hedef": "A1", "http": y.status_code})
        if y.status_code != 401:
            hatali.append(("iptal", m, p, y.status_code))
        y = c.request(m, _sahte_yol(p, {"plant_id": k["a1"]}), headers={"X-API-Key": "pvq_deadbeef_yanlis"}, json={})
        if y.status_code != 401:
            hatali.append(("gecersiz", m, p, y.status_code))
    _yaz_csv("dis_api_matrisi.csv", satir)
    assert not hatali, hatali


@db
def test_db_pvq_app_baglamindan_rlssiz_tablolar(iki_kiraci):
    """E-B1 (K3 şüphelerinin K1 sınaması, Ş-A1..A5): kiracı A bağlamında (SET ROLE pvq_app + app.tenant_id=A) RLS'siz tablolar B'nin
    satırlarını gösterir mi / değiştirilebilir mi? İşlem GERİ ALINIR (yan etkisiz). Sonuçlar raporlanır; doğrudan API sızıntısı DEĞİL
    (uygulama WHERE süzgeci var) — savunma derinliği eksiği. Beklenen (bulgu F9-E01): users ve tenants B'yi gösterir."""
    from sqlalchemy import text

    from pvquant.db import SessionLocal
    k = iki_kiraci
    s = SessionLocal()
    try:
        s.execute(text("SET LOCAL ROLE pvq_app"))
        s.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": k["a"]})
        sonuc = {
            "plants_B_gorunur": s.execute(text("SELECT count(*) FROM plants WHERE tenant_id=:b"), {"b": k["b"]}).scalar(),
            "portfoy_B_gorunur": s.execute(text("SELECT count(*) FROM portfoy WHERE tenant_id=:b"), {"b": k["b"]}).scalar(),
            "users_B_gorunur": s.execute(text("SELECT count(*) FROM users WHERE tenant_id=:b"), {"b": k["b"]}).scalar(),
            "tenants_B_gorunur": s.execute(text("SELECT count(*) FROM tenants WHERE id=:b"), {"b": k["b"]}).scalar(),
        }
        try:
            s.execute(text("SAVEPOINT sp1"))
            n = s.execute(text("UPDATE users SET role=role WHERE tenant_id=:b"), {"b": k["b"]}).rowcount
            sonuc["users_B_guncellenebilir"] = n
        except Exception as e: 
            s.execute(text("ROLLBACK TO SAVEPOINT sp1"))
            sonuc["users_B_guncellenebilir"] = f"red: {type(e).__name__}"
        try:
            s.execute(text("SAVEPOINT sp2"))
            s.execute(text("SELECT count(*) FROM kullanim_sayac")).scalar()
            sonuc["kullanim_sayac_tum_kiracilar_okunur"] = 1
        except Exception as e: 
            s.execute(text("ROLLBACK TO SAVEPOINT sp2"))
            sonuc["kullanim_sayac_tum_kiracilar_okunur"] = f"red: {type(e).__name__}"
    finally:
        s.rollback()
        s.close()
    _yaz_csv("db_pvq_app_rlssiz.csv", [{"kontrol": a, "sonuc": v} for a, v in sonuc.items()])
    print("\n", sonuc)
    assert sonuc["plants_B_gorunur"] == 0 and sonuc["portfoy_B_gorunur"] == 0        # RLS'li tablolar: yalıtım çalışıyor
    assert sonuc["users_B_gorunur"] == 1 and sonuc["tenants_B_gorunur"] == 1          # F9-E01: RLS'siz (belgeler; K3 → K1)


DEGISMEZ_NIYETLI = ["kgup_surum", "uzlastirma_bildirimi", "uzlastirma_saatlik", "canli_ornek", "sayac_yukleme", "kaynak_saatlik", "edge_alim",
                    "dogrulama_sonuc", "finansal_etki_sonuc", "portfoy_sonuc", "report_log", "paylasim_denetim", "forecast_runs", "forecast_values",
                    "denetim_izi", "abonelik_gecmisi", "kural_sicili_anlik", "piyasa_fiyat_surum", "meteo_kosu_kunye", "konformal_ayar_gecmis"]


@db
def test_pvq_api_degismez_tablolarda_tekil_yetkiler():
    """E-B2: «yalnız ekleme» niyetli tablolarda pvq_api'nin UPDATE ve DELETE yetkisi AYRI AYRI sorulur (test_db_rolu.py'nin virgüllü
    has_table_privilege kullanımı «herhangi biri» anlamına gelir — Ş-D11). Tetikleyiciyle korunanlar ayrıca işaretlenir. Mevcut durumu
    CSV'ye yazar; yalnız denetim_izi ve forecast_* için sertleştirme iddiasını doğrular."""
    from sqlalchemy import text

    from pvquant.db import sistem_baglami
    satir = []
    with sistem_baglami() as s:
        for t in DEGISMEZ_NIYETLI:
            var = s.execute(text("SELECT to_regclass(:t) IS NOT NULL"), {"t": t}).scalar()
            if not var:
                satir.append({"tablo": t, "var": 0, "update": None, "delete": None, "tetikleyici": None})
                continue
            u = s.execute(text("SELECT has_table_privilege('pvq_api', :t, 'UPDATE')"), {"t": t}).scalar()
            d = s.execute(text("SELECT has_table_privilege('pvq_api', :t, 'DELETE')"), {"t": t}).scalar()
            tg = s.execute(text("SELECT count(*) FROM pg_trigger WHERE tgrelid = to_regclass(:t) AND NOT tgisinternal"), {"t": t}).scalar()
            satir.append({"tablo": t, "var": 1, "update": int(u), "delete": int(d), "tetikleyici": int(tg)})
    _yaz_csv("pvq_api_degismez_yetkiler.csv", satir)
    print("\n", satir)
    sozluk = {r["tablo"]: r for r in satir}
    assert sozluk["denetim_izi"]["update"] == 0 and sozluk["denetim_izi"]["delete"] == 0
    for t in ("forecast_runs", "forecast_values"):
        assert sozluk[t]["tetikleyici"] >= 1 or (sozluk[t]["update"] == 0 and sozluk[t]["delete"] == 0)
