"""İnvertör bazlı dosyalar, kaynak adımı ve UTF-16 — SCADA envanterinde ölçülen kalan kusurlar.

Bulgu 1: zaman damgası başına N satır (SOURCE_KEY = invertör) içeren dosya
`resample("1h").mean()` ile ORTALANIYOR, santral 23x küçük çıkıyor, hiç uyarı yok,
DUPLICATE_TIME bayrağı hiç tetiklenmiyor (validate resample'dan sonra çalışıyor),
kümülatif tespiti iç içe geçmiş seride yanılıyor.
Bulgu 2: `timestep_minutes` kaynak adımını değil çıktı adımını (60) söylüyor.
SMA künyesi: Sunny Explorer dışa aktarımı UTF-16LE; `detect_encoding` cp1254 sanıyor.
Kaynak: ~/Desktop/scada-markalari/_arac/bulgular/ANA_OTURUM_BULGULARI.md
"""
import numpy as np
import pandas as pd
import pytest

from pvquant.io.ingestion.contracts import ColumnMapping, TransformSpec
from pvquant.io.ingestion.detection import detect_encoding, detect_file_format
from pvquant.io.ingestion.pipeline import ingest_file
from pvquant.io.ingestion.transform import transform_to_canonical

CIHAZ = 3            # invertör sayısı
CIHAZ_KW = 100.0     # her biri 100 kW → santral 300 kW
LAT, LON = 20.6, 76.5


def _invertor_bazli_df(gun: int = 2) -> pd.DataFrame:
    """Kaggle Plant_1 deseni: her 15 dk'da CİHAZ satır, her cihazın kendi ömür sayacı."""
    t = pd.date_range("2020-05-15", periods=gun * 96, freq="15min")
    saat = t.hour + t.minute / 60
    profil = np.clip(np.sin((saat - 6) / 12 * np.pi), 0, None)   # 06–18 arası çan
    satirlar = []
    for d in range(CIHAZ):
        guc = CIHAZ_KW * profil
        sayac = 1000.0 * (d + 1) + np.cumsum(guc * 0.25)            # kWh, cihaz başına ömür sayacı
        satirlar.append(pd.DataFrame({
            "DATE_TIME": t.strftime("%Y-%m-%d %H:%M:%S"),
            "SOURCE_KEY": f"INV{d}",
            "AC_POWER": np.round(guc, 3),
            "TOTAL_YIELD": np.round(sayac, 3),
        }))
    # gerçek dosyalardaki gibi zaman damgası bazında iç içe (INV0,INV1,INV2,INV0,...)
    return pd.concat(satirlar).sort_values(["DATE_TIME", "SOURCE_KEY"], kind="stable").reset_index(drop=True)


ESLEME = ColumnMapping(timestamp="DATE_TIME", power="AC_POWER", energy="TOTAL_YIELD")


# ───────────────────── Bulgu 1 — sessiz ortalama ─────────────────────

def test_cift_zaman_damgasi_varsayilanda_sessizce_gecmez():
    """Politika verilmezse hat karar VERMEZ: açık, Türkçe, satır sayısını söyleyen hata."""
    with pytest.raises(ValueError, match="(?i)zaman damgası başına"):
        transform_to_canonical(_invertor_bazli_df(), ESLEME, capacity_kwp=CIHAZ * CIHAZ_KW,
                               source_timezone="UTC")


def test_sum_politikasi_santral_toplamini_verir_ortalamayi_degil():
    """3 invertör × 100 kW → tepe 300 kW olmalı; eski davranış 100 kW (ortalama) veriyordu."""
    df, spec, _ = transform_to_canonical(_invertor_bazli_df(), ESLEME, capacity_kwp=CIHAZ * CIHAZ_KW,
                                         source_timezone="UTC", duplicate_policy="sum")
    assert df["power_kw"].max() == pytest.approx(CIHAZ * CIHAZ_KW, rel=0.02)


def test_sum_politikasi_kumulatif_sayaci_gruplamadan_sonra_tanir():
    """Cihaz sayaçları iç içe geçince seri monoton değil → eskiden energy_cumulative=False çıkıyordu."""
    _, spec, _ = transform_to_canonical(_invertor_bazli_df(), ESLEME, capacity_kwp=CIHAZ * CIHAZ_KW,
                                        source_timezone="UTC", duplicate_policy="sum")
    assert spec.energy_cumulative is True


def test_sum_politikasi_izi_spec_e_yazar():
    _, spec, _ = transform_to_canonical(_invertor_bazli_df(), ESLEME, capacity_kwp=CIHAZ * CIHAZ_KW,
                                        source_timezone="UTC", duplicate_policy="sum")
    assert spec.duplicate_policy == "sum"
    assert spec.rows_per_timestamp == pytest.approx(CIHAZ)


def test_mean_politikasi_ancak_acikca_istenirse():
    """Ortalama yasak değil — ama yalnız açıkça istenince ve izi kalarak."""
    df, spec, _ = transform_to_canonical(_invertor_bazli_df(), ESLEME, capacity_kwp=CIHAZ * CIHAZ_KW,
                                         source_timezone="UTC", duplicate_policy="mean")
    assert df["power_kw"].max() == pytest.approx(CIHAZ_KW, rel=0.02)
    assert spec.duplicate_policy == "mean"


def test_tek_satirli_dosya_politikadan_etkilenmez():
    """Gerileme koruması: zaman damgası başına tek satır → eski davranış aynen."""
    tek = _invertor_bazli_df()
    tek = tek[tek.SOURCE_KEY == "INV0"].reset_index(drop=True)
    df, spec, _ = transform_to_canonical(tek, ESLEME, capacity_kwp=CIHAZ_KW, source_timezone="UTC")
    assert df["power_kw"].max() == pytest.approx(CIHAZ_KW, rel=0.02)
    assert spec.rows_per_timestamp == pytest.approx(1.0)


def test_ingest_file_ucbucak_invertor_bazli_dosya(tmp_path):
    """Uçtan uca: varsayılan politika durdurur; 'sum' ile geçer, rapor uyarır, tepe doğru."""
    yol = tmp_path / "plant.csv"
    _invertor_bazli_df().to_csv(yol, index=False)
    with pytest.raises(ValueError, match="(?i)zaman damgası başına"):
        ingest_file(yol, capacity_kwp=CIHAZ * CIHAZ_KW, latitude=LAT, longitude=LON,
                    source_timezone="UTC")
    res = ingest_file(yol, capacity_kwp=CIHAZ * CIHAZ_KW, latitude=LAT, longitude=LON,
                      source_timezone="UTC", duplicate_policy="sum")
    assert res.data["power_kw"].max() == pytest.approx(CIHAZ * CIHAZ_KW, rel=0.02)
    assert any("satır" in u.lower() and "zaman damgası" in u.lower() for u in res.report.warnings)


# ───────────────────── Bulgu 2 — kaynak adımı kaybolmasın ─────────────────────

def test_kaynak_adimi_60a_ezilmez():
    """15 dk'lık kaynak saatliğe indirgense de kaynak adımı spec'te kalmalı."""
    tek = _invertor_bazli_df()
    tek = tek[tek.SOURCE_KEY == "INV0"].reset_index(drop=True)
    _, spec, _ = transform_to_canonical(tek, ESLEME, capacity_kwp=CIHAZ_KW, source_timezone="UTC")
    assert spec.timestep_minutes == 60              # çıktı adımı (mevcut sözleşme korunur)
    assert spec.source_timestep_minutes == 15       # KAYNAK adımı (yeni)


def test_eski_sablon_yeni_alanlar_olmadan_acilir():
    """TemplateStore eski JSON'u `TransformSpec(**d)` ile açar; yeni alanlar varsayılana düşmeli."""
    eski = {"source_timezone": "UTC", "power_unit": "kW", "irradiance_unit": None,
            "irradiance_unit_source": None, "timestep_minutes": 60,
            "energy_to_power": False, "energy_cumulative": False}
    spec = TransformSpec(**eski)
    assert spec.duplicate_policy == "error"
    assert spec.rows_per_timestamp == 1.0
    assert spec.source_timestep_minutes is None


# ───────────────────── SMA Sunny Explorer — UTF-16 ─────────────────────

def test_utf16_bom_taninir(tmp_path):
    """Sunny Explorer dosyası UTF-16LE + BOM; cp1254 'başarıyla' çözüp tek kolonlu çöp üretiyordu."""
    yol = tmp_path / "sma.csv"
    icerik = "sep=;\nVersion CSV1|Tool SE\n\n;SN: 1;SN: 1\n;Total yield;Power\n;Counter;Analog\n" \
             "dd/MM/yyyy hh:mm tt;kWh;kW\n10/05/2016 12:00 AM;7585.897;0.000\n10/05/2016 12:05 AM;7585.900;0.012\n"
    yol.write_bytes(icerik.encode("utf-16"))       # BOM ff fe ile
    assert detect_encoding(yol) == "utf-16"
    fmt = detect_file_format(yol)
    assert fmt.encoding == "utf-16"
    assert fmt.delimiter == ";"


def test_cihaz_bazli_fren_422_yapili_detayla(monkeypatch, tmp_path):
    """v2.363 — fren mesajı 500'ün içinde kaybolmaz: /scada ucu tipli hatayı
    yakalar, panelin Topla/Ortala seçimini besleyen yapılı 422 döner; geçersiz
    duplicate_policy de açıkça reddedilir (25 Eyl canlı, Kaggle 22 invertör)."""
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    from pvquant.io.ingestion.transform import DuplicateTimestampsError

    api_main.app.dependency_overrides[gecerli_kullanici] = (
        lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0})
    monkeypatch.setattr(api_main.plant_service, "getir",
                        lambda t, p: {"tz": "Europe/Istanbul", "capacity_kwp": 1000.0,
                                      "lat": 37.0, "lon": 35.0})
    import pvquant.io.ingestion.pipeline as pl
    def patlat(*a, **k):
        raise DuplicateTimestampsError(rows=68778, timestamps=3158, ratio=21.8)
    monkeypatch.setattr(pl, "ingest_file", patlat)
    try:
        c = TestClient(api_main.app)
        dosya = {"dosya": ("t.csv", b"a,b\n1,2\n", "text/csv")}
        y = c.post("/v1/plants/p1/scada", files=dosya)
        assert y.status_code == 422
        d = y.json()["detail"]
        assert d["tur"] == "cihaz_bazli" and d["damga"] == 3158 and "birleştirilmez" in d["mesaj"]
        y = c.post("/v1/plants/p1/scada", files=dosya, data={"duplicate_policy": "ortala"})
        assert y.status_code == 422 and "sum" in y.json()["detail"]
    finally:
        api_main.app.dependency_overrides.clear()
