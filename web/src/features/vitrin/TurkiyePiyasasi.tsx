/** Türkiye piyasası (v2.384, spec §3.5). Metinler v2.383 vitrininden aynen; elle yazılmış TL tutarı ve
 *  kurulu güç içeren saha dipnotu kalktı (sayılar canlı API'den gelir, kurulu güç yazılmaz). */
const KARTLAR = [
  ["Program hazır", "Saatlik üretim programı ve emre amadelik, teslim penceresi kapanmadan dosya olarak elinizde — gecikirse alarm çalar."],
  ["Sapmanın TL kartı", "Tahmin hatasının aylık TL karşılığı ve basit yönteme göre kurtarılan tutar panelde gün gün birikir; teminat etkisiyle birlikte."],
  ["Toplayıcıya tek tık", "Tahmin aralığı toplayıcı/DSG şablonlarında (saatlik ya da 15 dakikalık) dışa verilir; API anahtarıyla sistemden sisteme akar."],
] as const;

const MASALAR = [
  ["Operatör masası", "Program teslim penceresi, emre amadelik, veri gecikince çalan alarm, aylık bakım penceresine iklim beklentisi."],
  ["Ticaret masası", "İyimser–kötümser bant, sapmanın gün gün TL karşılığı, gün içi revizyon izi, API ile kendi sisteminize akış."],
] as const;

export function TurkiyePiyasasi() {
  return (
    <section className="vt-bolum vt-bolum--bant" id="para" aria-labelledby="vt-para-baslik">
      <div className="vt-kap">
        <div className="vt-bolum-bas">
          <h2 className="vt-h2" id="vt-para-baslik">Sapma burada soyut değil — TL yazar.</h2>
          <p className="vt-giris">Üretim programı her gün öğleden sonra bildirilir; gerçekleşen saparsa fark dengesizlik mekanizmasıyla faturalanır. PVQuant programı üretir, revizyon kapısını izler ve sapmanın TL karşılığını gün gün hesaplar.</p>
        </div>
        <div className="vt-izgara vt-izgara--3">
          {KARTLAR.map(([baslik, metin]) => (
            <article key={baslik} className="vt-kart"><h3 className="vt-h3">{baslik}</h3><p className="vt-kart__metin">{metin}</p></article>
          ))}
        </div>
        <div className="vt-izgara vt-izgara--2 vt-masalar">
          {MASALAR.map(([baslik, metin]) => (
            <article key={baslik} className="vt-kart vt-kart--masa"><h3 className="vt-h3">{baslik}</h3><p className="vt-kart__metin">{metin}</p></article>
          ))}
        </div>
        <p className="vt-not">Sapmanın TL karşılığı panelde, kendi santralinizin verisiyle hesaplanır.</p>
      </div>
    </section>
  );
}
