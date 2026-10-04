import { Rozet, type RozetGrubu, type RozetIkonu } from "./Rozet";

/** "Hangi iş için?" ızgarası (R31 + rakip analizi Ö8): dört masa, Aurora'nın fayda kalıbında —
 *  üst etiket (masa adı) → h3 (İŞ SONUCU) → tek fayda cümlesi → etiket–değer künyesi.
 *  Jargon (D-1, TPYS, kantil) künyeye ve bağlantılı sayfaya indi; her değer sitede zaten
 *  yazılı ürün gerçeği (Amperon'un etiket–değer BİÇİMİ alındı, kaynaksız rakamları alınmadı).
 *  Ticaret masası dördüncü kart: kitle listesi artık TEK (TL bölümündeki pencere kartları
 *  işlev gösterimidir, kitle listesi değil). Rakam vaadi ve müşteri iması yok. */
const ISLER: readonly {
  masa: string; sonuc: string; fayda: string;
  kunye: readonly (readonly [string, string])[];
  bag: readonly [string, string];
  grup: RozetGrubu; ikon: RozetIkonu;
}[] = [
  {
    masa: "Program teslimi",
    sonuc: "Programı teslim penceresi kapanmadan verin",
    fayda: "Program dosyanız TPYS'ye öneri CSV, toplayıcıya CSV/XLSX olarak panelden iner; gün içi revizyon penceresi izlenir.",
    kunye: [["Dosya", "D‑1 öğleden sonra"], ["Dilim", "saatlik ya da 15 dk"]],
    bag: ["#para", "Panelde nasıl görünür"],
    grup: "tahmin", ikon: "band",
  },
  {
    masa: "Ticaret masası",
    sonuc: "Teklifi önerilen kantille verin",
    fayda: "Gün öncesi teklif için önerilen kantil panelde; sapmanın TL karşılığı gün gün.",
    kunye: [["Teklif", "önerilen kantil"], ["Sapma", "TL · gün gün"]],
    bag: ["#para", "Sapmanın TL hesabı"],
    grup: "tahmin", ikon: "aylik",
  },
  {
    masa: "Operasyon nöbeti",
    sonuc: "Nöbeti kurallar tutsun, sabah karne hazır olsun",
    fayda: "Alarm kütüphanesi veri, teslim ve performans nöbetini tutar; gece karnesi her sabah hazırdır.",
    kunye: [["Alarm kuralı", "8"], ["Akış", "REST API · sabah webhook'u"]],
    bag: ["#karne", "Gece karnesine bakın"],
    grup: "operasyon", ikon: "alarm",
  },
  {
    masa: "Finansman dosyası",
    sonuc: "Beklentiyi bileşenleriyle raporlayın",
    fayda: "P50/P90 üretim beklentisi bileşenlerine ayrılmış belirsizlik bütçesiyle hesaplanır — dosya bağımsız doğrulamaya hazır biçimde.",
    kunye: [["Beklenti", "P50/P90"], ["Ölçüt", "IEC 61724 · ASTM E2848"]],
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
          <p className="vt-giris">Aynı tahmin hattı dört masaya dört ayrı dille hizmet eder. Dördü de bugün panelde.</p>
        </div>
        <div className="vt-izgara vt-izgara--4 vt-isler">
          {ISLER.map((is) => (
            <article key={is.masa} className="vt-kart vt-is">
              <div className="vt-kart__govde">
                <div className="vt-is__ust">
                  <Rozet grup={is.grup} ikon={is.ikon} />
                  <span className="vt-is__masa">{is.masa}</span>
                </div>
                <h3 className="vt-h3">{is.sonuc}</h3>
                <p className="vt-kart__metin">{is.fayda}</p>
                <dl className="vt-is__kunye">
                  {is.kunye.map(([et, deger]) => (
                    <div key={et} className="vt-is__satir"><dt>{et}</dt><dd>{deger}</dd></div>
                  ))}
                </dl>
                <a className="vt-bag vt-is__bag" href={is.bag[0]}>{is.bag[1]}</a>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
