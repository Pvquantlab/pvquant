import { GunesLogo } from "./GunesLogo";
import { Rozet } from "./Rozet";
import altUfuk from "./varlik/alt-ufuk.svg";

const SAYFA = [
  ["Nasıl çalışır", "#katmanlar"],
  ["Türkiye piyasası", "#para"],
  ["SSS", "#sss"],
  ["Başvuru", "#basla"],
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

/** Altbilgi (v2.384, V1 geniş site haritası — yalnız bugün var olan yüzeyler, R18).
 *  onPanel yoksa (/yontem) "Panele giriş" çıkmaz, çapalar ana sayfaya (/#…) gider. */
export function Altbilgi({ onPanel }: { onPanel?: () => void }) {
  const on = onPanel ? "" : "/";
  return (
    <footer className="vt-alt">
      <div className="vt-kap">
        <div className="vt-alt__izgara">
          <div>
            <a className="vt-logo" href="/"><GunesLogo />PVQuant</a>
            <p className="vt-alt__tanim">Güneş santralları için saatlik üretim tahmini — fizikten başlar, geçmişinizden öğrenir, her gece kendini sınar.</p>
          </div>
          <nav aria-label="Sayfa">
            <h2 className="vt-alt__baslik"><Rozet grup="notr" ikon="gunes" />Sayfa</h2>
            <ul className="vt-alt__liste vt-alt__liste--bag">
              {SAYFA.map(([ad, hedef]) => <li key={ad}><a href={on + hedef}>{ad}</a></li>)}
              {onPanel && <li><button type="button" onClick={onPanel}>Panele giriş</button></li>}
            </ul>
          </nav>
          <nav aria-label="Doğruluk">
            <h2 className="vt-alt__baslik"><Rozet grup="kanit" ikon="karne" />Doğruluk</h2>
            <ul className="vt-alt__liste vt-alt__liste--bag">
              {DOGRULUK.map(([ad, hedef]) => (
                <li key={ad}><a href={hedef.startsWith("#") ? on + hedef : hedef}>{ad}</a></li>
              ))}
            </ul>
          </nav>
          <div id="ilkeler">
            <h2 className="vt-alt__baslik"><Rozet grup="veri" ikon="yukleme" />İlkeler</h2>
            <ul className="vt-alt__liste">
              {ILKELER.map((ilke) => <li key={ilke} className="vt-alt__ilke">{ilke}</li>)}
            </ul>
          </div>
        </div>
        <p className="vt-alt__son vt-kunye">© PVQuant 2026</p>
      </div>
      <div className="vt-alt__ufuk" aria-hidden="true"><img src={altUfuk} alt="" width="1440" height="72" loading="lazy" decoding="async" /></div>
    </footer>
  );
}
