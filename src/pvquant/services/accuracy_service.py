"""Dogruluk sunum hesaplari. hata_matrisi: saat x gun isaretli hata matrisi.
Kurallar gece_skill ile ozdes (tek kural kitabi): flag='valid' eslesme,
ufuk = ts_utc - run_at, gunduz = power > %2 kapasite. Hesap hafif tutulur;
agir skorlar worker'da (tek uretici o), burada ham eslesme + pivot var."""
from __future__ import annotations
import pandas as pd
from sqlalchemy import text
from pvquant.db import tenant_baglami

_KOVALAR = {"0-24": (0, 24), "24-72": (24, 72),
            "72-168": (72, 168), "168+": (168, 999)}
_SAAT_ILK, _SAAT_SON = 5, 20          # rapor s06 ile ayni iskelet (05-20 yerel)


def hata_matrisi(tenant_id, plant_id, gun: int = 30, kova: str = "0-24"):
    """Dunle biten N tam YEREL gunun saat x gun isaretli hatasi (p50 - gercek, kW).
    Gece / verisiz / bayrakli hucreler None. Ayni hucreye birden cok gozlem
    duserse ortalama (kural belirsizligi olmasin)."""
    if kova not in _KOVALAR:
        raise ValueError("bilinmeyen kova: %s" % kova)
    lo, hi = _KOVALAR[kova]
    with tenant_baglami(tenant_id) as s:
        p = s.execute(text(
            "SELECT tz, capacity_kwp FROM plants WHERE id=:p"),
            {"p": plant_id}).mappings().first()
        if p is None:
            raise LookupError("santral yok: %s" % plant_id)
        df = pd.read_sql(text(
            "SELECT f.ts_utc, f.p50_kw, r.run_at, s.power_kw "
            "FROM forecast_values f "
            "JOIN forecast_runs r ON r.id=f.run_id "
            "JOIN scada_hourly s ON s.plant_id=f.plant_id AND s.ts_utc=f.ts_utc"
            " AND s.flag='valid' "
            "WHERE f.plant_id=:p "
            "AND f.ts_utc >= now() - ((:g + 2) * INTERVAL '1 day')"),
            s.connection(), params={"p": plant_id, "g": gun},
            parse_dates=["ts_utc", "run_at"])
    tz = p["tz"] or "UTC"
    saatler = ["%02d\u2013%02d" % (h, h + 1) for h in range(_SAAT_ILK, _SAAT_SON)]
    bos = {"gunler": [], "saatler": saatler, "hucreler": [],
           "metrik": "isaretli_hata", "birim": "kW", "kova": kova, "tz": tz}
    if df.empty:
        return bos
    ufuk = (df.ts_utc - df.run_at).dt.total_seconds() / 3600
    df = df[(ufuk > lo) & (ufuk <= hi)]
    if df.empty:
        return bos
    if df.ts_utc.dt.tz is None:                       # surucu naive verdiyse
        yerel = df.ts_utc.dt.tz_localize("UTC").dt.tz_convert(tz)
    else:                                             # psycopg3: zaten aware
        yerel = df.ts_utc.dt.tz_convert(tz)
    df = df.assign(y_gun=yerel.dt.date, y_saat=yerel.dt.hour)
    # dunle biten N tam yerel gun
    dun = (pd.Timestamp.now(tz=tz) - pd.Timedelta(days=1)).date()
    ilk = dun - pd.Timedelta(days=gun - 1)
    df = df[(df.y_gun >= ilk) & (df.y_gun <= dun)]
    df = df[(df.y_saat >= _SAAT_ILK) & (df.y_saat < _SAAT_SON)]
    df = df[df.power_kw > 0.02 * float(p["capacity_kwp"])]      # gunduz
    if df.empty:
        return bos
    df = df.assign(hata=df.p50_kw - df.power_kw)
    piv = df.pivot_table(index="y_saat", columns="y_gun",
                         values="hata", aggfunc="mean")
    gunler = sorted(df.y_gun.unique())
    piv = piv.reindex(index=range(_SAAT_ILK, _SAAT_SON), columns=gunler)
    hucreler = [[None if pd.isna(v) else round(float(v), 1) for v in satir]
                for satir in piv.values]
    return {"gunler": [g.isoformat() for g in gunler], "saatler": saatler,
            "hucreler": hucreler, "metrik": "isaretli_hata", "birim": "kW",
            "kova": kova, "tz": tz}
