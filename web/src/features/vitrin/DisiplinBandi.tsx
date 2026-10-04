/** Mühendislik disiplini bandı (R27): Solargis'in istatistik üçlüsünün DÜRÜST karşılığı —
 *  müşteri/proje sayısı değil (yok ve uydurulmaz), depo ve test takımı gerçekleri. Sayılar
 *  statiktir ve tarih künyesi taşır; bayatlarsa mühürle güncellenir (dal defteri kuralı).
 *  Kaynaklar: test takımı koşusu (python+web; "her mühürde tamamı koşar" sözünü ci.yml'deki
 *  iki iş birlikte tutar), forecast_horizon_days, alarm_service kuralları, BULGU_DEFTERI kayıtları. */
const RAKAMLAR = [
  ["700", "otomatik test", "her mühürde tamamı koşar"],
  ["15 gün", "tahmin ufku", "her saat için aralıkla"],
  ["8", "alarm kuralı", "veri, teslim ve performans nöbeti"],
  ["32", "mühürlü bulgu kaydı", "bulundu, düzeltildi, mühürlendi"],
] as const;

export function DisiplinBandi() {
  return (
    <section className="vt-disiplin" id="rakamlar" aria-labelledby="vt-disiplin-baslik" data-canlan="">
      <div className="vt-kap">
        <h2 className="vt-h3" id="vt-disiplin-baslik">Vitrinde logo duvarı yok; disiplin var.</h2>
        <div className="vt-izgara vt-izgara--4 vt-disiplin__izgara">
          {RAKAMLAR.map(([deger, etiket, alt]) => (
            <div key={etiket} className="vt-disiplin__oge">
              <div className="vt-disiplin__deger">{deger}</div>
              <div className="vt-disiplin__etiket">{etiket}</div>
              <div className="vt-disiplin__alt">{alt}</div>
            </div>
          ))}
        </div>
        <p className="vt-kunye vt-disiplin__kunye">
          04.10.2026 itibarıyla · kaynak: depo, test takımı ve bulgu defteri · <a className="vt-bag vt-disiplin__bag" href="/yontem#yt-disiplin">Aralık ve yayın disiplini</a>
        </p>
      </div>
    </section>
  );
}
