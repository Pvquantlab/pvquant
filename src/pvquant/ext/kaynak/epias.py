"""EPİAŞ Şeffaflık Platformu istemcisi — gerçekleşen üretim, PTF/SMF, KGÜP, dengesizlik.

Kimlik: kayıtlı kullanıcı adı/şifre ile TGT (https://giris.epias.com.tr/cas/v1/tickets;
11 Kas 2025'ten beri kimlik body'de). CAS limitleri: TGT 100/dk, ST 1.500/dk. Veri
servisleri POST + JSON gövde ({"startDate": "...T00:00:00+03:00", "endDate": ...}).
Doküman: https://seffaflik.epias.com.tr/electricity-service/technical/tr/index.html
Bu istemci minimaldir; üretimde `eptr2` (github.com/Tideseed/eptr2) de değerlendirilebilir.
Şifreler asla koda yazılmaz: EPIAS_KULLANICI / EPIAS_SIFRE ortam değişkenleri.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass

import httpx
import pandas as pd

TGT_URL = "https://giris.epias.com.tr/cas/v1/tickets"
KOK = "https://seffaflik.epias.com.tr/electricity-service"
UC = {
    "ptf": "/v1/markets/dam/data/mcp",
    "smf": "/v1/markets/bpm/data/system-marginal-price",
    "sistem_yonu": "/v1/markets/bpm/data/system-direction",
    "kgup": "/v1/generation/data/dpp",
    "kgup_ilk": "/v1/generation/data/dpp-first-version",
    "gercek_zamanli_uretim": "/v1/generation/data/realtime-generation",
    "dengesizlik_miktar": "/v1/markets/imbalance/data/imbalance-quantity",
    "dengesizlik_tutar": "/v1/markets/imbalance/data/imbalance-amount",
    "gip_aof": "/v1/markets/idm/data/weighted-average-price",
    "yek_dengesizlik_maliyeti": "/v1/renewables/data/imbalance-cost",
    "res_uretim_tahmin": "/v1/renewables/data/res-generation-and-forecast",
}


@dataclass
class SeffaflikIstemci:
    kullanici: str | None = None
    sifre: str | None = None
    timeout: float = 60.0
    _tgt: str | None = None
    _tgt_zaman: float = 0.0

    def _kimlik(self) -> tuple[str, str]:
        k = self.kullanici or os.environ.get("EPIAS_KULLANICI"); s = self.sifre or os.environ.get("EPIAS_SIFRE")
        if not k or not s:
            raise RuntimeError("EPIAS_KULLANICI / EPIAS_SIFRE ortam değişkenleri gerekli")
        return k, s

    def tgt(self) -> str:
        """TGT ~2 saat geçerli; 100 dk'da bir yeniler (CAS limiti 100/dk'ya karşı tutumlu)."""
        if self._tgt and time.time() - self._tgt_zaman < 100 * 60:
            return self._tgt
        k, s = self._kimlik()
        r = httpx.post(TGT_URL, data={"username": k, "password": s},
                       headers={"Accept": "text/plain", "Content-Type": "application/x-www-form-urlencoded"},
                       timeout=self.timeout)
        r.raise_for_status()
        self._tgt = r.text.strip(); self._tgt_zaman = time.time()
        return self._tgt

    def sorgu(self, ad: str, baslangic: str, bitis: str, **ek) -> pd.DataFrame:
        """ad: UC anahtarı. Tarihler 'YYYY-MM-DD' (İstanbul günü). ek: ör. powerPlantId=..., organizationId=..."""
        govde = {"startDate": f"{baslangic}T00:00:00+03:00", "endDate": f"{bitis}T23:00:00+03:00", **ek}
        r = httpx.post(KOK + UC[ad], json=govde, headers={"TGT": self.tgt(), "Content-Type": "application/json"},
                       timeout=self.timeout)
        if r.status_code == 429:
            time.sleep(30); r = httpx.post(KOK + UC[ad], json=govde, headers={"TGT": self.tgt()}, timeout=self.timeout)
        r.raise_for_status()
        j = r.json()
        satirlar = j.get("items") or j.get("body", {}).get("content") or j.get("content") or []
        df = pd.DataFrame(satirlar)
        for kol in ("date", "hour", "time"):
            if kol in df and df[kol].dtype == object and df[kol].astype(str).str.contains("T").any():
                df["zaman"] = pd.to_datetime(df[kol]).dt.tz_convert("Europe/Istanbul")
                break
        return df

    # Kısayollar
    def ptf(self, b, e): return self.sorgu("ptf", b, e)
    def smf(self, b, e): return self.sorgu("smf", b, e)
    def gercek_zamanli_uretim(self, b, e, **ek): return self.sorgu("gercek_zamanli_uretim", b, e, **ek)
    def kgup(self, b, e, **ek): return self.sorgu("kgup", b, e, **ek)


def dengesizlik_maliyeti(kgup_mwh: pd.Series, gerceklesen_mwh: pd.Series, ptf: pd.Series, smf: pd.Series,
                         k: float = 0.03, l: float = 0.03) -> pd.DataFrame:
    """DUY md. 110–111: sapma = gerçekleşen − KGÜP (saatlik MWh).
    Pozitif dengesizlik geliri = min(PTF,SMF)·(1−l)·sapma; negatif dengesizlik gideri = max(PTF,SMF)·(1+k)·|sapma|.
    'maliyet' = PTF ile satılsaydı elde edilecek gelire göre kayıp (TL). KÜPST ayrı hesaplanır (Kurul katsayıları)."""
    idx = kgup_mwh.index.intersection(gerceklesen_mwh.index).intersection(ptf.index).intersection(smf.index)
    sap = (gerceklesen_mwh - kgup_mwh).loc[idx]
    poz = sap.clip(lower=0.0); neg = (-sap).clip(lower=0.0)
    gelir_poz = poz * pd.concat([ptf.loc[idx], smf.loc[idx]], axis=1).min(axis=1) * (1 - l)
    gider_neg = neg * pd.concat([ptf.loc[idx], smf.loc[idx]], axis=1).max(axis=1) * (1 + k)
    referans = sap.abs() * ptf.loc[idx]
    out = pd.DataFrame({"sapma_mwh": sap, "pozitif_gelir_tl": gelir_poz, "negatif_gider_tl": gider_neg})
    out["maliyet_tl"] = (referans - gelir_poz).where(sap > 0, gider_neg - referans)
    return out
