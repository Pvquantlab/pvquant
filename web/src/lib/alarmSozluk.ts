/** v2.528 (P10, ENV-F05-4): alarm kuralı adları TEK yerde — Santralim ayarları, zil (Kabuk) ve Kurulus aynı sözlüğü okur; arka uç
 *  alarm_service.KURAL_ETIKET ile birebir (web bekçisi test/panel/alarm-sozluk.test.ts). lib/sozluk.ts'den ayrı dosya: oradaki «düştü» yasağı
 *  iş durumu diline aittir, alarm adları («Tahmin doğruluğu düştü») arka uçla birebir olmak zorundadır. */
export const ALARM_KURALI: Record<string, string> = {
    veri_gelmedi: "Veri gelmedi", skill_dustu: "Tahmin doğruluğu düştü", pr_dustu: "Performans oranı düştü",
    clipping_orani_yuksek: "Kırpma oranı yüksek", iletisim_kesintisi: "İletişim kesintisi", kullanilabilirlik_dustu: "Kullanılabilirlik düştü",
    kgup_teslim_gecikti: "Program bildirimi hazırlanamadı", dengesizlik_asimi: "Dengesizlik maliyeti yüksek",
    kgup_revizyon_onerisi: "Program revizyonu önerisi",
    takvim_son_tarih: "Yaklaşan son tarih", ptf_dusuk_saat: "Yarın düşük fiyat saati",
    ariza_sayaci_yaklasti: "Arıza sayacı eşiğe yaklaştı", teminat_hatirlatma: "Teminat saati hatırlatması", sayac_eksik_saat: "Sayaç verisi eksik",
    avans_hatirlatma: "Avans ödeme hatırlatması",
    sensor_kalibrasyon: "Sensör kalibrasyonu vadesi geçti",
};
