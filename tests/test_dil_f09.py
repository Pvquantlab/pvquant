"""29.10.2026 — F-09 dil bekçisi (Python tarafı): kullanıcıya ya da API yanıtına giden metinde «ceza», «tasarruf», «kurtardı» yok.
Kapsam: src/pvquant/services, src/pvquant/ext/turkiye, src/pvquant/ext/platform/rapor_sablon.py, apps/api, docs/api.
İzinli istisnalar: 6446 md.16 atfı; iç sezgisel puan yorumu (io/ingestion/detection.py); yedek dosyalar."""
import re
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
TARANAN = [KOK / "src/pvquant/services", KOK / "src/pvquant/ext/turkiye", KOK / "src/pvquant/ext/platform/rapor_sablon.py",
           KOK / "src/pvquant/ext/tahmin/dogrulama.py", KOK / "src/pvquant/ext/tahmin/alt_saatlik.py", KOK / "apps/api", KOK / "docs/api"]
YASAK = re.compile(r"\bceza|tasarruf|kurtard[ıi]|kurtar[ıi]r\b|tasarruf", re.IGNORECASE)
IZIN = re.compile(r"6446|md\.?\s*16|madde 16|cezai şart", re.IGNORECASE)   # cezai şart: LÜY sözleşmesi atfı (mevzuat alıntısı)


def _dosyalar():
    for t in TARANAN:
        if t.is_file():
            yield t
        else:
            for p in t.rglob("*"):
                if p.suffix in (".py", ".md") and ".bak" not in p.name and "__pycache__" not in p.parts:
                    yield p


def test_kullaniciya_giden_metinde_ceza_tasarruf_yok():
    ihlal = []
    for p in _dosyalar():
        for i, satir in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if YASAK.search(satir) and not IZIN.search(satir):
                ihlal.append(f"{p.relative_to(KOK)}:{i}: {satir.strip()[:100]}")
    assert ihlal == [], "F-09 ihlali:\n" + "\n".join(ihlal)


def test_api_yaniti_not_metni_ceza_icermez():
    from pvquant.services import dengesizlik_service as dz
    import pandas as pd
    ix = pd.date_range("2026-08-01", periods=48, freq="h", tz="UTC")
    f = pd.DataFrame({"ptf": 2500.0, "smf": 3000.0, "yon": "acik", "kaynak": "epias"}, index=ix)
    r = dz.oneri_kantili(f)
    assert r["durum"] == "ok" and not YASAK.search(r["not"])
    assert "kural_surumu" in dz.hesapla_df(pd.DataFrame({"ts_utc": ix, "gercek_kw": 800.0, "kgup_kw": 1000.0, "naif_kw": float("nan")}), f, segment="lisansli_serbest")
