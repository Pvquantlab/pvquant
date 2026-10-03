import { Rozet, type RozetGrubu, type RozetIkonu } from "./Rozet";
import levhaFizik from "./varlik/levha-fizik.svg";
import levhaOgrenen from "./varlik/levha-ogrenen.svg";
import levhaAralik from "./varlik/levha-aralik.svg";
import levhaKarne from "./varlik/levha-karne.svg";

/** Dört adım (v2.386, cila-a): V1 kartları yeni levha illüstrasyonlarıyla (grenli, tek ışık yönü;
 *  <img> — kimlik yalıtımı). Kart eylemlidir (vt-kart--bag: hover'da kalkar, R21); "Panelde: …"
 *  rozetli satırı panel girişini açar (R18: var olmayan alt sayfaya bağlantı verilmez).
 *  Cümleler v2.383 vitrinindeki KATMANLAR'dan aynen. */
const ADIM: readonly {
  no: string; baslik: string; cumle: string; etiket: string;
  levha: string; grup: RozetGrubu; ikon: RozetIkonu;
}[] = [
  { no: "01 / 04", baslik: "Fizik modeli", cumle: "Santralın geometrisinden yola çıkar — panel eğimi, tavan, kayıplar.", etiket: "Panelde: Kalibrasyon", levha: levhaFizik, grup: "kanit", ikon: "kalibrasyon" },
  { no: "02 / 04", baslik: "Öğrenen model", cumle: "Fiziğin gözden kaçırdığını santralın kendi geçmişinden öğrenir.", etiket: "Panelde: Kalibrasyon", levha: levhaOgrenen, grup: "kanit", ikon: "kalibrasyon" },
  { no: "03 / 04", baslik: "Dürüst aralık", cumle: "Tek sayı değil, gerçek hatayla ayarlanmış iyimser–kötümser bandı verir.", etiket: "Panelde: Tahminler", levha: levhaAralik, grup: "tahmin", ikon: "band" },
  { no: "04 / 04", baslik: "Gece karnesi", cumle: "Her gece tahmin gerçekleşenle yüzleşir; kanıt birikir.", etiket: "Panelde: Doğruluk", levha: levhaKarne, grup: "kanit", ikon: "karne" },
];

export function DortAdim({ onPanel }: { onPanel?: () => void }) {
  return (
    <section className="vt-bolum" id="katmanlar" aria-labelledby="vt-adim-baslik" data-canlan="">
      <div className="vt-kap">
        <div className="vt-bolum-bas">
          <h2 className="vt-h2" id="vt-adim-baslik">Tahmin dört adımda doğar — her adımı panelde görünür.</h2>
        </div>
        <div className="vt-izgara vt-izgara--2 vt-adimlar">
          {ADIM.map((a) => (
            <article key={a.no} className={onPanel ? "vt-kart vt-kart--bag vt-adim" : "vt-kart vt-adim"}>
              <div className="vt-levha" aria-hidden="true"><img src={a.levha} alt="" width="420" height="150" loading="lazy" decoding="async" /></div>
              <div className="vt-kart__govde">
                <span className="vt-kart__no">{a.no}</span>
                <h3 className="vt-h3">{a.baslik}</h3>
                <p className="vt-kart__metin">{a.cumle}</p>
                {onPanel ? (
                  <div className="vt-panelde">
                    <Rozet grup={a.grup} ikon={a.ikon} />
                    <button type="button" className="vt-bag" onClick={onPanel}>{a.etiket}</button>
                  </div>
                ) : (
                  <div className="vt-panelde">
                    <Rozet grup={a.grup} ikon={a.ikon} />
                    <span className="vt-panelde__et">{a.etiket}</span>
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
