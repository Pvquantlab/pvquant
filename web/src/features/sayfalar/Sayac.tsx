import { useEffect, useState } from "react";
import { useDamgaSurumu } from "../../shell/damgaOlay";
import { api } from "../../api/client";
import type { SayacOzet, SayacKaynak, SayacGun, SayacAyar } from "../../api/types";
import { Kart, Kpi, Sayfa, sayiTr, SayfaIskeleti } from "./parcalar";
import { Meta } from "../../lib/Meta";
import { tarihBicimi } from "../../lib/bicim";

/** v2.523 (P4a) — Sayaç: uzlaştırmaya esas sayaç verisi (OSOS / MASS / EPYS dışa aktarımı) SCADA'dan ayrı yüklenir; sayaç türüne göre EPİAŞ geliş
 *  beklentisi (Ölçüm Sist. Yön. m.8(2)–(3)), bu ayın eksik saatleri, 12. gün 17:30 düzeltme geri sayımı (DUY m.81, m.82), günlük SCADA ↔ sayaç
 *  farkı ve değer başına kaynak/nitelik etiketi (ölçülmüş / tahmini / doldurulmuş / elle). Lisanssızda SCADA bağlantı durumu (LÜY m.21(7)),
 *  kopukluk gün sayacı, uzaktan açma olayları ve Karar 14909 bedel göstergesi (müşterinin girdiği aylık sistem kullanım bedeliyle; askı 30.4.2027,
 *  tarih kısmen teyit). Hesap sunucuda (sayac_service); burada gösterim ve iki küçük form. */
const saatTr = (iso: string | null | undefined) => iso ? tarihBicimi("tr-TR", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(iso)) : "—";
// v2.537 (inceleme): saatli ISO damga (yükleme aralığı, UTC) yerel güne çevrilerek yazılır — «2026-09-30T21:00Z» = 1 Ekim 00:00 TSİ, 30 Eylül değil; yalnız gün olan
// metinler («2026-11-12», «2026-11-12 17:30») öğlen sabitlenerek olduğu gibi okunur
const gunTr = (iso: string | null | undefined) => iso ? tarihBicimi("tr-TR", { day: "numeric", month: "short", year: "numeric" }).format(/^\d{4}-\d{2}-\d{2}(\s|$)/.test(iso) ? new Date(iso.slice(0, 10) + "T12:00:00") : new Date(iso)) : "—";
const ayAd = (d: string) => `${d.slice(5)}.${d.slice(0, 4)}`;
const kwh = (v: number | null | undefined) => v == null ? "—" : sayiTr(v, 0);
const yuzde = (p: number | null | undefined) => p == null ? "—" : `${p < 0 ? "−" : p > 0 ? "+" : ""}%${sayiTr(Math.abs(p), 1)}`;
const imzali = (v: number | null | undefined, ondalik = 0) => v == null ? "—" : `${v < 0 ? "−" : v > 0 ? "+" : ""}${sayiTr(Math.abs(v), ondalik)}`;   // eksi işareti tek biçim (−)
const sureTr = (saat: number) => { const s = Math.abs(saat); return s < 1 ? `${sayiTr(Math.round(s * 60))} dk` : s < 48 ? `${sayiTr(s, 0)} sa` : `${sayiTr(s / 24, 0)} gün`; };
const sayiOku = (t: string): number | null | undefined => { const x = t.trim(); if (x === "") return null; const n = Number(x.includes(",") ? x.replace(/\./g, "").replace(",", ".") : x); return Number.isFinite(n) ? n : undefined; };
const NITELIK_AD: Record<string, string> = { sayac_olculmus: "sayaç ölçülmüş", sayac_tahmini: "sayaç tahmini", sayac_doldurulmus: "sayaç doldurulmuş", sayac_elle: "sayaç elle", sayac_yok: "sayaç «veri yok»",
  scada_dosya: "SCADA dosyası", epias_seffaflik: "Şeffaflık akışı", gercek_yok: "gerçekleşen yok", sayac_yok_saat: "sayaç verisi yok" };
const sol = { textAlign: "left" as const };
const amber = { color: "var(--amber-koyu, #8a5a00)" };

export function Sayac({ plantId }: { plantId: string }) {
  const ds = useDamgaSurumu();
  const [o, setO] = useState<SayacOzet | null | undefined>(undefined);
  const [gun, setGun] = useState(30);
  const [mesaj, setMesaj] = useState<{ metin: string; ton: "ok" | "hata" | "uyari" } | null>(null);
  const [dosya, setDosya] = useState<File | null>(null);
  const [dosyaAnahtar, setDosyaAnahtar] = useState(0);
  const [kaynak, setKaynak] = useState<SayacKaynak>("osos");
  const [yukleniyor, setYukleniyor] = useState(false);
  const [tur, setTur] = useState<string>("");
  const [girdi, setGirdi] = useState<"scada" | "sayac">("scada");   // v2.526 (P4a-2): uzlaştırma yeniden hesabında üretim kaynağı
  const [scada, setScada] = useState<{ durum: string; bas: string; uzaktan: boolean | null; bedel: string }>({ durum: "", bas: "", uzaktan: null, bedel: "" });
  const [ayarDurum, setAyarDurum] = useState<{ metin: string; ton: "ok" | "hata" } | null>(null);
  const [scadaDurumIleti, setScadaDurumIleti] = useState<{ metin: string; ton: "ok" | "hata" } | null>(null);
  const yukle = () => api.sayac(plantId, gun).then((y) => { setO(y); setTur(y.ayar.sayac_turu ?? ""); setGirdi(y.ayar.uzlastirma_girdi === "sayac" ? "sayac" : "scada");
    setScada({ durum: y.ayar.scada_durum ?? "", bas: y.ayar.scada_kopukluk_baslangic ?? "", uzaktan: y.ayar.uzaktan_acma_var, bedel: y.ayar.sistem_kullanim_bedeli_tl_ay != null ? String(y.ayar.sistem_kullanim_bedeli_tl_ay).replace(".", ",") : "" }); }, () => setO(null));
  useEffect(() => { setO(undefined); void yukle(); }, [plantId, ds, gun]);   // eslint-disable-line react-hooks/exhaustive-deps
  const gonder = () => {
    if (!dosya) { setMesaj({ metin: "Önce sayaç dışa aktarım dosyasını seçin (CSV ya da XLSX).", ton: "hata" }); return; }
    setMesaj(null); setYukleniyor(true);
    api.sayacYukle(plantId, dosya, kaynak).then((y) => {
      const nit = Object.entries(y.nitelik_sayim).filter(([k]) => k !== "olculmus").map(([k, n]) => `${sayiTr(n)} saat ${NITELIK_AD[`sayac_${k}`]?.replace("sayaç ", "") ?? k}`);
      const metin = `Yüklendi: ${y.kaynak_etiket}, ${sayiTr(y.n_saat)} saat (${gunTr(y.bas)} – ${gunTr(y.bit)}; ${y.cozunurluk_dk < 60 ? `${sayiTr(y.cozunurluk_dk)} dakikalık dilimler saate toplandı` : "saatlik"}), toplam ${sayiTr(y.toplam_veris_kwh, 0)} kWh.`
        + ` Sütunlar: zaman «${y.kolonlar.zaman}», veriş «${y.kolonlar.veris}»${y.kolonlar.nitelik ? `, nitelik «${y.kolonlar.nitelik}»` : ""}.` + (nit.length ? ` Nitelik: ${nit.join(", ")}.` : "") + (y.uyarilar.length ? ` ${y.uyarilar.join("; ")}.` : "");
      setMesaj({ metin, ton: y.uyarilar.length || nit.length ? "uyari" : "ok" }); setDosya(null); setDosyaAnahtar((k) => k + 1); void yukle(); })
      .catch((e) => setMesaj({ metin: String((e as Error).message ?? e), ton: "hata" })).finally(() => setYukleniyor(false));
  };
  const ayarKaydet = (g: SayacAyar, bildir = setAyarDurum) => { bildir(null); api.sayacAyar(plantId, g).then((y) => { setO(y); bildir({ metin: "Kaydedildi.", ton: "ok" }); }).catch((e) => bildir({ metin: String((e as Error).message ?? e), ton: "hata" })); };
  const scadaKaydet = () => {
    const bedel = sayiOku(scada.bedel);
    if (bedel === undefined || (bedel != null && bedel < 0)) { setScadaDurumIleti({ metin: "Aylık sistem kullanım bedeli sayı olmalı (TL).", ton: "hata" }); return; }
    ayarKaydet({ scada_durum: scada.durum || null, scada_kopukluk_baslangic: scada.durum === "kopuk" ? (scada.bas || null) : null, uzaktan_acma_var: scada.uzaktan, sistem_kullanim_bedeli_tl_ay: bedel }, setScadaDurumIleti);
  };
  if (o === undefined) return <Sayfa baslik="Sayaç"><SayfaIskeleti kpi={4} kart={2} /></Sayfa>;
  if (o === null) return <Sayfa baslik="Sayaç"><p className="soluk">Sayaç bilgisi alınamadı.</p></Sayfa>;
  const g = o.gelis; const f = o.fark; const t = f.toplam; const sc = o.scada; const sn = g.siniflama; const d0 = g.donemler[0]; const dSon = g.donemler[g.donemler.length - 1];
  const kaynakSayim = Object.entries(f.kaynak_sayim).filter(([, n]) => n > 0);
  const gunSatir = (r: SayacGun) => (
    <tr key={r.gun}>
      <td style={{ ...sol, whiteSpace: "nowrap" }}>{gunTr(r.gun)}</td>
      <td className="mono">{kwh(r.scada_kwh)}</td><td className="mono">{kwh(r.sayac_kwh)}</td>
      <td className="mono">{sayiTr(r.saat_ortak)}{r.saat_ortak < 24 ? <span className="soluk"> / {sayiTr(Math.max(r.saat_scada, r.saat_sayac))}</span> : null}</td>
      <td className="mono" style={{ whiteSpace: "nowrap" }}>{imzali(r.fark_kwh)}</td>
      <td className="mono">{yuzde(r.fark_pct)}</td>
      <td className="mono">{r.saat_tahmini ? yuzde(r.olc_fark_pct) : <span className="soluk">aynı</span>}</td>
      <td className="mono">{r.saat_tahmini ? <span style={amber}>{sayiTr(r.saat_tahmini)}</span> : "0"}</td>
    </tr>);
  return (
    <Sayfa baslik="Sayaç" alt="Sayaç ölçümlerinizi dosyayla yükleyin; son ölçümü, eksik saatleri, düzeltme son tarihini ve sayaç ile SCADA arasındaki farkı tek yerden izleyin. Sayaç verisi şebeke işletmecisinindir; PVQuant yalnız karşılaştırır."
      sag={<span className="dugme-sira">
        <select className="girdi" value={gun} onChange={(e) => setGun(Number(e.target.value))} aria-label="Karşılaştırma aralığı">
          <option value={30}>son 30 gün</option><option value={90}>son 90 gün</option><option value={365}>son 12 ay</option></select>
        <button className="dugme" onClick={() => api.sayacIndir(plantId, gun).catch((e) => setMesaj({ metin: String((e as Error).message ?? e), ton: "hata" }))}>Günlük tablo (CSV)</button></span>}>
      <div className="ızgara satir-4" style={{ marginBottom: 14 }}>
        <Kpi etiket="Son yüklenen sayaç ölçümü" bilgi="PVQuant'a yüklenmiş en son sayaç saati. EPİAŞ'a fiilen ulaşıp ulaşmadığı buradan görülmez; beklenen iletim anı sayaç türüne göre mevzuattan yazılır."
          deger={g.son_sayac_saat_once != null ? sureTr(g.son_sayac_saat_once) : "—"} birim={g.son_sayac_saat_once != null ? "önce" : undefined}
          alt={g.son_sayac ? <>{saatTr(g.son_sayac)}; son SCADA {saatTr(g.son_scada)}{(g.son_sayac_saat_once ?? 0) > 48 ? <span style={amber}> · PVQuant'a yeni sayaç ölçümü yüklenmemiş; güncel dosyanızı yükleyin</span> : null}</> : "henüz sayaç dosyası yüklenmedi; ilk dosyanızı aşağıdan yükleyin"} />
        <Kpi etiket={`Eksik ölçüm saatleri (${ayAd(g.ay)})`} bilgi="Vadesi gelen saat: ay başından şu anki saatten 2 saat öncesine kadar başlamış saat dilimleri (Ölçüm Sist. Yön. m.8(2), dilim sonundan sayıldı). Eksik: vadesi gelen ama PVQuant'a yüklenmemiş saat; EPİAŞ'a ulaşıp ulaşmadığı buradan görülmez. Diğer sayaçta aylık beklenti uygulanır, saat sayılmaz."
          deger={sn.eksik != null ? sayiTr(sn.eksik) : "—"} birim={sn.eksik != null ? "saat" : undefined} ton={sn.eksik ? "amber" : undefined}
          alt={sn.vadesi_gelen != null ? `${sayiTr(sn.vadesi_gelen)} saatin ölçümü bekleniyor, ${sayiTr(sn.yuklu)} saati yüklü${sn.yuklu_tahmini ? ` (${sayiTr(sn.yuklu_tahmini)} tahmini)` : ""}; ${sayiTr(sn.vadesi_gelmemis ?? 0)} saatin vadesi gelmedi. Eksik = PVQuant'a yüklenmemiş; EPİAŞ'ta eksik olduğu anlamına gelmez.` : g.sayac_turu === "diger" ? "aylık bildirim yapan sayaç; saat bazında beklenti yok" : "önce sayaç türünü seçin (sağdaki kart)"} />
        <Kpi etiket={`Sayaç ve SCADA üretim farkı (${sayiTr(f.pencere_gun)} gün)`} bilgi="Sayaç − SCADA, yalnız iki serinin de bulunduğu ve sayaç değeri ölçülmüş olan saatlerde; yüzde SCADA toplamına oranla. İkinci satır tahmini değerler dâhil. SCADA brüt AC üretim, sayaç şebekeye verilen net enerjidir; oran santrale özgüdür, PVQuant eşik koymaz."
          deger={yuzde(f.olculmus.fark_pct)} ikinci={f.tahmini_dahil.saat && f.tahmini_dahil.saat !== f.olculmus.saat ? { etiket: "tahmini değerler dâhil", deger: `${yuzde(f.tahmini_dahil.fark_pct)} (${sayiTr(f.tahmini_dahil.saat)} saat)` } : undefined}
          alt={f.olculmus.saat ? `${sayiTr(f.olculmus.saat)} ölçülmüş ortak saat; ${imzali(f.olculmus.fark_kwh)} kWh; kapsam %${sayiTr(f.kapsam.ortak_pct ?? 0, 0)} (${sayiTr(f.kapsam.ortak_saat)} / ${sayiTr(f.kapsam.pencere_saat)} saat). Sürekli benzer bir fark çoğunlukla ölçüm noktası ve öz tüketimdendir; tek başına arıza göstergesi değildir.` : "karşılaştırma için hem SCADA hem sayaç verisi olan saat gerekir"} />
        <Kpi etiket="Sayaç verisi düzeltme son tarihi" bilgi="DUY m.82(4): ayın 12'si 17:30'dan sonra gelen sayaç düzeltmesi o ayın uzlaştırmasına girmez; sayaç değerleri dönem sonunu izleyen ilk 10 gün içinde PYS'ye aktarılır (m.81(1)). Hafta sonuna denk gelen 12'si için EPİAŞ uygulaması metinde yazılı değil. Alt satır: dönemin sayaç kapsamı PVQuant'ta."
          deger={dSon ? (dSon.gecti ? "geçti" : sureTr(dSon.kalan_saat)) : "—"} birim={dSon && !dSon.gecti ? "kaldı" : undefined} ton={dSon && !dSon.gecti && dSon.kalan_saat <= 72 ? "amber" : undefined}
          alt={dSon ? <>{ayAd(dSon.donem)} dönemi: {gunTr(dSon.itiraz_son)} 17:30{d0 && d0 !== dSon ? ` (${ayAd(d0.donem)} geçti)` : ""}{dSon.hafta_sonu ? "; hafta sonu" : ""}; PVQuant'ta {sayiTr(dSon.kapsam.yuklu)} / {sayiTr(dSon.kapsam.vadesi_gelen)} saat{dSon.kapsam.eksik ? `, ${sayiTr(dSon.kapsam.eksik)} eksik` : ""}{!dSon.gecti ? <span className="soluk"> · bu tarihten sonra yapılan sayaç düzeltmesi {ayAd(dSon.donem)} uzlaştırmasına girmez</span> : null}</> : undefined} />
      </div>
      <div className="ızgara-cift">
        <Kart baslik="Sayaç dosyası yükleme" alt="Dağıtım şirketi portalından (OSOS), Millî Akıllı Sayaç Sistemi'nden (MASS) ya da EPİAŞ'ın EPYS sisteminden indirdiğiniz sayaç dosyasını (CSV ya da XLSX) yükleyin. Dosyada zaman ve veriş/üretim kWh sütunu olmalı; 15 dakikalık değerler saate toplanır, durum sütunu veri türü olarak saklanır.">
          <div className="form-izgara">
            <label className="girdi-etiket form-tam">Dosya<input key={dosyaAnahtar} className="girdi" type="file" accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={(e) => setDosya(e.target.files?.[0] ?? null)} /></label>
            <label className="girdi-etiket">Kaynak<select className="girdi" value={kaynak} onChange={(e) => setKaynak(e.target.value as SayacKaynak)} title={o.kaynaklar.find((k) => k.kod === kaynak)?.etiket}>
              {o.kaynaklar.map((k) => <option key={k.kod} value={k.kod} title={k.etiket}>{k.etiket.split(" (")[0]}</option>)}</select></label>
            <div className="dugme-sira" style={{ alignSelf: "end" }}><button className="dugme" onClick={gonder} disabled={yukleniyor}>{yukleniyor ? "Yükleniyor…" : "Yükle"}</button></div>
            {mesaj && <div className="form-tam"><span className={`ayar-durum ${mesaj.ton === "uyari" ? "" : mesaj.ton}`} style={mesaj.ton === "uyari" ? amber : undefined}>{mesaj.metin}</span></div>}
          </div>
          <p className="form-not" style={{ marginTop: 10, fontSize: 13.5 }}>Aynı saat için aynı kaynaktan yeniden yüklerseniz değer güncellenir (düzeltme); eski yüklemeler silinmez. Aynı saatte birden çok kaynak varsa EPYS, OSOS, MASS, elle sırasıyla biri gösterilir. Endeks (sayaç sayacı) sütunu tek başına yetmez; saatlik enerji (kWh) sütunu gerekir.</p>
          {o.yuklemeler.length > 0 && (
            <div className="grafik-kaydir" style={{ marginTop: 10 }}><table className="veri" style={{ fontSize: 13.5 }}>
              <thead><tr><th style={sol}>Yükleme</th><th style={sol}>Kaynak · dosya</th><th style={sol}>Aralık</th><th>Saat</th><th style={sol}>Veri türü</th></tr></thead>
              <tbody>{o.yuklemeler.map((y) => (
                <tr key={y.yukleme_id}>
                  <td style={{ ...sol, whiteSpace: "nowrap" }}>{saatTr(y.zaman)}</td><td style={{ ...sol, whiteSpace: "normal" }}>{y.kaynak_etiket.split(" (")[0]}<div className="soluk" style={{ fontSize: 12, wordBreak: "break-all" }}>{y.dosya_adi ?? "—"}</div></td>
                  <td style={{ ...sol, whiteSpace: "nowrap" }}>{gunTr(y.bas)} – {gunTr(y.bit)}</td><td className="mono">{sayiTr(y.n_saat)}</td>
                  <td style={sol}>{Object.entries(y.nitelik_sayim).filter(([k]) => k !== "olculmus").map(([k, n]) => `${sayiTr(n)} ${NITELIK_AD[`sayac_${k}`]?.replace("sayaç ", "") ?? k}`).join(", ") || "ölçülmüş"}{y.uyarilar.length ? <span className="soluk" title={y.uyarilar.join("; ")}> · uyarı</span> : null}</td></tr>))}</tbody>
            </table></div>)}
        </Kart>
        <Kart baslik="Beklenen sayaç verisi iletimi" alt="Sayaç türüne göre verinin EPİAŞ'a ne zaman ulaşması gerektiği; PVQuant'taki son sayaç ve SCADA saati; dönem düzeltme takvimi"
          sag={g.beklenen.kesinlik ? <span className={`rozet rozet-kucuk ${g.beklenen.kesinlik === "mevzuat" ? "rozet-ok" : "rozet-notr"}`} title={g.beklenen.not ?? g.beklenen.dayanak ?? ""}>{g.beklenen.kesinlik === "mevzuat" ? "mevzuat" : "belirsiz"}</span> : undefined}>
          <div className="form-izgara">
            <label className="girdi-etiket">Sayaç türü<select className="girdi" value={tur} onChange={(e) => setTur(e.target.value)}>
              <option value="">seçilmedi</option>{o.sayac_turleri.map((s) => <option key={s.kod} value={s.kod}>{s.etiket}</option>)}</select></label>   {/* v2.537: etiket s.etiket — yanlış üçlü her seçeneği «SCADA ölçümü» gösteriyordu */}
            <label className="girdi-etiket" title="Mutabakat ve dönem raporundaki uzlaştırma yeniden hesabında gerçekleşen üretimin kaynağı. Sayaç seçilirse yüklü sayaç saatlerinde sayacın veriş kWh'si, kalan saatlerde SCADA kullanılır; sayaç dosyasının uzlaştırmaya esas resmî sayaç değeriyle aynı olduğu doğrulanmaz.">
              Mali hesaplamada kullanılacak üretim verisi<select className="girdi" value={girdi} onChange={(e) => setGirdi(e.target.value === "sayac" ? "sayac" : "scada")}>
              {(o.uretim_secenekleri ?? [{ kod: "scada", etiket: "SCADA ölçümü" }, { kod: "sayac", etiket: "sayaç verisi (yüklü saatlerde; kalan saatler SCADA)" }]).map((s) => <option key={s.kod} value={s.kod}>{s.kod === "sayac" ? "sayaç ölçümü (yüklü saatlerde; kalanı SCADA)" : "SCADA ölçümü"}</option>)}</select></label>
            <div className="dugme-sira" style={{ alignSelf: "end" }}><button className="dugme" onClick={() => ayarKaydet({ sayac_turu: tur || null, uzlastirma_girdi: girdi })}>Kaydet</button>
              {ayarDurum && <span className={`ayar-durum ${ayarDurum.ton}`}>{ayarDurum.metin}</span>}</div>
          </div>
          <ul className="not-listesi" style={{ fontSize: 13.5, marginTop: 10 }}>
            <li><b>Beklenen iletim:</b> {g.beklenen.kural}{g.beklenen.dayanak ? ` (${g.beklenen.dayanak})` : ""}{g.beklenen.son_beklenen_saat ? `; şu an EPİAŞ'ta olması beklenen son dilim ${gunTr(g.beklenen.son_beklenen_saat)} ${g.beklenen.son_beklenen_dilim}` : ""}</li>
            {g.beklenen.not && <li className="soluk">{g.beklenen.not}</li>}
            {sn.vadesi_gelen != null && <li><b>Bu ay ({ayAd(g.ay)}):</b> {sayiTr(sn.gecen_saat)} saat geçti; ölçümü beklenen {sayiTr(sn.vadesi_gelen)}, henüz beklenmeyen {sayiTr(sn.vadesi_gelmemis ?? 0)}; yüklü {sayiTr(sn.yuklu)} ({sayiTr(sn.yuklu_olculmus)} ölçülmüş, {sayiTr(sn.yuklu_tahmini)} tahmini); PVQuant'a yüklenmemiş {sayiTr(sn.eksik ?? 0)}</li>}
            <li><b>PVQuant'taki son ölçüm:</b> sayaç {saatTr(g.son_sayac)}; SCADA {saatTr(g.son_scada)}</li>
            {g.donemler.map((d) => (
              <li key={d.donem}><b>{ayAd(d.donem)} dönemi:</b> şebeke işletmecisi sayaç değerlerini {gunTr(d.sayac_veri)} tarihine kadar EPİAŞ'a iletir; düzeltme son tarihi {gunTr(d.itiraz_son)} 17:30
                {d.gecti ? " (geçti)" : ` (${sureTr(d.kalan_saat)} kaldı)`}{d.not ? <span style={amber}> · {d.not}</span> : null}
                {d.kapsam.vadesi_gelen > 0 && <span className="soluk"> · PVQuant'ta {sayiTr(d.kapsam.yuklu)} / {sayiTr(d.kapsam.vadesi_gelen)} saat{d.kapsam.tahmini ? ` (${sayiTr(d.kapsam.tahmini)} tahmini)` : ""}{d.kapsam.eksik ? <span style={amber}>, {sayiTr(d.kapsam.eksik)} saat yüklenmemiş</span> : null}</span>}</li>))}
          </ul>
          <details className="aciklama" style={{ marginTop: 10 }}><summary>Dayanak</summary><p style={{ margin: "6px 0 0" }}>{g.kaynak}</p></details>
        </Kart>
      </div>
      <Kart baslik="Sayaç ve SCADA üretim karşılaştırması" alt={`${gunTr(f.bas)} – ${gunTr(f.bit)}; günlük toplam (Türkiye günü); fark = sayaç − SCADA, yalnız iki verinin de bulunduğu saatlerde`}
        sag={<span className="cip"><Meta items={[`${sayiTr(t.saat_ortak)} ortak saat`, t.saat_sayac ? `${sayiTr(t.saat_sayac)} sayaç saati` : "sayaç verisi yok", `${sayiTr(t.saat_scada)} SCADA saati`]} /></span>}>
        <p className="form-not" style={{ margin: "0 0 6px", fontSize: 13.5 }}><b>Yalnız ölçülmüş ortak saatler:</b> {f.olculmus.saat ? `${sayiTr(f.olculmus.saat)} saat, sayaç ${kwh(f.olculmus.sayac_kwh)} / SCADA ${kwh(f.olculmus.scada_kwh)} kWh, fark ${yuzde(f.olculmus.fark_pct)}` : "yok"}
          {f.tahmini_dahil.saat !== f.olculmus.saat ? <> · <b>Tahmini değerler dâhil:</b> {sayiTr(f.tahmini_dahil.saat)} saat, fark {yuzde(f.tahmini_dahil.fark_pct)}</> : null}
          {" · "}<b>Kapsam:</b> {sayiTr(f.kapsam.ortak_saat)} / {sayiTr(f.kapsam.pencere_saat)} saat ortak{f.kapsam.yalniz_scada_saat ? `, ${sayiTr(f.kapsam.yalniz_scada_saat)} yalnız SCADA` : ""}{f.kapsam.yalniz_sayac_saat ? `, ${sayiTr(f.kapsam.yalniz_sayac_saat)} yalnız sayaç` : ""}{f.kapsam.ikisi_de_yok_saat ? `, ${sayiTr(f.kapsam.ikisi_de_yok_saat)} ikisi de yok` : ""}</p>
        {kaynakSayim.length > 0 && <p className="form-not" style={{ margin: "0 0 10px", fontSize: 13.5 }}><b>Verinin kaynağı ({sayiTr(f.pencere_saat)} saat; sayaç sayımı SCADA'dan bağımsız):</b> {kaynakSayim.map(([k, n]) => `${NITELIK_AD[k] ?? k} ${sayiTr(n)}`).join(" · ")}
          {Object.keys(f.sayac_kaynak_sayim).length ? ` · sayaç kaynağı: ${Object.entries(f.sayac_kaynak_sayim).map(([k, n]) => `${k.toUpperCase()} ${sayiTr(n)}`).join(", ")}` : ""}</p>}
        {f.gunler.length === 0 ? <p className="soluk" style={{ margin: 0 }}>Bu aralıkta ne SCADA ne sayaç saati var.</p> : (
          <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 13.5 }}>
            <thead><tr><th style={sol}>Gün</th><th title="Geçerli SCADA saatlerinin kWh toplamı (dosya ya da Şeffaflık akışı)">SCADA (kWh)</th><th title="Sayaç veriş kWh toplamı">Sayaç (kWh)</th>
              <th title="İki serinin de bulunduğu saat sayısı / günün en çok saati">Ortak saat</th><th title="Ortak saatlerde sayaç − SCADA">Fark (kWh)</th><th title="SCADA toplamına oranla, bütün ortak saatler">Fark</th><th title="Yalnız sayaç değeri ölçülmüş olan ortak saatlerde fark">Ölçülmüş fark</th><th title="Tahmini, doldurulmuş ya da «veri yok» işaretli sayaç saatleri">Tahmini saat</th></tr></thead>
            <tbody>{[...f.gunler].reverse().map(gunSatir)}</tbody>
          </table></div>)}
        {f.en_buyuk_fark && <p className="form-not" style={{ marginTop: 8, fontSize: 13.5 }}><b>En büyük günlük fark:</b> {gunTr(f.en_buyuk_fark.gun)}, {imzali(f.en_buyuk_fark.fark_kwh)} kWh ({yuzde(f.en_buyuk_fark.fark_pct)}). Fark sürekli aynı yöndeyse ölçüm noktası ve öz tüketim; tek günlükse saat dilimi ya da eksik dilim en sık nedendir.</p>}
        <p className="form-not" style={{ marginTop: 8, fontSize: 13.5 }}>{f.aciklama}</p>
      </Kart>
      {!sc && o.scada_notu && <p className="form-not soluk" style={{ margin: "14px 0 0", fontSize: 13.5 }}><b>SCADA bağlantı durumu:</b> {o.scada_notu}</p>}
      {sc && (
        <Kart baslik="SCADA bağlantı durumu" alt="Lisanssız tesis (LÜY m.21(7)); durum beyandır. Karar 14909 bedel göstergesi varsayımsaldır; (f)/(g) askısı 30.4.2027 (tarih kısmen teyit)."
          sag={<span className={`rozet rozet-kucuk ${!sc.yukumlu ? "rozet-notr" : sc.durum === "bagli" ? "rozet-ok" : sc.durum ? "rozet-uyari" : "rozet-notr"}`} title={`${sc.dayanak_yukumluluk}. Durum kaynağı: beyan (bu formda girilir).`}>
            {!sc.yukumlu ? `${sayiTr(sc.esik_kw)} kW altı; yükümlülük yok` : `${sc.durum_etiket} · beyan`}</span>}>
          <div className="ızgara-cift">
            <div>
              <div className="form-izgara">
                <label className="girdi-etiket">Bağlantı durumu<select className="girdi" value={scada.durum} onChange={(e) => setScada({ ...scada, durum: e.target.value })}>
                  <option value="">girilmedi</option>{o.scada_durumlari.map((s) => <option key={s.kod} value={s.kod}>{s.etiket}</option>)}</select></label>   {/* v2.537: etiket s.etiket (bağlı / kopuk / entegrasyon yok) */}
                {scada.durum === "kopuk" && <label className="girdi-etiket">Kopukluk başlangıcı<input className="girdi" type="date" value={scada.bas} onChange={(e) => setScada({ ...scada, bas: e.target.value })} /></label>}
                <label className="girdi-etiket">Aylık sistem kullanım bedeli (TL)<input className="girdi" inputMode="decimal" placeholder="dağıtım faturasından" value={scada.bedel} onChange={(e) => setScada({ ...scada, bedel: e.target.value.replace(/[^0-9.,]/g, "") })} /></label>
                <label className="girdi-etiket form-tam" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                  <input type="checkbox" checked={!!scada.uzaktan} onChange={(e) => setScada({ ...scada, uzaktan: e.target.checked })} /> Uzaktan açma-kapama yeteneği var</label>
                <div className="form-tam dugme-sira"><button className="dugme" onClick={scadaKaydet}>Kaydet</button>{scadaDurumIleti && <span className={`ayar-durum ${scadaDurumIleti.ton}`}>{scadaDurumIleti.metin}</span>}</div>
              </div>
              <ul className="not-listesi" style={{ fontSize: 13.5, marginTop: 10 }}>
                <li><b>Yükümlülük:</b> {sc.kurulu_kaynak} {sayiTr(sc.kurulu_kw, 0)} kW {sc.yukumlu ? "≥" : "<"} {sayiTr(sc.esik_kw)} kW → {sc.yukumlu ? "SCADA bağlantısı zorunlu" : "bağlantı yükümlülüğü yok"} (LÜY m.21(7)); anlaşma tarafı {sc.anlasma === "dagitim" ? "dağıtım şirketi" : "TEİAŞ (iletim)"}; DUY m.75(4) kapsamı (900 kW ve üzeri): {sc.m75_kapsam ? "içinde" : "dışında"}</li>
                <li><b>Durum kaynağı:</b> beyan (bu form); PVQuant şebeke işletmecisinin SCADA'sına bağlı değildir. PVQuant'taki SCADA dosyası tazeliği ayrı bir göstergedir.</li>
                {sc.kopukluk_gun != null && <li><b>Kopukluk sayacı:</b> <span style={sc.kopukluk_gun > 30 ? amber : undefined}>{sayiTr(sc.kopukluk_gun)} gün</span> ({gunTr(sc.kopukluk_baslangic)} tarihinden beri); bir ay içinde onarılmazsa günlük bedel maddesi başlar</li>}
                <li><b>Uzaktan açma-kapama yeteneği:</b> {sc.uzaktan_acma_var == null ? "girilmedi" : sc.uzaktan_acma_var ? "var" : "yok"} (envanter bilgisi; DUY m.75(4) acil durum talimatı 900 kW ve üzerinden başlar)</li>
                <li><b>Uzaktan açma olayları (bu ay):</b> {sayiTr(sc.uzaktan_acma_ay)} — Olay kaydı › «Uzaktan açma yapılamadı» türüyle girilir</li>
                <li><b>Askı:</b> (f) ve (g) {gunTr(sc.aski_bitis)} tarihine kadar uygulanmaz ({sc.aski_gecti ? "süre doldu" : `${sayiTr(sc.aski_kalan_gun)} gün kaldı`}; tarih ikincil kaynaktan, kısmen teyit); (ç) için askı doğrulanmadı</li>
              </ul>
            </div>
            <div>
              <table className="veri" style={{ fontSize: 13.5 }}>
                <thead><tr><th style={sol}>Karar 14909 bedel göstergesi</th><th>Kat</th><th title="Varsayımsal: girdiğiniz bedelle kaba uygulama; tebliğ edilmiş borç değildir">Varsayımsal tutar (TL)</th></tr></thead>
                <tbody>{sc.kalemler.length === 0 ? <tr><td style={sol} colSpan={3} className="soluk">{!sc.yukumlu ? "Yükümlülük yok." : sc.anlasma === "iletim" ? "İletime bağlı tesis: dağıtım bağlantı anlaşması bedel maddeleri uygulanmaz." : "Bu ay için bedel maddesi tetiklenmedi (durum bağlı ya da 30 gün aşılmadı, uzaktan açma olayı yok)."}</td></tr>
                  : sc.kalemler.map((k) => <tr key={k.kod}><td style={sol}>{k.etiket}{k.kesinlik === "belirsiz" ? <span className="soluk" title={k.not ?? ""}> · belirsiz</span> : null}<div className="soluk" style={{ fontSize: 12 }}>{k.birim}{k.aski === "kapsamda" ? " · askıda" : k.aski === "dogrulanmadi" ? " · askı doğrulanmadı" : ""}</div></td>
                    <td className="mono">{sayiTr(k.kat, 2)}</td><td className="mono">{k.tutar_tl != null ? sayiTr(k.tutar_tl, 2) : "bedel girilmedi"}</td></tr>)}
                  {sc.kalemler.length > 0 && <tr style={{ fontWeight: 600 }}><td style={sol}>Toplam · varsayımsal{sc.toplam_aski_tl && !sc.aski_gecti ? <span className="soluk" style={{ fontWeight: 400 }}> ({sayiTr(sc.toplam_aski_tl, 2)} TL askı bitince{sc.toplam_aski_disi_tl ? `; ${sayiTr(sc.toplam_aski_disi_tl, 2)} TL askı doğrulanmadı` : ""})</span> : null}</td><td /><td className="mono">{sc.toplam_tl != null ? sayiTr(sc.toplam_tl, 2) : "—"}</td></tr>}</tbody>
              </table>
              {sc.uygulanmayan.length > 0 && <ul className="not-listesi soluk" style={{ fontSize: 13, marginTop: 6 }}>{sc.uygulanmayan.map((u) => <li key={u}>{u}</li>)}</ul>}
              <p className="form-not" style={{ marginTop: 8, fontSize: 13.5 }}>{sc.not}</p>
              <details className="aciklama" style={{ marginTop: 8 }}><summary>Dayanak</summary><p style={{ margin: "6px 0 0" }}>{sc.kaynak}</p></details>
            </div>
          </div>
        </Kart>)}
      <details className="aciklama" style={{ marginTop: 14 }}>
        <summary>Bu sayfa nasıl çalışır</summary>
        {/* v2.537 Sayaç dil turu: beş müşteri sorusu, kısa cevaplar; teknik ayrıntı ve dayanak ayrı açılır alanda */}
        <dl className="kunye" style={{ marginTop: 8 }}>
          <div><dt>Sayaç ölçümlerimi nasıl yüklerim?</dt><dd><span className="kunye-not">Dağıtım şirketi portalından (OSOS), Millî Akıllı Sayaç Sistemi'nden (MASS) ya da EPİAŞ'ın EPYS sisteminden indirdiğiniz dosyayı «Sayaç dosyası yükleme» kartından yükleyin. Dosyada zaman ve üretim (kWh) sütunu olması yeter; 15 dakikalık değerler saate toplanır. Aynı saati yeniden yüklerseniz değer güncellenir, eski yüklemeler silinmez.</span></dd></div>
          <div><dt>Eksik ölçüm var mı, nasıl anlarım?</dt><dd><span className="kunye-not">«Eksik ölçüm saatleri» kartı, bu ay ölçümü beklenen saatlerden PVQuant'a yüklenmemiş olanları sayar. Eksik, verinin PVQuant'ta olmadığını gösterir; EPİAŞ'a ulaşıp ulaşmadığını PVQuant göremez. Dönem satırlarında geçmiş ayların kapsamı da görünür.</span></dd></div>
          <div><dt>Sayaç ile SCADA üretimi neden farklı?</dt><dd><span className="kunye-not">SCADA ya da inverter santralin ürettiği brüt enerjiyi, sayaç şebekeye verilen net enerjiyi ölçer. Öz tüketim, trafo ve hat kayıpları, ölçüm noktası ve saat dilimi farkı iki değeri ayırır. Sürekli benzer bir fark olağandır; tek günlük büyük sapma eksik saat ya da saat dilimi hatasını düşündürür.</span></dd></div>
          <div><dt>Ölçülmüş değer ile tahmini değer farkı ne?</dt><dd><span className="kunye-not">Portal dosyasındaki durum kodu korunur: ölçülmüş, tahmini, doldurulmuş, elle girilmiş, veri yok. Karşılaştırmada «ölçülmüş fark» yalnız gerçekten okunmuş saatleri kullanır; tahmini saatler ayrıca sayılır ve mali hesaplamada da etiketlenir.</span></dd></div>
          <div><dt>Yanlış bir ölçüm varsa ne yapmalıyım?</dt><dd><span className="kunye-not">Düzeltme talebini sayacı okuyan kuruma (dağıtım şirketi ya da TEİAŞ) iletin; ayın 12'si 17:30'dan sonraki düzeltmeler o ayın uzlaştırmasına girmez. PVQuant resmî EPİAŞ sayaç kayıtlarını değiştirmez; yalnızca sizin yüklediğiniz dosyaları karşılaştırır.</span></dd></div>
        </dl>
        <details className="aciklama" style={{ marginTop: 8 }}>
          <summary>Teknik ayrıntılar ve dayanak</summary>
          <p style={{ margin: "6px 0 0" }}>{o.not}</p>
          <p style={{ margin: "6px 0 0" }}><b>Veri türü:</b> dağıtım şirketi portalının durum kodları korunur — ölçülmüş, tahmini, doldurulmuş, elle girilmiş, veri yok. Düzeltme talebi dağıtım şirketine ya da TEİAŞ'a başvuruyla yapılır (DUY m.82(3)); ayın 12'si 17:30'dan sonraki düzeltme o aya girmez (m.82(4)); tahmini saatler ayrı sayılır.</p>
          <p style={{ margin: "6px 0 0" }}><b>Dosya tanıma:</b> OSOS, MASS ve EPYS dosyalarının resmî sütun başlıkları elimizde yok; zaman (tarih/saat/profil tarihi), veriş/üretim kWh (ya da MWh), çekiş ve durum sütunları ipuçlarıyla tanınır. Zaman Türkiye saati ve dilim başı varsayılır. Gelecek tarihli, negatif ya da okunamayan satırlar alınmaz ve sayıları yükleme sonucunda yazılır.</p>
        </details>
      </details>
    </Sayfa>
  );
}
