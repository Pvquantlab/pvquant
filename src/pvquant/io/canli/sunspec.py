"""08.11.2026 v2.545 (P4b ilk bağlayıcı) — SunSpec okuyucu: keşif («SunS» imzası 40000 / 50000 / 0), model zinciri, ortak model (1) ve tek/üç fazlı
inverter modelleri (101–103 tam sayı + ölçek, 111–113 kayan nokta). Kaynak: SunSpec Alliance Information Model Reference (model 1, 101–103, 111–113);
durum kodları (St): 1 KAPALI, 2 UYKU, 3 BAŞLIYOR, 4 MPPT, 5 KISITLI, 6 KAPANIYOR, 7 ARIZA, 8 BEKLEMEDE. Yalnız okur.
"""
from __future__ import annotations

import struct

SUNS = 0x53756E53   # "SunS"
TEMEL_ADRESLER = (40000, 50000, 0)
DURUM = {1: "kapalı", 2: "uyku", 3: "başlıyor", 4: "üretimde (MPPT)", 5: "kısıtlı", 6: "kapanıyor", 7: "arıza", 8: "beklemede"}
OLAY1 = {0: "şebeke gerilimi", 1: "DC aşırı gerilim", 2: "AC kesici açık", 3: "DC kesici açık", 4: "şebeke kesici açık", 5: "kabin açık", 6: "elle kapatma",
         7: "aşırı sıcaklık", 8: "frekans aşımı", 9: "frekans altı", 10: "AC aşırı gerilim", 11: "AC düşük gerilim", 12: "sigorta", 13: "düşük sıcaklık",
         14: "bellek hatası", 15: "donanım testi"}
INVERTER_TAM = {101: "tek faz", 102: "bölünmüş faz", 103: "üç faz"}
INVERTER_FLOAT = {111: "tek faz", 112: "bölünmüş faz", 113: "üç faz"}


def _metin(regs: list[int]) -> str:
    b = b"".join(struct.pack(">H", r) for r in regs)
    return b.split(b"\x00", 1)[0].decode("ascii", errors="replace").strip()


def _i16(v: int) -> int:
    return v - 0x10000 if v >= 0x8000 else v


def _sf(v: int) -> int | None:
    return None if v == 0x8000 else _i16(v)


def _olcekli(deger: int, sf: int | None, isaretli: bool = False, gecersiz=(0xFFFF, 0x8000)) -> float | None:
    if sf is None or deger in gecersiz:
        return None
    d = _i16(deger) if isaretli else deger
    return float(d) * (10.0 ** sf)


def _u32(hi: int, lo: int) -> int | None:
    v = (hi << 16) | lo
    return None if v == 0xFFFFFFFF else v


def _f32(hi: int, lo: int) -> float | None:
    b = struct.pack(">HH", hi, lo)
    v = struct.unpack(">f", b)[0]
    return None if v != v else float(v)   # NaN → None


def kesfet(oku) -> tuple[int, list[tuple[int, int, int]]]:
    """oku(adres, adet) → kayıt listesi. Döner (temel adres, [(model_id, uzunluk, veri_adresi), …]). İmza yoksa ValueError."""
    for temel in TEMEL_ADRESLER:
        try:
            r = oku(temel, 2)
        except Exception:   # noqa: BLE001 — bu adres yoksa sıradakine
            continue
        if ((r[0] << 16) | r[1]) != SUNS:
            continue
        modeller = []
        adres = temel + 2
        for _ in range(64):   # zincir koruması
            r = oku(adres, 2)
            mid, uz = r[0], r[1]
            if mid == 0xFFFF:
                break
            modeller.append((mid, uz, adres + 2))
            adres += 2 + uz
        return temel, modeller
    raise ValueError("SunSpec imzası (SunS) 40000 / 50000 / 0 adreslerinde bulunamadı")


def ortak_model(oku, veri_adresi: int, uzunluk: int) -> dict:
    """Model 1: Mn (16), Md (16), Opt (8), Vr (8), SN (16), DA (1)."""
    r = oku(veri_adresi, min(uzunluk, 66))
    return {"uretici": _metin(r[0:16]), "model": _metin(r[16:32]), "secenek": _metin(r[32:40]), "surum": _metin(r[40:48]),
            "seri_no": _metin(r[48:64]), "cihaz_adresi": r[64] if len(r) > 64 else None}


def inverter_modeli(oku, model_id: int, veri_adresi: int, uzunluk: int) -> dict:
    """101–103 (tam sayı + ölçek) ya da 111–113 (float32) inverter modelinden anlık ölçümler (SI)."""
    r = oku(veri_adresi, uzunluk)
    if model_id in INVERTER_TAM:
        A, AphA, AphB, AphC, A_SF, PPV_AB, PPV_BC, PPV_CA, PhVphA, PhVphB, PhVphC, V_SF, W, W_SF, Hz, Hz_SF, VA, VA_SF, VAr, VAr_SF, PF, PF_SF = r[0:22]
        WH_hi, WH_lo, WH_SF, DCA, DCA_SF, DCV, DCV_SF, DCW, DCW_SF, TmpCab, TmpSnk, TmpTrns, TmpOt, Tmp_SF, St, StVnd = r[22:38]
        Evt1 = _u32(r[38], r[39]) if len(r) > 39 else None
        olc = {"faz": INVERTER_TAM[model_id], "akim_a": _olcekli(A, _sf(A_SF)), "gerilim_v": _olcekli(PhVphA, _sf(V_SF)),
               "guc_w": _olcekli(W, _sf(W_SF), isaretli=True), "frekans_hz": _olcekli(Hz, _sf(Hz_SF)),
               "gorunur_guc_va": _olcekli(VA, _sf(VA_SF), isaretli=True), "reaktif_guc_var": _olcekli(VAr, _sf(VAr_SF), isaretli=True),
               "guc_faktoru": _olcekli(PF, _sf(PF_SF), isaretli=True),
               "enerji_wh": (_u32(WH_hi, WH_lo) * (10.0 ** _sf(WH_SF)) if _u32(WH_hi, WH_lo) is not None and _sf(WH_SF) is not None else None),
               "dc_akim_a": _olcekli(DCA, _sf(DCA_SF)), "dc_gerilim_v": _olcekli(DCV, _sf(DCV_SF)), "dc_guc_w": _olcekli(DCW, _sf(DCW_SF), isaretli=True),
               "kabin_sicaklik_c": _olcekli(TmpCab, _sf(Tmp_SF), isaretli=True), "sogutucu_sicaklik_c": _olcekli(TmpSnk, _sf(Tmp_SF), isaretli=True),
               "durum_kodu": (St if St != 0xFFFF else None), "durum": DURUM.get(St, "bilinmeyen"), "uretici_durum_kodu": (StVnd if StVnd != 0xFFFF else None)}
    elif model_id in INVERTER_FLOAT:
        f = lambda i: _f32(r[i], r[i + 1])
        olc = {"faz": INVERTER_FLOAT[model_id], "akim_a": f(0), "gerilim_v": f(14), "guc_w": f(20), "frekans_hz": f(22), "gorunur_guc_va": f(24),
               "reaktif_guc_var": f(26), "guc_faktoru": f(28), "enerji_wh": f(30), "dc_akim_a": f(32), "dc_gerilim_v": f(34), "dc_guc_w": f(36),
               "kabin_sicaklik_c": f(38), "sogutucu_sicaklik_c": f(40), "durum_kodu": (r[46] if len(r) > 46 and r[46] != 0xFFFF else None),
               "durum": DURUM.get(r[46], "bilinmeyen") if len(r) > 46 else "bilinmeyen", "uretici_durum_kodu": (r[47] if len(r) > 47 and r[47] != 0xFFFF else None)}
        Evt1 = _u32(r[48], r[49]) if len(r) > 49 else None
    else:
        raise ValueError(f"model {model_id} inverter modeli değil")
    olc["olaylar"] = [OLAY1[b] for b in OLAY1 if Evt1 is not None and (Evt1 >> b) & 1] if Evt1 is not None else []
    olc["model_id"] = model_id
    return olc


def oku_cihaz(oku) -> dict:
    """Keşif + ortak model + ilk inverter modeli. Döner {temel, modeller, ortak, inverter}."""
    temel, modeller = kesfet(oku)
    ortak = next(({**ortak_model(oku, va, uz)} for mid, uz, va in modeller if mid == 1), None)
    inv = next((inverter_modeli(oku, mid, va, uz) for mid, uz, va in modeller if mid in INVERTER_TAM or mid in INVERTER_FLOAT), None)
    return {"temel_adres": temel, "modeller": [{"id": mid, "uzunluk": uz} for mid, uz, _ in modeller], "ortak": ortak, "inverter": inv}
