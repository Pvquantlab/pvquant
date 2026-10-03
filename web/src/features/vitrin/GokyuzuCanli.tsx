import { useEffect, useState } from "react";
import { gokDurumu, sureMetni } from "./gunesSaati";

/** Hero kartuşunun canlı satırı (R26): ziyaretçinin gerçek saatinde İç Anadolu göğü —
 *  gündüz: güneş yüksekliği + batışa kalan; gece: ufkun altında + doğuşa kalan ve gece
 *  sınavı notu (gece koşusu gerçekten bu aralıkta koşar). Dakikada bir tazelenir.
 *  Künye R26 gereği "astronomik hesap" der; ölçüm/tahmin iması yok. İlk değer ilk
 *  render'da hesaplanır ki satır sonradan belirip yerleşimi oynatmasın (CLS bulgusu). */
export function GokyuzuCanli() {
  const [gok, setGok] = useState(() => gokDurumu(new Date()));
  useEffect(() => {
    const sayac = window.setInterval(() => setGok(gokDurumu(new Date())), 60_000);
    return () => window.clearInterval(sayac);
  }, []);
  return (
    <span className="vt-gok-canli">
      {"astronomik hesap · şu an: "}
      {gok.gunduz
        ? `güneş yüksekliği ${Math.max(0, Math.round(gok.yukseklikDeg))}° · batışa ${sureMetni(gok.kalanDk)}`
        : `güneş ufkun altında · doğuşa ${sureMetni(gok.kalanDk)} — gece sınavı bu aralıkta koşar`}
    </span>
  );
}
