/** SSS (v2.384). Beş soru ve cevap v2.383 vitrininden aynen (kurumsal B2B dil). */
const SORULAR = [
  ["Kurulum gerekir mi?",
   "Gerekmez. Hesabınız oluşturulduktan sonra tahmin üretimi başlar; sahada donanım kurulumu yapılmaz ve mevcut sistemlerinize müdahale edilmez. Üretim (SCADA) verilerinizi dilediğiniz zaman panel üzerinden yükleyebilirsiniz."],
  ["SCADA verisi olmadan çalışır mı?",
   "Evet. Santralın temel bilgileriyle (konum, kurulu güç, panel yerleşimi) tahmin üretilir. Üretim verileriniz yüklendikçe model santralınıza özel olarak kalibre edilir ve doğruluk karneniz oluşmaya başlar."],
  ["Fiyatlandırma nasıl belirleniyor?",
   "Fiyatlandırma, kurulu güç başına aylık abonelik modeline dayanır ve santral sayısına göre belirlenir. Başvuru formunu doldurmanızın ardından teklifimiz e-posta ile iletilir."],
  ["Doğruluk değerleri neye dayanıyor?",
   "Tüm doğruluk değerleri ölçüme dayanır: tahminler her gece, gerçekleşen üretimle aynı yöntemle karşılaştırılır; sonuçlar panelde birikir ve geçmiş kayıtlar değiştirilemez. Bu sayfadaki Açık karne, aynı hesaplamanın kamuya açık örneğidir; yöntem tanımları karne bloğunun hemen altında yer alır."],
  ["Verilerimizin güvenliği nasıl sağlanıyor?",
   "Verileriniz kurumunuza aittir; dilediğiniz zaman tamamını dışa aktarabilir veya silebilirsiniz. Hesaplar birbirinden yalıtılmıştır; kurumlar arası paylaşım yalnızca sizin onayınızla açılır ve tüm erişimler denetim kaydına işlenir. Veri iletimi TLS ile şifrelenir."],
] as const;

export function Sss() {
  return (
    <section className="vt-bolum" id="sss" aria-labelledby="vt-sss-baslik">
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
