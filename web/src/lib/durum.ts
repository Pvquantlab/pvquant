/** v2.605 (Faz 4 F4-K) — durum sözlükleri (bileşen dosyasından ayrı: fast refresh yalnız bileşen dışa aktaran dosyalarda çalışır).
 *  Müşteri dili; iç terim yok. Hesap durumu finansal sonuç meta'sından (F4-G), tahmin etiketi arşiv etiketinden (F4-B). */
export const HESAP_DURUMU: Record<string, { etiket: string; sinif: string; aciklama: string }> = {
  tam: { etiket: "tam hesap", sinif: "rozet-ok", aciklama: "bütün saatler ölçülü ve EPİAŞ fiyatlı" },
  kismi: { etiket: "kısmi hesap", sinif: "rozet-uyari", aciklama: "ölçüm ya da fiyat eksik saatler var" },
  senaryo: { etiket: "senaryo", sinif: "rozet-notr", aciklama: "senaryo fiyatı ya da senaryo pozisyonuyla" },
  hesaplanamadi: { etiket: "hesaplanamadı", sinif: "rozet-notr", aciklama: "ölçüm yok" },
};

/** Tahmin etiketi (API `etiket`: yayin | gun_ici | elle | null) → müşteri dili. */
export const TAHMIN_ETIKETI: Record<string, string> = { yayin: "gece tahmini", gun_ici: "gün içi güncelleme", elle: "elle istenen tahmin" };

/** v2.608 (Faz 5 F5-B/C): hizmet durumu sözlüğü — API `durum` kodu (durum_sozlugu.py) → müşteri sözcüğü ve rozet sınıfı. Sözcükler uçtaki `etiket`
 *  ile aynıdır; burada yalnız sınıf eşlemesi ve yedek etiket durur. «kritik» uyarı ailesinin dolgulu türevi (`.rozet-kritik`). */
export const HIZMET_DURUMU: Record<string, { etiket: string; sinif: string }> = {
  saglikli: { etiket: "Sağlıklı", sinif: "rozet-ok" },
  dikkat: { etiket: "Dikkat gerekiyor", sinif: "rozet-uyari" },
  kritik: { etiket: "Kritik", sinif: "rozet-uyari rozet-kritik" },
  veri_bekleniyor: { etiket: "Veri bekleniyor", sinif: "rozet-notr" },
  dogrulanamadi: { etiket: "Doğrulanamadı", sinif: "rozet-notr" },
  uygulanmiyor: { etiket: "Uygulanmıyor", sinif: "rozet-notr" },
};
export const hizmetDurumu = (kod: string | null | undefined) => HIZMET_DURUMU[kod ?? ""] ?? { etiket: kod ?? "—", sinif: "rozet-notr" };
