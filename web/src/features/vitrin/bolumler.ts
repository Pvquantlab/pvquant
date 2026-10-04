/** Bölüm çubuğu çapaları (R30): sıra, sayfadaki bölüm sırasıyla BİREBİR aynıdır — scroll-spy
 *  "belge sırasında sonuncu" kuralı buna dayanır; yapi.test hem hedef kimlikleri hem sırayı
 *  Vitrin.tsx kompozisyonuna karşı bekçiler. SSS dahil: çubuk SSS okunurken ölü bölge bırakmasın
 *  (inceleme bulgusu). */
export const BOLUMLER = [
  ["katmanlar", "Dört adım"],
  ["para", "TL karşılığı"],
  ["isler", "Hangi iş için"],
  ["karne", "Açık karne"],
  ["rakamlar", "Rakamlar"],
  ["sss", "SSS"],
  ["basla", "Başvuru"],
] as const;
