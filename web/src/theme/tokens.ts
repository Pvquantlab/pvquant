/** PVQuant tasarim token'lari — frontend/design_tokens.py'nin TS karsiligi.
 *  Tek kaynak: renk/font/olcu buradan cekilir (Anayasa: ham hex yasak). */
export const renk = {
  marka: "#0F6E56",
  markaAcik: "#9FE1CB",
  markaKoyu: "#085041",
  lacivert: "#0E1D30",
  birincil: "#1F5288",
  metin: "#0F1B28",
  metinIkincil: "#5B6673",
  metinSoluk: "#898781",
  kenar: "#E2E6EA",
  sayfaZemin: "#F7F8F9",
  kartZemin: "#FFFFFF",
  yuzey: "#F1F3F4",
  basari: "#1E9E6A",
  uyari: "#C9502E",
  gercekelesen: "#E8940A",
  izgara: "#E1E0D9",
} as const;

export const yazi = {
  govde: "'IBM Plex Sans', system-ui, sans-serif",
  mono: "'IBM Plex Mono', ui-monospace, monospace",
} as const;

export const olcu = { yaricap: 8, kartYaricap: 12, hat: "0.5px" } as const;

/** Turkce sayi bicimi — styles.py'deki sayi_tr ile ayni sozlesme. */
export const sayiTr = (x: number, ondalik = 0): string =>
  new Intl.NumberFormat("tr-TR", {
    minimumFractionDigits: ondalik,
    maximumFractionDigits: ondalik,
  }).format(x);
