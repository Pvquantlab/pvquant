"""Anayasa 8.4 — Santralim sayfasinin tek okuma katmani.
Fable 5 v1.5+v1.8: forecast_service bitince tum bagimliliklar hazir;
ozet_service son_kosu+scada_oku+aktif calibrations okur, hero+KPI+grafik+
saglik doldurur. Icgoru sirasi (§7): verisi TAM olan ilk sablon kazanir.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional
import pandas as pd
from sqlalchemy import text
from pvquant.db import tenant_baglami
from pvquant.services.forecast_service import son_kosu
from pvquant.services.ingest_service import scada_oku


AYLAR_KISA_TR = ["Oca","Şub","Mar","Nis","May","Haz",
                 "Tem","Ağu","Eyl","Eki","Kas","Ara"]
GUNLER_KISA_TR = ["PZT","SAL","ÇAR","PER","CUM","CMT","PAZ"]


@dataclass
class GununOzeti:
    """Santralim sayfasinin BEKLEDIGI sozlesme (Anayasa 8.4)."""
    mode: Optional[str] = None
    sapma_pct: Optional[float] = None
    icgoru_cumlesi: Optional[str] = None
    hava_3gun: list = field(default_factory=list)
    bugun_kwh: Optional[float] = None
    yarin_kwh: Optional[float] = None
    yarin_hava: str = ""
    kalibrasyon_tarihi: object = None
    hafta_mwh: Optional[float] = None
    model_alt: str = ""
    saatler: list = field(default_factory=list)
    gercek_kw: list = field(default_factory=list)
    tahmin_kw: list = field(default_factory=list)
    p10_kw: list = field(default_factory=list)     # v2.43 bant
    p90_kw: list = field(default_factory=list)     # v2.43 bant
    simdi_idx: int = 0
    gunler: list = field(default_factory=list)
    gunluk_mwh: list = field(default_factory=list)
    bugun_idx: int = 0
    son_scada_tarihi: Optional[datetime] = None
    islenen_saat: int = 0
    anomali_sayisi: int = 0


def _icgoru_sec(o: GununOzeti, tenant_id, santral) -> Optional[str]:
    """Fable 5 v1.8 muhurlu kural: §7'deki sirayla dene, verisi TAM olan
    ilk sablon kazanir. Ucu de bulamazsa None -> icgoru satiri cizilmez."""
    if len(o.hava_3gun) >= 2 and o.bugun_kwh and o.yarin_kwh and o.bugun_kwh > 0:
        fark = (o.yarin_kwh - o.bugun_kwh) / o.bugun_kwh * 100
        # v2.16 P6: |fark| < 1,5 -> "ayni seviyede" (anlamsiz fark sunulmaz)
        if abs(fark) < 1.5:
            return "Yarın beklenen üretim bugünle aynı seviyede."
        fark_tam = round(abs(fark))
        yon = "yüksek" if fark >= 0 else "düşük"
        return (f"Yarın beklenen üretim bugünden "
                f"%{fark_tam} {yon}.")

    if o.gunler and o.gunluk_mwh and len(o.gunler) == len(o.gunluk_mwh):
        max_idx = max(range(len(o.gunluk_mwh)), key=lambda i: o.gunluk_mwh[i])
        _GUN_TAM = {"PAZ": "Pazar", "PZT": "Pazartesi", "SAL": "Salı",
                    "ÇAR": "Çarşamba", "PER": "Perşembe", "CUM": "Cuma",
                    "CMT": "Cumartesi", "BUGÜN": "bugün", "YARIN": "yarın"}
        _gun = _GUN_TAM.get(o.gunler[max_idx], o.gunler[max_idx])
        _mwh = f"{o.gunluk_mwh[max_idx]:.1f}".replace(".", ",")   # K4
        return (f"7 günlük ufukta en yüksek üretim {_gun} bekleniyor: "
                f"{_mwh} MWh.")

    if o.hafta_mwh is not None:
        with tenant_baglami(tenant_id) as s:
            gecen = s.execute(text(
                "SELECT SUM(COALESCE(energy_kwh, power_kw)) AS toplam FROM scada_hourly "
                "WHERE plant_id=:p AND flag='valid' "
                "AND ts_utc >= now() - interval '7 days'"),
                {"p": santral["id"]}).scalar()
        if gecen and gecen > 0:
            gecen_mwh = float(gecen) / 1000.0
            fark = (o.hafta_mwh - gecen_mwh) / gecen_mwh * 100
            yon = "üzerinde" if fark >= 0 else "altında"
            return (f"Bu hafta toplam beklenti {o.hafta_mwh:.1f} MWh — "
                    f"geçen haftanın %{abs(fark):.0f} {yon}.")

    return None


def _gun_etiketi(tarih_str: str, tz: str) -> str:
    """'2026-07-17' -> 'BUGÜN' / 'YARIN' / 'CUM' gibi kisaltma.
    Fable 5 v1.9: datetime.now(ZoneInfo(tz)) — sunucu UTC'de gun kaymaz."""
    try:
        d = datetime.fromisoformat(tarih_str).date()
    except Exception:
        return tarih_str
    bugun = datetime.now(ZoneInfo(tz)).date()
    if d == bugun:
        return "BUGÜN"
    if (d - bugun).days == 1:
        return "YARIN"
    return GUNLER_KISA_TR[d.weekday()]


def yedi_gun_serisi(gunluk_mwh: "pd.Series") -> "pd.Series":
    """v2.71: gunluk MWh serisinden ILK 7 dolu yerel gunu dondurur.

    v2.69 ufku 168 -> 384 saate cikardi; buradaki dilim yoktu, bu yuzden
    '7 GUNLUK TOPLAM' karti sessizce 16 gunu topluyordu (kanit: ekranda
    474,3 MWh, Tahminler 7g tablosu 213 MWh). Sifir-kuyruk gunler (v2.16 F2)
    once dusulur, sonra bastan 7 gun alinir - en buyuk 7 gun degil.
    """
    return gunluk_mwh[gunluk_mwh > 0].head(7)


def gunun_ozeti(tenant_id: str, santral: dict) -> GununOzeti:
    """Santralim'in tek cagrisi. Fable 5 v1.5: forecast_service bittikten
    sonra tum bagimliliklar hazir; okuma + sablon secimi burada."""
    o = GununOzeti()
    tz = santral.get("tz") or "Europe/Istanbul"

    # ---------- 1) Veri sagligi ----------
    with tenant_baglami(tenant_id) as s:
        row = s.execute(text(
            "SELECT MAX(ts_utc) AS son_ts, "
            " COUNT(*) FILTER (WHERE flag='valid') AS valid_n, "
            " COUNT(*) FILTER (WHERE flag<>'valid') AS anomali_n "
            "FROM scada_hourly WHERE plant_id=:p"),
            {"p": santral["id"]}).first()
    if row is not None:
        o.son_scada_tarihi = row.son_ts
        o.islenen_saat = int(row.valid_n or 0)
        o.anomali_sayisi = int(row.anomali_n or 0)

    # ---------- 2) Aktif calibrations ----------
    with tenant_baglami(tenant_id) as s:
        cal = s.execute(text(
            "SELECT mode, quality_json, created_at FROM calibrations "
            "WHERE plant_id=:p AND active LIMIT 1"),
            {"p": santral["id"]}).first()
    if cal:
        o.mode = cal.mode
        q = cal.quality_json if isinstance(cal.quality_json, dict) else {}
        o.sapma_pct = q.get("deviation_pct")
        o.model_alt = "Kalibre fizik" if cal.mode == "B" else "Hibrit"
        o.kalibrasyon_tarihi = cal.created_at  # v2.13: KPI alt satirinda

    # ---------- 3) son_kosu -> KPI + grafik + hava ----------
    df = son_kosu(tenant_id, santral["id"])
    if df is not None and len(df) > 0:
        df_yerel = df.tz_convert(tz).copy()
        bugun_yerel = datetime.now().astimezone().date()

        bugun_mask = df_yerel.index.date == bugun_yerel
        if bugun_mask.any():
            o.bugun_kwh = float(df_yerel.loc[bugun_mask, "p50_kw"].sum())

        from datetime import timedelta
        yarin_yerel = bugun_yerel + timedelta(days=1)
        yarin_mask = df_yerel.index.date == yarin_yerel
        if yarin_mask.any():
            o.yarin_kwh = float(df_yerel.loc[yarin_mask, "p50_kw"].sum())

        gunluk = df_yerel["p50_kw"].groupby(df_yerel.index.date).sum() / 1000.0
        gunluk = yedi_gun_serisi(gunluk)     # v2.71 (v2.16 F2 iceride)
        o.hafta_mwh = float(gunluk.sum())    # v2.71: kart = 7 cubugun toplami
        o.gunler = [_gun_etiketi(str(d), tz) for d in gunluk.index]
        o.gunluk_mwh = [float(v) for v in gunluk.values]
        for i, d in enumerate(gunluk.index):
            if d == bugun_yerel:
                o.bugun_idx = i
                break

        if bugun_mask.any():
            bugun_df = df_yerel.loc[bugun_mask]
            o.saatler = [ts.strftime("%H:%M") for ts in bugun_df.index]
            o.tahmin_kw = [float(v) for v in bugun_df["p50_kw"].values]
            # v2.43: bant ana sayfaya — kosuda p10/p90 varsa listelenir
            if "p10_kw" in bugun_df.columns and bugun_df["p10_kw"].notna().any():
                o.p10_kw = [None if v != v else float(v)
                            for v in bugun_df["p10_kw"].values]
                o.p90_kw = [None if v != v else float(v)
                            for v in bugun_df["p90_kw"].values]

            scada = scada_oku(tenant_id, santral["id"])
            if len(scada) > 0:
                scada_yerel = (scada.tz_convert(tz) if scada.index.tz
                               else scada.tz_localize("UTC").tz_convert(tz))
                bugun_scada = scada_yerel[scada_yerel.index.date == bugun_yerel]
                if len(bugun_scada) > 0:
                    # Gercek seri: son valid saate kadar dolu, sonrasi None (cizilmez)
                    reindexed = bugun_scada["power_kw"].reindex(bugun_df.index)
                    o.gercek_kw = [float(v) if pd.notna(v) else None
                                   for v in reindexed.values]
            # v2.16 F1: simdi imleci SCADA'dan BAGIMSIZ hesaplanir
            # (Fable 5 v1.9: simdi = gercek duvar saati, santral tz)
            simdi_wall = datetime.now(ZoneInfo(tz))
            for i, ts in enumerate(bugun_df.index):
                if ts >= simdi_wall:
                    o.simdi_idx = max(0, i - 1)
                    break
            else:
                o.simdi_idx = len(bugun_df) - 1  # gun sonuna gectiysek

        with tenant_baglami(tenant_id) as s:
            run_row = s.execute(text(
                "SELECT meteo_ozet_json FROM forecast_runs "
                "WHERE plant_id=:p ORDER BY run_at DESC LIMIT 1"),
                {"p": santral["id"]}).first()
        if run_row and run_row.meteo_ozet_json:
            ozet = run_row.meteo_ozet_json
            bugun_yerel_d = datetime.now(ZoneInfo(tz)).date()
            for g in ozet.get("gunler", []):
                try:
                    g_tarih = datetime.fromisoformat(g["tarih"]).date()
                except Exception:
                    continue
                if g_tarih < bugun_yerel_d:
                    continue  # Fable 5 v1.9: bayat-kosu koruma
                o.hava_3gun.append({
                    "gun": _gun_etiketi(g["tarih"], tz),
                    "derece": g["t_max"],
                    "kwhm2": g["ghi_kwh_m2"],
                })
                if len(o.hava_3gun) >= 3:
                    break

        if len(o.hava_3gun) >= 2:
            _kwhm2 = f'{o.hava_3gun[1]["kwhm2"]:.1f}'.replace(".", ",")  # K4
            o.yarin_hava = f'{_kwhm2} kWh/m² ışınım'

    # ---------- 4) Icgoru ----------
    o.icgoru_cumlesi = _icgoru_sec(o, tenant_id, santral)

    return o


def saat_ay_matrisi(tenant_id: str, plant_id: str):
    """v2.121 — Solargis Tablo 4.3 gelenegi: yerel saat x ay ortalama uretim (kW).
    Tum valid SCADA'dan; hucre = o ay o saatin cok-yilli ortalamasi.
    'toplam' satiri = saat ortalamalarinin toplami (tipik gunun kWh'i)."""
    import pandas as pd
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        p = s.execute(text("SELECT tz FROM plants WHERE id=:p"),
                      {"p": plant_id}).mappings().first()
        if p is None:
            raise LookupError("santral yok: %s" % plant_id)
        df = pd.read_sql(text(
            "SELECT ts_utc, power_kw FROM scada_hourly "
            "WHERE plant_id=:p AND flag='valid'"),
            s.connection(), params={"p": plant_id}, parse_dates=["ts_utc"])
    tz = p["tz"] or "UTC"
    if df.empty:
        return {"saatler": [], "hucreler": [], "toplam": [None] * 12,
                "birim": "kW", "tz": tz}
    if df.ts_utc.dt.tz is None:
        yerel = df.ts_utc.dt.tz_localize("UTC").dt.tz_convert(tz)
    else:
        yerel = df.ts_utc.dt.tz_convert(tz)
    df = df.assign(ay=yerel.dt.month, saat=yerel.dt.hour)
    piv = df.pivot_table(index="saat", columns="ay",
                         values="power_kw", aggfunc="mean")
    # gunduz iskeleti: ortalamasi anlamli (>=1 kW) ilk/son saat arasi —
    # gece sifir satirlari panelde yer kaplamasin (rapor 0-24 verir, panel vermez)
    anlamli = piv.index[piv.mean(axis=1, skipna=True) >= 1]
    if len(anlamli) == 0:
        anlamli = piv.index
    s_ilk, s_son = int(anlamli.min()), int(anlamli.max())
    piv = piv.reindex(index=range(s_ilk, s_son + 1), columns=range(1, 13))
    hucreler = [[None if pd.isna(v) else round(float(v)) for v in satir]
                for satir in piv.values]
    toplam = [None if pd.isna(piv[m].sum()) or piv[m].isna().all()
              else round(float(piv[m].sum(skipna=True)))
              for m in range(1, 13)]
    return {"saatler": [f"{h:02d}\u2013{h+1:02d}" for h in range(s_ilk, s_son + 1)],
            "hucreler": hucreler, "toplam": toplam, "birim": "kW", "tz": tz}
