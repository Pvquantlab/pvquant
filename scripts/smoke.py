"""PVQuant SMOKE GATE — tek komut, uçtan uca (Zeyilname v2.23).
Kullanım: PYTHONPATH=src python scripts/smoke.py
Çıkış: 0 = tüm adımlar yeşil, 1 = ilk kırmızıda detaylı rapor.
Felsefe: pytest PARÇALARI korur, smoke ZİNCİRİ korur. Her deploy
sonrası elle zorunlu; GÜN 0-5'te her sabah. İzole smoke tenant'ında
koşar (idempotent, varsa-kullan-yoksa-yarat); gerçek tenant'lara
DOKUNMAZ. Ağ gerektirir (Open-Meteo) — üretimde de gerekir.
"""
from __future__ import annotations

import inspect
import re
import secrets
import sys
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

SMOKE_EPOSTA = "smoke@pvquant.internal"
SMOKE_FIRMA = "Smoke Test A.Ş."
SMOKE_SANTRAL = "Smoke GES"
ORNEK_CSV = REPO / "tests" / "data" / "refplant_sample.csv"

# K4 taraması: kullanıcıya görünen metin pattern'leri.
# İLKE (v2.23): kod tanımlayıcıları bilinçli ASCII'dir — istisna
# satır-bazlı; dosya yeniden adlandırma YASAK (KURAL 5).
K4_PATTERNS = re.compile(
    r"Bugun|Yukleme'|gorunum[\"']|Once |kosu[ \"'.]|arsiv|"
    r"secilmedi|uretilmedi|bandi[ \"']|dusuk|saglik[ \"']|Islenen|"
    r"gunluk[ \"']|yukleyin|endiselenmeyin|Hizli |gecin|tanimasiyla|"
    r"Kalicilastir|dogrula\"|Farkli dosya|satir kaydedildi|hatasi:|"
    r"olusturulamadi|secmelisiniz|Yol ayrimina|donusturuluyor|Islem sirasinda|Kalibrasyona gec")
K4_ISTISNA = ("import", "login_gorunum", "def ", "class ", "#")

DURUM: list[tuple[str, str]] = []


def adim(ad):
    def sar(fn):
        def ic():
            try:
                detay = fn() or ""
                DURUM.append((ad, f"OK {detay}"))
                print(f"  [OK] {ad}  {detay}")
            except Exception as e:
                DURUM.append((ad, f"FAIL {e}"))
                print(f"  [FAIL] {ad}\n{traceback.format_exc()}")
                _ozet(); sys.exit(1)
        return ic
    return sar


def _ozet():
    print("\n===== SMOKE ÖZET =====")
    for ad, d in DURUM:
        print(f"  {ad}: {d.splitlines()[0][:80]}")


# ---------------- adımlar ----------------
@adim("1. DB bağlantısı")
def a1():
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        n = s.execute(text("SELECT count(*) FROM tenants")).scalar()
    return f"tenants={n}"


@adim("2. Smoke tenant/santral (idempotent)")
def a2():
    global TID, PID, PLANT
    from sqlalchemy import text
    from pvquant.db import sistem_baglami, tenant_baglami
    from pvquant.services import auth_service, plant_service
    with sistem_baglami() as s:
        row = s.execute(text(
            "SELECT tenant_id FROM users WHERE email=:e"),
            {"e": SMOKE_EPOSTA}).first()
    if row:
        TID = str(row.tenant_id)
    else:
        TID, _ = auth_service.tenant_ve_admin_olustur(
            SMOKE_FIRMA, SMOKE_EPOSTA, secrets.token_urlsafe(24))
    ps = [p for p in plant_service.listele(TID)
          if p["name"] == SMOKE_SANTRAL]
    if ps:
        PID = str(ps[0]["id"])
    else:
        PID = plant_service.olustur(TID, name=SMOKE_SANTRAL,
            lat=37.87, lon=32.49, tz="Europe/Istanbul",
            capacity_kwp=4514.0)
    PLANT = plant_service.getir(TID, PID)
    return f"tenant={TID[:8]} plant={PID[:8]}"


@adim("3. Ingest (repo fixture)")
def a3():
    from pvquant.services.ingest_service import yukle_ve_kaydet
    r = yukle_ve_kaydet(TID, PID, ORNEK_CSV, capacity_kwp=4514.0,
        latitude=37.87, longitude=32.49,
        source_timezone="Europe/Istanbul")
    assert r["n_satir"] > 0, "ingest 0 satır"
    return f"n={r['n_satir']}"


@adim("4. Kalibrasyon (Mod B — hız)")
def a4():
    from pvquant.services import calib_service
    r = calib_service.kalibre_et(TID, PLANT, hibrit=False)
    assert r.get("calibration_id"), "calibrations satırı yok"
    # v2.175: window_days artık quality_json'da ÖLÇÜMDEN — yoksa kök iş
    # geri açılmış demektir, smoke düşsün.
    cal = calib_service.aktif_kalibrasyon(TID, PID)
    q = cal.quality_json if (cal is not None and
                             isinstance(cal.quality_json, dict)) else {}
    wd = q.get("window_days")
    assert isinstance(wd, int) and wd >= 1, f"window_days yok/bozuk: {wd!r}"
    return f"mode={r['mode']} pencere={wd}g"


@adim("5. Tahmin + arşiv (ağ: Open-Meteo)")
def a5():
    from pvquant.services import forecast_service
    forecast_service.uret_ve_kaydet(TID, PLANT)
    df = forecast_service.son_kosu(TID, PID)
    assert df is not None and len(df) >= 24, f"son_kosu={0 if df is None else len(df)}"
    return f"saat={len(df)}"


@adim("6. Rapor (PDF bytes + ad bekçisi)")
def a6():
    from pvquant.services import report_service
    veri, ad, _ = report_service.uret(TID, PLANT, "pdf")
    ham = veri.getvalue() if hasattr(veri, "getvalue") else veri
    assert len(ham) > 5000, f"PDF küçük: {len(ham)}"
    # anonimlik bekçisi (Anonimleştirme R. kalıcı maddesi)
    metin = ham.decode("latin-1", errors="ignore").lower()
    assert "merkas" not in metin, "PDF'te eski santral adı!"
    return f"bytes={len(ham)} dosya={ad}"


@adim("7. Alarm taraması")
def a7():
    from pvquant.services.alarm_service import tara
    tara(PLANT)          # exception=fail; alerts yazabilir (spam kilitli)
    return "tarandı"


@adim("8. K4 diakritik bekçisi (web/src)")
def a9():
    # v2.160: bekci SPA'ya tasindi (Streamlit emekli) — kullanici metni ASCII'ye dusmez.
    allowlist_yolu = REPO / "scripts" / "k4_istisna.txt"
    allowlist = []
    if allowlist_yolu.exists():
        allowlist = [s.strip() for s in
                     allowlist_yolu.read_text(encoding="utf-8").splitlines()
                     if s.strip() and not s.startswith("#")]
    tsx_istisna = ("import ", "from ", "//", "/*", " * ", "console.")
    kirli = []
    for tsx in sorted((REPO / "web" / "src").rglob("*.tsx")):
        for i, satir in enumerate(tsx.read_text(encoding="utf-8")
                                  .splitlines(), 1):
            if any(x in satir for x in tsx_istisna):
                continue
            if any(pt in satir for pt in allowlist):
                continue
            if K4_PATTERNS.search(satir):
                kirli.append(f"{tsx.name}:{i}")
    assert not kirli, f"K4 kalıntı: {kirli[:6]}"
    return "temiz"


if __name__ == "__main__":
    print("PVQuant SMOKE GATE başlıyor…")
    for fn in (a1, a2, a3, a4, a5, a6, a7, a9):
        fn()
    _ozet()
    print("\nSMOKE: TÜMÜ YEŞİL ✓")
    sys.exit(0)
