import { GunesLogo } from "./GunesLogo";

const SAYFA = [
  ["Nasıl çalışır", "#katmanlar"],
  ["Türkiye piyasası", "/yontem#para"],
  ["SSS", "#sss"],
  ["Karnenizi başlatın", "#basla"],
] as const;

const DOGRULUK = [
  ["Açık karne", "#karne"],
  ["Yöntem ve doğrulama", "/yontem"],
  ["Metrik sözlüğü", "/yontem#yt-tanimlar"],
  ["Aralık ve yayın disiplini", "/yontem#yt-disiplin"],
] as const;

const ILKELER = [
  "Veriniz sizindir — dilediğiniz an dışa aktarır ya da silersiniz",
  "Geçmiş sonuç değiştirilmez; yenisi eklenir",
  "Kurumlar arası paylaşım yalnız sizin izninizle açılır ve denetim iziyle kayda geçer",
  "Hava tahmini bir aya uzatılmaz — aylık beklenti iklim geçmişinden gelir",
  "Vitrin vaat etmez; karne panelde canlıdır",
] as const;

/** Altbilgi (v2.384, V1 geniş site haritası — yalnız bugün var olan yüzeyler, R18). 13.10 jua kalıbı: ikonsuz büyük harf
 *  sütun başlıkları, sloganın son cümlesi italik gradyan vurgu (jua «for energy.»), telif/atıf satırı kullanıcı kararıyla yok.
 *  onPanel yoksa (/yontem) "Panele giriş" çıkmaz, çapalar ana sayfaya (/#…) gider. */
export function Altbilgi({ onPanel }: { onPanel?: () => void }) {
  const on = onPanel ? "" : "/";
  return (
    <footer className="vt-alt">
      <div className="vt-kap">
        <div className="vt-alt__izgara">
          <div>
            <a className="vt-logo" href="/"><GunesLogo />PVQuant</a>
            <p className="vt-alt__tanim">Saatlik üretim tahmini, <span className="vt-alt__vurgu">her gece sınanır.</span></p>
            <p className="vt-alt__alt">Güneş santralleri için. Santralinizin yapısından başlar, geçmiş üretiminizden öğrenir.</p>
          </div>
          <nav aria-label="Sayfa">
            <h2 className="vt-alt__baslik">Sayfa</h2>
            <ul className="vt-alt__liste vt-alt__liste--bag">
              {SAYFA.map(([ad, hedef]) => <li key={ad}><a href={hedef.startsWith("#") ? on + hedef : hedef}>{ad}</a></li>)}
              {onPanel && <li><button type="button" onClick={onPanel}>Panele giriş</button></li>}
            </ul>
          </nav>
          <nav aria-label="Doğruluk">
            <h2 className="vt-alt__baslik">Doğruluk</h2>
            <ul className="vt-alt__liste vt-alt__liste--bag">
              {DOGRULUK.map(([ad, hedef]) => (
                <li key={ad}><a href={hedef.startsWith("#") ? on + hedef : hedef}>{ad}</a></li>
              ))}
            </ul>
          </nav>
          <div id="ilkeler">
            <h2 className="vt-alt__baslik">İlkeler</h2>
            <ul className="vt-alt__liste">
              {ILKELER.map((ilke) => <li key={ilke} className="vt-alt__ilke">{ilke}</li>)}
            </ul>
          </div>
        </div>
      </div>
    </footer>
  );
}
