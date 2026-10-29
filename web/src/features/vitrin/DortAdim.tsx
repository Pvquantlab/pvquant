import { Fragment, type ReactNode } from "react";
import { Rozet, type RozetGrubu, type RozetIkonu } from "./Rozet";
import levhaFizik from "./varlik/adim-fizik.png";
import levhaOgrenen from "./varlik/adim-ogrenen.png";
import levhaAralik from "./varlik/adim-aralik.png";
import levhaKarne from "./varlik/adim-karne.png";
import { Levha } from "./Levha";

/** Dört adım (v2.386 cila-a + rakip analizi Ö9/Ö11): V1 kartları levha illüstrasyonlarıyla.
 *  Ö11: ≥1241'de dört kart TEK SIRA numaralı zincirdir (oklar grid hücresi — ::after kartın overflow'una kırpılıyordu);
 *  modele geri dönen ok BİLEREK çizilmez (yeniden eğitim sıklığı ürün gerçeklerinde yazmıyor);
 *  teslim kanalları zincirin çıkışı olarak bölüm notunda, iş kartlarına bağlanır.
 *  Ö9: bölümün dibinde «kendiniz işlerseniz ↔ PVQuant ile» ayna tablosu — sol sütun SORU kurar,
 *  rakip adı vermez; sağ sütun sitede zaten yazılı ürün gerçekleri (Enverus'un biçimi, ölçüsüz
 *  üstünlük iddiası olmadan). Kart eylemlidir (vt-kart--bag, R21); "Panelde: …" satırı panel
 *  girişini açar (R18). Cümleler v2.383 vitrinindeki KATMANLAR'dan aynen. */
const AYNA = [
  ["Hava tahminini üretime kim çeviriyor?", "Her saat için iyimser, beklenen ve kötümser üretim; 15 gün ileriye."],
  ["Tahmin tuttu mu, kim ölçüyor?", "Her gece gerçekleşen üretimle karşılaştırılır; sonuç panelde gün gün birikir."],
  ["Programı hangi seviyeden vereceğinizi kim söylüyor?", "İyimser–kötümser aralıktan siz seçersiniz; gerçekleşmeyle fark her sabah karnede, uzlaştırma kalemleri yürürlükteki kuralla panelde."],
] as const;
const ADIM: readonly {
  no: string; baslik: string; cumle: ReactNode; etiket: string;
  levha: string; grup: RozetGrubu; ikon: RozetIkonu;
}[] = [
  { no: "01 / 04", baslik: "Santralinizin yapısı", cumle: "Panel eğimi ve yönü, kurulu güç, inverter sınırı ve kayıplar: tahmin, santralinizin kendi özelliklerinden başlar.", etiket: "Panelde: Kalibrasyon", levha: levhaFizik, grup: "kanit", ikon: "kalibrasyon" },
  { no: "02 / 04", baslik: "Geçmiş üretiminiz", cumle: "Santralinizin geçmiş üretim verisiyle tahmin size özel ayarlanır; her yeni gün bu ayarı keskinleştirir.", etiket: "Panelde: Kalibrasyon", levha: levhaOgrenen, grup: "kanit", ikon: "kalibrasyon" },
  { no: "03 / 04", baslik: "İyimser–kötümser aralık", cumle: <>Tek bir sayı değil, geçmiş hatalara göre ayarlanmış bir <a className="vt-bag vt-bag--metin" href="/yontem#yt-tanimlar">iyimser–kötümser aralık</a>: programı hangi seviyeden vereceğinizi siz seçersiniz.</>, etiket: "Panelde: Tahminler", levha: levhaAralik, grup: "tahmin", ikon: "band" },
  { no: "04 / 04", baslik: "Her gece sınav", cumle: "Günün tahmini gerçekleşen üretimle karşılaştırılır; doğruluk karneniz gün gün birikir.", etiket: "Panelde: Doğruluk", levha: levhaKarne, grup: "kanit", ikon: "karne" },
];

export function DortAdim({ onPanel }: { onPanel?: () => void }) {
  return (
    <section className="vt-bolum" id="katmanlar" aria-labelledby="vt-adim-baslik" data-canlan="">
      <div className="vt-kap">
        <div className="vt-bolum-bas">
          <p className="vt-eyebrow">Nasıl çalışır</p>
          <h2 className="vt-h2" id="vt-adim-baslik">Dört adımlı, denetlenebilir tahmin süreci. <span className="vt-h2__soluk">Her adım panelde.</span></h2>
        </div>
        <div className="vt-izgara vt-izgara--2 vt-adimlar">
          {ADIM.map((a, i) => (<Fragment key={a.no}>
            {i > 0 && <span className="vt-adim__ok" aria-hidden="true">→</span>}
            <article className={onPanel ? "vt-kart vt-kart--bag vt-adim" : "vt-kart vt-adim"}>
              <div className={`vt-levha vt-levha--resim vt-levha--resim-${i + 1}`} aria-hidden="true"><Levha src={a.levha} alt="" width="2000" height="2000" loading="lazy" decoding="async" /></div>
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
        <p className="vt-not vt-adim__cikis">Sonuç, kullandığınız kanala gider: üretim programı dosyası (CSV/XLSX; TPYS şablonuna uyum pilotta doğrulanır), doğrudan sisteminize API ile ve her sabah otomatik bildirimle; <a className="vt-bag vt-bag--metin" href="#isler">işinize göre ayrıntısı iş birimi kartlarında</a>.</p>
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
