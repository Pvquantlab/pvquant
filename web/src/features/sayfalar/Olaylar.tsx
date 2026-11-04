import { useEffect, useState } from "react";
import { useDamgaSurumu } from "../../shell/damgaOlay";
import { api } from "../../api/client";
import type { Olay, OlayOzet, OlayTur, OlayGiris } from "../../api/types";
import { Kart, Kpi, Sayfa, sayiTr, SayfaIskeleti } from "./parcalar";
import { Meta } from "../../lib/Meta";
import { tarihBicimi } from "../../lib/bicim";

/** v2.521 (P1a) — Olay kaydı: planlı bakım, arıza, talimat (YAL/YAT), acil durum kesmesi, şebeke kesintisi, hasar. Kayıt santralın kendi
 *  kaydıdır; TPYS Arıza ve Bakım bildirimi ve Dâhilî Bilgi Platformu açıklaması ayrıca yapılır. Tüketiciler sunucuda: EAK dosyası (saatlik
 *  düşüm, kısmi saat orantılı, günün EAK tabanıyla sınırlı), KGÜP tavanı, aylık arıza sayacı (KÜPST n, alarm), kullanılabilirlik istisnası,
 *  hasar dosyası CSV. 01.11 ikinci inceleme: evre (planlı/sürüyor/bitti), çakışma uyarısı, kurumsal dil, açıklamalar bilgi alanlarında.
 *  02.11 üçüncü inceleme: devre dışı güç AC (kW), hasar «mücbir sebep»i otomatik seçmez, çakışma uyarısı dürüst, süren olay gün sonuna kadar,
 *  «Bitir» tam şimdi (UTC), dosyada «geçersiz». */
const saatTr = (iso: string | null | undefined) => iso ? tarihBicimi("tr-TR", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(iso)) : "—";
const sureTr = (bas: string, bit: string | null) => { const ms = (bit ? new Date(bit).getTime() : Date.now()) - new Date(bas).getTime(); if (ms <= 0) return "—"; const sa = ms / 3600000;
  return sa < 1 ? `${sayiTr(Math.round(ms / 60000))} dk` : sa < 48 ? `${sayiTr(sa, 1)} sa` : `${sayiTr(sa / 24, 1)} gün`; };
const yerelSimdi = () => { const d = new Date(); d.setSeconds(0, 0); const z = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}T${z(d.getHours())}:${z(d.getMinutes())}`; };
const EVRE: Record<string, string> = { planli: "planlı", suruyor: "sürüyor", bitti: "bitti", iptal: "geçersiz" };
const sayiOku = (t: string): number | null | undefined => { const x = t.trim(); if (x === "") return null; const n = Number(x.includes(",") ? x.replace(/\./g, "").replace(",", ".") : x); return Number.isFinite(n) ? n : undefined; };
const sol = { textAlign: "left" as const };

export function Olaylar({ plantId }: { plantId: string }) {
  const ds = useDamgaSurumu();
  const [o, setO] = useState<OlayOzet | null | undefined>(undefined);
  const [gun, setGun] = useState(90);
  const [mesaj, setMesaj] = useState<{ metin: string; ton: "ok" | "hata" | "uyari" } | null>(null);
  const [form, setForm] = useState<{ tur: OlayTur; baslangic: string; bitis: string; kw: string; gerekce: string; neden: string; kanit: string }>(
    { tur: "ariza", baslangic: yerelSimdi(), bitis: "", kw: "", gerekce: "", neden: "", kanit: "" });
  const yukle = () => api.olaylar(plantId, gun).then(setO, () => setO(null));
  useEffect(() => { setO(undefined); void yukle(); }, [plantId, ds, gun]);   // eslint-disable-line react-hooks/exhaustive-deps
  const kural = o?.turler.find((t) => t.kod === form.tur);
  const hata = (e: unknown) => setMesaj({ metin: String((e as Error).message ?? e), ton: "hata" });
  const kaydet = () => {
    setMesaj(null);
    const kw = sayiOku(form.kw);
    if (kw === undefined) { setMesaj({ metin: "Devre dışı güç sayı olmalı (kW); boş bırakılırsa tesisin tamamı sayılır.", ton: "hata" }); return; }
    if (!form.baslangic) { setMesaj({ metin: "Başlangıç saati gerekli.", ton: "hata" }); return; }
    if (form.bitis && form.bitis <= form.baslangic) { setMesaj({ metin: "Bitiş, başlangıçtan sonra olmalı.", ton: "hata" }); return; }
    const g: OlayGiris = { tur: form.tur, baslangic: form.baslangic, bitis: form.bitis || null, etkilenen_kw: kw, neden: form.neden || null,
      eak_gerekcesi: kural?.eak_dusur ? (form.gerekce || null) : null, kanit: form.kanit || null };
    api.olayEkle(plantId, g).then((y) => {
      const evreMetni = y.evre === "planli" ? "planlı" : y.evre === "suruyor" ? "sürüyor" : "bitti";
      setMesaj(y.uyari ? { metin: `Kaydedildi (${evreMetni}). ${y.uyari}`, ton: "uyari" } : { metin: `Kaydedildi: ${y.tur_etiket}, ${saatTr(y.baslangic)}${y.bitis ? ` – ${saatTr(y.bitis)}` : ""} (${evreMetni}).`, ton: "ok" });
      setForm({ ...form, bitis: "", kw: "", neden: "", kanit: "" }); void yukle(); }).catch(hata);
  };
  const bitir = (ol: Olay) => api.olayGuncelle(plantId, ol.id, { bitis: new Date().toISOString() }).then(() => { setMesaj({ metin: `Bitirildi: ${ol.tur_etiket} (${saatTr(ol.baslangic)}).`, ton: "ok" }); void yukle(); }).catch(hata);
  const gecersiz = (ol: Olay) => { if (!window.confirm(`${ol.tur_etiket} (${saatTr(ol.baslangic)}) kaydı geçersiz sayılsın mı?\nKayıt silinmez; hesaplardan çıkar ve dosyada «geçersiz» olarak kalır.`)) return;
    api.olayGuncelle(plantId, ol.id, { durum: "iptal" }).then(() => { setMesaj({ metin: `Geçersiz sayıldı: ${ol.tur_etiket}.`, ton: "ok" }); void yukle(); }).catch(hata); };
  if (o === undefined) return <Sayfa baslik="Olay kaydı"><SayfaIskeleti kpi={4} kart={2} /></Sayfa>;
  if (o === null) return <Sayfa baslik="Olay kaydı"><p className="soluk">Olay kaydı alınamadı.</p></Sayfa>;
  const sayac = o.ariza_sayaci; const sayacTon = sayac.sayi >= sayac.esik ? "uyari" : sayac.sayi >= sayac.uyari ? "amber" : undefined;
  const dahili = o.dahili_bilgi.find((d) => !d.gecti) ?? o.dahili_bilgi[0];
  const ayAd = `${o.ariza_sayaci.ay.slice(5)}.${o.ariza_sayaci.ay.slice(0, 4)}`;
  return (
    <Sayfa baslik="Olay kaydı" alt="Bakım, arıza, talimat, kesinti ve hasar olaylarını girin. Kayıtlar üretim programının tavanını, TPYS EAK dosyasını, aylık arıza sayacını ve kullanılabilirlik hesabını besler."
      sag={<span className="dugme-sira">
        <select className="girdi" value={gun} onChange={(e) => setGun(Number(e.target.value))} aria-label="Liste aralığı">
          <option value={30}>son 30 gün</option><option value={90}>son 90 gün</option><option value={365}>son 12 ay</option></select>
        <button className="dugme kucuk" title="Son 12 ayın olay listesi; sigorta ve hasar dosyası için (; ayraçlı CSV)" onClick={() => api.olaylarIndir(plantId, 365).catch(hata)}>Olay listesini indir (CSV)</button></span>}>
      <div className="ızgara satir-4" style={{ marginBottom: 14 }}>
        <Kpi etiket="Süren olay" deger={sayiTr(o.acik)} ton={o.acik > 0 ? "uyari" : undefined}
          alt={o.acik > 0 ? `başlamış, bitişi girilmemiş; program ve kullanılabilirlik hesabında sürüyor sayılır${o.planli > 0 ? `; ayrıca ${sayiTr(o.planli)} planlı` : ""}` : o.planli > 0 ? `süren olay yok; ${sayiTr(o.planli)} planlı (ileri tarihli)` : "süren olay yok"} />
        <Kpi etiket={`Arıza kaydı (${ayAd})`} deger={sayiTr(sayac.sayi)} birim={`/ ${sayiTr(sayac.esik)}`} ton={sayacTon}
          alt={sayac.sayi >= sayac.esik ? "eşik aşıldı: bu ay sapma tutarı katsayısı 0,08" : `${sayiTr(sayac.esik)} ve üzerinde sapma tutarı katsayısı 0,05'ten 0,08'e çıkar; kaynak ${sayac.kaynak}`} />
        <Kpi etiket="Bugün kapasite düşümü" deger={sayiTr(o.eak_bugun.saat_sayisi)} birim="saat" ton={o.eak_bugun.saat_sayisi > 0 ? "amber" : undefined}
          alt={o.eak_bugun.saat_sayisi > 0 ? `en çok ${sayiTr(o.eak_bugun.en_cok_kw, 0)} kW (taban ${sayiTr(o.eak_bugun.taban_kw, 0)} kW)${o.eak_bugun.kismi_saat > 0 ? `; ${sayiTr(o.eak_bugun.kismi_saat)} saatte kısmi süre, orantılı` : ""}${o.eak_bugun.suren > 0 ? "; bitişi girilmemiş olay gün sonuna kadar sayılır" : ""}` : "bugün kapasiteyi düşüren olay yok"} />
        <Kpi etiket="Dâhilî bilgi açıklaması" deger={dahili ? (dahili.gecti ? "süre doldu" : `${sayiTr(dahili.kalan_dk)} dk`) : "—"} ton={dahili ? (dahili.basladi === false ? "amber" : "uyari") : undefined}
          alt={dahili ? `${dahili.tur}, ${dahili.esik} eşiği: en geç ${saatTr(dahili.son_saat)} (1 saat kuralı; yürürlük ${dahili.yururluk}${dahili.basladi === false ? " — henüz başlamadı, bilgi amaçlı" : ""})`
            : `1 saat kuralı (yürürlük ${o.dahili_yururluk?.etiket ?? "01.01.2027"}): tesis 30 MW / portföy 50 MW eşiğinde süren olay yok`} />   {/* v2.538 (DK-613) */}
      </div>
      <div className="ızgara-cift">
        <Kart baslik="Yeni olay" alt="Olay başladığında girin; bitişi sonradan «Bitir» ile verin. Planlı bakımı ileri tarihle girebilirsiniz.">
          <div className="form-izgara">
            <label className="girdi-etiket">Olay türü<select className="girdi" value={form.tur} onChange={(e) => { const t = e.target.value as OlayTur; const k = o.turler.find((x) => x.kod === t); setForm({ ...form, tur: t, gerekce: k?.gerekce ?? "" }); }}>
              {o.turler.map((t) => <option key={t.kod} value={t.kod}>{t.etiket}</option>)}</select></label>
            <label className="girdi-etiket">Başlangıç (Türkiye saati)<input className="girdi" type="datetime-local" value={form.baslangic} onChange={(e) => setForm({ ...form, baslangic: e.target.value })} /></label>
            <label className="girdi-etiket">Bitiş (boşsa olay sürüyor)<input className="girdi" type="datetime-local" value={form.bitis} min={form.baslangic || undefined} onChange={(e) => setForm({ ...form, bitis: e.target.value })} /></label>
            <label className="girdi-etiket" title="Devre dışı kalan güç, invertör çıkışı (AC) olarak; boş bırakılırsa tesisin tamamı (günün EAK tabanı) sayılır">Devre dışı güç (kW, AC; boşsa tesisin tamamı)<input className="girdi" inputMode="decimal" placeholder="ör. 1.500" value={form.kw} onChange={(e) => setForm({ ...form, kw: e.target.value })} /></label>
            {kural?.eak_dusur && <label className="girdi-etiket">TPYS EAK dosyasında gerekçe<select className="girdi" value={form.gerekce || kural.gerekce || ""} onChange={(e) => setForm({ ...form, gerekce: e.target.value })}>
              {o.gerekceler.map((g) => <option key={g.kod} value={g.kod}>{g.etiket}</option>)}</select></label>}
            <label className="girdi-etiket">Açıklama (isteğe bağlı)<input className="girdi" maxLength={500} placeholder="ör. invertör 3 arızası" value={form.neden} onChange={(e) => setForm({ ...form, neden: e.target.value })} /></label>
            <label className="girdi-etiket">Belge / tutanak no (isteğe bağlı)<input className="girdi" maxLength={500} placeholder="ör. servis raporu SR-1182" value={form.kanit} onChange={(e) => setForm({ ...form, kanit: e.target.value })} /></label>
            <div className="form-tam dugme-sira"><button className="dugme" onClick={kaydet}>Kaydet</button>
              {mesaj && <span className={`ayar-durum ${mesaj.ton === "uyari" ? "" : mesaj.ton}`} style={mesaj.ton === "uyari" ? { color: "var(--amber-koyu, #8a5a00)" } : undefined}>{mesaj.metin}</span>}</div>
          </div>
          {kural && <p className="form-not" style={{ marginTop: 10, fontSize: 13.5 }}><b>{kural.etiket}:</b> {kural.not}.</p>}
        </Kart>
        <Kart baslik="Olay türleri ve etkileri" alt="Her türün kapasite (EAK), aylık arıza sayacı ve kullanılabilirlik hesabına etkisi">
          <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 13.5 }}>
            <thead><tr><th style={sol}>Tür</th><th title="O saatlerde verilebilecek güç ve program tavanı düşer">Kapasiteyi düşürür</th><th title="Ayda 30 ve üzeri arıza kaydı sapma tutarı katsayısını yükseltir">Arıza sayacına girer</th><th title="Santralın elinde olmayan saatler kullanılabilirlik hesabından düşülür">Kullanılabilirlikten düşülür</th><th style={sol} title="TPYS EAK dosyasında eksik kapasitenin yazıldığı sütun; tür için varsayılan, kayıt girilirken değiştirilebilir">EAK gerekçesi (varsayılan)</th></tr></thead>
            <tbody>{o.turler.map((t) => (
              <tr key={t.kod}><td style={sol}>{t.etiket}</td><td>{t.eak_dusur ? "evet" : "—"}</td><td>{t.sayac ? "evet" : "—"}</td><td>{t.istisna ? "evet" : "—"}</td>
                <td style={sol}>{o.gerekceler.find((g) => g.kod === t.gerekce)?.etiket ?? "—"}</td></tr>))}</tbody>
          </table></div>
          <details className="aciklama" style={{ marginTop: 10 }}>
            <summary>Bu sayfa nasıl çalışır</summary>
            <p style={{ margin: "6px 0 0" }}><b>Kapasite:</b> {o.aciklama.kapasite}</p>
            <p style={{ margin: "6px 0 0" }}><b>Arıza sayacı:</b> {o.aciklama.sayac}</p>
            <p style={{ margin: "6px 0 0" }}><b>Kullanılabilirlik:</b> {o.aciklama.kullanilabilirlik}</p>
            <p style={{ margin: "6px 0 0" }}><b>EAK gerekçesi:</b> {o.aciklama.gerekce}</p>
            <p style={{ margin: "6px 0 0" }}><b>Bitir / geçersiz say:</b> {o.aciklama.islem}</p>
            {o.aciklama.talimat && <p style={{ margin: "6px 0 0" }}><b>Talimat tutarı:</b> {o.aciklama.talimat}</p>}   {/* v2.538 (DK-733/DK-740) */}
            {o.dahili_yururluk && <p style={{ margin: "6px 0 0" }}><b>Dâhilî bilgi açıklaması:</b> {o.dahili_yururluk.not}</p>}   {/* v2.538 (DK-613) */}
            <p style={{ margin: "6px 0 0" }}>{o.not}</p>
          </details>
        </Kart>
      </div>
      <Kart baslik="Olaylar" alt={`son ${sayiTr(o.pencere_gun)} gün, süren ve planlı olaylar; geçersiz sayılanlar listede ve hesaplarda yok, indirilen dosyada «geçersiz» olarak kalır`}
        sag={<span className="cip"><Meta items={[`${sayiTr(o.olaylar.length)} olay`, `${sayiTr(o.acik)} sürüyor`, ...(o.planli > 0 ? [`${sayiTr(o.planli)} planlı`] : [])]} /></span>}>
        {o.olaylar.length === 0 ? <p className="soluk" style={{ margin: 0 }}>Bu aralıkta olay kaydı yok.</p> : (
          <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 13.5 }}>
            <thead><tr><th style={sol}>Tür</th><th style={sol}>Başlangıç</th><th style={sol}>Bitiş</th><th title="Süren olayda şu ana kadar">Süre</th><th>Devre dışı (kW)</th><th style={sol}>EAK gerekçesi</th><th style={sol}>Açıklama</th><th>Evre</th><th>İşlem</th></tr></thead>
            <tbody>{o.olaylar.map((ol) => (
              <tr key={ol.id}><td style={sol}>{ol.tur_etiket}</td><td style={{ ...sol, whiteSpace: "nowrap" }}>{saatTr(ol.baslangic)}</td>
                <td style={{ ...sol, whiteSpace: "nowrap" }}>{ol.bitis ? saatTr(ol.bitis) : <span className="soluk">girilmedi</span>}</td>
                <td className="mono" style={{ whiteSpace: "nowrap" }}>{ol.evre === "planli" && !ol.bitis ? "—" : sureTr(ol.baslangic, ol.bitis)}</td><td className="mono" style={{ whiteSpace: "nowrap" }}>{ol.etkilenen_kw != null ? sayiTr(ol.etkilenen_kw, 0) : "tamamı"}</td>
                <td style={sol}>{o.gerekceler.find((g) => g.kod === ol.eak_gerekcesi)?.etiket ?? "—"}</td>
                <td style={{ ...sol, whiteSpace: "normal", minWidth: 160 }}>{ol.neden ?? "—"}{ol.kanit ? <span className="soluk"> · belge: {ol.kanit}</span> : null}</td>
                <td><span className={`rozet rozet-kucuk ${ol.evre === "suruyor" ? "rozet-uyari" : ol.evre === "planli" ? "rozet-ok" : "rozet-notr"}`}>{EVRE[ol.evre]}</span></td>
                <td style={{ whiteSpace: "nowrap" }}>{ol.evre === "suruyor" && <button className="dugme kucuk" title="Bitiş saati olarak şimdiyi yazar; kayıt hesaplarda kalır" onClick={() => bitir(ol)}>Bitir</button>} <button className="dugme kucuk" title="Yanlış kaydı hesaplardan çıkarır; silinmez" onClick={() => gecersiz(ol)}>Geçersiz say</button></td></tr>))}</tbody>
          </table></div>)}
      </Kart>
    </Sayfa>
  );
}
