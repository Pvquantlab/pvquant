/** Panel durum dili (v2.415, Hat B1) — yükleme / boş / hata TEK kalıptan gelir.
 *  Kaynak karar: skill bilesen-dili.md «Durum matrisi» (satır içi stilli ad-hoc
 *  «Yükleniyor…» div'leri yasak; bekçi: test/panel/durum.test.ts). Dürüstlük:
 *  iskelet yalnız NÖTR kutudur — sahte eğri/sahte sayı çizilmez (anti-slop §Veri 5);
 *  boş durum nedenini ve ne zaman dolacağını söyler; hata durumu gerçek bir
 *  «Yeniden dene» eylemi taşır. */

/** Sayfa/kart yüklenirken. `iskelet` ile KPI+kart yer tutucuları (nötr kutular). */
export function Yukleniyor({ iskelet = false }: { iskelet?: boolean }) {
  return (
    <div className="durum" role="status">
      <span className="durum-notu"><span className="durum-doner" aria-hidden="true" />Yükleniyor…</span>
      {iskelet && (
        <div className="iskelet-dizi" aria-hidden="true">
          <div className="iskelet-kpiler"><span className="iskelet" /><span className="iskelet" /><span className="iskelet" /></div>
          <div className="iskelet iskelet--kart" />
        </div>
      )}
    </div>
  );
}

/** Veri henüz yokken: ne olduğu + neden/ne zaman dolacağı; isteğe bağlı eylem. */
export function BosDurum({ baslik, aciklama, eylem }: {
  baslik: string; aciklama?: string; eylem?: React.ReactNode;
}) {
  return (
    <div className="durum durum--bos">
      <p className="durum-baslik">{baslik}</p>
      {aciklama && <p className="durum-aciklama">{aciklama}</p>}
      {eylem}
    </div>
  );
}

/** Veri alınamadığında: dürüst mesaj + gerçek yeniden deneme. */
export function HataDurumu({ mesaj, tekrar }: { mesaj: string; tekrar: () => void }) {
  return (
    <div className="durum durum--hata" role="alert">
      <p className="durum-baslik">{mesaj}</p>
      <button type="button" className="dugme" onClick={tekrar}>Yeniden dene</button>
    </div>
  );
}
