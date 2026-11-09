"""v2.551 (Aşama 2, S1): SunSpec 7xx (IEEE 1547 DER) okuyucu — sahte cihaz 1 + 701 + 702 + 714; öncelik 701 > 1xx; TotWhInj isteğe bağlı → 1xx WH yedeği →
güç entegrasyonu; InvSt eşlemesi (bir eksik); zincir savunması. Gerçek cihaz yok (Opus 08 §2 register tabloları; sunspec/models JSON ofsetleri)."""
from __future__ import annotations

import pytest

from pvquant.io.canli import sunspec as ss
from pvquant.services import canli_alim_service as ca


def _regs701(**d):
    r = [0xFFFF] * 121
    r[0] = 2            # ACType THREE_PHASE
    r[1] = 1            # St ON
    r[2] = 3            # InvSt RUNNING → 103.St 4 (MPPT)
    r[3] = 1            # ConnSt CONNECTED
    r[4], r[5] = 0, 0   # Alrm yok
    r[8] = 9876         # W (int16) × 10^W_SF
    r[9], r[10], r[11], r[12] = 10000, 500, 99, 1500
    r[14] = 400         # LNV
    r[15], r[16] = 0, 5000   # Hz uint32 → 50.00 (Hz_SF −2)
    r[17:21] = [0, 0, 0x007A, 0x1200]   # TotWhInj 8.000.000 Wh
    r[34], r[35] = 350, 420   # TmpCab, TmpSnk (×10⁻¹)
    r[108] = 0          # ThrotPct
    r[111:121] = [-1 & 0xFFFF, -1 & 0xFFFF, (-2) & 0xFFFF, 1, (-2) & 0xFFFF, 0, 0, 0, 0, (-1) & 0xFFFF]   # A_SF −1, V_SF −1, Hz_SF −2, W_SF 1, PF_SF −2, VA, Var, TotWh 0, TotVarh 0, Tmp −1
    for k, v in d.items():
        r[int(k)] = v
    return r


def _regs702():
    r = [0xFFFF] * 50
    r[0] = 1000   # WMaxRtg × 10^W_SF
    r[5] = 1100
    r[43], r[45], r[46] = 2, 2, 2   # W_SF, VA_SF, Var_SF
    return r


def _regs714(nprt=2):
    r = [0xFFFF] * (18 + 25 * nprt)
    r[0], r[1] = 0, 0
    r[2] = nprt
    r[3], r[4] = 250, 1050          # DCA ×10⁻¹, DCW ×10²
    r[5:9] = [0, 0, 0, 1234]        # DCWhInj
    r[13:18] = [(-1) & 0xFFFF, 0, 2, 0, (-1) & 0xFFFF]
    for k in range(nprt):
        b = 18 + 25 * k
        r[b] = 0; r[b + 1] = k + 1
        for i, ch in enumerate((f"MPPT{k + 1}".encode() + b"\x00" * 16)[:16:2]):
            r[b + 2 + i] = (ch << 8) | ((f"MPPT{k + 1}".encode() + b"\x00" * 16)[2 * i + 1])
        r[b + 10], r[b + 11], r[b + 12] = 125, 7000, 525
        r[b + 13:b + 17] = [0, 0, 0, 600]
        r[b + 21], r[b + 22] = 300, 1
    return r


def _cihaz(modeller: dict, ortak=True):
    """modeller: {model_id: regs}; zincir 40000'den."""
    adresler, a = {}, 40002
    if ortak:
        adresler[a] = (1, 66, [0] * 66); a += 68
    for mid, regs in modeller.items():
        adresler[a] = (mid, len(regs), regs); a += 2 + len(regs)
    son = a
    def oku(adres, adet):
        if adres == 40000: return [0x5375, 0x6E53]
        if adres == son: return [0xFFFF, 0]
        if adres in adresler:
            mid, uz, _ = adresler[adres]; return [mid, uz]
        for base, (mid, uz, regs) in adresler.items():
            if adres == base + 2:
                return list(regs[:adet]) + [0] * max(0, adet - len(regs))
            if base + 2 < adres < base + 2 + uz:   # blok içi parçalı okuma (adet > 125 bölünür)
                off = adres - (base + 2); return list(regs[off:off + adet]) + [0] * max(0, adet - (len(regs) - off))
        return [0] * adet
    return oku


def test_701_oncelik_enerji_ve_durum():
    c = ss.oku_cihaz(_cihaz({701: _regs701(), 702: _regs702(), 714: _regs714()}))
    inv = c["inverter"]
    assert c["profil"] == "7xx" and c["enerji_yolu"] == "701" and [m["id"] for m in c["modeller"]] == [1, 701, 702, 714]
    assert inv["guc_w"] == pytest.approx(98760.0) and inv["enerji_wh"] == pytest.approx(8_000_000.0) and inv["frekans_hz"] == pytest.approx(50.0)
    assert inv["durum_kodu"] == 4 and inv["durum"] == "üretimde (MPPT)" and inv["der_durum"] == "üretimde" and inv["olaylar"] == []
    assert inv["kabin_sicaklik_c"] == pytest.approx(35.0) and inv["faz"] == "üç faz"
    assert c["kapasite"]["anma_guc_w"] == pytest.approx(100000.0)                  # 702 WMaxRtg 1000 × 10²
    assert c["dc"]["dc_guc_w"] == pytest.approx(105000.0) and len(c["dc"]["portlar"]) == 2 and c["dc"]["portlar"][1]["ad"] == "MPPT2" and c["dc"]["portlar"][0]["dc_guc_w"] == pytest.approx(52500.0)
    assert inv["dc_guc_w"] == pytest.approx(105000.0)                                # 714 toplamı inverter DC alanına taşınır


def test_701_enerji_yok_1xx_yedegi_ve_entegrasyon_yolu():
    yok = _regs701(**{"17": 0xFFFF, "18": 0xFFFF, "19": 0xFFFF, "20": 0xFFFF})       # TotWhInj uygulanmamış
    c = ss.oku_cihaz(_cihaz({701: yok}))
    assert c["enerji_yolu"] == "yok" and c["inverter"]["enerji_wh"] is None and c["inverter"]["enerji_durumu"] == "uygulanmamis" and c["inverter"]["guc_w"] == pytest.approx(98760.0)
    r103 = [1500, 500, 500, 500, 0xFFFF, 400, 400, 400, 230, 230, 230, 0, 9876, 1, 5000, 0xFFFE, 0, 0, 0, 0, 0, 0, 0x7A, 0x1200, 0] + [0] * 25
    c2 = ss.oku_cihaz(_cihaz({701: yok, 103: r103}))                                   # aynı cihazda 701 + 103: güç 701'den, enerji 103 WH'den; çift sayım yok
    assert c2["profil"] == "7xx" and c2["enerji_yolu"] == "1xx" and c2["inverter"]["enerji_wh"] == pytest.approx(8_000_000.0) and c2["inverter"]["model_id"] == 701
    # sınama özeti enerji yolunu ve «entegrasyon» uyarısını taşır
    class Sahte:
        def __init__(self, *a): self.oku = _cihaz({701: yok})
        def __enter__(self): return self
        def __exit__(self, *a): return False
    r = ca.sina({"host": "10.0.0.5"}, onay=True, istemci_fabrikasi=Sahte)
    assert r["durum"] == "ok" and r["ozet"]["profil"] == "7xx" and r["ozet"]["enerji_yolu"] == "yok" and "entegrasyon" in r["not"]


def test_701_invst_eslemesi_ve_alarm_bitleri():
    c = ss.oku_cihaz(_cihaz({701: _regs701(**{"2": 6, "4": 0, "5": 0b10000001})}))   # InvSt FAULT → 7; Alrm bit0 toprak, bit7 aşırı sıcaklık
    inv = c["inverter"]
    assert inv["durum_kodu"] == 7 and inv["durum"] == "arıza" and inv["der_durum_kodu"] == 6 and set(inv["olaylar"]) == {"toprak arızası", "aşırı sıcaklık"}
    c2 = ss.oku_cihaz(_cihaz({701: _regs701(**{"2": 0xFFFF, "1": 0})}))               # InvSt uygulanmamış, St OFF → kapalı
    assert c2["inverter"]["durum_kodu"] == 1 and c2["inverter"]["der_durum"] == "bilinmiyor"


def test_kesif_savunmasi_ve_kismi():
    def bozuk(adres, adet):
        if adres == 40000: return [0x5375, 0x6E53]
        if adres == 40002: return [1, 66]
        if adres == 40070: return [701, 0]        # L=0 (0xFFFF değil) → zincir biter
        return [0] * adet
    temel, modeller = ss.kesfet(bozuk)
    assert temel == 40000 and [m[0] for m in modeller] == [1]
    c = ss.oku_cihaz(bozuk)
    assert c["inverter"] is None and c["profil"] is None and c["enerji_yolu"] == "yok"
    def kisa701(adres, adet):
        if adres == 40000: return [0x5375, 0x6E53]
        if adres == 40002: return [1, 66]
        if adres == 40070: return [701, 50]       # belgelenen 153'ten kısa
        if adres == 40122: return [0xFFFF, 0]
        return [0] * adet
    with pytest.raises(ValueError, match="701 kısa"):
        ss.oku_cihaz(kisa701)
