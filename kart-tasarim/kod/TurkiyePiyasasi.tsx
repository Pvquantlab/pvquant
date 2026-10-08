import sahneZemin from "./varlik/sahne-zemin.svg";
import { PncEkranAna, PncEkranIkinci } from "./TextliCizimler";
import { CizimProgram, CizimSapma, CizimAktarim, CizimAlarm, CizimAralik } from "./KartCizimleri";

/** Türkiye piyasası (v2.386 cila-a + kart-tasarim «panel kesiti»): solda bölüm başı, sağda SAHNELENMİŞ
 *  panel penceresi (dokunulmadı; {EKRAN} yuvası gerçek ekran görüntüsüne/canlı bileşene açık, R22).
 *  Beş kart ayrı kutu değil, tek beyaz yüzeyin 1 px çizgiyle bölünmüş hücreleri (.vt-kesit): her hücre
 *  panelden kesilmiş bir modül — etiket → ad → veri diyagramı → tek cümle → künye çipleri.
 *  Her kart TEK yeti grubu anlatır (tekrar yok); roller «Hangi iş için?» bölümünde kalır.
 *  Diyagramlarda mavi = tahmin, amber = yalnız gerçekleşen; sembol ikon (₺, zil, </>) yok.
 *  Kartlar eylemsizdir (kalkmaz, R21). Adlar ve metinler tek veri alanında (aşağıda). */
const KARTLAR: readonly {
  ad: string; etiket: string; metin: string; kunye: readonly string[];
  Cizim: () => React.JSX.Element; genis?: true;
}[] = [
  { ad: "Teslim programı", etiket: "D‑1 · teslim penceresi", Cizim: CizimProgram,
    metin: "Yarının saatlik programı ve emre amadelik bildirimi teslim penceresi kapanmadan hazırdır; bir gecikme olursa alarm sizi uyarır.",
    kunye: ["saatlik", "emre amadelik", "alarm çalar"] },
  { ad: "Sapma maliyeti", etiket: "Ay boyunca · gün gün", Cizim: CizimSapma,
    metin: "Tahmin hatasının size aylık kaç TL'ye mal olduğunu, basit yönteme göre farkı ve teminata etkisini tek yerde görürsünüz.",
    kunye: ["TL · aylık", "basit yönteme karşı", "teminat etkisi"] },
  { ad: "Şablonlu dışa verim", etiket: "Teslimle birlikte", Cizim: CizimAktarim,
    metin: "Tahmin aralığını toplayıcınızın ya da DSG'nin şablonunda indirirsiniz; biçimi elle düzeltmeniz gerekmez. İsterseniz API anahtarıyla doğrudan sisteminize akar.",
    kunye: ["CSV · XLSX", "saatlik ya da 15 dk", "API anahtarı"] },
  { ad: "Alarm kütüphanesi", etiket: "Gece ve gündüz", Cizim: CizimAlarm, genis: true,
    metin: "Gece ekrana kimse bakmazken kurallar bakar. Sabah ilk iş gece karnesini ve açık alarmları görürsünüz.",
    kunye: ["8 kural", "veri · teslim · performans", "gece karnesi"] },
  { ad: "Gün içi aralık", etiket: "Sabah koşusundan itibaren", Cizim: CizimAralik, genis: true,
    metin: "İyimser–kötümser bant gün içinde güncellendikçe önceki hâlleri izde kalır; sabah koşusu bitince webhook sisteminize haber verir.",
    kunye: ["iyimser–kötümser", "gün içi revizyon", "sabah webhook’u"] },
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
        <div className="vt-kesit">
          {KARTLAR.map(({ ad, etiket, metin, kunye, Cizim, genis }) => (
            <article key={ad} className={genis ? "vt-kesit__hucre vt-kesit__hucre--genis" : "vt-kesit__hucre"}>
              <header className="vt-kesit__bas"><h3 className="vt-h3">{ad}</h3><p className="vt-kesit__etiket">{etiket}</p></header>
              <div className="vt-kesit__cizim" aria-hidden="true"><Cizim /></div>
              <p className="vt-kart__metin">{metin}</p>
              <ul className="vt-kesit__kunye">{kunye.map((d) => <li key={d}>{d}</li>)}</ul>
            </article>
          ))}
        </div>
        <p className="vt-not">Sapmanın TL karşılığı panelde, kendi santralinizin verisiyle hesaplanır.</p>
      </div>
    </section>
  );
}
