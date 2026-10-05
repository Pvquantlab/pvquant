import sahneZemin from "./varlik/sahne-zemin.svg";
import vinProgram from "./varlik/vinyet-program.svg";
import vinToplayici from "./varlik/vinyet-toplayici.svg";
import { PncEkranAna, PncEkranIkinci, VinyetTl, VinyetTicaretGenis, VinyetTicaretDar } from "./TextliCizimler";
import vinOperatorGenis from "./varlik/vinyet-operator-genis.svg";
import vinOperatorDar from "./varlik/vinyet-operator-dar.svg";

/** Türkiye piyasası (v2.386, cila-a): solda bölüm başı, sağda SAHNELENMİŞ panel penceresi
 *  (güneş gradyanlı zemin üstünde kırpılmış, üst üste iki pencere; içerik ÇİZİMDİR — {EKRAN}
 *  yuvası gerçek ekran görüntüsüne/canlı bileşene açık, R22). Beş kart kendi veri-türevi
 *  vinyetini taşır; geniş iki masa kartının dar-ekran vinyet çifti vardır. Kartlar eylemsizdir
 *  (kalkmaz, R21). Metinler v2.383'ten aynen; elle yazılmış TL/kurulu güç dipnotu yok. */
type Vinyet = string | (() => React.JSX.Element);
const KARTLAR: readonly (readonly [string, string, Vinyet])[] = [
  ["Program hazır", "Saatlik üretim programı ve emre amadelik, teslim penceresi kapanmadan dosya olarak elinizde — gecikirse alarm çalar.", vinProgram],
  ["Sapmanın TL kartı", "Tahmin hatasının aylık TL karşılığı ve basit yönteme göre kurtarılan tutar panelde gün gün birikir; teminat etkisiyle birlikte.", VinyetTl],
  ["Toplayıcıya tek tık", "Tahmin aralığı toplayıcı/DSG şablonlarında (saatlik ya da 15 dakikalık) dışa verilir; API anahtarıyla sistemden sisteme akar.", vinToplayici],
];

const MASALAR: readonly (readonly [string, string, Vinyet, Vinyet])[] = [
  ["Operatör masası", "Program teslim penceresi, emre amadelik, veri gecikince çalan alarm, aylık bakım penceresine iklim beklentisi.", vinOperatorGenis, vinOperatorDar],
  ["Ticaret masası", "İyimser–kötümser bant, sapmanın gün gün TL karşılığı, gün içi revizyon izi, API ile kendi sisteminize akış.", VinyetTicaretGenis, VinyetTicaretDar],
];

export function TurkiyePiyasasi() {
  return (
    <section className="vt-bolum vt-bolum--bant" id="para" aria-labelledby="vt-para-baslik" data-canlan="">
      <div className="vt-kap">
        <div className="vt-para-ust">
          <div className="vt-bolum-bas">
            <h2 className="vt-h2" id="vt-para-baslik">Tahmin hatasının maliyetini TL olarak görün.</h2>
            <p className="vt-giris">Elektrik piyasasında her santral, ertesi gün ne üreteceğini önceden bildirmekle yükümlüdür; gerçekleşen üretim bu programdan saptığında aradaki fark santrale fatura edilir. PVQuant üretim programınızı hazırlar, gün içi güncelleme fırsatlarını izler ve sapmanın size maliyetini her gün TL olarak raporlar.</p>
          </div>
          <div className="vt-sahne">
            <div className="vt-sahne__zemin" aria-hidden="true"><img src={sahneZemin} alt="" width="700" height="460" loading="lazy" decoding="async" /></div>
            <div className="vt-pnc vt-pnc--ana" role="img" aria-label="Panel penceresi örneği: Sapmanın TL kartı — temsili görünüm, sonuç değil">
              <div className="vt-pnc__serit" aria-hidden="true"><span>panel.pvquant</span></div>
              <div className="vt-pnc__ekran">
                <PncEkranAna />
                <span className="vt-pnc__etiket">temsili görünüm · sonuç değil</span>
              </div>
            </div>
            <div className="vt-pnc vt-pnc--ikinci" aria-hidden="true">
              <div className="vt-pnc__serit"><span>panel.pvquant</span></div>
              <div className="vt-pnc__ekran"><PncEkranIkinci /></div>
            </div>
          </div>
        </div>
        <div className="vt-izgara vt-izgara--3">
          {KARTLAR.map(([baslik, metin, vinyet]) => (
            <article key={baslik} className="vt-kart vt-vin-kart">
              <div className="vt-levha" aria-hidden="true">
                {typeof vinyet === "string" ? <img src={vinyet} alt="" width="384" height="176" loading="lazy" decoding="async" /> : vinyet()}
              </div>
              <div className="vt-kart__govde"><h3 className="vt-h3">{baslik}</h3><p className="vt-kart__metin">{metin}</p></div>
            </article>
          ))}
        </div>
        <div className="vt-izgara vt-izgara--2 vt-masalar">
          {MASALAR.map(([baslik, metin, genis, dar]) => (
            <article key={baslik} className="vt-kart vt-vin-kart">
              <div className="vt-levha" aria-hidden="true">
                {typeof genis === "string" ? <img className="vt-v-genis" src={genis} alt="" width="588" height="176" loading="lazy" decoding="async" /> : genis()}
                {typeof dar === "string" ? <img className="vt-v-dar" src={dar} alt="" width="384" height="176" loading="lazy" decoding="async" /> : dar()}
              </div>
              <div className="vt-kart__govde"><h3 className="vt-h3">{baslik}</h3><p className="vt-kart__metin">{metin}</p></div>
            </article>
          ))}
        </div>
        <p className="vt-not">Sapmanın TL karşılığı panelde, kendi santralinizin verisiyle hesaplanır.</p>
      </div>
    </section>
  );
}
