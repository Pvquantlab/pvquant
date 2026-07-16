"""Anayasa 8.4 — Santralim sayfasinin tek okuma katmani.
P3'te calibrations/forecast_runs sorgulariyla doldurulur.
Simdilik ISKELET: DB'de veri yoksa mode=None doner (K1 — sahte deger yok)."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from sqlalchemy import text
from pvquant.db import tenant_baglami


@dataclass
class GununOzeti:
    """Santralim sayfasinin BEKLEDIGI sozlesme (Anayasa 8.4)."""
    # Kanit seridi
    mode: Optional[str] = None            # None => 'Kalibre değil'
    sapma_pct: Optional[float] = None     # sadece mode != None ise
    # Hero
    icgoru_cumlesi: Optional[str] = None  # None => satir cizilmez (K1)
    hava_3gun: list = field(default_factory=list)  # bos => hava kartlari yok
    # KPI'lar
    bugun_kwh: Optional[float] = None
    yarin_kwh: Optional[float] = None
    yarin_hava: str = ""
    hafta_mwh: Optional[float] = None
    model_alt: str = ""
    # Grafikler
    saatler: list = field(default_factory=list)
    gercek_kw: list = field(default_factory=list)
    tahmin_kw: list = field(default_factory=list)
    simdi_idx: int = 0
    gunler: list = field(default_factory=list)
    gunluk_mwh: list = field(default_factory=list)
    bugun_idx: int = 0
    # Veri sagligi
    son_scada_tarihi: Optional[datetime] = None
    islenen_saat: int = 0
    anomali_sayisi: int = 0


def gunun_ozeti(tenant_id: str, santral: dict) -> GununOzeti:
    """Santralim sayfasi bu tek fonksiyonu cagirir.
    Simdilik: yalniz veri sagligini scada_hourly'den okur; kalibrasyon ve
    forecast alanlari P3'te doldurulur (mode=None kalir)."""
    o = GununOzeti()
    with tenant_baglami(tenant_id) as s:
        # Veri sagligi — scada_hourly'den ozet
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
    # NOT: mode/sapma/icgoru/KPI/grafikler => P3
    # (Anayasa K1 — bu alanlar 'kalibrasyon var mi' sorgusundan gelir)
    return o
