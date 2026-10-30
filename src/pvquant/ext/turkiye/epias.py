"""EPİAŞ Şeffaflık entegrasyonu — TGT, uç noktalar, önbellek, UTC hizalama, gerçekleşen üretim adaptörü.

Doküman: https://seffaflik.epias.com.tr/electricity-service/technical/tr/index.html (Wayback'te en yeni v1.15.15, TR 21.05.2026 / EN 06.06.2026;
önceki «v1.16.4» notu hiçbir anlık görüntüde yok — doğrulanamadı; resmî changelog yok, şema swagger.json info.version ile izlenir — 31.10.2026 bulgular/11.md)
Kimlik: POST https://giris.epias.com.tr/cas/v1/tickets (username/password form gövdesi) → TGT (Şeffaflık dokümanı 2 saat;
CAS duyuruları 8 saat diyor — kısa olan esas). CAS limiti: TGT 100/dk (28.07.2025 duyurusu); veri servisi limiti DOĞRULANAMADI
→ TGT önbelleklenir (100 dk). Sistem yönü (system-direction) METİN döner («Enerji Açığı/Fazlası/Dengede»); sayıya çevrilmez,
kurallar.yon_normalize ile 'acik'|'fazla'|'dengede' olarak saklanır (29.10.2026: önceki sürüm sayıya çevirip NaN yazıyordu). Veri servisleri: POST + JSON gövde
{"startDate": "YYYY-MM-DDT00:00:00+03:00", "endDate": "...T23:00:00+03:00", ...}; yanıt {"items":[...]}.
Şifre koda yazılmaz: EPIAS_KULLANICI / EPIAS_SIFRE. Ağsız test için `transport` (httpx.MockTransport) enjekte edilir.
Önbellek: yerel CSV (gün bazlı) — aynı günü ikinci kez çekmez (fiyatlar kesinleştikten sonra değişmez).
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import pandas as pd

TGT_URL = "https://giris.epias.com.tr/cas/v1/tickets"
KOK = "https://seffaflik.epias.com.tr/electricity-service"
UC = {
    "ptf": ("/v1/markets/dam/data/mcp", "price"),
    "smf": ("/v1/markets/bpm/data/system-marginal-price", "systemMarginalPrice"),
    "sistem_yonu": ("/v1/markets/bpm/data/system-direction", "systemDirection"),
    "kgup": ("/v1/generation/data/dpp", "toplam"),
    "kgup_ilk": ("/v1/generation/data/dpp-first-version", "toplam"),
    "gercek_zamanli_uretim": ("/v1/generation/data/realtime-generation", "total"),
    "dengesizlik_miktar": ("/v1/markets/imbalance/data/imbalance-quantity", "positiveImbalance"),
    "dengesizlik_tutar": ("/v1/markets/imbalance/data/imbalance-amount", "positiveImbalance"),
    "gip_aof": ("/v1/markets/idm/data/weighted-average-price", "wap"),
    "yek_dengesizlik": ("/v1/renewables/data/imbalance-cost", "imbalanceCost"),   # ESKİ DÖNEM UCU (31.10.2026 canlı sınama): yalnız ≤30.04.2016 veri; sonrası 400 (BUS)SEF1181 «Seçtiğiniz tarihlerde veri bulunmamaktadır» → güncel YEKDEM kaynağı DEĞİL
    "santral_listesi": ("/v1/generation/data/powerplant-list", None),
    "uevcb_listesi": ("/v1/generation/data/uevcb-list", None),                     # UevcbListRequestDto: required [organizationId, startDate]; endDate ŞEMADA YOK (swagger v1.15.8)
    "organizasyon_listesi": ("/v1/generation/data/organization-list", None),       # OrganizationListRequestDto: required [startDate, endDate] → organizationId kaynağı
    "uevcb_santraldan": ("/v1/markets/data/uevcb-list-by-power-plant-id", None),  # UevcbRequestDto: required [powerPlantId, startDate]
}
IST = "Europe/Istanbul"
# 29.10 (v2.505, canlı sınama): liste uçları GET'tir (POST → 404 «Method not found or disabled»); KGÜP uçları `region` ister (yoksa 400).
UC_GET = {"santral_listesi"}
VARSAYILAN_EK = {"kgup": {"region": "TR1"}, "kgup_ilk": {"region": "TR1"}}
# 31.10 (v2.510, 04 #11): şemasında endDate olmayan uçlar — gövde yalnız startDate + ek alanlar. CANLI SINAMA 31.10.2026 (sunucu, kayıtlı kimlik):
# organization-list 692 kuruluş; uevcb-list {organizationId,startDate} → 200 (eski gövde → 400 teyit); uevcb-list-by-power-plant-id → 200;
# powerplant-list 1832 santral.
UC_BITIS_YOK = {"uevcb_listesi", "uevcb_santraldan"}
UC_ZORUNLU = {"uevcb_listesi": ("organizationId",), "uevcb_santraldan": ("powerPlantId",)}


@dataclass
class Istemci:
    kullanici: str | None = None
    sifre: str | None = None
    timeout: float = 60.0
    onbellek_dizin: str | Path | None = None
    transport: httpx.BaseTransport | None = None
    _tgt: str | None = field(default=None, repr=False)
    _tgt_zaman: float = 0.0

    def _http(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout, transport=self.transport)

    def tgt(self) -> str:
        if self._tgt and time.time() - self._tgt_zaman < 100 * 60:
            return self._tgt
        k = self.kullanici or os.environ.get("EPIAS_KULLANICI"); s = self.sifre or os.environ.get("EPIAS_SIFRE")
        if not k or not s:
            raise RuntimeError("EPIAS_KULLANICI / EPIAS_SIFRE gerekli")
        with self._http() as c:
            r = c.post(TGT_URL, data={"username": k, "password": s}, headers={"Accept": "text/plain"})
            r.raise_for_status()
        self._tgt = r.text.strip(); self._tgt_zaman = time.time()
        return self._tgt

    def ham(self, ad: str, baslangic: str, bitis: str, **ek) -> list[dict]:
        yol, _ = UC[ad]
        ek = {**VARSAYILAN_EK.get(ad, {}), **ek}
        eksik = [z for z in UC_ZORUNLU.get(ad, ()) if z not in ek]
        if eksik:
            raise ValueError(f"EPİAŞ {ad}: zorunlu alan eksik: {', '.join(eksik)} (şema v1.15.8)")
        govde = {"startDate": f"{baslangic}T00:00:00+03:00", **ek} if ad in UC_BITIS_YOK else \
                {"startDate": f"{baslangic}T00:00:00+03:00", "endDate": f"{bitis}T23:00:00+03:00", **ek}
        for deneme in range(3):
            with self._http() as c:
                if ad in UC_GET:
                    r = c.get(KOK + yol, headers={"TGT": self.tgt(), "Accept": "application/json"})
                else:
                    r = c.post(KOK + yol, json=govde, headers={"TGT": self.tgt(), "Content-Type": "application/json"})
            if r.status_code == 429:
                time.sleep(15 * (deneme + 1)); continue
            if r.status_code == 401 and deneme == 0:
                self._tgt = None; continue
            r.raise_for_status()
            j = r.json()
            return j.get("items") or j.get("body", {}).get("content") or j.get("content") or []
        raise RuntimeError(f"EPİAŞ {ad}: tekrar denemeler tükendi")

    def seri(self, ad: str, baslangic: str, bitis: str, alan: str | None = None, **ek) -> pd.Series:
        """Saatlik seri, index UTC. alan verilmezse UC'deki varsayılan değer alanı."""
        alan = alan or UC[ad][1]
        onb = self._onbellek_oku(ad, baslangic, bitis, alan, ek)
        if onb is not None:
            return onb
        satirlar = self.ham(ad, baslangic, bitis, **ek)
        if not satirlar:
            return pd.Series(dtype=float, name=ad)
        df = pd.DataFrame(satirlar)
        zaman_kolon = next((c for c in ("date", "time", "hour", "datetime") if c in df), None)
        if zaman_kolon is None:
            raise ValueError(f"zaman kolonu bulunamadı: {list(df.columns)[:8]}")
        t = pd.to_datetime(df[zaman_kolon], utc=False)
        t = t.dt.tz_localize(IST) if t.dt.tz is None else t.dt.tz_convert(IST)
        s = pd.Series(pd.to_numeric(df[alan], errors="coerce").values, index=pd.DatetimeIndex(t).tz_convert("UTC"), name=ad).sort_index()
        s = s[~s.index.duplicated(keep="last")]
        self._onbellek_yaz(ad, baslangic, bitis, alan, ek, s)
        return s

    # --- önbellek ---
    def _anahtar(self, ad, b, e, alan, ek):
        ekstra = "_".join(f"{k}-{v}" for k, v in sorted(ek.items()))
        return f"{ad}_{alan}_{b}_{e}{('_' + ekstra) if ekstra else ''}.csv"

    def _onbellek_oku(self, ad, b, e, alan, ek):
        if not self.onbellek_dizin:
            return None
        p = Path(self.onbellek_dizin) / self._anahtar(ad, b, e, alan, ek)
        if not p.exists():
            return None
        df = pd.read_csv(p, parse_dates=["zaman"]); s = pd.Series(df["deger"].values, index=pd.DatetimeIndex(df["zaman"]).tz_convert("UTC"), name=ad)
        return s

    def _onbellek_yaz(self, ad, b, e, alan, ek, s: pd.Series):
        if not self.onbellek_dizin or s.empty:
            return
        # yalnız bitmiş günler önbelleğe (bugün değişebilir)
        if pd.Timestamp(e, tz=IST) >= pd.Timestamp.now(tz=IST).normalize():
            return
        Path(self.onbellek_dizin).mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"zaman": s.index, "deger": s.values}).to_csv(Path(self.onbellek_dizin) / self._anahtar(ad, b, e, alan, ek), index=False)

    # --- kısayollar ---
    def ptf(self, b, e): return self.seri("ptf", b, e)
    def smf(self, b, e): return self.seri("smf", b, e)
    def sistem_yonu(self, b, e) -> pd.Series:
        """Sistem yönü: EPİAŞ metni → 'acik' | 'fazla' | 'dengede' (bilinmeyen → None). Index UTC saatlik."""
        from pvquant.ext.turkiye.kurallar import yon_normalize
        satirlar = self.ham("sistem_yonu", b, e)
        if not satirlar:
            return pd.Series(dtype=object, name="sistem_yonu")
        df = pd.DataFrame(satirlar)
        zaman_kolon = next((c for c in ("date", "time", "hour", "datetime") if c in df), None)
        alan = next((c for c in ("systemDirection", "direction", "systemDirectionName", "yon") if c in df), None)
        if zaman_kolon is None or alan is None:
            raise ValueError(f"sistem yönü kolonu bulunamadı: {list(df.columns)[:8]}")
        t = pd.to_datetime(df[zaman_kolon], utc=False)
        t = t.dt.tz_localize(IST) if t.dt.tz is None else t.dt.tz_convert(IST)
        s = pd.Series([yon_normalize(v) for v in df[alan]], index=pd.DatetimeIndex(t).tz_convert("UTC"), name="sistem_yonu", dtype=object).sort_index()
        return s[~s.index.duplicated(keep="last")]
    def kgup(self, b, e, **ek): return self.seri("kgup", b, e, **ek)
    def santral_listesi(self) -> list[dict]:
        """29.10 (v2.505): Şeffaflık santral listesi (GET; id, name, eic, shortName) — EPİAŞ santral kimliği eşlemesi için."""
        return self.ham("santral_listesi", "1970-01-01", "1970-01-01")

    # 31.10 (v2.510, 04 #11): şemaya uygun gövdeler — canlı sınama bekliyor (bulgular/11.md §11.1-A)
    def organizasyon_listesi(self, baslangic: str, bitis: str) -> list[dict]:
        """POST organization-list {startDate, endDate} → [{organizationId, organizationName, ...}]; uevcb_listesi için organizationId kaynağı."""
        return self.ham("organizasyon_listesi", baslangic, bitis)

    def uevcb_listesi(self, organizasyon_id: int, baslangic: str) -> list[dict]:
        """POST uevcb-list {organizationId, startDate} (endDate şemada yok) → [{id, eic, name}]."""
        return self.ham("uevcb_listesi", baslangic, baslangic, organizationId=int(organizasyon_id))

    def uevcb_santraldan(self, santral_id: int, baslangic: str) -> list[dict]:
        """POST uevcb-list-by-power-plant-id {powerPlantId, startDate}; powerplant-list (GET) id'sinden UEVÇB'ye geçiş."""
        return self.ham("uevcb_santraldan", baslangic, baslangic, powerPlantId=int(santral_id))
    def gercek_zamanli_uretim(self, b, e, **ek): return self.seri("gercek_zamanli_uretim", b, e, **ek)

    def fiyat_paketi(self, b, e) -> pd.DataFrame:
        """Dengesizlik simülatörünün istediği üçlü: ptf, smf, yön (UTC saatlik)."""
        return pd.DataFrame({"ptf": self.ptf(b, e), "smf": self.smf(b, e), "yon": self.sistem_yonu(b, e)})


def gerceklesen_adaptoru(uretim_mwh: pd.Series, kurulu_guc_mw: float | None = None) -> pd.DataFrame:
    """EPİAŞ gerçek zamanlı üretimi SCADA sözleşmesine çevirir: index UTC saat başı, kolon 'uretim_mwh' + 'kaynak'.
    Tavanı aşan/negatif değerler bayraklanır (silinmez)."""
    df = pd.DataFrame({"uretim_mwh": uretim_mwh.astype(float)})
    df["kaynak"] = "epias_realtime"
    df["bayrak"] = ""
    df.loc[df["uretim_mwh"] < 0, "bayrak"] = "negatif"
    if kurulu_guc_mw:
        df.loc[df["uretim_mwh"] > kurulu_guc_mw * 1.05, "bayrak"] = "tavan_asimi"
    return df


def sahte_tasiyici(yanitlar: dict[str, list[dict]], tgt: str = "TGT-TEST") -> httpx.MockTransport:
    """Ağsız test: yol → items listesi."""
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/cas/v1/tickets"):
            return httpx.Response(201, text=tgt)
        for yol, items in yanitlar.items():
            if req.url.path.endswith(yol):
                return httpx.Response(200, json={"items": items})
        return httpx.Response(404, json={"items": []})
    return httpx.MockTransport(handler)
