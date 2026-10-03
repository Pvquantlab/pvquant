import { useEffect } from "react";
import "./fontlar";
import "./vitrin.css";
import { UstCubuk } from "./UstCubuk";
import { Altbilgi } from "./Altbilgi";
import { useDogrulama } from "./useDogrulama";
import { useCapaKaydir } from "./useCapaKaydir";
import { ADIMLAR, METRIKLER } from "./yontem-metni";
import { yuzdeTr } from "./bicim";

/** /yontem — yöntem ve doğrulama alt sayfası (v2.333; v2.384'te Yön A diline geçti).
 *  Dürüstlük kuralları burada da geçerli: sayı vaat edilmez; canlı değer yalnız kamuya açık
 *  /v1/dogrulama ucundan gelir, uç kapalıysa satır çizilmez. Metinler yontem-metni.ts'ten. */
export function Yontem() {
  const durum = useDogrulama();
  useCapaKaydir(durum.tur);
  useEffect(() => {
    const eski = document.title;
    document.title = "PVQuant — Yöntem ve doğrulama";
    return () => { document.title = eski; };
  }, []);
  const dg = durum.tur === "acik" ? durum.veri : null;
  return (
    <div className="vt vt--a">
      <a className="vt-atla" href="#icerik">İçeriğe geç</a>
      <UstCubuk kip="yontem" />
      <main id="icerik">
        <section className="vt-yontem-giris">
          <div className="vt-kap vt-dar">
            <h1 className="vt-h1">Sayıların arkasındaki yöntem.</h1>
            <p className="vt-giris">Vitrindeki ve paneldeki her doğruluk değeri aynı gece sürecinden çıkar. Bu sayfa o süreci, metrik tanımlarını ve sonuçların nasıl denetlenebileceğini açıklar — beyan değil, tarif.</p>
          </div>
        </section>

        <section className="vt-bolum vt-bolum--bant" aria-labelledby="yt-adimlar">
          <div className="vt-kap vt-dar">
            <h2 className="vt-h2 vt-bolum-bas" id="yt-adimlar">Karne nasıl oluşur</h2>
            <div className="vt-izgara vt-izgara--2">
              {ADIMLAR.map(([baslik, metin], i) => (
                <article key={baslik} className="vt-kart">
                  <span className="vt-kart__no">{String(i + 1).padStart(2, "0")}</span>
                  <h3 className="vt-h3">{baslik}</h3>
                  <p className="vt-kart__metin">{metin}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="vt-bolum" aria-labelledby="yt-tanimlar">
          <div className="vt-kap vt-dar">
            <h2 className="vt-h2 vt-bolum-bas" id="yt-tanimlar">Metrikler ne ölçer</h2>
            <dl className="vt-tanimlar">
              {METRIKLER.map(([ad, tanim]) => (
                <div key={ad} className="vt-tanim"><dt>{ad}</dt><dd>{tanim}</dd></div>
              ))}
            </dl>
          </div>
        </section>

        <section className="vt-bolum vt-bolum--gece" aria-labelledby="yt-disiplin">
          <div className="vt-kap vt-dar">
            <h2 className="vt-h2 vt-bolum-bas" id="yt-disiplin">Aralık ve yayın disiplini</h2>
            <div className="vt-izgara">
              <div className="vt-gece-kart">
                <h3 className="vt-h3">Aralık gerçek hatayla ayarlanır</h3>
                <p>İyimser–kötümser bandın genişliği varsayımla değil, santralın geçmiş sınav sonuçlarıyla kalibre edilir ve tahmin ufkuna göre değişir: yarın için dar, üç gün sonrası için daha geniştir. Kapsama hedeften saparsa bant otomatik olarak daraltılır ya da genişletilir.</p>
              </div>
              <div className="vt-gece-kart">
                <h3 className="vt-h3">Yetersiz veriyle karne yayımlanmaz</h3>
                <p>Kamuya açık karne, en az 30 günlük gece sınavı birikmeden yayımlanmaz; doğruluk değerleri kaç günlük pencereden hesaplandıysa o pencere karnenin üzerinde yazar. Ölçüm olmayan dönem için değer üretilmez — eksik veri tire ile gösterilir.</p>
              </div>
              <div className="vt-gece-kart">
                <h3 className="vt-h3">Denetlenebilirlik</h3>
                <p>Vitrindeki Açık karne elle yazılmış değildir; kimlik doğrulaması gerektirmeyen bir uçtan canlı okunur. Aynı sayıları herkes, herhangi bir anda kendisi çekebilir:</p>
                <code className="vt-kod">GET /v1/dogrulama</code>
                {dg && (
                  <p className="vt-kunye">şu an: {dg.santral_etiketi} · {dg.pencere_gun} sınav günü · ortalama sapma {yuzdeTr(dg.wmape_pct)}</p>
                )}
              </div>
            </div>
            <div className="vt-eylemler vt-ust-bosluk">
              <a className="vt-dugme vt-dugme--gece" href="/#karne">Açık karneyi görün</a>
              <a className="vt-dugme vt-dugme--gece-cizgi" href="/#basla">Kendi karnenizi başlatın</a>
            </div>
          </div>
        </section>
      </main>
      <Altbilgi />
    </div>
  );
}
