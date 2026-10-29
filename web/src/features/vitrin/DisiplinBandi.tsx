/** Mühendislik disiplini bandı (R27 + rakip analizi Ö7/Ö14): Solargis'in istatistik üçlüsünün
 *  DÜRÜST karşılığı — müşteri/proje sayısı değil, depo ve test takımı gerçekleri. Ö7: her rakamın
 *  alt satırı alıcı dilinde tek anlam cümlesi ve rakama kendi kanıt bağlantısı; Mercury usulü
 *  dipnot sayım kuralını verir (13.10: rakam üstündeki «1» imi kalktı; «sayım kuralı →» bağı dipnota götürür). Ö14: başlık olumsuz kurgudan çıktı («logo duvarı yok» →
 *  «Disiplin, tarihli rakamla.»), iç jargon («mühür») vitrinden indi. Sayılar statiktir ve tarih
 *  künyesi taşır; bayatlarsa sürümle güncellenir (dal defteri kuralı). Kaynaklar: test takımı
 *  koşusu (python+web; "her sürümde tamamı koşar" sözünü ci.yml'deki iki iş birlikte tutar),
 *  forecast_horizon_days, alarm_service kuralları, BULGU_DEFTERI kayıtları. */
import { Meta } from "../../lib/Meta";
const RAKAMLAR = [
  ["800", "otomatik test", "testlerin tamamı her sürümde koşar", "#vt-dipnot-1", "sayım kuralı"],
  ["15 gün", "tahmin ufku", "15 güne dek her saat için iyimser–kötümser aralık", "/yontem#yt-tanimlar", "aralığın tanımı"],
  ["2 + 6", "alarm kuralı", "ikisi varsayılan izler; altısı santrale göre açılır", "#isler", "operasyon nöbeti"],
  ["32", "kapatılmış bulgu kaydı", "bulundu, düzeltildi, kayda geçti", "", ""],
] as const;

export function DisiplinBandi() {
  return (
    <section className="vt-disiplin" id="rakamlar" aria-labelledby="vt-disiplin-baslik" data-canlan="">
      <div className="vt-kap">
        <h2 className="vt-disiplin__baslik" id="vt-disiplin-baslik">Vaat değil, tarihli rakam.</h2>
        <div className="vt-izgara vt-izgara--4 vt-disiplin__izgara">
          {RAKAMLAR.map(([deger, etiket, anlam, hedef, bagAd]) => (
            <div key={etiket} className="vt-disiplin__oge">
              <div className="vt-disiplin__deger">{deger}</div>
              <div className="vt-disiplin__etiket">{etiket}</div>
              <div className="vt-disiplin__alt">{anlam}</div>
              {hedef ? <a className="vt-bag vt-disiplin__bag" href={hedef}>{bagAd}</a> : <span className="vt-disiplin__bag" aria-hidden="true" />}
            </div>
          ))}
        </div>
        <p className="vt-kunye vt-disiplin__kunye"><Meta items={["29.10.2026 itibarıyla", "kaynak: yazılım deposu, otomatik test takımı ve bulgu kayıt defteri"]} /></p>
        <p className="vt-kunye vt-disiplin__dipnot" id="vt-dipnot-1">Sayım kuralı: 29.10.2026 sürümündeki iki test takımının (hesaplama motoru 748 + arayüz 102) toplamı, yüzlüğe aşağı yuvarlanmış; her sürümde iki takım da baştan sona koşar.</p>
      </div>
    </section>
  );
}
