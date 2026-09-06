import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { Damga } from "../api/types";

/** v2.265 (Dalga 5.17) — otomatik tazeleme, dürüst ve ucuz: sunucudaki değişim damgasını yoklar
 *  (görünür sekmede 60 s, arka planda 5 dk; hata sonrası üstel geri çekilme, tavan 15 dk), yalnız ETag
 *  değişince `surum` artar — sayfalar bunu bağımlılık olarak alıp veriyi yeniden çeker.
 *  `sonYoklama` ancak yoklama gerçekten başarılıysa dolar: telemetri şeridi 'tazelendi' iddiasını buna bağlar. */
export function useDamga(plantId: string | undefined, { gorunurSn = 60, arkaPlanSn = 300, hataTabanSn = 30, hataTavanSn = 900 } = {}) {
  const [surum, setSurum] = useState(0);
  const [damga, setDamga] = useState<Damga | null>(null);
  const [sonYoklama, setSonYoklama] = useState<Date | null>(null);
  const etag = useRef<string | null>(null); const hata = useRef(0); const zam = useRef<number | null>(null);
  useEffect(() => {
    if (!plantId) return;
    let iptal = false; etag.current = null; hata.current = 0;
    const cek = async () => {
      try {
        const r = await api.damga(plantId, etag.current);
        if (iptal) return;
        if (r.degisti) { const ilk = etag.current === null; etag.current = r.etag; setDamga(r.veri); if (!ilk) setSurum((s) => s + 1); }
        hata.current = 0; setSonYoklama(new Date());
      } catch { hata.current += 1; }
      if (iptal) return;
      const sn = hata.current ? Math.min(hataTabanSn * 2 ** (hata.current - 1), hataTavanSn)
                              : (document.visibilityState === "visible" ? gorunurSn : arkaPlanSn);
      zam.current = window.setTimeout(cek, sn * 1000);
    };
    cek();
    const gor = () => { if (document.visibilityState === "visible" && !iptal) { if (zam.current) clearTimeout(zam.current); cek(); } };
    document.addEventListener("visibilitychange", gor);
    return () => { iptal = true; if (zam.current) clearTimeout(zam.current); document.removeEventListener("visibilitychange", gor); };
  }, [plantId, gorunurSn, arkaPlanSn, hataTabanSn, hataTavanSn]);
  return { surum, damga, sonYoklama };
}
