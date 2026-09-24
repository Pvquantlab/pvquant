"""Kolon eşleme — SCADA marka envanterinde (20 Eylül 2026) ölçülen üç sessiz kusur.

Her test, gerçek bir marka dosyasından alınmış kolon adlarıyla kurulur; kaynak
`~/Desktop/scada-markalari/_arac/bulgular/ANA_OTURUM_BULGULARI.md` (Bulgu 7, 8A–8C).
İçerik doğrulaması için sayısal/tarih değerleri gerçekçi tutulur.
"""
import pandas as pd
import pytest

from pvquant.io.ingestion.mapping import normalize_name, suggest_mapping

ZAMAN = pd.date_range("2019-06-01 10:00", periods=6, freq="1min").strftime("%Y-%m-%d %H:%M:%S")


def _df(**kolonlar):
    """Zaman kolonu + verilen sayısal kolonlarla küçük bir çerçeve."""
    veri = {"measured_on": ZAMAN}
    for ad, deger in kolonlar.items():
        veri[ad] = [deger] * 6
    return pd.DataFrame(veri)


# ───────────────────────────── Kusur 1 — power_factor ≠ power ─────────────────────────────

def test_measured_on_zaman_kolonu_olarak_taninir():
    """PVDAQ'ın tüm dosyaları `measured_on` kullanır; sözlükte yalnız `measured_at` vardı."""
    m, _ = suggest_mapping(_df(ac_power__584=2163.0))
    assert m.timestamp == "measured_on"


def test_power_factor_guc_sanilmaz():
    """PVDAQ sistem 33: power_factor__596 (0–1 oran) `power` seçiliyordu, gerçek güç eşlenmemiş kalıyordu."""
    m, _ = suggest_mapping(_df(ac_power__584=2163.0, power_factor__596=0.998))
    assert m.power == "ac_power__584"


@pytest.mark.parametrize("kolon", ["Reactive Power", "Apparent Power", "Radiation power (average, tilt, cell)"])
def test_guc_olmayan_power_kolonlari_guc_sanilmaz(kolon):
    """Reaktif/görünür güç ve ışınım gücü aktif güç değildir (Ingeteam, SunSpec, skytron)."""
    m, _ = suggest_mapping(_df(**{"Active Power": 1500.0, kolon: 300.0}))
    assert m.power == "Active Power"


def test_esit_skorda_ozgul_esanlamli_kazanir_alfabetik_degil():
    """İki kolon da 0.8 alınca seçim kolon adının alfabetik sırasına düşüyordu."""
    m, _ = suggest_mapping(_df(zzz_power=1500.0, ac_power=1500.0))
    assert m.power == "ac_power"


# ───────────────────────────── Kusur 2 — parantez içi anlam ─────────────────────────────

def test_parantez_ici_sozcuk_birim_sanilip_silinmez():
    """Sungrow: `Temp. (PV module)` → 'temp' → temp_ambient 1.0 güvenle. Modül sıcaklığıdır."""
    m, _ = suggest_mapping(_df(**{"Active Power": 1500.0, "Temp. (PV module)": 41.2}))
    assert m.temp_module == "Temp. (PV module)"
    assert m.temp_ambient is None


def test_parantez_ici_reaktif_guc_sanilmaz():
    m, _ = suggest_mapping(_df(**{"Active Power": 1500.0, "Power (reactive)": 12.0}))
    assert m.power == "Active Power"


def test_birim_parantezi_hala_soyulur():
    """Gerileme koruması: `(kW)`, `(W/m2)`, `(°C)` gerçekten birimdir, atılmalı."""
    assert normalize_name("Active Power (kW)") == "active power"
    assert normalize_name("Irradiance [W/m2]") == "irradiance"
    assert normalize_name("Ambient Temperature (°C)") == "ambient temperature"


# ───────────────────────────── Kusur 3 — GHI ≠ POA, çıplak temp/wind ─────────────────────────────

@pytest.mark.parametrize("kolon", ["Total Horizontal Irradiation", "Daily Horizontal Irradiation"])
def test_yatay_isinim_poa_ya_gitmez(kolon):
    """Sungrow'un yatay ışınım alanları `irradiation` eşanlamlısı yüzünden POA'ya gidiyordu —
    modül docstring'inin açıkça yasakladığı durum."""
    m, _ = suggest_mapping(_df(**{"Active Power": 1500.0, kolon: 612.0}))
    assert m.ghi == kolon
    assert m.poa_irradiance is None


@pytest.mark.parametrize("kolon", ["CellTemp", "pv_temperature", "ModuleTemperature", "modultemperatur"])
def test_modul_sicakligi_ortam_sanilmaz(kolon):
    """Çıplak `temp` eşanlamlısı her sıcaklığı temp_ambient'a çekiyordu (FIMER, Huawei, Solar-Log, skytron)."""
    m, _ = suggest_mapping(_df(**{"Active Power": 1500.0, kolon: 41.2}))
    assert m.temp_module == kolon
    assert m.temp_ambient is None


def test_ruzgar_uretimi_ruzgar_hizi_sanilmaz():
    """Türkiye ülke geneli dosyası: `wind` = rüzgâr santrali üretimi (MW), 1.0 güvenle wind_speed oluyordu."""
    m, _ = suggest_mapping(_df(**{"Active Power": 3394.4, "wind": 10612.5}))
    assert m.wind_speed is None


def test_ambient_kolonu_hala_bulunur():
    """Gerileme koruması: gerçek ortam sıcaklığı adları eşleşmeye devam etmeli."""
    m, _ = suggest_mapping(_df(**{"Active Power": 1500.0, "ambient_temp__589": 20.3, "Wind Speed": 3.1}))
    assert m.temp_ambient == "ambient_temp__589"
    assert m.wind_speed == "Wind Speed"


def test_kendi_disa_aktarimimiz_kayipsiz_geri_okunur():
    """v2.357 — yuvarlak yolculuk: "Veriniz sizindir" CSV'sinin başlıkları
    (ingest_service.DISA_KOLONLAR) eksiksiz eşlenmeli. Canlıda yakalandı:
    t_air listede yoktu, ortam sıcaklığı sessizce düşüyordu."""
    m, rapor = suggest_mapping(pd.DataFrame({
        "ts_utc": ZAMAN, "power_kw": [1.8] * 6, "energy_kwh": [1.8] * 6,
        "poa_wm2": [850.0] * 6, "t_air": [24.5] * 6, "t_module": [41.2] * 6,
        "wind_ms": [2.7] * 6}))
    assert m.timestamp == "ts_utc"
    assert m.power == "power_kw"
    assert m.energy == "energy_kwh"
    assert m.poa_irradiance == "poa_wm2"
    assert m.temp_ambient == "t_air"
    assert m.temp_module == "t_module"
    assert m.wind_speed == "wind_ms"
