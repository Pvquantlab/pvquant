import { useEffect, useState } from "react";
import { useDamgaSurumu } from "../../shell/damgaOlay";
import { api } from "../../api/client";
import type { MutabakatOzet, MutabakatSatir, SaatlikKiyas } from "../../api/types";
import { Kart, Kpi, Sayfa, sayiTr, SayfaIskeleti, YerTutucu } from "./parcalar";
import { ModulNotu } from "./Abonelik";   // v2.609 (Faz 6 F6-D): kapalı özellik notu (uyarı kipi)
import { Meta } from "../../lib/Meta";
import { tarihBicimi } from "../../lib/bicim";

/** v2.522 (P2b-1) — Mutabakat: müşterinin EPYS'den indirdiği «Uzlaştırma Bildirimi» dosyası (CSV/XLSX) yüklenir; kalemler tanınır ve PVQuant'ın
 *  yeniden hesabıyla (enerji dengesizlik tutarı, KGÜP sapma tutarı, lisanslı YEKDEM'de YEK alacağı) kalem kalem yan yana konur. Bildirim esastır;
 *  GÖP/GİP/DGP/GDDK/fark tutarı/SBDT/PİÜ/faiz/zam kalemleri yalnız bildirimden gösterilir. 02.11 ikinci inceleme: kapsamı farklı toplamlar yan yana
 *  konmaz (EPİAŞ toplamı ≠ karşılaştırılan kalemler), güvenilirlik etiketi (gerçek / kısmi / senaryo / doğrulanamadı), sürüm etiketi takvimle
 *  doğrulanır (EPİAŞ durumu doğrulanamaz), eşik PVQuant işletme ölçütüdür, yükleme tarihçesi. */
const DURUM: Record<string, { etiket: string; sinif: string }> = {
  uyumlu: { etiket: "uyumlu", sinif: "rozet-ok" }, fark: { etiket: "fark var", sinif: "rozet-uyari" }, senaryo: { etiket: "senaryo hesabı", sinif: "rozet-notr" },
  hesaplanamaz: { etiket: "yalnız bildirim", sinif: "rozet-notr" }, bildirimde_yok: { etiket: "bildirimde yok", sinif: "rozet-notr" }, hesap_yok: { etiket: "hesaplanamadı", sinif: "rozet-notr" } };
const GUVEN_SINIF: Record<string, string> = { gercek: "rozet-ok", kismi: "rozet-notr", senaryo: "rozet-uyari", veri_yok: "rozet-notr" };
const saatTr = (iso: string | null | undefined) => iso ? tarihBicimi("tr-TR", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(iso)) : "—";
const gunTr = (iso: string | null | undefined) => iso ? tarihBicimi("tr-TR", { day: "numeric", month: "short", year: "numeric" }).format(new Date(iso.slice(0, 10) + "T12:00:00")) : "—";
const ayAd = (d: string) => `${d.slice(5)}.${d.slice(0, 4)}`;
const tl = (v: number | null | undefined) => v == null ? "—" : sayiTr(v, 2);   // kuruşlu: bildirimdeki tutarla birebir
const binTl = (v: number | null | undefined) => v == null ? "—" : sayiTr(v / 1000, 1);
const yuzde = (p: number | null) => p == null ? "" : ` (${p < 0 ? "−" : "+"}%${sayiTr(Math.abs(p), 1)})`;
const sol = { textAlign: "left" as const };
const oncekiAy = () => { const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() - 1); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`; };

/** v2.527 (P2b-2): EPYS saatlik detayı ↔ PVQuant dökümü — yalnız ortak saatlerde (eş kapsamlı) kıyas, fark ayrıştırması, en büyük farklı saatler, CSV */
function SaatlikDetayKarti({ plantId, donem, uretim, ds }: { plantId: string; donem: string; uretim: string | null; ds: number }) {
  const [k, setK] = useState<SaatlikKiyas | null | undefined>(undefined);
  const [dosya, setDosya] = useState<File | null>(null); const [anahtar, setAnahtar] = useState(0);
  const [mesaj, setMesaj] = useState<{ metin: string; ton: "ok" | "hata" | "uyari" } | null>(null); const [mesgul, setMesgul] = useState(false);
  const yukle = () => api.saatlikKiyas(plantId, donem, uretim).then(setK, () => setK(null));
  useEffect(() => { setK(undefined); void yukle(); }, [plantId, donem, uretim, ds]);   // eslint-disable-line react-hooks/exhaustive-deps
  const gonder = () => {
    if (!dosya) { setMesaj({ metin: "Önce EPYS'den indirdiğiniz saatlik detay dosyasını seçin (XLSX ya da CSV).", ton: "hata" }); return; }
    setMesaj(null); setMesgul(true);
    api.saatlikYukle(plantId, dosya, donem).then((y) => {
      setMesaj({ metin: `Yüklendi: ${ayAd(y.donem)}, ${sayiTr(y.saat)} saat, ${EKRAN_AD[y.kaynak_ekran] ?? y.kaynak_ekran}; sütunlar: ${y.kolon_etiketleri.join(", ")}.${y.uyarilar.length ? ` ${y.uyarilar.join("; ")}.` : ""}`, ton: y.uyarilar.length ? "uyari" : "ok" });
      setDosya(null); setAnahtar((a) => a + 1); void yukle(); }).catch((e) => setMesaj({ metin: String((e as Error).message ?? e), ton: "hata" })).finally(() => setMesgul(false));
  };
  const t = k?.toplam; const a = k?.ayristirma;
  const fark = (v: number | null | undefined) => v == null ? "—" : `${v > 0 ? "+" : v < 0 ? "−" : ""}${sayiTr(Math.abs(v), 2)}`;
  return (
    <Kart baslik="Saatlik detay kıyası (EPYS)" alt="EPYS › Uzlaştırma › Uzlaştırma Dönemi Detay / Dengesizlik Uzlaştırma / KÜPST Detay ekranından indirdiğiniz saatlik dosya ile PVQuant dökümü yalnız iki tarafta da bulunan saatlerde karşılaştırılır (eş kapsamlı). EPİAŞ tutarı esastır."
      sag={k?.yuklu ? <span className="cip"><Meta items={[`${sayiTr(k.epias_saat)} EPİAŞ saati`, `${sayiTr(k.ortak_saat)} ortak`, k.uretim === "sayac" ? "üretim: sayaç" : "üretim: SCADA"]} /></span> : undefined}>
      <div className="form-izgara">
        <label className="girdi-etiket form-tam">Saatlik detay dosyası ({ayAd(donem)})<input key={anahtar} className="girdi" type="file" accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={(e) => setDosya(e.target.files?.[0] ?? null)} /></label>
        <div className="form-tam dugme-sira"><button className="dugme" onClick={gonder} disabled={mesgul}>{mesgul ? "Yükleniyor…" : "Yükle"}</button>
          {k?.yuklu ? <button className="dugme" onClick={() => api.saatlikKiyasIndir(plantId, donem, uretim).catch((e) => setMesaj({ metin: String((e as Error).message ?? e), ton: "hata" }))}>Saatlik kıyas (CSV)</button> : null}
          {mesaj && <span className={`ayar-durum ${mesaj.ton === "uyari" ? "" : mesaj.ton}`} style={mesaj.ton === "uyari" ? { color: "var(--amber-koyu, #8a5a00)" } : undefined}>{mesaj.metin}</span>}</div>
      </div>
      {k === undefined ? <YerTutucu yukseklik={60} /> : k === null ? <p className="soluk" style={{ margin: "10px 0 0" }}>Saatlik kıyas alınamadı.</p> : !k.yuklu ? (
        <p className="soluk" style={{ margin: "10px 0 0", fontSize: 13.5 }}>Bu dönem için saatlik detay yüklenmedi. Aylık bildirimle karşılaştırma kapsam farkı taşır; saatlik dosya yüklenince fark saat bazında ve eş kapsamlı görülür.</p>
      ) : k.ortak_saat === 0 ? (
        <p className="soluk" style={{ margin: "10px 0 0", fontSize: 13.5 }}>{sayiTr(k.epias_saat)} EPİAŞ saati yüklü ama PVQuant dökümüyle ortak saat yok (döküm bu dönem için {sayiTr(k.pv_saat ?? 0)} saat).</p>
      ) : (
        <>
          <div className="ızgara satir-4" style={{ margin: "12px 0" }}>
            <Kpi etiket={`Ortak saat (${ayAd(k.donem)})`} deger={sayiTr(k.ortak_saat)} alt={`EPİAŞ ${sayiTr(k.epias_saat)}, PVQuant ${sayiTr(k.pv_saat ?? 0)} saat${k.yalniz_epias_saat ? `; yalnız EPİAŞ'ta ${sayiTr(k.yalniz_epias_saat)}` : ""}${k.yalniz_pvquant_saat ? `; yalnız PVQuant'ta ${sayiTr(k.yalniz_pvquant_saat)}` : ""}`} />
            <Kpi etiket="Dengesizlik neti — EPİAŞ" deger={t?.edt_net_epias_tl != null ? binTl(t.edt_net_epias_tl) : "—"} birim={t?.edt_net_epias_tl != null ? "bin TL" : undefined} alt={t?.edt_net_epias_tl != null ? `alacak ${sayiTr(t.edt_poz_epias_tl ?? 0, 2)} − borç ${sayiTr(t.edt_neg_epias_tl ?? 0, 2)} TL` : "dosyada EDT sütunu yok"} />
            <Kpi etiket="Dengesizlik neti — PVQuant" deger={binTl(t?.edt_net_pvquant_tl)} birim="bin TL" alt={`alacak ${sayiTr(t?.edt_poz_pvquant_tl ?? 0, 2)} − borç ${sayiTr(t?.edt_neg_pvquant_tl ?? 0, 2)} TL; aynı ${sayiTr(k.ortak_saat)} saat`} />
            <Kpi etiket="Eş kapsamlı dengesizlik farkı" bilgi="Yalnız dengesizlik tutarı (EDT), yalnız ortak saatlerde: PVQuant − EPİAŞ. Artı: PVQuant daha çok alacak ya da daha az borç hesaplıyor. KÜPST ayrı kalemdir (altta); bu sayı toplam uzlaştırma farkı değildir. Aylık bildirimle karşılaştırmanın aksine kapsam farkı taşımaz."
              deger={t?.edt_net_fark_tl != null ? fark(t.edt_net_fark_tl) : "—"} birim={t?.edt_net_fark_tl != null ? "TL" : undefined} ton={t?.edt_net_fark_tl != null && Math.abs(t.edt_net_fark_tl) > 50 ? "amber" : undefined}
              alt={t?.kupst_fark_tl != null ? `KÜPST borcu ayrı: EPİAŞ ${sayiTr(t.kupst_epias_tl ?? 0, 2)}, PVQuant ${sayiTr(t.kupst_pvquant_tl, 2)} TL; fark ${fark(t.kupst_fark_tl)} (artı: PVQuant daha çok KÜPST borcu)` : "KÜPST sütunu yok"} />
          </div>
          {a && (
            <p style={{ margin: "0 0 10px", fontSize: 13.5, lineHeight: 1.5 }}><b>Fark ayrıştırması ({sayiTr(a.edt_farki_saat ?? 0)} saatte dengesizlik tutarı farklı, {sayiTr(a.uyumlu_saat ?? 0)} uyumlu):</b>{" "}
              {a.fiyat_karsilastirildi ? `${sayiTr(a.fiyat_farki_saat)} saatte fiyat (PTF/SMF)` : "fiyat karşılaştırılmadı"}; {a.uretim_karsilastirildi ? `${sayiTr(a.uretim_farki_saat)} saatte üretim (UEVM ↔ PVQuant ${k.uretim === "sayac" ? "sayaç" : "SCADA"})` : "üretim karşılaştırılmadı (UEVM sütunu yok)"};{" "}
              {a.program_karsilastirildi ? `${sayiTr(a.program_farki_saat)} saatte program (BUDÜP ↔ PVQuant programı)` : "program karşılaştırılmadı (BUDÜP sütunu yok)"};{" "}
              {a.pozisyon_karsilastirildi ? `${sayiTr(a.pozisyon_farki_saat ?? 0)} saatte dengesizlik miktarı (EDM ↔ PVQuant sapması: pozisyon / ikili anlaşma / DSG payı)` : "dengesizlik miktarı karşılaştırılmadı (EDM sütunu yok)"};{" "}
              {sayiTr(a.yuvarlama_saat ?? 0)} saatte yuvarlama; {sayiTr(a.kural_farki_saat)} saatte girdiler eşitken tutar farklı (kural / sistem yönü / hesap). <span className="soluk">{a.not}</span></p>)}
          {k.en_buyuk.length > 0 && (
            <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 13 }}>
              <thead><tr><th style={sol}>Saat (en büyük fark)</th><th>PTF EPİAŞ / PVQuant</th><th>UEVM / gerçekleşen (MWh)</th><th>BUDÜP / program (MWh)</th><th title="EPİAŞ dengesizlik miktarı (pozitif − negatif EDM) / PVQuant sapması (gerçekleşen − pozisyon); yön PVQuant'ın kullandığı sistem yönü">EDM / sapma (MWh) · yön</th><th>EDT net EPİAŞ</th><th>EDT net PVQuant</th><th>Fark (TL)</th><th style={sol}>Neden</th></tr></thead>
              <tbody>{k.en_buyuk.map((s) => (
                <tr key={s.zaman}><td style={sol} className="mono">{s.zaman}</td>
                  <td className="mono">{s.ptf_epias != null ? sayiTr(s.ptf_epias, 2) : "—"} / {s.ptf_pvquant != null ? sayiTr(s.ptf_pvquant, 2) : "—"}</td>
                  <td className="mono">{s.uevm_mwh != null ? sayiTr(s.uevm_mwh, 3) : "—"} / {s.gerceklesen_pvquant_mwh != null ? sayiTr(s.gerceklesen_pvquant_mwh, 3) : "—"}</td>
                  <td className="mono">{s.budup_mwh != null ? sayiTr(s.budup_mwh, 3) : "—"} / {s.program_pvquant_mwh != null ? sayiTr(s.program_pvquant_mwh, 3) : "—"}{s.program_kaynak === "oneri" ? <span className="soluk"> öneri</span> : null}</td>
                  <td className="mono">{s.edm_epias_mwh != null ? sayiTr(s.edm_epias_mwh, 3) : "—"} / {s.sapma_pvquant_mwh != null ? sayiTr(s.sapma_pvquant_mwh, 3) : "—"}{s.yon ? <span className="soluk"> {YON_AD[s.yon] ?? s.yon}</span> : null}</td>
                  <td className="mono">{s.edt_net_epias_tl != null ? sayiTr(s.edt_net_epias_tl, 2) : "—"}</td><td className="mono">{s.edt_net_pvquant_tl != null ? sayiTr(s.edt_net_pvquant_tl, 2) : "—"}</td>
                  <td className="mono">{fark(s.edt_fark_tl)}</td><td style={sol} title={s.nedenler.map((n) => k.neden_aciklama?.[n] ?? NEDEN_ACIKLAMA[n] ?? n).join(" · ")}>{s.nedenler.length ? s.nedenler.map((n) => NEDEN_AD[n] ?? n).join(", ") : "—"}</td></tr>))}</tbody>
            </table></div>)}
          <p className="soluk" style={{ fontSize: 13, margin: "8px 0 0" }}>{k.not} Toleranslar: fiyat {sayiTr(k.tolerans.fiyat_tl_mwh, 2)} TL/MWh, miktar {sayiTr(k.tolerans.mwh * 1000, 1)} kWh, tutar {sayiTr(k.tolerans.tl, 2)} TL.{k.yuklemeler.length ? ` Kullanılan yükleme: ${k.yuklemeler.map((y) => `${EKRAN_AD[y.kaynak_ekran] ?? y.kaynak_ekran} (${saatTr(y.zaman)}, ${sayiTr(y.saat)} saat${y.versiyon ? `, sürüm ${y.versiyon}` : ""})`).join("; ")}.` : ""}</p>
        </>)}
    </Kart>
  );
}
/** 03.11 inceleme: sürüm etiketi dosyadan/kullanıcıdan gelir; resmî durum EPİAŞ'tan doğrulanmaz — takvimden önceyse «resmî doğrulama bekleniyor» */
const surumDurumu = (bil: { surum_etiket: string; surum_kaynagi?: string | null; surum_dogrulama?: { durum: string } | null }) =>
  bil.surum_dogrulama?.durum === "takvimden_once" ? `${bil.surum_etiket} (${bil.surum_kaynagi === "kullanici" ? "seçiminizde" : "dosyada"}) — resmî doğrulama bekleniyor` : `${bil.surum_etiket} — resmî durum doğrulanmadı`;
const EKRAN_AD: Record<string, string> = { detay: "Uzlaştırma Dönemi Detay", dengesizlik: "Dengesizlik Uzlaştırma", kupst: "KÜPST Detay" };
const NEDEN_AD: Record<string, string> = { fiyat: "fiyat", uretim: "üretim", program: "program", pozisyon: "EDM (pozisyon)", yuvarlama: "yuvarlama", kural: "kural / yön" };
const NEDEN_ACIKLAMA: Record<string, string> = { fiyat: "PTF ya da SMF farklı (fiyat kaynağı / sürümü)", uretim: "UEVM ile PVQuant gerçekleşeni farklı", program: "BUDÜP ile PVQuant programı farklı",
  pozisyon: "üretim ve program eşit ama EPİAŞ'ın dengesizlik miktarı PVQuant sapmasından farklı — ikili anlaşma / piyasa pozisyonu ya da DSG grup payı", yuvarlama: "girdiler tolerans içinde ve tutar farkı küçük — yuvarlama",
  kural: "fiyat, üretim, program ve miktar eşitken tutar farklı — sistem yönü (k/l katsayıları), kural sürümü ya da hesap" };
const YON_AD: Record<string, string> = { fazla: "sistem fazlası", acik: "sistem açığı", dengede: "dengede", enerji_fazlasi: "sistem fazlası", enerji_acigi: "sistem açığı" };

export function Mutabakat({ plantId }: { plantId: string }) {
  const ds = useDamgaSurumu();
  const [o, setO] = useState<MutabakatOzet | null | undefined>(undefined);
  const [donem, setDonem] = useState<string | null>(null);
  const [surum, setSurum] = useState<string | null>(null);
  const [uretim, setUretim] = useState<string | null>(null);   // v2.526 (P4a-2): boş = santral ayarı
  const [mesaj, setMesaj] = useState<{ metin: string; ton: "ok" | "hata" | "uyari" } | null>(null);
  const [dosya, setDosya] = useState<File | null>(null);
  const [dosyaAnahtar, setDosyaAnahtar] = useState(0);   // yükleme sonrası dosya alanı sıfırlanır
  const [yukDonem, setYukDonem] = useState(oncekiAy());
  const [yukSurum, setYukSurum] = useState("");
  const [yukleniyor, setYukleniyor] = useState(false);
  const yukle = () => api.mutabakat(plantId, donem, surum, uretim).then(setO, () => setO(null));
  useEffect(() => { setO(undefined); void yukle(); }, [plantId, ds, donem, surum, uretim]);   // eslint-disable-line react-hooks/exhaustive-deps
  const gonder = () => {
    if (!dosya) { setMesaj({ metin: "Önce EPYS'den indirdiğiniz bildirim dosyasını seçin (CSV ya da XLSX).", ton: "hata" }); return; }
    setMesaj(null); setYukleniyor(true);
    api.mutabakatYukle(plantId, dosya, yukDonem || null, yukSurum || null).then((y) => {
      const sd = y.surum_dogrulama;
      const metin = `Yüklendi: ${ayAd(y.donem)} ${y.surum === "nihai" ? "nihai" : "ön"} bildirim (${y.surum_kaynagi === "dosya" ? "durum dosyadan" : y.surum_kaynagi === "kullanici" ? "sürüm seçiminiz" : "varsayılan"}), ${sayiTr(y.kalem_sayisi)} kalem.`
        + (sd?.durum === "takvimden_once" ? ` ${sd.aciklama}` : "") + (y.uyarilar.length ? ` ${y.uyarilar.join("; ")}.` : "");
      setMesaj({ metin, ton: y.uyarilar.length || sd?.durum === "takvimden_once" ? "uyari" : "ok" });
      setDosya(null); setDosyaAnahtar((k) => k + 1); setDonem(y.donem); setSurum(y.surum); }).catch((e) => setMesaj({ metin: String((e as Error).message ?? e), ton: "hata" })).finally(() => setYukleniyor(false));
  };
  if (o === undefined) return <Sayfa baslik="Mutabakat"><SayfaIskeleti kpi={4} kart={2} /></Sayfa>;
  if (o === null) return <Sayfa baslik="Mutabakat"><p className="soluk">Mutabakat alınamadı.</p></Sayfa>;
  const m = o.secili; const oz = m.ozet; const bil = m.bildirim; const g = m.guvenilirlik; const sd = bil?.surum_dogrulama;
  const donemler = Array.from(new Set([...o.donemler.map((d) => d.donem), m.donem])).sort().reverse();
  const hesaplanan = m.satirlar.filter((s) => s.hesaplanir); const digerler = m.satirlar.filter((s) => !s.hesaplanir);
  const satir = (s: MutabakatSatir) => (
    <tr key={s.kod} className={s.hesaplanir ? undefined : "soluk"}>
      <td style={sol}>{s.etiket}{s.kalem_ad && s.kalem_ad !== s.etiket ? <span className="soluk"> · {s.kalem_ad}</span> : null}{s.kaba ? <span className="soluk" title={s.pvquant_not ?? ""}> · kaba hesap</span> : null}</td>
      <td className="mono">{tl(s.bildirim_alacak_tl)}</td><td className="mono">{tl(s.bildirim_borc_tl)}</td>
      <td className="mono">{s.hesaplanir ? tl(s.pvquant_alacak_tl) : "—"}</td><td className="mono">{s.hesaplanir ? tl(s.pvquant_borc_tl) : "—"}</td>
      <td className="mono" style={{ whiteSpace: "nowrap" }} title={s.fark_alacak_tl != null ? `alacak farkı ${sayiTr(s.fark_alacak_tl, 2)} TL; borç farkı ${sayiTr(s.fark_borc_tl ?? 0, 2)} TL` : undefined}>
        {s.fark_tl != null ? `${s.fark_tl > 0 ? "+" : ""}${sayiTr(s.fark_tl, 2)}${yuzde(s.fark_pct)}` : "—"}</td>
      <td><span className={`rozet rozet-kucuk ${DURUM[s.durum].sinif}`} title={s.dogrulama === "kismi" ? "Kısmi kapsam: EPİAŞ tutarı bütün ayı, PVQuant tutarı yalnız hesaplanan saatleri kapsar; hüküm tam ay verisiyle kesinleşir" : (s.bilesen_notu ?? s.pvquant_not ?? undefined)}>{DURUM[s.durum].etiket}{s.dogrulama === "kismi" && (s.durum === "uyumlu" || s.durum === "fark") ? " · kısmi" : ""}</span>{s.bilesen_notu ? <div className="soluk" style={{ fontSize: 12, marginTop: 2 }}>{s.bilesen_notu}</div> : null}</td>
    </tr>);
  return (
    <Sayfa baslik="Mutabakat" alt="EPİAŞ uzlaştırma bildirimini PVQuant'ın yeniden hesabıyla kalem kalem karşılaştırın. EPİAŞ bildirimi esastır; PVQuant tutarları yeniden hesaptır, fark bilgi amaçlıdır."
      sag={<span className="dugme-sira">
        <ModulNotu kod="mutabakat" />
        <select className="girdi" value={m.donem} onChange={(e) => setDonem(e.target.value)} aria-label="Fatura dönemi">
          {donemler.map((d) => <option key={d} value={d}>{ayAd(d)}</option>)}</select>
        <select className="girdi" value={surum ?? ""} onChange={(e) => setSurum(e.target.value || null)} aria-label="Bildirim sürümü">
          <option value="">son yüklenen sürüm</option>{o.surumler.map((s) => <option key={s.kod} value={s.kod}>{s.etiket}</option>)}</select>
        <select className="girdi" style={{ maxWidth: "calc(100vw - 48px)" }} value={uretim ?? ""} onChange={(e) => setUretim(e.target.value || null)} aria-label="Üretim girdisi" title="Yeniden hesapta gerçekleşen üretimin kaynağı. «Santral ayarı» Sayaç sayfasındaki kalıcı seçimdir; öbür ikisi bu sayfada geçici görünümdür (ayarla aynı olan seçenek aynı sonucu verir).">
          <option value="">üretim: santral ayarı — {o.uretim_ayari === "sayac" ? "sayaç" : "SCADA"}</option>{o.uretim_secenekleri.map((s) => <option key={s.kod} value={s.kod}>üretim: {s.kod === "sayac" ? "sayaç, yüklü saatlerde" : "SCADA"} (geçici)</option>)}</select></span>}>
      <div className="ızgara satir-4" style={{ marginBottom: 14 }}>
        <Kpi etiket={`EPİAŞ toplam alacak (${m.donem_etiket})`} bilgi="EPİAŞ bildirimindeki bütün alacak kalemlerinin toplamı (GÖP, GİP, YEK, dengesizlik, …); «Toplam» satırı hariç. PVQuant bu toplamın yalnız bir bölümünü yeniden hesaplar."
          deger={binTl(oz.bildirim_alacak_tl)} birim={oz.bildirim_alacak_tl != null ? "bin TL" : undefined}
          alt={bil ? `${surumDurumu(bil)}; yükleme ${saatTr(bil.zaman)}` : "bu dönem için bildirim yüklenmedi"} />
        <Kpi etiket="EPİAŞ toplam borç" bilgi="EPİAŞ bildirimindeki bütün borç kalemlerinin toplamı (dengesizlik, KÜPST, PİÜ, …); «Toplam» satırı hariç."
          deger={binTl(oz.bildirim_borc_tl)} birim={oz.bildirim_borc_tl != null ? "bin TL" : undefined}
          alt={bil ? "tüm kalemler; kapsamı PVQuant hesabından geniştir" : "bildirim yok"} />
        <Kpi etiket="PVQuant yeniden hesaplanan tutar" bilgi="Yalnız santral verisinden hesaplanabilen kalemler: enerji dengesizlik tutarı, KGÜP sapma tutarı (lisanslı YEKDEM'de YEK alacağı). Net = alacak − borç; eksi tutar santralin ödediğidir. EPİAŞ toplamıyla değil, aynı kalemlerin EPİAŞ tutarıyla karşılaştırılır."
          deger={binTl(oz.pvquant_net_tl)} birim={oz.pvquant_net_tl != null ? "bin TL" : undefined}
          ikinci={oz.bildirim_kiyas_net_tl != null ? { etiket: "aynı kalemlerde EPİAŞ", deger: `${binTl(oz.bildirim_kiyas_net_tl)} bin TL` } : undefined}
          alt={oz.kapsam ? `net; kapsam: ${oz.kapsam} (${sayiTr(m.pvquant.saat)} saat)` : m.pvquant.saat ? "karşılaştırılacak kalem yok" : "bu dönem için saatlik veri yok"} />
        <Kpi etiket="Hesaplama farkı (aylık bildirim)" bilgi="Aylık bildirim ↔ PVQuant: PVQuant net − EPİAŞ net, yalnız karşılaştırılan kalemlerde (dengesizlik + KÜPST). Kapsam farklıdır: EPİAŞ bütün ay, PVQuant hesaplanan saatler. Saatlik detay yüklüyse ikinci satırdaki eş kapsamlı dengesizlik farkı ayrı bir ölçüdür; ikisi birbirinin yerine geçmez. Artı: PVQuant daha çok alacak hesaplıyor; eksi: daha çok borç. Uyum ölçütü PVQuant'ın işletme ölçütüdür, mevzuat toleransı değildir."
          deger={oz.fark_tl != null ? `${oz.fark_tl > 0 ? "+" : ""}${binTl(oz.fark_tl)}` : "—"} birim={oz.fark_tl != null ? "bin TL" : undefined}
          ton={oz.farkli > 0 ? "amber" : undefined}
          ikinci={m.saatlik_detay?.yuklu && m.saatlik_detay.toplam?.edt_net_fark_tl != null ? { etiket: `saatlik eş kapsamlı, ${sayiTr(m.saatlik_detay.ortak_saat)} saat (yalnız dengesizlik)`, deger: `${m.saatlik_detay.toplam.edt_net_fark_tl > 0 ? "+" : m.saatlik_detay.toplam.edt_net_fark_tl < 0 ? "−" : ""}${sayiTr(Math.abs(m.saatlik_detay.toplam.edt_net_fark_tl), 2)} TL` } : undefined}
          alt={oz.kiyaslanan ? (g.durum === "senaryo" ? `${sayiTr(oz.kiyaslanan)} kalem; senaryo hesabı, uyum sınıflandırması yapılmadı` : g.durum === "kismi" ? `aylık bildirim ↔ PVQuant, ${sayiTr(oz.kiyaslanan)} kalem: ${sayiTr(oz.uyumlu)} uyumlu, ${sayiTr(oz.farkli)} farklı — kapsam kısmi (${sayiTr(oz.kapsam_saat ?? m.pvquant.saat)}/${sayiTr(oz.beklenen_saat ?? 0)} saat), fark doğrulanmış değil` : `${sayiTr(oz.kiyaslanan)} kalem: ${sayiTr(oz.uyumlu)} uyumlu, ${sayiTr(oz.farkli)} farklı; ölçüt bileşen başına %${sayiTr(m.uyum.pct)} ya da ${sayiTr(m.uyum.tl)} TL`) : "kıyaslanacak kalem yok"} />
      </div>
      <div className="ızgara-cift">
        <Kart baslik="EPİAŞ bildirimi yükleme" alt="EPYS › Uzlaştırma › Uzlaştırma Bildirimi ekranından indirdiğiniz dosya (CSV ya da XLSX). Dönem ve uzlaştırma durumu dosyadan okunur; okunamazsa buradaki seçim geçerlidir.">
          <div className="form-izgara">
            <label className="girdi-etiket form-tam">Dosya<input key={dosyaAnahtar} className="girdi" type="file" accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={(e) => setDosya(e.target.files?.[0] ?? null)} /></label>
            <label className="girdi-etiket">Fatura dönemi (ay)<input className="girdi" type="month" value={yukDonem} onChange={(e) => setYukDonem(e.target.value)} /></label>
            <label className="girdi-etiket">Sürüm (dosyada yoksa)<select className="girdi" value={yukSurum} onChange={(e) => setYukSurum(e.target.value)}>
              <option value="">dosyadan oku</option>{o.surumler.map((s) => <option key={s.kod} value={s.kod}>{s.etiket}</option>)}</select></label>
            <div className="form-tam dugme-sira"><button className="dugme" onClick={gonder} disabled={yukleniyor}>{yukleniyor ? "Yükleniyor…" : "Yükle"}</button>
              {mesaj && <span className={`ayar-durum ${mesaj.ton === "uyari" ? "" : mesaj.ton}`} style={mesaj.ton === "uyari" ? { color: "var(--amber-koyu, #8a5a00)" } : undefined}>{mesaj.metin}</span>}</div>
          </div>
          <p className="form-not" style={{ marginTop: 10, fontSize: 13.5 }}>Her yükleme ayrı sürüm olarak saklanır; önceki yüklemeler silinmez, dönem ve sürüm başına en yeni yükleme hesaba girer. Ön bildirim (izleyen ayın 11'i) ve nihai bildirim (15'i, iş günü) ayrı yüklenebilir; dosyadaki «Uzlaştırma Durumu» alanı seçiminizden üstündür.</p>
          {o.donemler.length > 0 && (
            <div className="grafik-kaydir" style={{ marginTop: 10 }}><table className="veri" style={{ fontSize: 13.5 }}>
              <thead><tr><th style={sol}>Dönem</th><th style={sol}>Sürüm</th><th style={sol}>Yükleme</th><th style={sol} title="Sürüm etiketinin resmî takvimle tutarlılığı; EPİAŞ'ın uzlaştırma durumu dosyadan doğrulanamaz">Takvim</th><th style={sol}>Dosya</th><th>Kalem</th></tr></thead>
              <tbody>{o.donemler.map((d) => (
                <tr key={d.yukleme_id} style={d.yukleme_id === bil?.yukleme_id ? { fontWeight: 600 } : !d.gecerli ? { opacity: 0.7 } : undefined}>
                  <td style={sol}><button className="dugme kucuk" title="Bu dönemi ve sürümü göster" onClick={() => { setDonem(d.donem); setSurum(d.surum); }}>{ayAd(d.donem)}</button></td>
                  <td style={sol}>{d.surum_etiket}{d.surum_kaynagi === "dosya" ? "" : <span className="soluk"> · {d.surum_kaynagi === "kullanici" ? "seçim" : "varsayılan"}</span>}{!d.gecerli && <span className="soluk"> · eski yükleme</span>}</td>
                  <td style={{ ...sol, whiteSpace: "nowrap" }}>{saatTr(d.zaman)}</td>
                  <td style={sol}><span className={`rozet rozet-kucuk ${d.surum_dogrulama.durum === "takvimden_once" ? "rozet-uyari" : "rozet-notr"}`} title={`${d.surum_dogrulama.aciklama} Takvim tarihi: ${gunTr(d.surum_dogrulama.beklenen_tarih)}.`}>{d.surum_dogrulama.durum === "takvimden_once" ? "takvimden önce" : "doğrulanmadı"}</span></td>
                  <td style={{ ...sol, whiteSpace: "normal" }}>{d.dosya_adi ?? "—"}</td><td className="mono">{sayiTr(d.kalem_sayisi)}</td></tr>))}</tbody>
            </table></div>)}
        </Kart>
        <Kart baslik="Hesaplamada kullanılan veriler" alt="PVQuant'ın bu dönem için saatlik yeniden hesabının girdileri; sonucun güvenilirliği bunlara bağlıdır"
          sag={<span className={`rozet rozet-kucuk ${GUVEN_SINIF[g.durum]}`} title={g.nedenler.join("; ") || "dönemin bütün saatleri EPİAŞ fiyatı ve bildirilen KGÜP ile hesaplandı"}>{g.etiket}</span>}>
          {(() => { const uk = m.pvquant.uretim_kaynak; const sy = m.pvquant.sayac; const sayacla = uk?.secim === "sayac" && uk.sayac_olculmus_saat + uk.sayac_tahmini_saat > 0;
            return (<>
          <ul className="not-listesi" style={{ fontSize: 13.5 }}>
            <li><b>Kapsam:</b> {sayiTr(m.pvquant.saat)}{m.pvquant.beklenen_saat ? ` / ${sayiTr(m.pvquant.beklenen_saat)} saat` : " saat"}{m.pvquant.son_saat ? `; son üretim verisi ${m.pvquant.son_saat}` : ""}{m.pvquant.hesaplanamayan_saat ? `; ${sayiTr(m.pvquant.hesaplanamayan_saat)} saat hesaplanamadı` : ""}</li>
            <li><b>Üretim:</b> {sayacla && uk ? <>{sayiTr(uk.sayac_olculmus_saat + uk.sayac_tahmini_saat)} saat sayaç ({sayiTr(uk.sayac_olculmus_saat)} ölçülmüş{uk.sayac_tahmini_saat ? `, ${sayiTr(uk.sayac_tahmini_saat)} tahmini` : ""}){uk.scada_saat ? `, ${sayiTr(uk.scada_saat)} saat SCADA (sayaç satırı olmayan saatler)` : ""}{uk.sayac_kullanilmayan_saat ? `; ${sayiTr(uk.sayac_kullanilmayan_saat)} sayaç saati SCADA satırı olmadığından hesaba girmedi` : ""}</>
              : <>SCADA ölçümü, {sayiTr(m.pvquant.saat)} saat{uk?.secim === "sayac" ? " (sayaç seçili ama dönemde sayaç verisi yok)" : ""}{sy?.yuklu ? `; Sayaç sayfasında ${sayiTr(sy.yuklu)} / ${sayiTr(sy.toplam_saat)} saat sayaç verisi var, hesaba girmedi` : ""}</>}</li>
            <li><b>Program:</b> {m.pvquant.bildirilen_saat ? `${sayiTr(m.pvquant.bildirilen_saat)} saat bildirilen KGÜP${m.pvquant.bildirilen_saat < m.pvquant.saat ? `, ${sayiTr(m.pvquant.saat - m.pvquant.bildirilen_saat)} saat PVQuant önerisi` : ""}` : "PVQuant önerisi (bildirilen KGÜP yüklü değil)"}</li>
            <li><b>Fiyat:</b> {m.pvquant.senaryo_saat ? `${sayiTr(m.pvquant.senaryo_saat)} saatte senaryo fiyatı (EPİAŞ verisi yok)` : "EPİAŞ saatlik PTF, SMF ve sistem yönü"}</li>
            {bil && <li><b>Bildirim sürümü:</b> {surumDurumu(bil)}{sd?.durum === "takvimden_once" ? ` (resmî yayın en erken ${sd.beklenen_tarih.split("-").reverse().join(".")})` : ""}</li>}
            {m.pvquant.hata && <li className="soluk">Hesap alınamadı: {m.pvquant.hata}</li>}
          </ul>
          {m.program_notu && <p className="form-not" style={{ marginTop: 8, fontSize: 13.5, color: "var(--amber-koyu, #8a5a00)" }}>{m.program_notu}</p>}
          {m.eylem && <p className="form-not" style={{ marginTop: 8, fontSize: 13.5 }}><b>Ne yapmalı:</b> {m.eylem}</p>}
          <details className="aciklama" style={{ marginTop: 10 }}>
            <summary>Ayrıntılar: kural sürümü, güvenilirlik nedenleri, sayaç ile SCADA, sürüm takvimi</summary>
            {m.pvquant.kural_surumu && <p style={{ margin: "6px 0 0" }}><b>Kural sürümü:</b> {m.pvquant.kural_surumu}{m.pvquant.kupst_kaynak ? <>; KÜPST katsayıları: {m.pvquant.kupst_kaynak}{m.pvquant.kupst_gecersiz_kilma ? <span style={{ color: "var(--amber-koyu, #8a5a00)" }}> — resmî tablo yerine santral ayarındaki değer kullanıldı, EPİAŞ ile fark buradan doğabilir</span> : null}</> : null}</p>}   {/* v2.541: kupst_kaynak */}
            {g.nedenler.length > 0 && <p style={{ margin: "6px 0 0" }}><b>{g.etiket}:</b> {g.nedenler.join("; ")}</p>}
            <p style={{ margin: "6px 0 0" }}><b>Üretim kaynağı:</b> {sayacla ? "Sayaç dosyasının uzlaştırmaya esas UEVM ile aynı olduğu doğrulanmaz; sayaç satırı olmayan saatlerde SCADA kullanılır (Doğruluk sayfasındaki 90 günlük hesap SCADA ile kalır)." : "SCADA brüt üretimdir, EPİAŞ uzlaştırmaya esas sayaç verisi (UEVM) değildir; sayaç net veriştir. Hesabı sayaçla görmek için yukarıdan «üretim: sayaç» seçin ya da Sayaç sayfasında kalıcı ayarlayın."}
              {uk?.kiyas && uk.kiyas.edt_net_fark_tl != null ? <> Aynı dönem SCADA ile hesaba göre: dengesizlik neti {uk.kiyas.edt_net_fark_tl >= 0 ? "+" : "−"}{sayiTr(Math.abs(uk.kiyas.edt_net_fark_tl), 2)} TL ({uk.kiyas.edt_net_fark_tl >= 0 ? "sayaçla daha lehte" : "sayaçla daha aleyhte"}){uk.kiyas.kupst_fark_tl ? <>, KÜPST borcu {uk.kiyas.kupst_fark_tl >= 0 ? "+" : "−"}{sayiTr(Math.abs(uk.kiyas.kupst_fark_tl), 2)} TL ({uk.kiyas.kupst_fark_tl >= 0 ? "daha aleyhte" : "daha lehte"})</> : null}.</> : null}
              {sy?.yuklu && sy.olc_fark_pct != null ? <> Ölçülmüş saatlerde sayaç − SCADA {sy.olc_fark_pct < 0 ? "−" : "+"}%{sayiTr(Math.abs(sy.olc_fark_pct), 1)}.</> : null}</p>
            {sd && <p style={{ margin: "6px 0 0", color: sd.durum === "takvimden_once" ? "var(--amber-koyu, #8a5a00)" : undefined }}><b>Sürüm:</b> {sd.aciklama}</p>}
          </details>
          {m.itiraz && <details className="aciklama" style={{ marginTop: 6 }}>   {/* v2.538 (EK-3 DK-557/DK-395): itiraz süreleri ve geriye dönük düzeltme penceresi */}
            <summary>İtiraz süreleri ve geriye dönük düzeltme ({m.donem_etiket})</summary>
            <ul className="not-listesi" style={{ fontSize: 13.5, marginTop: 6 }}>
              <li><b>Ön bildirime itiraz:</b> {m.itiraz.on_bildirim_itiraz_son.split(" ")[0].split("-").reverse().join(".")} 17:30'a kadar (DUY m.132/B(1))</li>
              <li><b>Faturaya itiraz:</b> tebliğden itibaren 60 gün içinde yazılı; takvime göre {m.itiraz.fatura_itiraz_60_gun.split("-").reverse().join(".")} (m.133(1))</li>
              <li><b>Geriye dönük itiraz:</b> başvuru tarihinden en fazla {sayiTr(m.itiraz.geriye_donuk.pencere_ay)} ay önceki fatura dönemi; bu dönem için son başvuru {m.itiraz.geriye_donuk.son_basvuru.split("-").reverse().join(".")}
                {m.itiraz.geriye_donuk.gecti ? " (geçti)" : ` (${sayiTr(m.itiraz.geriye_donuk.kalan_gun)} gün kaldı)`}; sonuç {sayiTr(m.itiraz.geriye_donuk.sonuc_ay)} ay içinde, düzeltme GDDK kalemiyle sonraki faturada (m.133(5), (7); m.134(1)) — son gün çıkarımdır, sayım yöntemi metinde yok</li>
              <li><b>İnceleme süreleri:</b> ölçüm değerlerine itirazı TEİAŞ/dağıtım şirketi {sayiTr(m.itiraz.inceleme.olcum_teias_dagitim_gun)} gün içinde sonuçlandırır, EPİAŞ sonucu {sayiTr(m.itiraz.inceleme.olcum_epias_is_gunu)} iş günü içinde işler; ölçüm dışı itirazlar {sayiTr(m.itiraz.inceleme.olcum_disi_is_gunu)} iş günü ({m.itiraz.inceleme.dayanak})</li>
              {m.itiraz.lisanssiz && <li><b>Lisanssız tesis:</b> {m.itiraz.lisanssiz.not} İnceleme {sayiTr(m.itiraz.lisanssiz.inceleme_is_gunu)} iş günü ({m.itiraz.lisanssiz.dayanak}).</li>}
            </ul>
            <p className="soluk" style={{ margin: "6px 0 0", fontSize: 13 }}>{m.itiraz.dayanak}</p>
          </details>}
          <details className="aciklama" style={{ marginTop: 6 }}>
            <summary>Bu sayfa nasıl çalışır</summary>
            <p style={{ margin: "6px 0 0" }}>{m.not}</p>
            <p style={{ margin: "6px 0 0" }}><b>Uyum ölçütü:</b> {m.uyum.not}</p>
            <p style={{ margin: "6px 0 0" }}><b>Güvenilirlik:</b> «{o.guvenilirlik_etiketleri.gercek}» dönemin bütün saatleri EPİAŞ fiyatı ve bildirilen KGÜP ile; «{o.guvenilirlik_etiketleri.kismi}» eksik saat, PVQuant önerisi ya da tahmini sayaç; «{o.guvenilirlik_etiketleri.senaryo}» EPİAŞ fiyatı yerine senaryo. Kısmi kapsamda «uyumlu / fark var» hükmü tam ay verisiyle kesinleşir.</p>
            <p style={{ margin: "6px 0 0" }}><b>Sürüm:</b> ön bildirim izleyen ayın 11'i, nihai bildirim 15'i (hafta sonu ve tatilde izleyen iş günü; DUY m.132/A). Etiket dosyadaki «Uzlaştırma Durumu» alanından ya da seçiminizden gelir; EPİAŞ'ın resmî durumu PVQuant'tan doğrulanmaz.</p>
            <p style={{ margin: "6px 0 0" }}><b>Dosya tanıma:</b> EPYS dosyasının resmî kolon başlıkları elimizde yok; «Uzlaştırma Kalemleri» ve «Tutar (TL)» sütunları ile alacak/borç bölümleri ya da ayrı sütunlar tanınır; saatlik detayda tarih (+saat) ve bilinen ölçüm sütunları aranır.</p>
          </details>
          </>); })()}
        </Kart>
      </div>
      <Kart baslik="Uzlaştırma kalemlerinin karşılaştırılması" alt={`${m.donem_etiket} dönemi; EPİAŞ bildirimi ↔ PVQuant yeniden hesabı; fark = PVQuant net − EPİAŞ net (artı: PVQuant daha çok alacak hesaplıyor); uyum alacak ve borç bileşenlerine ayrı bakılır`}
        sag={<span className="cip"><Meta items={[bil ? surumDurumu(bil) : "bildirim yok", g.etiket, `${sayiTr(hesaplanan.length)} karşılaştırılan`, `${sayiTr(digerler.length)} yalnız bildirim`]} /></span>}>
        {m.satirlar.length === 0 ? <p className="soluk" style={{ margin: 0 }}>Bu dönem için ne bildirim ne de saatlik hesap var. Önce bildirim dosyasını yükleyin.</p> : (
          <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 13.5 }}>
            <thead><tr><th style={sol}>Kalem</th><th title="EPİAŞ bildirimindeki alacak tutarı">EPİAŞ alacak (TL)</th><th title="EPİAŞ bildirimindeki borç tutarı">EPİAŞ borç (TL)</th>
              <th title="PVQuant yeniden hesabı: fazla üretim alacağı, YEK alacağı">PVQuant alacak (TL)</th><th title="PVQuant yeniden hesabı: eksik üretim borcu, KÜPST">PVQuant borç (TL)</th><th title="PVQuant net − EPİAŞ net; parantezde EPİAŞ netine oranı; alacak ve borç farkları ipucunda">Fark (TL)</th><th>Durum</th></tr></thead>
            <tbody>{hesaplanan.map(satir)}{digerler.map(satir)}</tbody>
          </table></div>)}
      </Kart>
      <SaatlikDetayKarti plantId={plantId} donem={m.donem} uretim={uretim} ds={ds} />
    </Sayfa>
  );
}
