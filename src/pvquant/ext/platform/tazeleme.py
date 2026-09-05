"""Otomatik tazeleme — dürüst ve ucuz: 'değişti mi?' damgası + koşullu istek + geri çekilmeli yoklama + SSE.

Sunucu tarafı: `DegisimDamgasi` her veri kümesi için (plant, kaynak) son değişim anını ve bir sürüm etiketi (ETag)
tutar; `kosullu_yanit` If-None-Match ile 304 döndürür. İstemci politikası: görünür sekmede 60 s, arka planda 5 dk,
hata sonrası üstel geri çekilme (max 15 dk); yalnız damga değiştiyse veri çekilir.
SSE üreteci: damga değişince olay yayınlar (uzun yoklama yerine). SPA kancası `use_tazeleme_js` string olarak.
Telemetri şeridindeki 'tazelenir' iddiası ancak bu katman canlıyken yazılır (dürüstlük).
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class DegisimDamgasi:
    _kayit: dict[str, tuple[float, str]] = field(default_factory=dict)

    def guncelle(self, anahtar: str, icerik_ozeti: str | bytes | None = None) -> str:
        """Veri değişince çağrılır (worker koşusu bitti, SCADA yüklendi). ETag = sha256(anahtar|zaman|özet)[:16]."""
        t = time.time()
        h = hashlib.sha256(f"{anahtar}|{t}|{icerik_ozeti or ''}".encode()).hexdigest()[:16]
        self._kayit[anahtar] = (t, h)
        return h

    def etag(self, anahtar: str) -> str | None:
        return self._kayit.get(anahtar, (None, None))[1]

    def zaman(self, anahtar: str) -> float | None:
        return self._kayit.get(anahtar, (None, None))[0]

    def degisti_mi(self, anahtar: str, istemci_etag: str | None) -> bool:
        return self.etag(anahtar) != istemci_etag

    def durum(self) -> dict[str, dict]:
        return {k: {"etag": v[1], "zaman": v[0]} for k, v in self._kayit.items()}


def kosullu_yanit(damga: DegisimDamgasi, anahtar: str, istemci_etag: str | None, veri_uret) -> tuple[int, dict, object | None]:
    """(durum_kodu, başlıklar, gövde). 304 → gövde None. veri_uret() yalnız değiştiyse çağrılır."""
    et = damga.etag(anahtar)
    if et is not None and istemci_etag == et:
        return 304, {"ETag": et, "Cache-Control": "no-cache"}, None
    veri = veri_uret()
    if et is None:
        et = damga.guncelle(anahtar, json.dumps(veri, default=str)[:512])
    return 200, {"ETag": et, "Cache-Control": "no-cache"}, veri


@dataclass
class YoklamaPolitikasi:
    gorunur_sn: int = 60
    arka_plan_sn: int = 300
    hata_taban_sn: int = 30
    hata_tavan_sn: int = 900
    ardisik_hata: int = 0

    def sonraki_sn(self, gorunur: bool, hata: bool = False) -> int:
        if hata:
            self.ardisik_hata += 1
            return min(self.hata_taban_sn * (2 ** (self.ardisik_hata - 1)), self.hata_tavan_sn)
        self.ardisik_hata = 0
        return self.gorunur_sn if gorunur else self.arka_plan_sn


def sse_akisi(damga: DegisimDamgasi, anahtarlar: list[str], son_etagler: dict[str, str] | None = None,
              bekleme_sn: float = 2.0, azami_sn: float = 3600.0, uyku=time.sleep) -> Iterator[str]:
    """Server-Sent Events: damga değişince 'event: degisti' yayınlar; 25 s'de bir yorum satırı (bağlantı canlı)."""
    son = dict(son_etagler or {}); baslangic = time.time(); son_kalp = baslangic
    while time.time() - baslangic < azami_sn:
        for a in anahtarlar:
            et = damga.etag(a)
            if et is not None and son.get(a) != et:
                son[a] = et
                yield f"event: degisti\ndata: {json.dumps({'anahtar': a, 'etag': et})}\n\n"
        if time.time() - son_kalp > 25:
            son_kalp = time.time(); yield ": kalp\n\n"
        uyku(bekleme_sn)


USE_TAZELEME_JS = r"""
// useTazeleme — yalnız damga değişince veri çeker; görünürlük ve hata geri çekilmesi politikayla.
import { useEffect, useRef, useState } from "react";
export function useTazeleme(url, { gorunurSn = 60, arkaPlanSn = 300, hataTabanSn = 30, hataTavanSn = 900 } = {}) {
  const [veri, setVeri] = useState(null); const [sonTazeleme, setSonTazeleme] = useState(null);
  const etag = useRef(null); const hata = useRef(0); const zam = useRef(null);
  useEffect(() => {
    let iptal = false;
    const cek = async () => {
      try {
        const r = await fetch(url, { headers: etag.current ? { "If-None-Match": etag.current } : {} });
        if (r.status === 200) { etag.current = r.headers.get("ETag"); setVeri(await r.json()); setSonTazeleme(new Date()); }
        hata.current = 0;
      } catch { hata.current += 1; }
      if (iptal) return;
      const sn = hata.current ? Math.min(hataTabanSn * 2 ** (hata.current - 1), hataTavanSn)
                              : (document.visibilityState === "visible" ? gorunurSn : arkaPlanSn);
      zam.current = setTimeout(cek, sn * 1000);
    };
    cek();
    const gor = () => { if (document.visibilityState === "visible") { clearTimeout(zam.current); cek(); } };
    document.addEventListener("visibilitychange", gor);
    return () => { iptal = true; clearTimeout(zam.current); document.removeEventListener("visibilitychange", gor); };
  }, [url]);
  return { veri, sonTazeleme };
}
"""
