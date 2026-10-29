import { Rozet, type RozetGrubu, type RozetIkonu } from "./Rozet";
import isTeslim from "./varlik/is-teslim.png";
import isTicaret from "./varlik/is-ticaret.png";
import isNobet from "./varlik/is-nobet.png";
import isFinansman from "./varlik/is-finansman.png";
import { Levha } from "./Levha";

/** "Hangi iş için?" ızgarası (R31 + rakip analizi Ö8): dört masa, Aurora'nın fayda kalıbında —
 *  üst etiket (masa adı) → h3 (İŞ SONUCU) → tek fayda cümlesi → etiket–değer künyesi.
 *  Jargon (D-1, TPYS, kantil) künyeye ve bağlantılı sayfaya indi; her değer sitede zaten
 *  yazılı ürün gerçeği (Amperon'un etiket–değer BİÇİMİ alındı, kaynaksız rakamları alınmadı).
 *  Ticaret masası dördüncü kart: kitle listesi artık TEK (TL bölümündeki pencere kartları
 *  işlev gösterimidir, kitle listesi değil). Rakam vaadi ve müşteri iması yok. */
/** resim: Storyset levhası (12.10) — kullanıcının masaüstünden bayt bayt; ölçek dengesi CSS sınıfında. */
const ISLER: readonly {
  masa: string; sonuc: string; fayda: string;
  kunye: readonly (readonly [string, string])[];
  bag: readonly [string, string];
  grup: RozetGrubu; ikon: RozetIkonu; resim: string;
}[] = [
  {
    masa: "Program teslimi",
    sonuc: "Üretim programınız (KGÜP) zamanında hazır olsun",
    fayda: "Yarının saatlik programı ve emre amade kapasite panelden dosya olarak iner (CSV/XLSX); teslim penceresi ve gün içi düzeltme fırsatları izlenir.",
    kunye: [["Hazır", "bir gün önce, öğleden sonra"], ["Çözünürlük", "saatlik (15 dk veri hazır)"]],
    bag: ["/yontem#para", "Panelde nasıl görünür"],
    grup: "tahmin", ikon: "band", resim: isTeslim,
  },
  {
    masa: "Ticaret masası",
    sonuc: "Gün öncesi teklifinizi doğru seviyeden verin",
    fayda: "Teklif seviyenizi iyimser–kötümser aralıktan seçersiniz; gerçekleşme ile farkı her sabah görürsünüz. Uzlaştırma kalemleri (dengesizlik tutarı ve KGÜP sapması) yürürlükteki kuralla, fiyat kaynağı etiketiyle panelde.",
    kunye: [["Teklif", "önerilen seviye (gerçek fiyat akışıyla)"], ["Uzlaştırma", "EDT ve KÜPST ayrı, kural etiketli"]],
    bag: ["/yontem#para", "Uzlaştırma kalemlerinin hesabı"],
    grup: "tahmin", ikon: "aylik", resim: isTicaret,
  },
  {
    masa: "Operasyon nöbeti",
    sonuc: "Geceyi kurallar beklesin, sabah karne hazır olsun",
    fayda: "Veri kesildi mi, tahmin isabeti düştü mü: iki kural varsayılan izler; santralinize göre ek kurallar (program hazırlığı, performans, kullanılabilirlik) açılır; sabah karne hazırdır.",
    kunye: [["Alarm kuralı", "2 varsayılan + seçilebilir"], ["Bildirim", "API, her sabah otomatik"]],
    bag: ["#karne", "Gece karnesine bakın"],
    grup: "operasyon", ikon: "alarm", resim: isNobet,
  },
  {
    masa: "Finansman dosyası",
    sonuc: "Yatırımcıya ve bankaya üretim beklentisini raporlayın",
    fayda: "Beklenen (P50) ve güvenli (P90) üretim, belirsizliğin nereden geldiği kalem kalem gösterilerek hesaplanır; dosya denetlenebilir kaynak künyesi taşır.",
    kunye: [["Beklenti", "P50/P90"], ["Ölçüt", "IEC 61724, ASTM E2848"]],
    bag: ["/yontem", "Yöntemin tamamı"],
    grup: "kanit", ikon: "rapor", resim: isFinansman,
  },
];

export function IsIzgarasi() {
  return (
    <section className="vt-bolum" id="isler" aria-labelledby="vt-isler-baslik" data-canlan="">
      <div className="vt-kap">
        <div className="vt-bolum-bas">
          <p className="vt-eyebrow">Kimin için</p>
          <h2 className="vt-h2" id="vt-isler-baslik">Dört iş birimi, tek tahmin altyapısı.</h2>
          <p className="vt-giris">Program teslimi, ticaret masası, operasyon ve finansman aynı tahminden beslenir. Dördü de bugün panelde.</p>
        </div>
        <div className="vt-izgara vt-izgara--4 vt-isler">
          {ISLER.map((is, i) => (
            <article key={is.masa} className="vt-kart vt-is">
              <div className={`vt-levha vt-levha--resim vt-is__levha vt-is__levha--${i + 1}`} aria-hidden="true"><Levha src={is.resim} alt="" width="2000" height="2000" loading="lazy" decoding="async" /></div>
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
