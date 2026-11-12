import { useEffect, useState } from "react";
import { api, rolum } from "../../api/client";
import type { BelirsizlikDurum, FinansNitelik, PortfoyDetay, PortfoyDsgT, PortfoyFinansT, PortfoyKisa, PortfoyRevizyonT, PortfoyRiskT, PortfoySapmaT, PortfoySozlesme, PortfoyTahminT, RiskEtiket } from "../../api/types";
import { donemSecenekleri, TUR_AD, type FinansDonemTur } from "../../lib/donem";
import { tarihBicimi } from "../../lib/bicim";
import { Meta } from "../../lib/Meta";
import { HesapDurumu, Kart, Kpi, Sayfa, sayiTr, SayfaIskeleti, YerTutucu } from "./parcalar";

/** v2.595 (Faz 3 F3-H) — Portföy yönetimi: toplayıcı ya da DSG yöneticisinin portföyünü birkaç saniyede okuması için tek sayfa.
 *  Santral tahminleri, uzlaştırma ve finansal etki hesapları değişmez; bu sayfa zamanlı üyelik kayıtlarıyla (F3-A) portföy tahmini ve
 *  belirsizliğini (F3-B), sapma ve riski (F3-C), DSG üç perspektifini (F3-D), revizyon önerilerini (F3-E) ve portföy finansal etkisini (F3-G) derler.
 *  Dürüstlük: belirsizlik aralığı yalnız geçmiş sınavla «doğrulandı» ise öyle yazılır; sözleşmesel dağılım yalnız doğrulanmış belgeli sözleşmede
 *  «sözleşmeye dayalı», aksi «varsayımsal»; eksik ölçüm 0 sayılmaz; tutarlar yeniden hesaptır, EPİAŞ sonucu değildir. Otomatik bildirim yok. */
const NITELIK: Record<FinansNitelik, { etiket: string; sinif: string }> = {
  resmi: { etiket: "resmî", sinif: "rozet-ok" }, hesaplanan: { etiket: "hesaplanan", sinif: "rozet-notr" }, sozlesme_tahmini: { etiket: "sözleşme tahmini", sinif: "rozet-notr" },
  senaryo: { etiket: "senaryo", sinif: "rozet-uyari" }, eksik: { etiket: "eksik", sinif: "rozet-notr" } };
const BELIRSIZLIK: Record<BelirsizlikDurum, { etiket: string; sinif: string }> = {
  dogrulandi: { etiket: "aralık doğrulandı", sinif: "rozet-ok" }, dogrulanmadi: { etiket: "aralık doğrulanmadı", sinif: "rozet-uyari" }, yetersiz_veri: { etiket: "aralık için veri yetersiz", sinif: "rozet-notr" } };
const RISK: Record<RiskEtiket, string> = { dogrulanmis: "rozet-ok", tahmini: "rozet-uyari", eksik: "rozet-notr", gecti: "rozet-notr", bilgi: "rozet-notr" };
const ONERI_SINIF: Record<string, string> = { eylem: "rozet-dikkat", oneri: "rozet-uyari", bilgi: "rozet-notr" };
const DOGRULAMA_SINIF: Record<string, string> = { dogrulandi: "rozet-ok", belgeli: "rozet-notr", beyan: "rozet-uyari" };
const TUR_ETIKET: Record<string, string> = { toplayici: "toplayıcı portföyü", dsg: "dengeden sorumlu grup", isletme: "işletme portföyü", ozel: "özel portföy" };
/* 12.11 inceleme 1: sözleşme kayıtları tablosunda iç kod («sabit_pay», «dsg») görünmez — arka uç sözlüğüyle (dagitim.YONTEM_AD, DENGESIZLIK_SORUMLULARI) aynı adlar. */
const DAGILIM_AD: Record<string, string> = { sapma: "sapma payına göre", esit: "eşit paylarla", uretim: "üretime göre", sabit_pay: "sözleşmedeki sabit paylarla", ozel: "sözleşmedeki özel kurallarla" };
const SORUMLU_AD: Record<string, string> = { santral: "santral", toplayici: "toplayıcı", dsg: "dengeden sorumlu grup", gts: "görevli tedarik şirketi" };
const SAYFA_AD: Record<string, string> = { tahminler: "Tahminler", santralim: "Santralim", kurulus: "Ayarlar", veri: "Veri yükleme", finans: "Finansal etki" };
const sol = { textAlign: "left" as const };
const yaz = (v: number | null | undefined, ondalik = 0) => v == null ? "—" : `${v < 0 ? "−" : ""}${sayiTr(Math.abs(v), ondalik)}`;
const isaretli = (v: number | null | undefined, ondalik = 0) => v == null ? "—" : `${v > 0 ? "+" : v < 0 ? "−" : ""}${sayiTr(Math.abs(v), ondalik)}`;
const binTl = (v: number | null | undefined) => v == null ? "—" : `${v < 0 ? "−" : ""}${sayiTr(Math.abs(v) / 1000, 1)}`;
const gunYaz = (iso: string | null | undefined) => iso ? tarihBicimi("tr-TR", { day: "numeric", month: "short", year: "numeric" }).format(new Date(iso.slice(0, 10) + "T12:00:00")) : "—";
const saatYaz = (iso: string | null | undefined) => iso ? tarihBicimi("tr-TR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(iso)) : "—";
const bugunIso = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };
const yarinIso = () => { const d = new Date(); d.setDate(d.getDate() + 1); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };

function Rozet({ sinif, children, title }: { sinif: string; children: React.ReactNode; title?: string }) {
  return <span className={`rozet rozet-kucuk ${sinif}`} title={title}>{children}</span>;
}
function Nitelik({ n }: { n: FinansNitelik | undefined }) { const x = NITELIK[n ?? "eksik"] ?? NITELIK.eksik; return <Rozet sinif={x.sinif}>{x.etiket}</Rozet>; }

type Yuk<T> = T | null | undefined;   // undefined = yükleniyor, null = alınamadı

export function Portfoyler() {
  const yazabilir = rolum() === "admin" || rolum() === "editor"; const yonetici = rolum() === "admin";
  const [liste, setListe] = useState<Yuk<PortfoyKisa[]>>(undefined);
  const [secili, setSecili] = useState<string>(() => localStorage.getItem("pvq_portfoy") ?? "");
  const [tur, setTur] = useState<FinansDonemTur>("ay");
  const [kod, setKod] = useState<string>(() => donemSecenekleri("ay")[1]?.kod ?? donemSecenekleri("ay")[0].kod);
  const [hedef, setHedef] = useState<"yarin" | "bugun">("yarin");
  const [detay, setDetay] = useState<Yuk<PortfoyDetay>>(undefined);
  const [tahmin, setTahmin] = useState<Yuk<PortfoyTahminT>>(undefined);
  const [sapma, setSapma] = useState<Yuk<PortfoySapmaT>>(undefined);
  const [risk, setRisk] = useState<Yuk<PortfoyRiskT>>(undefined);
  const [dsg, setDsg] = useState<Yuk<PortfoyDsgT>>(undefined);
  const [rev, setRev] = useState<Yuk<PortfoyRevizyonT>>(undefined);
  const [fin, setFin] = useState<Yuk<PortfoyFinansT>>(undefined);
  const [sozlesmeler, setSozlesmeler] = useState<Yuk<PortfoySozlesme[]> | "yetki_yok">(undefined);
  const [yenile, setYenile] = useState(0);
  const secenekler = donemSecenekleri(tur);

  useEffect(() => {
    let acik = true; setListe(undefined);
    api.portfoyler().then((l) => { if (!acik) return; setListe(l); if (l && l.length && !l.some((p) => p.id === secili)) setSecili(l[0].id); }, () => { if (acik) setListe(null); });
    return () => { acik = false; };
  }, [yenile]);   // eslint-disable-line react-hooks/exhaustive-deps -- seçim yalnız ilk listede düzeltilir
  useEffect(() => {
    if (!secili) return;
    localStorage.setItem("pvq_portfoy", secili);
    let acik = true;
    setDetay(undefined); setTahmin(undefined); setSapma(undefined); setDsg(undefined); setFin(undefined); setSozlesmeler(undefined);
    const yukle = <T,>(p: Promise<T | null>, set: (v: Yuk<T>) => void) => p.then((v) => { if (acik) set(v); }, () => { if (acik) set(null); });
    yukle(api.portfoyDetay(secili), setDetay); yukle(api.portfoylerTahmin(secili, 7), setTahmin); yukle(api.portfoySapma(secili, kod), setSapma);
    yukle(api.portfoyDsgPerspektif(secili, kod), setDsg); yukle(api.portfoyFinans(secili, kod), setFin);
    if (yazabilir) api.sozlesmeler(secili).then((z) => { if (acik) setSozlesmeler(z); }, (e: Error) => { if (acik) setSozlesmeler(/403/.test(e.message) ? "yetki_yok" : null); });
    else setSozlesmeler("yetki_yok");
    return () => { acik = false; };
  }, [secili, kod, yenile, yazabilir]);
  useEffect(() => {
    if (!secili) return;
    let acik = true; setRisk(undefined); setRev(undefined);
    api.portfoyRisk(secili, 2).then((v) => { if (acik) setRisk(v); }, () => { if (acik) setRisk(null); });
    api.portfoyRevizyon(secili, hedef).then((v) => { if (acik) setRev(v); }, () => { if (acik) setRev(null); });
    return () => { acik = false; };
  }, [secili, hedef, yenile]);
  const turDegis = (t: FinansDonemTur) => { setTur(t); const s = donemSecenekleri(t); setKod((t === "ay" || t === "ceyrek" || t === "yil") && s[1] ? s[1].kod : s[0].kod); };

  const secici = (
    <span className="dugme-sira">
      {liste && liste.length > 0 && <select className="girdi" value={secili} onChange={(e) => setSecili(e.target.value)} aria-label="Portföy">
        {liste.map((p) => { const tur = TUR_ETIKET[p.tur] ?? p.tur; const adTuruIceriyor = p.ad.toLocaleLowerCase("tr").includes(tur.toLocaleLowerCase("tr"));   // 12.11 inceleme: «Toplayıcı portföyü · toplayıcı portföyü» tekrarı
          return <option key={p.id} value={p.id}>{p.ad}{adTuruIceriyor ? "" : ` · ${tur}`}{p.gecerli ? "" : " (geçerli değil)"}</option>; })}</select>}
      <select className="girdi" value={tur} onChange={(e) => turDegis(e.target.value as FinansDonemTur)} aria-label="Dönem türü">
        {(Object.keys(TUR_AD) as FinansDonemTur[]).map((t) => <option key={t} value={t}>{TUR_AD[t]}</option>)}</select>
      <select className="girdi" value={kod} onChange={(e) => setKod(e.target.value)} aria-label="Dönem">
        {secenekler.map((s) => <option key={s.kod} value={s.kod}>{s.etiket}</option>)}</select>
    </span>);
  const alt = "Portföyünüzün bugünkü durumu: üretim beklentisi ve belirsizliği, program sapması, dengeden sorumlu grup ve sözleşme ilişkileri, revizyon önerileri. Tutarlar PVQuant'ın yeniden hesabıdır; EPİAŞ uzlaştırma sonucu değildir.";
  if (liste === undefined) return <Sayfa baslik="Portföy yönetimi" alt={alt}><SayfaIskeleti kpi={4} kart={3} /></Sayfa>;
  if (liste === null) return <Sayfa baslik="Portföy yönetimi" alt={alt}><p className="soluk">Portföy listesi alınamadı. Bağlantıyı kontrol edip sayfayı yenileyin.</p></Sayfa>;
  if (liste.length === 0) return (
    <Sayfa baslik="Portföy yönetimi" alt={alt}>
      <div className="bos-durum"><div className="bos-bas">Henüz tanımlı portföy yok</div>
        <p>Portföy, santrallerinizin ticari ilişkisini tarihli üyeliklerle tutar: toplayıcı portföyü, dengeden sorumlu grup, işletme portföyü ya da özel grup.
          {yazabilir ? " Aşağıdan ilk portföyü tanımlayın; santral ekledikçe tahmin, sapma ve risk görünümleri burada birikir." : " Portföyü kuruluşunuzun editör ya da yönetici yetkili kullanıcısı tanımlar."}</p></div>
      {yazabilir && <PortfoyFormu onBitti={() => setYenile((n) => n + 1)} />}
    </Sayfa>);
  const p = liste.find((x) => x.id === secili) ?? liste[0];
  const kat = sapma?.katkilar?.satirlar ?? []; const o = sapma?.ozet; const g = tahmin?.gunluk ?? []; const yarin = g.find((x) => x.gun === yarinIso()) ?? g.find((x) => x.gun === bugunIso());
  const bel = tahmin?.belirsizlik?.durum ?? risk?.belirsizlik?.durum;
  const uyeler = detay?.uyeler ?? [];
  const etkin = uyeler.filter((u) => !u.gecerli_bit || u.gecerli_bit >= bugunIso());
  const kapasite = tahmin?.kapasite_kwp ?? sapma?.kapasite_kwp ?? etkin.reduce((t, u) => t + (u.capacity_kwp ?? 0), 0);
  const rs = risk?.risk; const per = dsg?.perspektifler; const topFin = fin?.toplam;
  const yogun = kat.length ? kat.reduce((a, b) => (Math.abs(b.mwh ?? 0) > Math.abs(a.mwh ?? 0) ? b : a)) : null;
  const rho = sapma?.korelasyon?.rho; const rhoOrt = rho ? (() => { const v: number[] = []; const ad = Object.keys(rho); ad.forEach((a, i) => ad.slice(i + 1).forEach((b) => { const x = rho[a]?.[b]; if (typeof x === "number") v.push(x); })); return v.length ? v.reduce((s, x) => s + x, 0) / v.length : null; })() : null;
  return (
    <Sayfa baslik="Portföy yönetimi" alt={alt} sag={secici}>
      <p className="form-not" style={{ margin: "0 0 12px", fontSize: 13.5 }}>
        <b>{p.ad}</b> · {TUR_ETIKET[p.tur] ?? p.tur}{p.dsg_kodu ? ` · DSG kodu ${p.dsg_kodu}` : ""}{p.kurulus_ad ? ` · ${p.kurulus_ad}` : ""} · geçerlilik {gunYaz(p.gecerli_bas)}{p.gecerli_bit ? ` – ${gunYaz(p.gecerli_bit)}` : " – süresiz"} · {sayiTr(p.uye_sayisi)} üye bugün
        {rev?.ozet && <> · <span style={{ color: "var(--metin)" }}>{rev.ozet}</span></>}
      </p>
      <div className="ızgara satir-4" style={{ marginBottom: 14 }}>
        <Kpi etiket="Kurulu güç" bilgi="Bugün geçerli üyelerin kurulu gücü (DC). Üyelik tarihli tutulur; geçmiş dönemler o tarihteki üyelikle hesaplanır."
          deger={kapasite ? sayiTr(kapasite / 1000, 1) : "—"} birim={kapasite ? "MW" : undefined}
          alt={`${sayiTr(etkin.length)} etkin santral${tahmin?.tahmin_yok?.length ? `; ${tahmin.tahmin_yok.length} santralin tahmini yok` : ""}`} />
        <Kpi etiket={`Üretim beklentisi (${yarin?.gun === yarinIso() ? "yarın" : "bugün"})`} bilgi="Santral tahminlerinin toplamı (merkez). Aralık, santraller arası bağımlılık hesaba katılarak kurulur; naif toplam gibi şişirilmez. Aralığın doğrulandığı yalnız geçmiş gerçekleşmelerle sınandığında yazılır."
          deger={yarin?.p50_mwh == null ? "—" : sayiTr(yarin.p50_mwh, 1)} birim={yarin?.p50_mwh == null ? undefined : "MWh"}
          ikinci={yarin?.p10_mwh != null && yarin?.p90_mwh != null ? { etiket: "Aralık", deger: `${sayiTr(yarin.p10_mwh, 0)} – ${sayiTr(yarin.p90_mwh, 0)}`, birim: "MWh" } : undefined}
          alt={bel ? <><Rozet sinif={BELIRSIZLIK[bel].sinif}>{BELIRSIZLIK[bel].etiket}</Rozet> {tahmin?.tazelik?.farkli_yayin ? "tahminler farklı saatlerde yayımlandı" : tahmin?.tazelik?.en_yeni ? `en yeni tahmin ${saatYaz(tahmin.tazelik.en_yeni)}` : ""}</> : (tahmin === null ? "tahmin alınamadı" : "yükleniyor")} />
        <Kpi etiket={`Program sapması (${sapma?.donem?.etiket ?? "dönem"})`} bilgi="Gerçekleşen − program, yalnız bütün üyelerin ölçümü ve programı olan saatlerde; artı fazla üretim. Eksik ölçüm sıfır sayılmaz. Tahmin hatası ve fiziksel sapma ayrı satırlarda tutulur."
          deger={isaretli(o?.program_sapma.mwh, 1)} birim={o?.program_sapma.mwh == null ? undefined : "MWh"}
          ikinci={o?.program_sapma.pct != null ? { etiket: o.program_sapma.mwh! > 0 ? "Fazla üretim" : "Eksik üretim", deger: `%${sayiTr(Math.abs(o.program_sapma.pct), 1)}`, birim: "programın" } : undefined}
          alt={sapma?.kapsama ? `${sayiTr(sapma.kapsama.sapma_tam_saat)} / ${sayiTr(sapma.kapsama.beklenen_saat)} saatte program ve ölçüm birlikte · kapsama ${sapma.kapsama.guvenilirlik_ad.toLowerCase()}` : sapma === null ? "sapma alınamadı" : sapma?.durum === "uye_yok" ? "bu dönemde üye yok" : "yükleniyor"} />
        <Kpi etiket="Tahmini finansal etki" bilgi="Enerji satışı + enerji dengesizlik tutarı (bağımsız santral toplamı) + KGÜP sapma tutarı, net; artı portföy lehine. DSG içi tutar bağımsız tutarın yerine geçer, toplanmaz; ayrı gösterilir."
          deger={binTl(topFin?.tutar_tl)} birim={topFin?.tutar_tl == null ? undefined : "bin TL"}
          ikinci={fin?.toplam_dsg?.tutar_tl != null ? { etiket: "DSG içi hesapla", deger: `${binTl(fin.toplam_dsg.tutar_tl)} bin TL` } : undefined}
          alt={topFin ? <><Nitelik n={topFin.nitelik} /> <HesapDurumu d={fin?.meta?.hesap_durumu} /> {fin?.kayitli_santral ? `${sayiTr(fin.kayitli_santral)} santral gece kaydından` : "anlık hesap"}{fin?.toplama_girmeyen?.length ? `; ${fin.toplama_girmeyen.length} santral toplam dışı` : ""}</> : fin === null ? "finansal etki alınamadı" : "yükleniyor"} />
      </div>

      <Kart baslik="Santral katkıları" alt="Dönemde her üyenin programı, gerçekleşeni ve portföy sapmasına katkısı; yarınki tahmini ve üyelik durumu."
        sag={<span className="cip"><Meta items={[sapma?.donem?.etiket, o && `${sayiTr(o.saat)} saat`, sapma?.katkilar?.not && "karşıt sapmalar netleşiyor"]} /></span>}>
        {sapma === undefined ? <YerTutucu yukseklik={120} /> : !sapma || sapma.durum !== "ok" ? <p className="soluk" style={{ margin: 0 }}>{sapma?.not ?? "Dönem görünümü alınamadı."}</p> : (
          <>
            <div className="grafik-kaydir"><table className="veri sayisal">
              <thead><tr><th style={sol}>Santral</th><th>Kurulu güç (kW)</th><th>Program (MWh)</th><th>Gerçekleşen (MWh)</th><th>Sapma (MWh)</th><th title="Santralin, üyelerin mutlak sapmaları toplamındaki payı">Sapma payı (%)</th><th>Yarın (MWh)</th><th style={sol}>Ölçüm</th><th style={sol}>Üyelik</th></tr></thead>
              <tbody>{kat.map((s) => {
                const u = uyeler.find((x) => x.santral === s.santral); const t = tahmin?.katkilar?.[s.santral]; const b = sapma.santral_bilgi?.[s.santral];
                return (<tr key={s.santral}>
                  <td style={sol}>{u ? <a href={`#santralim/${u.plant_id}`}>{s.santral}</a> : s.santral}</td>
                  <td className="mono">{s.kapasite_kwp == null ? "—" : sayiTr(s.kapasite_kwp)}</td><td className="mono">{yaz(s.program_mwh, 1)}</td><td className="mono">{yaz(s.gercek_mwh, 1)}</td>
                  <td className="mono">{isaretli(s.mwh, 1)}{s.pct != null && <span className="soluk"> (%{sayiTr(Math.abs(s.pct), 1)})</span>}</td>
                  <td className="mono">{s.mutlak_pay_pct == null ? "—" : sayiTr(s.mutlak_pay_pct, 0)}</td>
                  <td className="mono">{t?.p50_mwh == null ? "—" : sayiTr(t.p50_mwh, 1)}</td>
                  <td style={sol} className="soluk">{b?.olcum_saat != null ? `${sayiTr(b.olcum_saat)} saat${b.uretim === "sayac" ? ", sayaç" : ""}` : "—"}</td>
                  <td style={sol}>{u ? <Rozet sinif={DOGRULAMA_SINIF[u.dogrulama] ?? "rozet-notr"} title={`${u.kaynak}; ${gunYaz(u.gecerli_bas)}${u.gecerli_bit ? ` – ${gunYaz(u.gecerli_bit)}` : " – süresiz"}`}>{u.dogrulama_ad.toLowerCase()}</Rozet> : "—"}</td>
                </tr>); })}</tbody>
            </table></div>
            {sapma.katkilar?.not && <p className="form-not" style={{ margin: "10px 0 0", fontSize: 13.5 }}>{sapma.katkilar.not}</p>}
          </>)}
      </Kart>

      <div className="ızgara-cift">
        <Kart baslik="Portföy riski" alt="Önümüzdeki günlerde program ile tahmin arasındaki beklenen fark, aralık dışı saatler ve geçmişte sapmanın yoğunlaştığı yerler."
          sag={rs ? <Rozet sinif={RISK[rs.etiket]}>{rs.etiket_ad}</Rozet> : undefined}>
          {risk === undefined ? <YerTutucu yukseklik={140} /> : !risk || risk.durum !== "ok" || !rs ? <p className="soluk" style={{ margin: 0 }}>{risk?.not ?? "Risk görünümü alınamadı."}</p> : (
            <>
              <dl className="kunye">
                <div><dt>Beklenen sapma</dt><dd>{rs.beklenen_sapma_mwh == null ? <span className="kunye-durum eksik">Program yok</span> : <><span className="kunye-sayi">{isaretli(rs.beklenen_sapma_mwh, 1)} MWh</span><span className="kunye-not"> {rs.beklenen_sapma_pct != null ? `%${sayiTr(Math.abs(rs.beklenen_sapma_pct), 1)}, ` : ""}{sayiTr(rs.saat ?? 0)} saat, {risk.kural_ad?.toLowerCase()}</span></>}</dd></div>
                <div><dt>Aralık</dt><dd>{rs.aralik_mwh ? <><span className="kunye-sayi">{isaretli(rs.aralik_mwh.p10, 1)} … {isaretli(rs.aralik_mwh.p90, 1)} MWh</span>{bel && <span className="kunye-not"> {BELIRSIZLIK[bel].etiket}</span>}</> : <span className="kunye-durum eksik">Hesaplanamadı</span>}</dd></div>
                <div><dt>Aralık dışı saat</dt><dd><span className="kunye-sayi">{sayiTr(rs.riskli_saat ?? 0)}</span><span className="kunye-not"> program tahmin aralığının dışında</span></dd></div>
                <div><dt>Geçmiş sınav</dt><dd>{tahmin?.belirsizlik?.kapsama?.picp80 != null ? <><span className="kunye-sayi">%{sayiTr(tahmin.belirsizlik.kapsama.picp80, 0)}</span><span className="kunye-not"> gerçekleşen aralık içinde kaldı ({sayiTr(tahmin.belirsizlik.kapsama.n_gun)} gün; hedef %80)</span></> : <span className="kunye-not">Henüz sınanmadı; gece hesabı ilk sınavı yapar.</span>}</dd></div>
                <div><dt>Yoğunlaşma</dt><dd>{yogun && yogun.mwh != null ? <>{yogun.santral}<span className="kunye-not"> dönem sapmasının %{sayiTr(yogun.mutlak_pay_pct ?? 0, 0)}'i</span></> : <span className="kunye-not">—</span>}</dd></div>
                <div><dt>Santraller arası bağımlılık</dt><dd>{rhoOrt != null ? <><span className="kunye-sayi">{sayiTr(rhoOrt, 2)}</span><span className="kunye-not"> ortalama sapma korelasyonu ({sayiTr(sapma?.korelasyon?.n_gun ?? 0)} gün)</span></> : <span className="kunye-not">{sapma?.korelasyon?.durum === "yetersiz_veri" ? "Yeterli ortak gün yok." : "—"}</span>}</dd></div>
              </dl>
              {(rs.saatler ?? []).length > 0 && (
                <div className="grafik-kaydir" style={{ marginTop: 10 }}><table className="veri sayisal dar">
                  <thead><tr><th style={sol}>Saat</th><th>Program</th><th>Tahmin aralığı</th><th>Fark</th></tr></thead>
                  <tbody>{(rs.saatler ?? []).slice(0, 8).map((s) => <tr key={s.ts}><td style={sol} className="mono">{saatYaz(s.ts)}</td><td className="mono">{sayiTr(s.program_mwh, 1)}</td><td className="mono">{s.p10_mwh == null || s.p90_mwh == null ? "—" : `${sayiTr(s.p10_mwh, 0)}–${sayiTr(s.p90_mwh, 0)}`}</td><td className="mono">{isaretli(s.fark_mwh, 1)}</td></tr>)}</tbody>
                </table></div>)}
              {(rs.saatler ?? []).length > 0 && <p className="soluk" style={{ margin: "6px 0 0", fontSize: 12.5 }}>Aralık dışı saatler, MWh; fark = tahmin − program, en büyük fark önce.</p>}
              {(sapma?.riskli_gunler ?? []).length > 0 && <p className="form-not" style={{ margin: "10px 0 0", fontSize: 13.5 }}><b>Dönemde en çok sapan günler:</b> {sapma!.riskli_gunler!.slice(0, 3).map((d) => `${gunYaz(d.gun)} ${isaretli(d.sapma_mwh, 1)} MWh`).join("; ")}.</p>}
              {rs.not && <p className="soluk" style={{ margin: "8px 0 0", fontSize: 13 }}>{rs.not}</p>}
            </>)}
        </Kart>
        <Kart baslik="Revizyon önerileri" alt="Güncel tahmin ile üretim programı arasındaki farktan türeyen, dayanaklı öneriler. Karar sizindir; PVQuant program bildirmez, piyasaya teklif vermez."
          sag={<span className="dugme-sira"><div className="seg" role="group" aria-label="Hedef gün">
            <button type="button" className={hedef === "yarin" ? "secili" : undefined} onClick={() => setHedef("yarin")}>Yarın</button>
            <button type="button" className={hedef === "bugun" ? "secili" : undefined} onClick={() => setHedef("bugun")}>Bugün</button></div></span>}>
          {rev === undefined ? <YerTutucu yukseklik={140} /> : !rev || rev.durum !== "ok" ? <p className="soluk" style={{ margin: 0 }}>{rev?.not ?? "Öneriler alınamadı."}</p> : (
            <>
              {rev.pencere && hedef === "yarin" && <p className="form-not" style={{ margin: "0 0 8px", fontSize: 13.5 }}>{rev.pencere.durum === "pencere_acik" ? `Yarının programı için bildirim süresi açık; 15:30'a ${sayiTr(rev.pencere.dakika_kaldi)} dakika.` : rev.pencere.durum === "erken" ? "Yarının programı için bildirim 14:00–15:30 arasında yapılır." : "Yarın için bildirim süresi (15:30) geçti; değişiklik yalnız gün içi düzeltme ile."}</p>}
              {rev.gun_ici && hedef === "bugun" && <p className="form-not" style={{ margin: "0 0 8px", fontSize: 13.5 }}>{rev.gun_ici.acik ? `Bir sonraki teslimat saati için gün içi düzeltme ${sayiTr(rev.gun_ici.dakika_kaldi ?? 0)} dakika daha yapılabilir.` : "Bir sonraki teslimat saati için düzeltme süresi geçti."}</p>}
              <ul className="not-listesi">
                {(rev.oneriler ?? []).map((x) => (
                  <li key={x.kod} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                    <span className={`rozet rozet-kucuk ${ONERI_SINIF[x.tur] ?? "rozet-notr"}`} style={{ flex: "0 0 auto", marginTop: 2 }}>{x.tur_ad}</span>
                    <span>{x.metin} <Rozet sinif={RISK[x.etiket] ?? "rozet-notr"}>{x.etiket_ad.toLowerCase()}</Rozet>{x.sayfa && SAYFA_AD[x.sayfa] ? <> <a href={`#${x.sayfa}`}>{SAYFA_AD[x.sayfa]} sayfasına git</a></> : null}</span>
                  </li>))}
              </ul>
            </>)}
        </Kart>
      </div>

      <div className="ızgara-cift">
        <Kart baslik="Üyeler, DSG ve sözleşmeler" alt="Portföyün tarihli üyelikleri; dengeden sorumlu grupta üç perspektif: tek başına, grup içinde ve sözleşmeye göre pay.">
          {detay === undefined ? <YerTutucu yukseklik={120} /> : !detay ? <p className="soluk" style={{ margin: 0 }}>Üyelikler alınamadı.</p> : (
            <>
              <div className="grafik-kaydir"><table className="veri dar">
                <thead><tr><th style={sol}>Santral</th><th style={sol}>Üyelik dönemi</th><th style={sol}>Doğrulama</th></tr></thead>
                <tbody>{uyeler.length === 0 ? <tr><td colSpan={3} className="soluk" style={sol}>Bu portföyde üye yok.</td></tr> : uyeler.map((u) => <tr key={u.id} className={u.gecerli_bit && u.gecerli_bit < bugunIso() ? "soluk" : undefined}>
                  <td style={sol}><a href={`#santralim/${u.plant_id}`}>{u.santral}</a>{u.segment && <div className="hucre-alt soluk">{u.segment.replace(/_/g, " ")}</div>}</td>
                  <td style={sol} className="mono">{gunYaz(u.gecerli_bas)} – {u.gecerli_bit ? gunYaz(u.gecerli_bit) : "süresiz"}</td>
                  <td style={sol}><Rozet sinif={DOGRULAMA_SINIF[u.dogrulama] ?? "rozet-notr"} title={u.kaynak === "belge" ? "kaynak: belge" : u.kaynak === "paylasim" ? "kaynak: paylaşım" : "kaynak: beyan"}>{u.dogrulama_ad.toLowerCase()}</Rozet>{u.belge_adi ? <div className="hucre-alt soluk">{u.belge_adi}</div> : null}</td></tr>)}</tbody>
              </table></div>
              {p.tur === "dsg" && (dsg === undefined ? <YerTutucu yukseklik={80} /> : !dsg || dsg.durum !== "ok" || !per ? <p className="soluk" style={{ margin: "10px 0 0" }}>{dsg?.not ?? "DSG hesabı alınamadı."}</p> : (
                <>
                  <p className="etiket-ust" style={{ margin: "12px 0 4px" }}>Üç perspektif</p>
                  <dl className="kunye">
                    <div><dt>Tek başına toplam</dt><dd><span className="kunye-sayi">{binTl(per.bagimsiz.toplam_edt_tl)} bin TL</span> <Nitelik n={per.bagimsiz.nitelik} /><span className="kunye-not"> her üyenin kendi programı ve ölçümüyle, grup olmasaydı taşıyacağı dengesizlik tutarlarının toplamı</span></dd></div>
                    <div><dt>Grup içinde</dt><dd><span className="kunye-sayi">{binTl(per.dsg_ici.edt_dsg_tl)} bin TL</span> <Nitelik n={per.dsg_ici.nitelik} /><span className="kunye-not"> netleşme farkı {isaretli(per.dsg_ici.netlesme_farki_tl == null ? null : per.dsg_ici.netlesme_farki_tl / 1000, 1)} bin TL; eşik içindeki karşıt sapmalar grup fiyatıyla netleşir</span></dd></div>
                    <div><dt>Sözleşmeye göre paylar</dt><dd><span className="kunye-sayi">{binTl(per.sozlesmesel.toplam?.toplam_tl)} bin TL</span> <Rozet sinif={per.sozlesmesel.etiket.startsWith("Sözleşmeye") ? "rozet-ok" : "rozet-uyari"}>{per.sozlesmesel.etiket.toLowerCase()}</Rozet><span className="kunye-not"> {per.sozlesmesel.yontem_ad}</span></dd></div>
                  </dl>
                  {per.sozlesmesel.satirlar.length > 0 && <div className="grafik-kaydir"><table className="veri sayisal dar">
                    <thead><tr><th style={sol}>Üye</th><th>Tek başına (TL)</th><th title="Sözleşmedeki pay">Sözleşme payı (%)</th><th>Grup payı (TL)</th><th>Üyede kalan (TL)</th><th>Ücret (TL)</th><th>Toplam (TL)</th><th>KÜPST (TL)</th></tr></thead>
                    <tbody>{per.sozlesmesel.satirlar.map((s) => { const b = per.bagimsiz.satirlar.find((x) => x.santral === s.santral); return <tr key={s.santral}><td style={sol}>{s.santral}</td><td className="mono">{yaz(b?.edt_tek_tl)}</td><td className="mono">{s.pay_pct == null ? "—" : sayiTr(s.pay_pct, 1)}</td><td className="mono">{yaz(s.grup_payi_tl)}</td><td className="mono">{yaz(s.edt_bireysel_tl)}</td><td className="mono">{yaz(s.ucret_tl)}</td><td className="mono" style={{ fontWeight: 600 }}>{yaz(s.toplam_tl)}</td><td className="mono soluk">{yaz(s.kupst_tl)}</td></tr>; })}</tbody>
                  </table></div>}
                  <ul className="not-listesi">
                    {per.dsg_ici.aciklama && <li>{per.dsg_ici.aciklama}</li>}
                    {dsg.kural?.esik != null && <li>Üye eşiği %{sayiTr(dsg.kural.esik * 100, 0)}{dsg.kural.esik_kaynak ? ` (${dsg.kural.esik_kaynak})` : ""}.{dsg.kural.belirsiz_2027 ? " 2027 kuralı henüz yayımlanmadı; 2026 kuralı sürdürüldü." : ""}</li>}
                    {(dsg.notlar ?? []).slice(0, 2).map((n) => <li key={n}>{n}</li>)}
                  </ul>
                </>))}
              {p.tur !== "dsg" && <p className="soluk" style={{ margin: "10px 0 0", fontSize: 13.5 }}>Bu portföy bir dengeden sorumlu grup değil; dengesizlik tutarları santral santral hesaplanır. Netleşme hesabı yalnız DSG türündeki portföylerde yapılır.</p>}
              <details className="aciklama" style={{ marginTop: 10 }}>
                <summary>Sözleşme kayıtları</summary>
                {sozlesmeler === "yetki_yok" ? <p className="soluk" style={{ margin: 0 }}>Sözleşme kayıtları editör ve yönetici yetkili kullanıcılara açıktır.</p> : sozlesmeler === undefined ? <YerTutucu yukseklik={40} /> : sozlesmeler === null ? <p className="soluk" style={{ margin: 0 }}>Sözleşme listesi alınamadı.</p> : sozlesmeler.length === 0 ? <p className="soluk" style={{ margin: 0 }}>Bu portföy için sözleşme kaydı yok; dağılım varsayımsal anahtarla gösterilir.</p> : (
                  <div className="grafik-kaydir"><table className="veri dar">
                    <thead><tr><th style={sol}>Tür</th><th style={sol}>Geçerlilik</th><th style={sol}>Dağılım</th><th style={sol}>Dengesizlik sorumlusu</th><th style={sol}>Doğrulama</th><th style={sol}>Taraflar</th></tr></thead>
                    <tbody>{sozlesmeler.map((z) => <tr key={z.id}><td style={sol}>{z.tur === "dsg_uyelik" ? "DSG üyeliği" : z.tur === "toplayici" ? "toplayıcı" : z.tur === "satis" ? "satış" : "işletme"}</td><td style={{ ...sol, whiteSpace: "nowrap" }} className="mono">{gunYaz(z.gecerli_bas)}{z.gecerli_bit ? ` – ${gunYaz(z.gecerli_bit)}` : " – süresiz"}</td>
                      {/* 12.11 inceleme: dar kartta altı sütun — tarih tek satır, dağılım metni ve rozet alt alta, belge adı kendi satırında; taraflar kırılmaz */}
                      <td style={sol}>{z.dagitim_yontemi ? (DAGILIM_AD[z.dagitim_yontemi] ?? z.dagitim_yontemi) : "—"}<div><Rozet sinif={z.dagilim_etiketi.startsWith("Sözleşmeye") ? "rozet-ok" : "rozet-uyari"}>{z.dagilim_etiketi.toLowerCase()}</Rozet></div></td><td style={sol}>{z.dengesizlik_sorumlusu ? (SORUMLU_AD[z.dengesizlik_sorumlusu] ?? z.dengesizlik_sorumlusu) : "—"}</td>
                      <td style={sol}><Rozet sinif={DOGRULAMA_SINIF[z.dogrulama] ?? "rozet-notr"}>{z.dogrulama_ad.toLowerCase()}</Rozet>{z.belge_adi ? <div className="soluk" style={{ fontSize: 12.5, wordBreak: "break-all" }}>{z.belge_adi}</div> : null}</td><td style={sol} className="soluk">{[z.taraf_a_ad, z.taraf_b_ad].filter(Boolean).join(" – ") || "—"}</td></tr>)}</tbody>
                  </table></div>)}
              </details>
            </>)}
        </Kart>
        <Kart baslik="Finansal etki bileşenleri" alt="Dönemde portföy satırları: aynı santral hesaplarının toplamı; toplama yalnız ilk üç girer. DSG içi tutar, netleşme farkı ve dağılım bilgi satırıdır."
          sag={fin?.dsg ? <Rozet sinif={fin.dsg.etiket.startsWith("Sözleşmeye") ? "rozet-ok" : "rozet-uyari"}>{fin.dsg.etiket.toLowerCase()}</Rozet> : undefined}>
          {fin === undefined ? <YerTutucu yukseklik={120} /> : !fin || fin.durum !== "ok" || !fin.bilesenler ? <p className="soluk" style={{ margin: 0 }}>{fin?.not ?? "Finansal etki alınamadı."}</p> : (
            <>
              <div className="grafik-kaydir"><table className="veri sayisal dar">
                <thead><tr><th style={sol}>Bileşen</th><th>Net (TL)</th><th style={sol}>Nitelik</th><th style={sol}>Kaynak</th></tr></thead>
                <tbody>
                  {fin.bilesenler.filter((b) => b.toplanir).map((b) => <tr key={b.kod}><td style={{ ...sol, whiteSpace: "normal" }}>{b.ad}</td><td className="mono">{yaz(b.tutar_tl)}</td><td style={sol}><Nitelik n={b.nitelik} /></td><td style={sol} className="soluk">{b.kaynak || "—"}</td></tr>)}
                  <tr style={{ fontWeight: 600 }}><td style={sol}>Toplam</td><td className="mono">{yaz(topFin?.tutar_tl)}</td><td style={sol}><Nitelik n={topFin?.nitelik} /></td><td style={sol} className="soluk">{fin.mwh ? `${sayiTr(fin.mwh.toplanan.santral)} santral toplamı` : ""}</td></tr>
                  {fin.toplam_dsg && <tr><td style={sol}>Toplam, DSG içi hesapla</td><td className="mono">{yaz(fin.toplam_dsg.tutar_tl)}</td><td style={sol}><Nitelik n={fin.toplam_dsg.nitelik} /></td><td style={{ ...sol, whiteSpace: "normal" }} className="soluk">bağımsız tutarın yerine</td></tr>}
                  <tr><td colSpan={4} className="etiket-ust" style={{ ...sol, paddingTop: 12 }}>Toplama girmeyen satırlar</td></tr>
                  {fin.bilesenler.filter((b) => !b.toplanir && b.nitelik !== "eksik").map((b) => <tr key={b.kod} className="soluk"><td style={{ ...sol, whiteSpace: "normal" }}>{b.ad}</td><td className="mono">{yaz(b.tutar_tl)}</td><td style={sol}><Nitelik n={b.nitelik} /></td><td style={sol}>{b.kaynak || "—"}</td></tr>)}
                </tbody>
              </table></div>
              <ul className="not-listesi">{(fin.notlar ?? []).map((n) => <li key={n}>{n}</li>)}</ul>
            </>)}
        </Kart>
      </div>

      {yazabilir && (
        <Kart baslik="Üyelikler ve sözleşmeler" alt="Portföy, üyelik ve sözleşme kayıtları tarihli tutulur; kayıt silinmez, bitiş tarihiyle kapatılır. Her değişiklik denetim izine yazılır.">
          <details className="aciklama"><summary>Yeni portföy</summary><PortfoyFormu onBitti={() => setYenile((n) => n + 1)} /></details>
          <details className="aciklama"><summary>Üyelik ekle ya da kapat</summary><UyelikFormu portfoyId={p.id} uyeler={uyeler} onBitti={() => setYenile((n) => n + 1)} /></details>
          {yonetici ? <details className="aciklama"><summary>Sözleşme ekle</summary><SozlesmeFormu portfoyId={p.id} uyeler={uyeler} onBitti={() => setYenile((n) => n + 1)} /></details>
            : <p className="soluk" style={{ margin: "8px 0 0", fontSize: 13.5 }}>Sözleşme kaydını yalnız yönetici ekler.</p>}
        </Kart>)}
    </Sayfa>
  );
}

function hataMetni(e: unknown): string {
  const m = e instanceof Error ? e.message : String(e);
  return /403/.test(m) ? "Bu işlem için yetkiniz yok." : /404/.test(m) ? "Kayıt bulunamadı." : m.replace(/^\d{3}\s*/, "") || "İşlem yapılamadı.";
}

function PortfoyFormu({ onBitti }: { onBitti: () => void }) {
  const [ad, setAd] = useState(""); const [tur, setTur] = useState("toplayici"); const [bas, setBas] = useState(bugunIso().slice(0, 4) + "-01-01"); const [dsgKodu, setDsgKodu] = useState("");
  const [durum, setDurum] = useState<string | null>(null);
  const gonder = () => {
    setDurum(null);
    api.portfoyEkle({ ad, tur, gecerli_bas: bas, dsg: tur === "dsg" ? { dsg_kodu: dsgKodu } : null }).then(() => { setDurum("Portföy tanımlandı."); setAd(""); onBitti(); }, (e) => setDurum(hataMetni(e)));
  };
  return (
    <div className="portfoy-form"><div className="ayar-kontrol" style={{ flexWrap: "wrap", gap: 10 }}>
      <label className="girdi-etiket">Ad<input className="girdi" value={ad} onChange={(e) => setAd(e.target.value)} placeholder="ör. Toplayıcı 2026" /></label>
      <label className="girdi-etiket">Tür<select className="girdi" value={tur} onChange={(e) => setTur(e.target.value)}>{Object.entries(TUR_ETIKET).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
      <label className="girdi-etiket">Başlangıç<input className="girdi" type="date" value={bas} onChange={(e) => setBas(e.target.value)} /></label>
      {tur === "dsg" && <label className="girdi-etiket">DSG kodu<input className="girdi" value={dsgKodu} onChange={(e) => setDsgKodu(e.target.value)} placeholder="EPİAŞ DSG kodu" /></label>}
      <button type="button" className="dugme dugme-ana" disabled={!ad || (tur === "dsg" && !dsgKodu)} onClick={gonder}>Tanımla</button>
    </div>{durum && <p className="form-not" style={{ margin: "8px 0 0" }}>{durum}</p>}</div>);
}

function UyelikFormu({ portfoyId, uyeler, onBitti }: { portfoyId: string; uyeler: PortfoyDetay["uyeler"]; onBitti: () => void }) {
  const [santraller, setSantraller] = useState<{ id: string; ad: string }[]>([]);
  const [plant, setPlant] = useState(""); const [bas, setBas] = useState(bugunIso()); const [dogrulama, setDogrulama] = useState("beyan"); const [belge, setBelge] = useState("");
  const [kapat, setKapat] = useState(""); const [bit, setBit] = useState(bugunIso()); const [durum, setDurum] = useState<string | null>(null);
  useEffect(() => { api.portfoy().then((p) => { if (p) setSantraller(p.santraller.map((s) => ({ id: s.id, ad: s.ad }))); }).catch(() => {}); }, []);
  const ekle = () => { setDurum(null); api.uyelikEkle(portfoyId, { plant_id: plant, gecerli_bas: bas, dogrulama, belge_adi: belge || null }).then(() => { setDurum("Üyelik eklendi."); onBitti(); }, (e) => setDurum(hataMetni(e))); };
  const kapatGonder = () => { setDurum(null); api.uyelikGuncelle(portfoyId, kapat, { gecerli_bit: bit }).then(() => { setDurum("Üyelik kapatıldı."); onBitti(); }, (e) => setDurum(hataMetni(e))); };
  const acik = uyeler.filter((u) => !u.gecerli_bit);
  return (
    <div className="portfoy-form">
      <div className="ayar-kontrol" style={{ flexWrap: "wrap", gap: 10 }}>
        <label className="girdi-etiket">Santral<select className="girdi" value={plant} onChange={(e) => setPlant(e.target.value)}><option value="">seçiniz</option>{santraller.map((s) => <option key={s.id} value={s.id}>{s.ad}</option>)}</select></label>
        <label className="girdi-etiket">Başlangıç<input className="girdi" type="date" value={bas} onChange={(e) => setBas(e.target.value)} /></label>
        <label className="girdi-etiket">Doğrulama<select className="girdi" value={dogrulama} onChange={(e) => setDogrulama(e.target.value)}><option value="beyan">beyan</option><option value="belgeli">belgeli</option><option value="dogrulandi">doğrulandı</option></select></label>
        {dogrulama !== "beyan" && <label className="girdi-etiket">Belge adı<input className="girdi" value={belge} onChange={(e) => setBelge(e.target.value)} placeholder="üyelik belgesi" /></label>}
        <button type="button" className="dugme dugme-ana" disabled={!plant || (dogrulama !== "beyan" && !belge)} onClick={ekle}>Üyelik ekle</button>
      </div>
      {acik.length > 0 && <div className="ayar-kontrol" style={{ flexWrap: "wrap", gap: 10, marginTop: 10 }}>
        <label className="girdi-etiket">Kapatılacak üyelik<select className="girdi" value={kapat} onChange={(e) => setKapat(e.target.value)}><option value="">seçiniz</option>{acik.map((u) => <option key={u.id} value={u.id}>{u.santral} ({gunYaz(u.gecerli_bas)} – süresiz)</option>)}</select></label>
        <label className="girdi-etiket">Bitiş<input className="girdi" type="date" value={bit} onChange={(e) => setBit(e.target.value)} /></label>
        <button type="button" className="dugme" disabled={!kapat} onClick={kapatGonder}>Kapat</button>
      </div>}
      {durum && <p className="form-not" style={{ margin: "8px 0 0" }}>{durum}</p>}
    </div>);
}

function SozlesmeFormu({ portfoyId, uyeler, onBitti }: { portfoyId: string; uyeler: PortfoyDetay["uyeler"]; onBitti: () => void }) {
  const [tur, setTur] = useState("dsg_uyelik"); const [bas, setBas] = useState(bugunIso()); const [yontem, setYontem] = useState("sapma"); const [dogrulama, setDogrulama] = useState("beyan"); const [belge, setBelge] = useState("");
  const [paylar, setPaylar] = useState<Record<string, string>>({}); const [durum, setDurum] = useState<string | null>(null);
  const gonder = () => {
    setDurum(null);
    const prm = yontem === "sabit_pay" || yontem === "ozel" ? { paylar: Object.fromEntries(uyeler.filter((u) => !u.gecerli_bit).map((u) => [u.santral, Number(paylar[u.santral] ?? 0) / 100])) } : {};
    api.sozlesmeEkle({ tur, gecerli_bas: bas, portfoy_id: portfoyId, dagitim_yontemi: yontem, parametreler: prm, dogrulama, belge_adi: belge || null }).then(() => { setDurum("Sözleşme kaydedildi."); onBitti(); }, (e) => setDurum(hataMetni(e)));
  };
  return (
    <div className="portfoy-form">
      <div className="ayar-kontrol" style={{ flexWrap: "wrap", gap: 10 }}>
        <label className="girdi-etiket">Tür<select className="girdi" value={tur} onChange={(e) => setTur(e.target.value)}><option value="dsg_uyelik">DSG üyeliği</option><option value="toplayici">toplayıcı</option><option value="satis">satış</option><option value="isletme">işletme</option></select></label>
        <label className="girdi-etiket">Başlangıç<input className="girdi" type="date" value={bas} onChange={(e) => setBas(e.target.value)} /></label>
        <label className="girdi-etiket">Dağılım<select className="girdi" value={yontem} onChange={(e) => setYontem(e.target.value)}><option value="sapma">sapma payına göre</option><option value="esit">eşit</option><option value="uretim">üretime göre</option><option value="sabit_pay">sabit paylar</option><option value="ozel">özel</option></select></label>
        <label className="girdi-etiket">Doğrulama<select className="girdi" value={dogrulama} onChange={(e) => setDogrulama(e.target.value)}><option value="beyan">beyan</option><option value="belgeli">belgeli</option><option value="dogrulandi">doğrulandı</option></select></label>
        {dogrulama !== "beyan" && <label className="girdi-etiket">Belge adı<input className="girdi" value={belge} onChange={(e) => setBelge(e.target.value)} placeholder="sözleşme dosyası" /></label>}
      </div>
      {(yontem === "sabit_pay" || yontem === "ozel") && <div className="ayar-kontrol" style={{ flexWrap: "wrap", gap: 10, marginTop: 10 }}>
        {uyeler.filter((u) => !u.gecerli_bit).map((u) => <label key={u.id} className="girdi-etiket">{u.santral} payı (%)<input className="girdi" type="number" min={0} max={100} step={0.1} value={paylar[u.santral] ?? ""} onChange={(e) => setPaylar({ ...paylar, [u.santral]: e.target.value })} /></label>)}
        <span className="soluk" style={{ fontSize: 13 }}>Paylar toplamı 100 olmalı; eksik ya da fazla ise kayıt reddedilir.</span>
      </div>}
      <div className="ayar-kontrol" style={{ marginTop: 10 }}><button type="button" className="dugme dugme-ana" disabled={dogrulama !== "beyan" && !belge} onClick={gonder}>Kaydet</button></div>
      {durum && <p className="form-not" style={{ margin: "8px 0 0" }}>{durum}</p>}
    </div>);
}
