import { VAKA_15DK, VAKA_PENCERESI, VAKA_SAATI, gunSerisi, VARSAYILAN_GUN, trTarih } from "./referansVeri";

/** Türkiye piyasası (v2.416 «Ö4 vakası» — rakip analizi uyarlanabilir-oneriler §Ö4).
 *  Stilize panel-pencere maketleri ve beş özellik kartı KALKTI; bölüm artık hero'da
 *  başlayan 01.10 araştırma koşusu VAKASININ teslim sahnesidir: saat kartı (12:00'ın
 *  P10/P50/P90'ı mavi, gerçekleşeni amber) kesik mürekkep çizgisiyle aynı koşunun GERÇEK
 *  15 dk teslim dilimlerine bağlanır (Raptor Maps emsali; dilimler depodaki
 *  ext.alt_saatlik ile üretildi — referansVeri.VAKA_15DK, kapasiteye oran: mutlak MW
 *  santral ölçeğini açığa çıkarır). Her sahnede aynı mono künye: «01.10 araştırma
 *  koşusu … teslim edilmedi». Ö4(b) TL karşılığı GÖSTERİLMEZ (depoda bu koşu için
 *  hesaplanmadı; tek-gün kıyası da yanıltıcı olur — 46 günlük karne açık karne
 *  bölümündedir, köprü cümle oraya işaret eder). Ö4(c): alarm kütüphanesi bu koşuda
 *  çalıştırılmadı — yeti satırı bunu AÇIKÇA söyler. Yetiler kart değil, tek yüzeyin
 *  çizgili satırlarıdır; sayı uydurulmaz, amber yalnız gerçekleşen. */

const yz = (v: number) => "%" + (v * 100).toFixed(1).replace(".", ",");

const YETILER: readonly { ad: string; metin: string; kunye?: string }[] = [
  { ad: "Teslim programı", metin: "Yarının saatlik programı ve emre amadelik bildirimi teslim penceresi kapanmadan hazırdır; bir gecikme olursa alarm sizi uyarır." },
  { ad: "Alarm kütüphanesi", metin: "Gece ekrana kimse bakmazken kurallar bakar; sabah ilk iş gece karnesini ve açık alarmları görürsünüz.",
    kunye: "bu araştırma koşusunda alarm kütüphanesi çalıştırılmadı" },
  { ad: "Şablonlu dışa verim", metin: "Tahmin aralığını toplayıcınızın ya da DSG'nin şablonunda CSV/XLSX olarak indirirsiniz; isterseniz API anahtarıyla doğrudan sisteminize akar." },
];

export function TurkiyePiyasasi() {
  const saat12 = gunSerisi(VARSAYILAN_GUN).find((n) => n.saat === VAKA_SAATI)!;
  return (
    <section className="vt-bolum vt-bolum--bant" id="para" aria-labelledby="vt-para-baslik" data-canlan="">
      <div className="vt-kap">
        <div className="vt-para-ust">
          <div className="vt-bolum-bas">
            <h2 className="vt-h2" id="vt-para-baslik">Tahmin hatasının maliyetini TL olarak görün.</h2>
            <p className="vt-giris">Elektrik piyasasında her santral, ertesi gün ne üreteceğini önceden bildirmekle yükümlüdür; gerçekleşen üretim bu programdan saptığında aradaki fark santrale fatura edilir. PVQuant üretim programınızı hazırlar, gün içi güncelleme fırsatlarını izler ve sapmanın size maliyetini her gün TL olarak raporlar.</p>
            <p className="vt-giris vt-para-kopru">Aşağıdaki sahne, yukarıdaki grafikle aynı araştırma koşusunun teslim biçimidir — tek bir gündür; 46 günlük isabet, <a href="#karne">açık karne</a> bölümündedir.</p>
          </div>

          <figure className="vt-vaka" aria-label="01.10 araştırma koşusunun teslim biçimi: 12:00 saat kartı ve 15 dakikalık dilimler">
            <figcaption className="vt-vaka__kunye">{trTarih(VARSAYILAN_GUN)} araştırma koşusu · hero'daki referans santral · teslim edilmedi</figcaption>
            <div className="vt-vaka__govde">
              <div className="vt-vaka__saat vt-nesne">
                <div className="vt-vaka__saat-bas">{String(VAKA_SAATI).padStart(2, "0")}:00<span>teslim saati</span></div>
                <dl className="vt-vaka__degerler">
                  <div><dt>P10</dt><dd>{yz(saat12.p10)}</dd></div>
                  <div><dt>P50</dt><dd>{yz(saat12.p50)}</dd></div>
                  <div><dt>P90</dt><dd>{yz(saat12.p90)}</dd></div>
                  <div className="vt-vaka__gercek"><dt>Gerçekleşen</dt><dd>{saat12.gercek === null ? "—" : yz(saat12.gercek)}</dd></div>
                </dl>
                <p className="vt-vaka__saat-not">kapasiteye oran · bant o sabah bulut revizyonuyla genişledi</p>
              </div>
              <span className="vt-vaka__bag" aria-hidden="true" />
              <div className="vt-vaka__tablo">
                <div className="vt-vaka__tablo-bas">
                  <b>Toplayıcı biçimi · 15 dk</b>
                  <span>{VAKA_PENCERESI}</span>
                </div>
                <table>
                  <thead>
                    <tr><th scope="col">Saat</th><th scope="col">P10</th><th scope="col">P50</th><th scope="col">P90</th><th scope="col">Gerçekleşen</th></tr>
                  </thead>
                  <tbody>
                    {VAKA_15DK.map((d) => (
                      <tr key={d.saat} className={d.saat.startsWith(String(VAKA_SAATI)) ? "vt-vaka__kapsam" : undefined}>
                        <th scope="row">{d.saat}</th>
                        <td>{yz(d.p10)}</td><td>{yz(d.p50)}</td><td>{yz(d.p90)}</td>
                        <td className="vt-vaka__amber">{yz(d.gercek)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="vt-vaka__tablo-not">saatlik koşu teslim için 15 dk dilimlere bölünür; her saatin ortalaması saatlik değere eşittir · panelde CSV · XLSX · API, MW cinsinden</p>
              </div>
            </div>
          </figure>
        </div>

        <ul className="vt-yetiler" role="list">
          {YETILER.map((y) => (
            <li key={y.ad} className="vt-yeti">
              <h3 className="vt-h3">{y.ad}</h3>
              <p className="vt-kart__metin">{y.metin}</p>
              {y.kunye && <p className="vt-yeti__kunye">{y.kunye}</p>}
            </li>
          ))}
        </ul>
        <p className="vt-not">Sapmanın TL karşılığı panelde, kendi santralinizin verisiyle hesaplanır.</p>
      </div>
    </section>
  );
}
