/** Bölüm çubuğu çapaları (R30): sıra, sayfadaki bölüm sırasıyla BİREBİR aynıdır — scroll-spy
 *  "belge sırasında sonuncu" kuralı buna dayanır; yapi.test hem hedef kimlikleri hem sırayı
 *  Vitrin.tsx kompozisyonuna karşı bekçiler. SSS dahil: çubuk SSS okunurken ölü bölge bırakmasın
 *  (inceleme bulgusu). */
export const BOLUMLER = [
  ["karne", "Açık karne"],        // 29.10: karne Hero'dan hemen sonra (04 §3.4)
  ["katmanlar", "Dört adım"],
  ["isler", "İş birimleri"],
  ["rakamlar", "Rakamlar"],
  ["sss", "SSS"],
  ["basla", "Başvuru"],
] as const;
