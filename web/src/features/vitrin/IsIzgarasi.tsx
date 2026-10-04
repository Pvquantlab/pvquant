import { Rozet, type RozetGrubu, type RozetIkonu } from "./Rozet";

/** "Hangi iş için?" ızgarası (R31): Solargis'in use-case ızgarasının dürüst karşılığı —
 *  üç İŞ, üçü de panelde bugün var olan yetilerle anlatılır. İnceleme sonrası sözler kapsama
 *  kırpıldı: TPYS dosyası "öneri CSV"dir (resmî şablon teyitsiz), 15 dk dilimli CSV/XLSX
 *  toplayıcı çıktısıdır; dış API bugün tahmini okur, webhook sabah koşusunu haber verir;
 *  belirsizlik bütçesi bileşen sayısı santrala göre değişir (kalibre değilse bazıları 0).
 *  Müşteri/proje sayısı, rakamlı kazanç vaadi yok; bağlantılar kanıta ya da yönteme gider. */
const ISLER: readonly {
  baslik: string; metin: string; bag: [string, string];
  grup: RozetGrubu; ikon: RozetIkonu;
}[] = [
  {
    baslik: "Program teslimi",
    metin: "Program yükümlüsü üretici için: D-1 öğleden sonra program dosyası hazırdır — TPYS'ye öneri CSV, toplayıcıya 15 dakikalık dilimli CSV/XLSX, teklif kantili önerisi ve revizyon kuralları bir arada.",
    bag: ["#para", "Sapmanın TL hesabı"],
    grup: "tahmin", ikon: "band",
  },
  {
    baslik: "Operasyon nöbeti",
    metin: "Saha ve portföy ekibi için: sekiz kurallık alarm kütüphanesi veri, teslim ve performans nöbeti tutar; gece karnesi her sabah hazırdır — tahmin REST API ile çekilir, sabah koşusu webhook ile haber verir.",
    bag: ["#karne", "Gece karnesine bakın"],
    grup: "operasyon", ikon: "alarm",
  },
  {
    baslik: "Finansman dosyası",
    metin: "Banka ve yatırımcı masası için: P50/P90 üretim beklentisi bileşenlerine ayrılmış belirsizlik bütçesiyle hesaplanır; performans oranı IEC 61724, kapasite testi ASTM E2848 ölçütleriyle raporlanır — dosya bağımsız doğrulamaya hazır biçimde.",
    bag: ["/yontem", "Yöntemin tamamı"],
    grup: "kanit", ikon: "rapor",
  },
];

export function IsIzgarasi() {
  return (
    <section className="vt-bolum" id="isler" aria-labelledby="vt-isler-baslik" data-canlan="">
      <div className="vt-kap">
        <div className="vt-bolum-bas">
          <h2 className="vt-h2" id="vt-isler-baslik">Hangi iş için?</h2>
          <p className="vt-giris">Aynı tahmin hattı üç masaya üç ayrı dille hizmet eder. Üçü de bugün paneldedir — yol haritası değil.</p>
        </div>
        <div className="vt-izgara vt-izgara--3 vt-isler">
          {ISLER.map((is) => (
            <article key={is.baslik} className="vt-kart vt-is">
              <div className="vt-kart__govde">
                <Rozet grup={is.grup} ikon={is.ikon} />
                <h3 className="vt-h3">{is.baslik}</h3>
                <p className="vt-kart__metin">{is.metin}</p>
                <a className="vt-bag vt-is__bag" href={is.bag[0]}>{is.bag[1]}</a>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
