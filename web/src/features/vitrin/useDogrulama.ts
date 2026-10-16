import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { Dogrulama } from "../../api/types";
import { dogrulamaDurumu, type DogrulamaDurumu } from "./dogrulamaDurumu";

declare global {
  interface Window {
    /** index.html'deki erken istek (vite.config «pvq-vitrin-kabugu», yalnız aynı köken derlemesi). */
    __pvqDogr?: Promise<Dogrulama | null>;
    /** Erken isteğin sonucu; yanıt gelene dek tanımsız, hata/!ok'ta null. */
    __pvqDogrSonuc?: Dogrulama | null;
  }
}

/** Erken istek sayfa başına BİR kez kullanılır: vitrin sonradan yeniden takılırsa (giriş → çıkış) taze okunur. */
let erkenKullanildi = false;

/** /v1/dogrulama'yı bir kez okur (v2.384). Yeniden deneme yok; sayfa yenilenince yeniden denenir.
 *  16.10 hız turu 4: istek HTML'le birlikte başlar (window.__pvqDogr); yanıt React'in ilk çiziminden önce
 *  geldiyse durum ilk çizimde hazırdır — iskelet → içerik ikinci tam çizimi ve çapa yeniden kaydırması olmaz. */
export function useDogrulama(): DogrulamaDurumu {
  const [durum, setDurum] = useState<DogrulamaDurumu>(() =>
    !erkenKullanildi && window.__pvqDogrSonuc !== undefined ? dogrulamaDurumu(window.__pvqDogrSonuc) : { tur: "yukleniyor" });
  useEffect(() => {
    const ilk = !erkenKullanildi;
    erkenKullanildi = true;
    const sonuc = ilk ? window.__pvqDogrSonuc : undefined;
    // ilk çizimde okunduysa aynı durum döner (React yeniden çizmez); yanıt çizimle efekt ARASINDA geldiyse şimdi işlenir
    if (sonuc !== undefined) { setDurum((d) => (d.tur === "yukleniyor" ? dogrulamaDurumu(sonuc) : d)); return; }
    let canli = true;
    ((ilk ? window.__pvqDogr : undefined) ?? api.dogrulama())
      .then((yanit) => { if (canli) setDurum(dogrulamaDurumu(yanit)); })
      .catch(() => { if (canli) setDurum({ tur: "hata" }); });
    return () => { canli = false; };
  }, []);
  return durum;
}
