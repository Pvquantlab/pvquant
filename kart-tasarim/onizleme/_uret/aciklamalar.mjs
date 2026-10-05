// 5. aşama: her kart için beş açıklama alternatifi. Beş «ton» her kartta aynı sırayla;
// bir ton seçilirse beş kart tek sesle konuşur. Her iddia görev §0 yeti listesinden.

export const TONLAR = [
  ["1", "Fayda önce", "Okurun eline geçen sonuçla başlar, nasılını ikinci yarıda söyler."],
  ["2", "Ürün özne", "«PVQuant … yapar» kalıbı; en açık ve en kurumsal, ama beş kez tekrarlanınca tekdüzeleşebilir."],
  ["3", "Gününüzden bir an", "Okurun iş gününde somut bir ana bağlanır; en insani ton."],
  ["4", "Kısa künye cümlesi", "Tek satır, fiilsiz ya da tek fiilli; ayrıntıyı künye çipleri taşır. En yalın."],
  ["5", "Sorun → çözüm", "Önce kısa bir gerçek, sonra ürünün karşılığı; iki cümle."],
];

/** Kart başına: künye çipleri (C tasarımında sabit) + beş tonun metni. */
export const ACIKLAMALAR = {
  k1: {
    kunye: ["saatlik", "emre amadelik", "alarm çalar"],
    metin: [
      "Yarının saatlik programı ve emre amadelik bildirimi teslim penceresi kapanmadan hazırdır; bir gecikme olursa alarm sizi uyarır.",
      "PVQuant yarının saatlik üretim programını ve emre amadelik bildirimini hazırlar, teslim penceresini izler ve gecikmede alarm verir.",
      "Teslim penceresi açıldığında yarının programı ve emre amadelik bildirimi dosya olarak elinizdedir. Bir şey gecikirse ilk siz duyarsınız.",
      "Saatlik program ve emre amadelik, teslim penceresi kapanmadan hazır.",
      "Program teslimi bir son saate bağlıdır. Dosya pencere kapanmadan hazırlanır; gecikme olursa alarm çalar.",
    ],
  },
  k2: {
    kunye: ["TL · aylık", "basit yönteme karşı", "teminat etkisi"],
    metin: [
      "Tahmin hatasının size aylık kaç TL'ye mal olduğunu, basit yönteme göre farkı ve teminata etkisini tek yerde görürsünüz.",
      "PVQuant tahmin hatasını aylık TL'ye çevirir; basit yönteme göre farkı ve teminat etkisini aynı tabloda gösterir.",
      "Ay sonunu beklemeden sapmanın kaça mal olduğunu bilirsiniz; basit yöntemle kıyas ve teminat etkisi hemen yanındadır.",
      "Tahmin hatasının aylık TL karşılığı, basit yönteme göre farkıyla.",
      "Yüzde, bütçe toplantısında az şey söyler. Sapmanın aylık TL karşılığını, basit yönteme göre farkı ve teminat etkisini görürsünüz.",
    ],
  },
  k3: {
    kunye: ["CSV · XLSX", "saatlik ya da 15 dk", "API anahtarı"],
    metin: [
      "Tahmin aralığını toplayıcınızın ya da DSG'nin şablonunda indirirsiniz; biçimi elle düzeltmeniz gerekmez. İsterseniz API anahtarıyla doğrudan sisteminize akar.",
      "PVQuant tahmin aralığını toplayıcı ve DSG şablonlarında, saatlik ya da 15 dakikalık dilimle verir; API anahtarıyla sistemden sisteme de akar.",
      "Dosyayı karşı tarafın beklediği biçimde indirirsiniz: toplayıcı ya da DSG şablonu, saatlik ya da 15 dakikalık. Kendi sisteminiz varsa API anahtarı yeter.",
      "Toplayıcı ve DSG şablonlarında dosya, ya da API ile doğrudan akış.",
      "Her alıcı başka bir dosya biçimi ister. Tahmin aralığı her birinin şablonunda hazırlanır; dosya istemeyen sistemler API anahtarıyla bağlanır.",
    ],
  },
  k4: {
    kunye: ["8 kural", "veri · teslim · performans", "gece karnesi"],
    metin: [
      "Sekiz kural veri, teslim ve performans tarafını sizin yerinize izler; gece karnesi her sabah hazırdır.",
      "PVQuant'ın alarm kütüphanesi sekiz kuralla veri, teslim ve performans nöbetini tutar; gece karnesini her sabah hazırlar.",
      "Gece ekrana kimse bakmazken kurallar bakar. Sabah ilk iş gece karnesini ve açık alarmları görürsünüz.",
      "Veri, teslim ve performans için 8 kural; her sabah gece karnesi.",
      "Nöbet bir kişinin dikkatine bağlı kalmamalı. Sekiz kural veri, teslim ve performansı izler; gece karnesi her sabah hazırdır.",
    ],
  },
  k5: {
    kunye: ["iyimser–kötümser", "gün içi revizyon", "sabah webhook’u"],
    metin: [
      "İyimser–kötümser bant gün içinde güncellendikçe önceki hâlleri izde kalır; sabah koşusu bitince webhook sisteminize haber verir.",
      "PVQuant tahmini iyimser–kötümser bant olarak verir, gün içindeki her revizyonun izini tutar ve sabah koşusu bitince webhook gönderir.",
      "Sabah koşusu bittiğinde sisteminize haber gider. Gün boyunca bant değiştikçe neyin ne zaman değiştiğini görürsünüz.",
      "Gün içinde revize edilen bant, izi ve sabah webhook'u.",
      "Tek bir sayı riskin ne kadar olduğunu söylemez. Bant iyimser ve kötümser sınırı gösterir; gün içi revizyonlar iz bırakır, sabah koşusu webhook ile duyurulur.",
    ],
  },
};

/** Uygulanan seçim (ton numarası, 1–5). 2026-10-05: kullanıcı ton seçmeden «Sırayla devam et» dedi →
 *  öneri uygulandı (Ton 1, K4 için Ton 3); değiştirmek için yalnız bu satırı düzenleyip üreteçleri çalıştırın. */
export const SECIM = { k1: 1, k2: 1, k3: 1, k4: 3, k5: 1 };
export const secilenMetin = (id) => ACIKLAMALAR[id].metin[SECIM[id] - 1];
