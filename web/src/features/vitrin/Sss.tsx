import type { ReactNode } from "react";

/** SSS (v2.384 + rakip analizi Ö13). İlk beş soru v2.383 vitrininden aynen; altıncı soru en yakın
 *  rakibin kendi SSS'sinde sorduğu güven sorusunun bizim kanıt düzenimizle cevabı (dört adım
 *  diliyle + «güven bizden değil karneden» + Açık karne bağı). Model/kütüphane adı yok. */
const SORULAR = [
  ["Kurulum gerekir mi?",
   "Gerekmez. Hesabınız oluşturulduktan sonra tahmin üretimi başlar; sahada donanım kurulumu yapılmaz ve mevcut sistemlerinize müdahale edilmez. Üretim (SCADA) verilerinizi dilediğiniz zaman panel üzerinden yükleyebilirsiniz."],
  ["SCADA verisi olmadan çalışır mı?",
   "Evet. Santralin temel bilgileriyle (konum, kurulu güç, panel yerleşimi) tahmin üretilir. Üretim verileriniz yüklendikçe model santralinize özel olarak kalibre edilir ve doğruluk karneniz oluşmaya başlar."],
  ["Fiyatlandırma nasıl belirleniyor?",
   "Fiyatlandırma, kurulu güç başına aylık abonelik modeline dayanır ve santral sayısına göre belirlenir. Başvuru formunu doldurmanızın ardından teklifimiz e-posta ile iletilir."],
  ["Doğruluk değerleri neye dayanıyor?",
   "Tüm doğruluk değerleri ölçüme dayanır: tahminler her gece, gerçekleşen üretimle aynı yöntemle karşılaştırılır; sonuçlar panelde birikir ve geçmiş kayıtlar değiştirilemez. Bu sayfadaki Açık karne, aynı hesaplamanın kamuya açık örneğidir; yöntem tanımları karne bloğunun hemen altında yer alır."],
  ["Verilerimizin güvenliği nasıl sağlanıyor?",
   "Verileriniz kurumunuza aittir; dilediğiniz zaman tamamını dışa aktarabilir veya silebilirsiniz. Hesaplar birbirinden yalıtılmıştır; kurumlar arası paylaşım yalnızca sizin onayınızla açılır ve tüm erişimler denetim kaydına işlenir. Veri iletimi TLS ile şifrelenir."],
  ["Modelinize neden güvenelim?",
   <>Tahmin zinciri açıktır: fizik modeli santralin geometrisinden kurar, öğrenen düzeltme santralin kendi geçmişinden gelir, dürüst aralık gerçek hatayla ayarlanır, gece karşılaştırması da sonucu ölçer. Güven bizden değil karneden gelir: tahmin her gece basit yönteme ve sıkı referansa karşı aynı kuralla sınanır; geçmiş değiştirilmez. Referans santralin karnesi 30 sınav günü dolduğunda <a className="vt-bag vt-bag--metin" href="#karne">bu sayfadaki Açık karnede</a> herkese açıktır.</>],
] as const satisfies readonly (readonly [string, ReactNode])[];

export function Sss() {
  return (
    <section className="vt-bolum" id="sss" aria-labelledby="vt-sss-baslik" data-canlan="">
      <div className="vt-kap">
        <div className="vt-sss-yer">
          <div className="vt-bolum-bas"><h2 className="vt-h2" id="vt-sss-baslik">Sık sorulan sorular</h2></div>
          <div>
            {SORULAR.map(([soru, cevap]) => (
              <details key={soru} className="vt-sss">
                <summary>{soru}</summary>
                <p>{cevap}</p>
              </details>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
