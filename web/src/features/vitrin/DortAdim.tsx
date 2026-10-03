import { AdimCizim } from "./AdimCizim";

/** Dört adım (v2.384, V1 kartları): üstte veri-türevi levha illüstrasyonu, 2×2 ızgara, kartın
 *  "Panelde: …" bağlantısı panel girişini açar (R18: var olmayan alt sayfaya bağlantı verilmez;
 *  panel girişi bugün var olan dürüst hedeftir). Cümleler v2.383 vitrinindeki KATMANLAR'dan aynen. */
const ADIM = [
  ["01", "Fizik modeli", "Santralın geometrisinden yola çıkar — panel eğimi, tavan, kayıplar.", "Panelde: Kalibrasyon"],
  ["02", "Öğrenen model", "Fiziğin gözden kaçırdığını santralın kendi geçmişinden öğrenir.", "Panelde: Kalibrasyon"],
  ["03", "Dürüst aralık", "Tek sayı değil, gerçek hatayla ayarlanmış iyimser–kötümser bandı verir.", "Panelde: Tahminler"],
  ["04", "Gece karnesi", "Her gece tahmin gerçekleşenle yüzleşir; kanıt birikir.", "Panelde: Doğruluk"],
] as const;

export function DortAdim({ onPanel }: { onPanel?: () => void }) {
  return (
    <section className="vt-bolum" id="katmanlar" aria-labelledby="vt-adim-baslik">
      <div className="vt-kap">
        <div className="vt-bolum-bas">
          <h2 className="vt-h2" id="vt-adim-baslik">Tahmin dört adımda doğar — her adımı panelde görünür.</h2>
        </div>
        <div className="vt-izgara vt-izgara--2 vt-adimlar">
          {ADIM.map(([no, baslik, cumle, etiket], i) => (
            <article key={no} className="vt-adim">
              <div className="vt-adim__levha" aria-hidden="true"><AdimCizim no={(i + 1) as 1 | 2 | 3 | 4} /></div>
              <div className="vt-adim__govde">
                <span className="vt-kart__no">{no} / 04</span>
                <h3 className="vt-h3">{baslik}</h3>
                <p className="vt-kart__metin">{cumle}</p>
                {onPanel
                  ? <button type="button" className="vt-bag vt-adim__bag" onClick={onPanel}>{etiket}</button>
                  : <span className="vt-kart__etiket">{etiket}</span>}
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
