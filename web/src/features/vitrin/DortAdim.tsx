import { Fragment, type ReactNode } from "react";
import { Rozet, type RozetGrubu, type RozetIkonu } from "./Rozet";
import levhaFizik from "./varlik/levha-fizik.svg";
import levhaOgrenen from "./varlik/levha-ogrenen.svg";
import levhaAralik from "./varlik/levha-aralik.svg";
import levhaKarne from "./varlik/levha-karne.svg";

/** Dört adım (v2.386 cila-a + rakip analizi Ö9/Ö11): V1 kartları levha illüstrasyonlarıyla.
 *  Ö11: ≥1241'de dört kart TEK SIRA numaralı zincirdir (oklar grid hücresi — ::after kartın overflow'una kırpılıyordu);
 *  modele geri dönen ok BİLEREK çizilmez (yeniden eğitim sıklığı ürün gerçeklerinde yazmıyor);
 *  teslim kanalları zincirin çıkışı olarak bölüm notunda, iş kartlarına bağlanır.
 *  Ö9: bölümün dibinde «kendiniz işlerseniz ↔ PVQuant ile» ayna tablosu — sol sütun SORU kurar,
 *  rakip adı vermez; sağ sütun sitede zaten yazılı ürün gerçekleri (Enverus'un biçimi, ölçüsüz
 *  üstünlük iddiası olmadan). Kart eylemlidir (vt-kart--bag, R21); "Panelde: …" satırı panel
 *  girişini açar (R18). Cümleler v2.383 vitrinindeki KATMANLAR'dan aynen. */
const AYNA = [
  ["Işınımı MWh'e kim çeviriyor?", "Saatlik P10/P50/P90 üretim aralığı, 15 güne dek."],
  ["Tahmin tuttu mu, kim hesaplıyor?", "Her gece gerçekleşenle karşılaştırılır; sonuç panelde gün gün birikir."],
  ["Sapmanın bedelini ne zaman görüyorsunuz?", "Dengesizlik maliyetinin TL karşılığı panelde gün gün, teklif kantili önerisiyle."],
] as const;
const ADIM: readonly {
  no: string; baslik: string; cumle: ReactNode; etiket: string;
  levha: string; grup: RozetGrubu; ikon: RozetIkonu;
}[] = [
  { no: "01 / 04", baslik: "Fizik modeli", cumle: "Santralin geometrisinden yola çıkar — panel eğimi, tavan, kayıplar.", etiket: "Panelde: Kalibrasyon", levha: levhaFizik, grup: "kanit", ikon: "kalibrasyon" },
  { no: "02 / 04", baslik: "Öğrenen model", cumle: "Fiziğin gözden kaçırdığını santralin kendi geçmişinden öğrenir.", etiket: "Panelde: Kalibrasyon", levha: levhaOgrenen, grup: "kanit", ikon: "kalibrasyon" },
  { no: "03 / 04", baslik: "Dürüst aralık", cumle: <>Tek sayı değil, gerçek hatayla ayarlanmış <a className="vt-bag vt-bag--metin" href="/yontem#yt-tanimlar">iyimser–kötümser bandı</a> verir.</>, etiket: "Panelde: Tahminler", levha: levhaAralik, grup: "tahmin", ikon: "band" },
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
          {ADIM.map((a, i) => (<Fragment key={a.no}>
            {i > 0 && <span className="vt-adim__ok" aria-hidden="true">→</span>}
            <article className={onPanel ? "vt-kart vt-kart--bag vt-adim" : "vt-kart vt-adim"}>
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
          </Fragment>))}
        </div>
        <p className="vt-not vt-adim__cikis">Zincirin çıkışı teslim kanallarıdır — TPYS&#39;ye öneri CSV, toplayıcıya CSV/XLSX, REST API ve sabah webhook&#39;u; <a className="vt-bag vt-bag--metin" href="#isler">masanıza göre ayrıntısı iş kartlarında</a>.</p>
        <div className="vt-ayna" role="table" aria-label="Tahmini kendiniz işlerseniz ve PVQuant ile karşılaştırması">
          <div className="vt-ayna__bas" role="row">
            <span role="columnheader">Tahmini kendiniz işlerseniz</span>
            <span role="columnheader">PVQuant ile</span>
          </div>
          {AYNA.map(([soru, cevap]) => (
            <div key={soru} className="vt-ayna__satir" role="row">
              <span className="vt-ayna__soru" role="cell">{soru}</span>
              <span className="vt-ayna__cevap" role="cell">{cevap}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
