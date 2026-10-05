/** Mühendislik disiplini bandı (R27 + rakip analizi Ö7/Ö14): Solargis'in istatistik üçlüsünün
 *  DÜRÜST karşılığı — müşteri/proje sayısı değil, depo ve test takımı gerçekleri. Ö7: her rakamın
 *  alt satırı alıcı dilinde tek anlam cümlesi ve rakama kendi kanıt bağlantısı; Mercury usulü
 *  dipnot sayım kuralını verir. Ö14: başlık olumsuz kurgudan çıktı («logo duvarı yok» →
 *  «Disiplin, tarihli rakamla.»), iç jargon («mühür») vitrinden indi. Sayılar statiktir ve tarih
 *  künyesi taşır; bayatlarsa sürümle güncellenir (dal defteri kuralı). Kaynaklar: test takımı
 *  koşusu (python+web; "her sürümde tamamı koşar" sözünü ci.yml'deki iki iş birlikte tutar),
 *  forecast_horizon_days, alarm_service kuralları, BULGU_DEFTERI kayıtları. */
const RAKAMLAR = [
  ["700", "otomatik test", "testlerin tamamı her sürümde koşar", "#vt-dipnot-1", "sayım kuralı", "1"],
  ["15 gün", "tahmin ufku", "15 güne dek her saat için iyimser–kötümser aralık", "/yontem#yt-tanimlar", "aralığın tanımı", ""],
  ["8", "alarm kuralı", "veri, teslim ve performans nöbetini kurallar tutar", "#isler", "operasyon nöbeti", ""],
  ["32", "kapatılmış bulgu kaydı", "bulundu, düzeltildi, kayda geçti", "", "", ""],
] as const;

export function DisiplinBandi() {
  return (
    <section className="vt-disiplin" id="rakamlar" aria-labelledby="vt-disiplin-baslik" data-canlan="">
      <div className="vt-kap">
        <h2 className="vt-disiplin__baslik" id="vt-disiplin-baslik">Disiplin, tarihli rakamla.</h2>
        <div className="vt-izgara vt-izgara--4 vt-disiplin__izgara">
          {RAKAMLAR.map(([deger, etiket, anlam, hedef, bagAd, dipnot]) => (
            <div key={etiket} className="vt-disiplin__oge">
              <div className="vt-disiplin__deger">{deger}{dipnot && <sup className="vt-disiplin__dip" aria-hidden="true">{dipnot}</sup>}{dipnot && <span className="vt-srgizli"> (dipnot {dipnot})</span>}</div>
              <div className="vt-disiplin__etiket">{etiket}</div>
              <div className="vt-disiplin__alt">{anlam}</div>
              {hedef ? <a className="vt-bag vt-disiplin__bag" href={hedef}>{bagAd}</a> : <span className="vt-disiplin__bag" aria-hidden="true" />}
            </div>
          ))}
        </div>
        <p className="vt-kunye vt-disiplin__kunye">04.10.2026 itibarıyla · kaynak: depo, test takımı ve bulgu defteri</p>
        <p className="vt-kunye vt-disiplin__dipnot" id="vt-dipnot-1"><sup aria-hidden="true">1</sup> 04.10.2026 sürümündeki iki test takımının (hesap hattı + arayüz) toplamı, aşağı yuvarlanmış; her sürümde iki takım da baştan sona koşar.</p>
      </div>
    </section>
  );
}
