/** 24.10 performans turu — Intl biçimleyici önbelleği. `new Intl.DateTimeFormat/NumberFormat` kurmak pahalıdır
 *  (yüzlerce µs); saat serisi döngülerinde nokta başına yeniden kuruluyordu (Santralim gün gruplaması 384 nokta × 2:
 *  4× CPU'da 145 ms tek işlev). Aynı yerel ayar + seçenek için tek nesne; biçim sonucu birebir aynı. */
const tarihler = new Map<string, Intl.DateTimeFormat>();
const sayilar = new Map<string, Intl.NumberFormat>();
export function tarihBicimi(yerel: string, secenek: Intl.DateTimeFormatOptions): Intl.DateTimeFormat {
  const k = yerel + JSON.stringify(secenek);
  let b = tarihler.get(k);
  if (!b) { b = new Intl.DateTimeFormat(yerel, secenek); tarihler.set(k, b); }
  return b;
}
export function sayiBicimi(yerel: string, secenek: Intl.NumberFormatOptions): Intl.NumberFormat {
  const k = yerel + JSON.stringify(secenek);
  let b = sayilar.get(k);
  if (!b) { b = new Intl.NumberFormat(yerel, secenek); sayilar.set(k, b); }
  return b;
}


/** 26.10 ortak sözlük — göreli yaş: «3 dk önce», «10 saat önce», «2 gün önce» (iki panel aynı eşikler: 60 dk, 48 saat). */
export function yasTr(s: string | null | undefined, simdi = Date.now()): string {
  if (!s) return "—";
  const dk = Math.max(0, Math.round((simdi - new Date(s).getTime()) / 60000));
  if (dk < 60) return `${dk} dk önce`;
  if (dk < 48 * 60) return `${Math.round(dk / 60)} saat önce`;
  return `${Math.round(dk / 1440)} gün önce`;
}

/** 26.10 ortak sözlük — kısa tarih-saat «26.10.2026 12:33» (tarayıcının yerel saati; iki panel de yerel saat gösterir). */
/** 16.11: API dönem sınırları DIŞLAYICI bitişlidir (`donem_bit`, `ufuk.bit`: ertesi günün 00:00'ı; sorgular `ts_utc < :b`). Ekranda kapsanan SON gün
 *  yazılır; aksi hâlde «1 Eki – 1 Kas» 32 gün, «25 Ağu – 24 Eki» 61 gün gibi okunur. */
export function kapsananSonGun(bitIso: string): string {
  const d = new Date(bitIso.slice(0, 10) + "T12:00:00"); d.setDate(d.getDate() - 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** 16.11 (inceleme): kısa gün «1 Eki 2026» — öğlen sabitlenir, saat dilimi günü kaydırmaz; değer yoksa tire. */
export function gunYaz(iso: string | null | undefined): string {
  return iso ? tarihBicimi("tr-TR", { day: "numeric", month: "short", year: "numeric" }).format(new Date(iso.slice(0, 10) + "T12:00:00")) : "—";
}
/** Dışlayıcı bitişin kapsadığı son günü yazar; null-güvenli (Finansal etki ve Doğruluk künyeleri aynı yardımcıyı kullanır). */
export function sonGunYaz(bitIso: string | null | undefined): string {
  return bitIso ? gunYaz(kapsananSonGun(bitIso)) : "—";
}

/** 16.11 (yüzde işaret sırası): «%» ÖNEK, işaret ondan önce — «−%8,4», isaret=true ile «+%2,1»; sıfırda işaret yok. Değer yoksa tire.
 *  Eskiden `%${sayiTr(v)}` kalıbı «%−8,4» üretiyordu; Sayaç/Genel bakış ise «−%3,2» — tek kural burada. */
export function yuzdeTr(v: number | null | undefined, hane = 1, isaret = false): string {
  if (v == null || Number.isNaN(v)) return "—";
  const n = Number(Math.abs(v).toFixed(hane));
  const govde = sayiBicimi("tr-TR", { minimumFractionDigits: hane, maximumFractionDigits: hane }).format(n);
  const on = v < 0 && n !== 0 ? "\u2212" : isaret && v > 0 && n !== 0 ? "+" : "";
  return `${on}%${govde}`;
}

export function zamanTr(s: string | null | undefined): string {
  // 15.11.2026 (Genel bakış turu): gün ve ay iki haneli — «1.10.2026 03:55» ile «24.10.2026 06:12» aynı kolonda farklı genişlikteydi.
  return s ? new Intl.DateTimeFormat("tr-TR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(s)) : "—";
}

/** v2.641 (Parti 3, 02B-B6): Türkçe yazılmış sayıyı okur — «12.000,5» → 12000.5, «12,5» → 12.5, «12.5» → 12.5, «12.000» → 12000
 *  (yalnız nokta ve 3'lü gruplar → binlik ayracı). Boş ya da okunamayan → null. Number("12.000".replace(",", ".")) = 12 tuzağının yerine. */
export function sayiOku(metin: string | null | undefined): number | null {
  const s = (metin ?? "").trim().replace(/\s/g, "");
  if (s === "") return null;
  let duz: string;
  if (s.includes(",") && s.includes(".")) duz = s.replace(/\./g, "").replace(",", ".");
  else if (s.includes(",")) duz = s.replace(",", ".");
  else if (/^-?\d{1,3}(\.\d{3})+$/.test(s)) duz = s.replace(/\./g, "");
  else duz = s;
  const v = Number(duz);
  return Number.isFinite(v) ? v : null;
}
