/** Yöntem metni — TEK KAYNAK (v2.384). Karne bandının yöntem kutusu ve /yontem sayfası buradan okur.
 *  Tanımlar hesapla eşlendi:
 *    - apps/worker/main.py gece_skill: gündüz saati = gerçekleşen > %2 kurulu güç;
 *      naif = dünkü üretim × açık-gök(t) / açık-gök(t − 24 sa), oran [1/4, 4].
 *    - ext/tahmin/dogrulama.py picp: saatlerin ortalaması; services/dogrulama_service.py avg(picp80):
 *      günlük değerlerin ortalaması.
 *  Hesap tanımı değişirse YALNIZ burası güncellenir. */

export const ADIMLAR = [
  ["Tahmin önceden kaydedilir",
   "Her santral için saatlik tahmin ve iyimser–kötümser aralık, gün başlamadan üretilir ve zaman damgasıyla saklanır. Kayıt üzerinde sonradan düzeltme yapılmaz."],
  ["Gerçekleşen üretim toplanır",
   "Üretim (SCADA/sayaç) verisi geldikçe saatlik seriye işlenir. Ölçüm gelmeyen saatler karneye dâhil edilmez; eksik veri sıfır sayılmaz."],
  ["Her gece otomatik karşılaştırma",
   "Kapanan günün tahmini ile gerçekleşen üretimi, tüm santraller için aynı kuralla karşılaştırılır. Hesap kişiye ve güne göre değişmez."],
  ["Sonuç birikir, geçmiş değişmez",
   "Karne satırları yalnızca eklenir; kötü geçen gün silinmez, yeniden hesaplanmaz. Doğruluk değerleri bu birikimin penceresidir."],
] as const;

export const METRIKLER = [
  ["Ortalama sapma (WMAPE)",
   "Gündüz saatlerinde |tahmin − gerçekleşen| toplanır ve o günün toplam gerçekleşen üretimine bölünür; pencere değeri, günlük değerlerin ortalamasıdır. Üretime ağırlıklıdır: düşük üretimli saatlerdeki küçük mutlak farkların yüzdeyi şişirmesine izin verilmez. Küçük değer iyidir. Gündüz saati: gerçekleşen üretimin kurulu gücün %2'sini aştığı saat."],
  ["Kapasiteye oranlı sapma (nMAE)",
   "Gündüz saatlerindeki |tahmin − gerçekleşen| ortalaması kurulu güce bölünür. Üretime değil kapasiteye oranlandığı için mevsimden ve santral büyüklüğünden daha az etkilenir; farklı santralleri ve sistemleri kıyaslamanın ortak dilidir. Ortalama sapma (WMAPE) ile aynı saatlerden hesaplanır ama paydası farklıdır — iki değer birbirinin yerine okunmaz."],
  ["Basit yöntem (referans)",
   "“Yarın = dün aynı saat” kuralı; değer, güneşin iki gün arasındaki konum farkına göre (açık-gök ışınımı oranıyla) ölçeklenir. Maliyeti sıfır olduğu için sektörde taban kabul edilir; her doğruluk değeri bu tabanla yan yana yayımlanır. Tabanı geçemeyen tahminin değeri yoktur."],
  ["Sıkı referans",
   "Ay ve saate göre iklim beklentisi ile akıllı sürekliliğin birleşimi — basit yöntemden belirgin ölçüde zor bir kıyas çıtası. Kolay rakibe karşı değil, güçlü referansa karşı ölçülürüz."],
  ["Beceri",
   "Referansa göre iyileşme oranı: (referans sapması − PVQuant sapması) / referans sapması. Sıfırın üstü, tahminin referanstan iyi olduğu anlamına gelir."],
  ["Bant kapsaması",
   "Gerçekleşen üretimin, önceden ilan edilen iyimser–kötümser aralık içinde kaldığı gündüz saatlerinin oranı; her gün ayrı hesaplanır, pencere boyunca ortalanır. Hedef %80'dir — %100 değil: her zaman tutan bant, karar için fazla geniş demektir."],
  ["D-1 teslim kesiti",
   "Karnenin ana değerleri gün içi güncellemeleri de içerir; bu kesit ise her gün için yalnız önceki gün 15:30'dan (İstanbul) önce verilmiş son tahminle hesaplanır — piyasaya verilen üretim programının tabi olduğu gerçek ufuk budur. Sistemler arası «gün öncesi» kıyası bu kesitten okunur."],
] as const;

export const KISA_TANIMLAR = [
  ["Ortalama sapma",
   "her gündüz saatinde |tahmin − gerçekleşen| toplanır, o günün gerçekleşen üretimine bölünür ve günler ortalanır (gün içinde üretime ağırlıklı; gündüz saati = gerçekleşen üretimin kurulu gücün %2'sini aştığı saat)."],
  ["Basit yöntem",
   "“yarın = dün aynı saat”, güneşin konum farkına göre açık-gök ışınımı oranıyla ölçeklenir — sektörün sıfır maliyetli tabanı."],
  ["Sıkı referans",
   "iklim beklentisiyle akıllı sürekliliğin en iyi ağırlıklı karışımı — geçilmesi zor, dürüst kıyas çıtası."],
  ["Bant kapsaması",
   "gerçekleşen üretimin önceden söylenen iyimser–kötümser aralıkta kaldığı gündüz saatlerinin oranı; her gün ayrı hesaplanır, pencere boyunca ortalanır."],
] as const;

export const YONTEM_KAPANIS = "Hepsi her gece aynı kuralla, otomatik hesaplanır; geçmiş değiştirilmez.";
