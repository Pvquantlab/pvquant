import { useEffect, useState } from "react";
import { useDamgaSurumu } from "../../shell/damgaOlay";
import { api } from "../../api/client";
import type { MutabakatOzet, MutabakatSatir } from "../../api/types";
import { Kart, Kpi, Sayfa, sayiTr, SayfaIskeleti } from "./parcalar";
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

export function Mutabakat({ plantId }: { plantId: string }) {
  const ds = useDamgaSurumu();
  const [o, setO] = useState<MutabakatOzet | null | undefined>(undefined);
  const [donem, setDonem] = useState<string | null>(null);
  const [surum, setSurum] = useState<string | null>(null);
  const [mesaj, setMesaj] = useState<{ metin: string; ton: "ok" | "hata" | "uyari" } | null>(null);
  const [dosya, setDosya] = useState<File | null>(null);
  const [dosyaAnahtar, setDosyaAnahtar] = useState(0);   // yükleme sonrası dosya alanı sıfırlanır
  const [yukDonem, setYukDonem] = useState(oncekiAy());
  const [yukSurum, setYukSurum] = useState("");
  const [yukleniyor, setYukleniyor] = useState(false);
  const yukle = () => api.mutabakat(plantId, donem, surum).then(setO, () => setO(null));
  useEffect(() => { setO(undefined); void yukle(); }, [plantId, ds, donem, surum]);   // eslint-disable-line react-hooks/exhaustive-deps
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
      <td><span className={`rozet rozet-kucuk ${DURUM[s.durum].sinif}`} title={s.bilesen_notu ?? s.pvquant_not ?? undefined}>{DURUM[s.durum].etiket}</span>{s.bilesen_notu ? <div className="soluk" style={{ fontSize: 12, marginTop: 2 }}>{s.bilesen_notu}</div> : null}</td>
    </tr>);
  return (
    <Sayfa baslik="Mutabakat" alt="EPİAŞ uzlaştırma bildirimini PVQuant'ın yeniden hesabıyla kalem kalem karşılaştırın. EPİAŞ bildirimi esastır; PVQuant tutarları yeniden hesaptır, fark bilgi amaçlıdır."
      sag={<span className="dugme-sira">
        <select className="girdi" value={m.donem} onChange={(e) => setDonem(e.target.value)} aria-label="Fatura dönemi">
          {donemler.map((d) => <option key={d} value={d}>{ayAd(d)}</option>)}</select>
        <select className="girdi" value={surum ?? ""} onChange={(e) => setSurum(e.target.value || null)} aria-label="Bildirim sürümü">
          <option value="">son yüklenen sürüm</option>{o.surumler.map((s) => <option key={s.kod} value={s.kod}>{s.etiket}</option>)}</select></span>}>
      <div className="ızgara satir-4" style={{ marginBottom: 14 }}>
        <Kpi etiket={`EPİAŞ toplam alacak (${m.donem_etiket})`} bilgi="EPİAŞ bildirimindeki bütün alacak kalemlerinin toplamı (GÖP, GİP, YEK, dengesizlik, …); «Toplam» satırı hariç. PVQuant bu toplamın yalnız bir bölümünü yeniden hesaplar."
          deger={binTl(oz.bildirim_alacak_tl)} birim={oz.bildirim_alacak_tl != null ? "bin TL" : undefined}
          alt={bil ? `${bil.surum_etiket}, yükleme ${saatTr(bil.zaman)}` : "bu dönem için bildirim yüklenmedi"} />
        <Kpi etiket="EPİAŞ toplam borç" bilgi="EPİAŞ bildirimindeki bütün borç kalemlerinin toplamı (dengesizlik, KÜPST, PİÜ, …); «Toplam» satırı hariç."
          deger={binTl(oz.bildirim_borc_tl)} birim={oz.bildirim_borc_tl != null ? "bin TL" : undefined}
          alt={bil ? "tüm kalemler; kapsamı PVQuant hesabından geniştir" : "bildirim yok"} />
        <Kpi etiket="PVQuant yeniden hesaplanan tutar" bilgi="Yalnız santral verisinden hesaplanabilen kalemler: enerji dengesizlik tutarı, KGÜP sapma tutarı (lisanslı YEKDEM'de YEK alacağı). Net = alacak − borç; eksi tutar santralin ödediğidir. EPİAŞ toplamıyla değil, aynı kalemlerin EPİAŞ tutarıyla karşılaştırılır."
          deger={binTl(oz.pvquant_net_tl)} birim={oz.pvquant_net_tl != null ? "bin TL" : undefined}
          ikinci={oz.bildirim_kiyas_net_tl != null ? { etiket: "aynı kalemlerde EPİAŞ", deger: `${binTl(oz.bildirim_kiyas_net_tl)} bin TL` } : undefined}
          alt={oz.kapsam ? `net; kapsam: ${oz.kapsam} (${sayiTr(m.pvquant.saat)} saat)` : m.pvquant.saat ? "karşılaştırılacak kalem yok" : "bu dönem için saatlik veri yok"} />
        <Kpi etiket="Hesaplama farkı" bilgi="PVQuant net − EPİAŞ net, yalnız karşılaştırılan kalemlerde. Artı: PVQuant daha çok alacak hesaplıyor; eksi: daha çok borç. Uyum ölçütü PVQuant'ın işletme ölçütüdür, mevzuat toleransı değildir."
          deger={oz.fark_tl != null ? `${oz.fark_tl > 0 ? "+" : ""}${binTl(oz.fark_tl)}` : "—"} birim={oz.fark_tl != null ? "bin TL" : undefined}
          ton={oz.farkli > 0 ? "amber" : undefined}
          alt={oz.kiyaslanan ? (g.durum === "senaryo" ? `${sayiTr(oz.kiyaslanan)} kalem; senaryo hesabı, uyum sınıflandırması yapılmadı` : `${sayiTr(oz.kiyaslanan)} kalem: ${sayiTr(oz.uyumlu)} uyumlu, ${sayiTr(oz.farkli)} farklı; ölçüt bileşen başına %${sayiTr(m.uyum.pct)} ya da ${sayiTr(m.uyum.tl)} TL`) : "kıyaslanacak kalem yok"} />
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
        <Kart baslik="Hesaplamada kullanılan veriler" alt="Dönem için PVQuant'ın saatlik uzlaştırma dökümü (Doğruluk › Uzlaştırma kalemleri ile aynı hesap); sonucun güvenilirliği buradaki verilere bağlıdır"
          sag={<span className={`rozet rozet-kucuk ${GUVEN_SINIF[g.durum]}`} title={g.nedenler.join("; ") || "dönemin bütün saatleri EPİAŞ fiyatı ve bildirilen KGÜP ile hesaplandı"}>{g.etiket}</span>}>
          <ul className="not-listesi" style={{ fontSize: 13.5 }}>
            <li><b>Saat:</b> {sayiTr(m.pvquant.saat)}{m.pvquant.beklenen_saat ? ` / ${sayiTr(m.pvquant.beklenen_saat)} (dönemin saati)` : ""}{m.pvquant.son_saat ? `; son üretim verisi ${m.pvquant.son_saat}` : ""}{m.pvquant.hesaplanamayan_saat ? `; ${sayiTr(m.pvquant.hesaplanamayan_saat)} saat hesaplanamadı` : ""}</li>
            <li><b>Program:</b> {m.pvquant.bildirilen_saat ? `${sayiTr(m.pvquant.bildirilen_saat)} saatte bildirilen KGÜP (TPYS'ye bildirildiği beyan edilen dosya)${m.pvquant.bildirilen_saat < m.pvquant.saat ? `, kalan ${sayiTr(m.pvquant.saat - m.pvquant.bildirilen_saat)} saatte PVQuant önerisi` : ""}` : "PVQuant önerisi (bildirilen KGÜP yüklü değil)"}</li>
            <li><b>Fiyat:</b> {m.pvquant.senaryo_saat ? `${sayiTr(m.pvquant.senaryo_saat)} saatte senaryo fiyatı (EPİAŞ fiyat verisi yok; sistem yönü dengede varsayıldı)` : "EPİAŞ saatlik PTF, SMF ve sistem yönü"}</li>
            <li><b>Üretim:</b> SCADA ölçümü (geçerli bayraklı saatler); EPİAŞ uzlaştırmaya esas sayaç verisi (UEVM) değildir</li>
            {m.pvquant.kural_surumu && <li><b>Kural:</b> {m.pvquant.kural_surumu}</li>}
            {g.nedenler.length > 0 && <li><b>{g.etiket}:</b> {g.nedenler.join("; ")}</li>}
            {m.pvquant.hata && <li className="soluk">Hesap alınamadı: {m.pvquant.hata}</li>}
          </ul>
          {sd && sd.durum === "takvimden_once" && <p className="form-not" style={{ marginTop: 8, fontSize: 13.5, color: "var(--amber-koyu, #8a5a00)" }}><b>Sürüm:</b> {sd.aciklama}</p>}
          {m.program_notu && <p className="form-not" style={{ marginTop: 8, fontSize: 13.5, color: "var(--amber-koyu, #8a5a00)" }}>{m.program_notu}</p>}
          {m.eylem && <p className="form-not" style={{ marginTop: 8, fontSize: 13.5 }}><b>Ne yapmalı:</b> {m.eylem}</p>}
          <details className="aciklama" style={{ marginTop: 10 }}>
            <summary>Bu sayfa nasıl çalışır</summary>
            <p style={{ margin: "6px 0 0" }}>{m.not}</p>
            <p style={{ margin: "6px 0 0" }}><b>Uyum ölçütü:</b> {m.uyum.not}</p>
            <p style={{ margin: "6px 0 0" }}><b>Güvenilirlik:</b> «{o.guvenilirlik_etiketleri.gercek}» dönemin bütün saatleri EPİAŞ fiyatı ve bildirilen KGÜP ile; «{o.guvenilirlik_etiketleri.kismi}» eksik saat, öneri program ya da hesaplanamayan saat var; «{o.guvenilirlik_etiketleri.senaryo}» EPİAŞ fiyatı yerine senaryo fiyatı kullanıldı, uyum sınıflandırması yapılmaz; «{o.guvenilirlik_etiketleri.veri_yok}» dönem için saatlik veri yok.</p>
            <p style={{ margin: "6px 0 0" }}><b>Sürüm:</b> ön bildirim izleyen ayın 11'i, nihai bildirim 15'i (hafta sonu ve tatilde izleyen iş günü; DUY m.132/A). Etiket dosyadaki «Uzlaştırma Durumu» alanından ya da seçiminizden gelir; EPİAŞ'ın durumu dosyadan doğrulanamaz, yükleme takvim tarihinden önceyse işaretlenir. Dosyadaki tesis ya da organizasyon kimliği doğrulanmaz.</p>
            <p style={{ margin: "6px 0 0" }}><b>Dosya tanıma:</b> EPYS dosyasının resmî kolon başlıkları elimizde yok; «Uzlaştırma Kalemleri» ve «Tutar (TL)» sütunları ile alacak/borç bölümleri ipuçlarıyla tanınır. Tanınmayan kalemler «diğer» olarak adıyla saklanır.</p>
          </details>
        </Kart>
      </div>
      <Kart baslik="Uzlaştırma kalemlerinin karşılaştırılması" alt={`${m.donem_etiket} dönemi; EPİAŞ bildirimi ↔ PVQuant yeniden hesabı; fark = PVQuant net − EPİAŞ net (artı: PVQuant daha çok alacak hesaplıyor); uyum alacak ve borç bileşenlerine ayrı bakılır`}
        sag={<span className="cip"><Meta items={[bil ? `${bil.surum_etiket}` : "bildirim yok", g.etiket, `${sayiTr(hesaplanan.length)} karşılaştırılan`, `${sayiTr(digerler.length)} yalnız bildirim`]} /></span>}>
        {m.satirlar.length === 0 ? <p className="soluk" style={{ margin: 0 }}>Bu dönem için ne bildirim ne de saatlik hesap var. Önce bildirim dosyasını yükleyin.</p> : (
          <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 13.5 }}>
            <thead><tr><th style={sol}>Kalem</th><th title="EPİAŞ bildirimindeki alacak tutarı">EPİAŞ alacak (TL)</th><th title="EPİAŞ bildirimindeki borç tutarı">EPİAŞ borç (TL)</th>
              <th title="PVQuant yeniden hesabı: fazla üretim alacağı, YEK alacağı">PVQuant alacak (TL)</th><th title="PVQuant yeniden hesabı: eksik üretim borcu, KÜPST">PVQuant borç (TL)</th><th title="PVQuant net − EPİAŞ net; parantezde EPİAŞ netine oranı; alacak ve borç farkları ipucunda">Fark (TL)</th><th>Durum</th></tr></thead>
            <tbody>{hesaplanan.map(satir)}{digerler.map(satir)}</tbody>
          </table></div>)}
      </Kart>
    </Sayfa>
  );
}
