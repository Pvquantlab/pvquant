import { useEffect, useState } from "react";
import { useDamgaSurumu } from "../../shell/damgaOlay";
import { api } from "../../api/client";
import type { FinansalEtki as FinansalEtkiT, FinansalEtkiGecmis, FinansBilesen, FinansDonemTur, FinansNitelik } from "../../api/types";
import { donemSecenekleri, TUR_AD } from "../../lib/donem";   // v2.595: ortak dönem seçenekleri
import { HesapDurumu, Kart, Kpi, Sayfa, sayiTr, SayfaIskeleti, YerTutucu } from "./parcalar";
import { Meta } from "../../lib/Meta";
import { tarihBicimi } from "../../lib/bicim";

/** v2.584 (Faz 2 F2-F) — Finansal etki: seçilen dönemde planlanan ve gerçekleşen üretim, sapma ve tahmini mali karşılığı. Var olan hesapların
 *  (dengesizlik, KGÜP sapma tutarı, tarife, YEKDEM, kayıp ayrışımı, mutabakat) aynı saat kümesinde derlenmiş hâlidir; formül yazmaz. Her satır
 *  niteliğini taşır: resmî (EPİAŞ bildirimi) › hesaplanan (EPİAŞ fiyatıyla yeniden hesap) › sözleşme tahmini (tarife varsayımı) › senaryo › eksik.
 *  İşaret: artı santral lehine (alacak), eksi aleyhine (borç). Toplama yalnız satış geliri, dengesizlik ve KGÜP sapma tutarı girer; resmî satırlar,
 *  DSG, göstergeler, üretim düşüklüğü ve ileriye dönük maruziyet yan yana gösterilir, toplanmaz (çift sayım yok). */
const NITELIK: Record<FinansNitelik, { etiket: string; sinif: string; aciklama: string }> = {
  resmi: { etiket: "resmî", sinif: "rozet-ok", aciklama: "EPİAŞ uzlaştırma bildiriminden ya da resmî fiyat ve kur kaydından alınan değer." },
  hesaplanan: { etiket: "hesaplanan", sinif: "rozet-notr", aciklama: "PVQuant'ın EPİAŞ saatlik fiyatı ve sistem yönüyle yeniden hesabı; resmî uzlaştırma sonucu değildir." },
  sozlesme_tahmini: { etiket: "sözleşme tahmini", sinif: "rozet-notr", aciklama: "Santral ayarlarındaki tarife ya da sözleşme varsayımıyla hesaplanan tahmin; fatura değildir." },
  senaryo: { etiket: "senaryo", sinif: "rozet-uyari", aciklama: "Varsayımsal hesap: senaryo fiyatı, varsayılan sistem yönü ya da sözleşme verisi olmayan üyelik." },
  eksik: { etiket: "eksik", sinif: "rozet-notr", aciklama: "Gerekli veri (fiyat, sistem yönü, katsayı, ölçüm ya da bildirim) olmadığından hesaplanamadı." },
};
const ONERI_SINIF: Record<string, string> = { eylem: "rozet-dikkat", oneri: "rozet-uyari", bilgi: "rozet-notr" };
const SAYFA_AD: Record<string, string> = { tahminler: "Tahminler", kgup: "KGÜP", mutabakat: "Mutabakat", santralim: "Santralim", kurulus: "Ayarlar", veri: "Veri yükleme", olaylar: "Olay kaydı", hakkinda: "Hakkında", sayac: "Sayaç" };
const sol = { textAlign: "left" as const };
const yaz = (v: number | null | undefined, ondalik = 0) => v == null ? "—" : `${v < 0 ? "−" : ""}${sayiTr(Math.abs(v), ondalik)}`;
const isaretli = (v: number | null | undefined, ondalik = 0) => v == null ? "—" : `${v > 0 ? "+" : v < 0 ? "−" : ""}${sayiTr(Math.abs(v), ondalik)}`;
const binTl = (v: number | null | undefined) => v == null ? "—" : `${v < 0 ? "−" : ""}${sayiTr(Math.abs(v) / 1000, 1)}`;
const saatYaz = (iso: string | null | undefined) => iso ? tarihBicimi("tr-TR", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(iso)) : "—";
const gunYaz = (iso: string | null | undefined) => iso ? tarihBicimi("tr-TR", { day: "numeric", month: "short", year: "numeric" }).format(new Date(iso.slice(0, 10) + "T12:00:00")) : "—";

function Rozet({ n, kucuk = true }: { n: FinansNitelik; kucuk?: boolean }) {
  const x = NITELIK[n] ?? NITELIK.eksik;
  return <span className={`rozet ${kucuk ? "rozet-kucuk " : ""}${x.sinif}`} title={x.aciklama}>{x.etiket}</span>;
}

function BilesenSatiri({ b }: { b: FinansBilesen }) {
  return (
    <tr className={b.toplanir ? undefined : "soluk"}>
      <td style={{ ...sol, whiteSpace: "normal" }}>{b.ad}{b.notlar.length > 0 && <div className="hucre-alt soluk" style={{ whiteSpace: "normal", maxWidth: "48ch" }}>{b.notlar[0]}</div>}</td>
      <td className="mono" style={{ fontWeight: b.toplanir ? 600 : 400 }}>{yaz(b.tutar_tl)}</td>
      <td className="mono">{b.alacak_tl == null ? "—" : sayiTr(b.alacak_tl, 0)}</td>
      <td className="mono">{b.borc_tl == null ? "—" : sayiTr(b.borc_tl, 0)}</td>
      <td><Rozet n={b.nitelik} /></td>
      <td className="mono">{b.kapsam_saat != null && b.beklenen_saat ? `${sayiTr(b.kapsam_saat)} / ${sayiTr(b.beklenen_saat)}` : "—"}</td>
      <td style={{ ...sol, whiteSpace: "normal" }} className="soluk">{b.kaynak || "—"}</td>
    </tr>);
}

export function FinansalEtki({ plantId }: { plantId: string }) {
  const ds = useDamgaSurumu();
  const [tur, setTur] = useState<FinansDonemTur>("ay");
  const [kod, setKod] = useState<string>(() => donemSecenekleri("ay")[1]?.kod ?? donemSecenekleri("ay")[0].kod);   // varsayılan son tam ay
  const [uretim, setUretim] = useState<string | null>(null);
  const [pozisyon, setPozisyon] = useState<"program" | "uretim">("program");
  const [o, setO] = useState<FinansalEtkiT | null | undefined>(undefined);
  const [gecmis, setGecmis] = useState<FinansalEtkiGecmis | null | undefined>(undefined);
  const secenekler = donemSecenekleri(tur);
  useEffect(() => {
    let acik = true; setO(undefined); setGecmis(undefined);
    const istek = pozisyon === "program" ? api.finansalEtki(plantId, kod, uretim) : api.finansalEtkiSenaryo(plantId, kod, pozisyon, null, uretim);
    istek.then((v) => { if (acik) setO(v); }, () => { if (acik) setO(null); });
    return () => { acik = false; };
  }, [plantId, kod, uretim, pozisyon, ds]);
  const turDegis = (t: FinansDonemTur) => { setTur(t); const s = donemSecenekleri(t); setKod((t === "ay" || t === "ceyrek" || t === "yil") && s[1] ? s[1].kod : s[0].kod); };
  const gecmisAc = () => { if (gecmis === undefined) api.finansalEtkiGecmis(plantId, kod).then(setGecmis, () => setGecmis(null)); };
  const secici = (
    <span className="dugme-sira">
      <select className="girdi" value={tur} onChange={(e) => turDegis(e.target.value as FinansDonemTur)} aria-label="Dönem türü">
        {(Object.keys(TUR_AD) as FinansDonemTur[]).map((t) => <option key={t} value={t}>{TUR_AD[t]}</option>)}</select>
      <select className="girdi" value={kod} onChange={(e) => setKod(e.target.value)} aria-label="Dönem">
        {secenekler.map((s) => <option key={s.kod} value={s.kod}>{s.etiket}</option>)}</select>
      <select className="girdi" value={uretim ?? ""} onChange={(e) => setUretim(e.target.value || null)} aria-label="Üretim girdisi" title="Gerçekleşen üretimin kaynağı: santral ayarı (Sayaç sayfasındaki kalıcı seçim), SCADA ya da yüklü saatlerde sayaç (geçici görünüm)">
        <option value="">üretim: santral ayarı</option><option value="scada">üretim: SCADA (geçici)</option><option value="sayac">üretim: sayaç, yüklü saatlerde (geçici)</option></select>
      <select className="girdi" value={pozisyon} onChange={(e) => setPozisyon(e.target.value as "program" | "uretim")} aria-label="Satış pozisyonu senaryosu" title="Senaryo: satışın programa eşit sayılması (varsayılan) ya da üretildiği kadar satış (dengesizlik alıcıda, yalnız KGÜP sapma tutarı kalır). Senaryo kaydedilmez.">
        <option value="program">pozisyon: santral ayarı</option><option value="uretim">senaryo: üretildiği kadar satış</option></select>
    </span>);
  if (o === undefined) return <Sayfa baslik="Finansal etki" sag={secici}><SayfaIskeleti kpi={4} kart={3} /></Sayfa>;
  if (o === null) return <Sayfa baslik="Finansal etki" sag={secici}><p className="soluk">Finansal etki alınamadı; dönem kodu geçersiz ya da gelecek dönem olabilir. Başka bir dönem seçin ya da sayfayı yenileyin.</p></Sayfa>;
  const u = o.uretim; const top = o.toplam; const uz = o.uzlastirma; const r = uz.resmi; const du = o.dusukluk; const ma = o.maruziyet; const m = o.meta;
  const toplananlar = o.bilesenler.filter((b) => b.toplanir); const digerleri = o.bilesenler.filter((b) => !b.toplanir);
  const resmiEdt = r.bilesenler.find((b) => b.kod === "dengesizlik_resmi"); const resmiKupst = r.bilesenler.find((b) => b.kod === "kupst_resmi");
  const hesEdt = uz.bilesenler.find((b) => b.kod === "dengesizlik"); const hesKupst = uz.bilesenler.find((b) => b.kod === "kupst");
  const kapsama = u.gerceklesen.kapsama; const th = du.tahmin_hatasi;
  const durumMetni = o.kayitli ? `gece hesabı ${saatYaz(o.hesap_zamani ?? m.hesap_zamani)}` : m.senaryo ? "senaryo hesabı" : "anlık hesap";
  return (
    <Sayfa baslik="Finansal etki" alt="Seçilen dönemde planlanan ve gerçekleşen üretim, aradaki fark ve bunun tahmini mali karşılığı. Tutarlar PVQuant'ın yeniden hesabıdır; EPİAŞ uzlaştırma sonucu değildir. Resmî değerler ayrıca işaretlenir; eksi tutar santralin ödediğidir." sag={secici}>
      {m.senaryo && <p className="form-not" style={{ margin: "0 0 12px", fontSize: 13.5, color: "var(--uyari-metin)" }}><b>Senaryo görünümü:</b> {m.senaryo.etiket}. {m.senaryo.not}</p>}
      <div className="ızgara satir-4" style={{ marginBottom: 14 }}>
        <Kpi etiket={`Planlanan üretim (${o.donem.etiket.replace(" (süren dönem, bugüne kadar)", ", süren")})`} bilgi="Üretim programı: TPYS'ye bildirildiği beyan edilen KGÜP varsa o, yoksa bir gün önce 15:30'dan önceki son PVQuant tahmini. Ölçümsüz saatlerin programı da sayılır."
          deger={u.planlanan.mwh == null ? "—" : sayiTr(u.planlanan.mwh, 1)} birim={u.planlanan.mwh == null ? undefined : "MWh"}
          alt={`${u.planlanan.kaynak_etiket}; ${sayiTr(u.planlanan.saat)} saat${u.planlanan.tamamlanan_saat ? `, ${sayiTr(u.planlanan.tamamlanan_saat)} saati tahmin arşivinden` : ""}`} />
        <Kpi etiket="Gerçekleşen üretim" ton="amber" bilgi="Ölçülen üretim: SCADA brüt AC ya da santral ayarına göre bağlantı noktası sayacı (net). Ölçümü olmayan saat sıfır sayılmaz, toplama girmez."
          deger={u.gerceklesen.mwh == null ? "—" : sayiTr(u.gerceklesen.mwh, 1)} birim={u.gerceklesen.mwh == null ? undefined : "MWh"}
          ikinci={{ etiket: "Ölçülen saat", deger: `${sayiTr(u.gerceklesen.saat)} / ${sayiTr(u.gerceklesen.beklenen_saat)}`, birim: "saat" }}
          alt={`${u.gerceklesen.sinir_etiket}${kapsama?.kapsama_pct != null ? `; kapsama %${sayiTr(kapsama.kapsama_pct, 0)}` : ""}`} />
        <Kpi etiket="Üretim ve program farkı" bilgi="Gerçekleşen − program, yalnız hem program hem ölçüm olan saatlerde. Artı fazla üretim, eksi eksik üretim. Mali karşılığı enerji dengesizlik satırındadır."
          deger={isaretli(u.sapma.mwh, 1)} birim={u.sapma.mwh == null ? undefined : "MWh"}
          ikinci={u.sapma.pct != null ? { etiket: u.sapma.yon === "fazla" ? "Fazla üretim" : u.sapma.yon === "eksik" ? "Eksik üretim" : "Dengede", deger: `%${sayiTr(Math.abs(u.sapma.pct), 1)}`, birim: "programın" } : undefined}
          alt={u.sapma.mwh == null ? "program ve ölçüm aynı saatlerde yok" : `${sayiTr(u.sapma.ortak_saat)} ortak saat${u.sapma.tahmine_gore_mwh != null ? `; gün öncesi tahmine göre ${isaretli(u.sapma.tahmine_gore_mwh, 1)} MWh` : ""}`} />
        <Kpi etiket="Tahmini finansal etki" bilgi={`Enerji satışı + enerji dengesizlik tutarı + KGÜP sapma tutarı, net. ${top.isaret}. Resmî satırlar, DSG, göstergeler, üretim düşüklüğü ve maruziyet bu toplama girmez.`}
          deger={binTl(top.tutar_tl)} birim={top.tutar_tl == null ? undefined : "bin TL"}
          ikinci={resmiEdt ? { etiket: "EPİAŞ bildirimi, dengesizlik", deger: `${binTl(resmiEdt.tutar_tl)} bin TL` } : undefined}
          alt={<><Rozet n={top.nitelik} /> <HesapDurumu d={m.hesap_durumu} /> {top.giren.length ? `${top.giren.length} bileşen toplandı` : "toplanacak bileşen yok"}{top.eksik.length ? `; eksik: ${top.eksik.length}` : ""}</>} />   {/* v2.605 (F4-K): hesap durumu (tam / kısmi / senaryo) */}
      </div>
      <Kart baslik="Finansal sonuç bileşenleri" alt="Aynı saat kümesinden derlenen satırlar; toplama yalnız ilk grup girer. Alacak ve borç ayrı sütunlarda, net tutar işaretli."
        sag={<span className="cip"><Meta items={[`${sayiTr(o.donem.saat)} saat`, uz.fiyat.senaryo_saat > 0 ? `${sayiTr(uz.fiyat.senaryo_saat)} saat senaryo fiyatı` : "EPİAŞ fiyatı", uz.hesaplanamayan_saat > 0 && `${sayiTr(uz.hesaplanamayan_saat)} saat hesaplanamadı`, durumMetni]} /></span>}>
        <div className="grafik-kaydir"><table className="veri sayisal">
          <thead><tr><th style={sol}>Bileşen</th><th>Net (TL)</th><th>Alacak (TL)</th><th>Borç (TL)</th><th style={sol}>Nitelik</th><th>Kapsam (saat)</th><th style={sol}>Kaynak</th></tr></thead>
          <tbody>
            {toplananlar.map((b) => <BilesenSatiri key={b.kod} b={b} />)}
            <tr style={{ fontWeight: 600 }}><td style={sol}>Toplam</td><td className="mono">{yaz(top.tutar_tl)}</td><td className="mono">{top.alacak_tl == null ? "—" : sayiTr(top.alacak_tl, 0)}</td><td className="mono">{top.borc_tl == null ? "—" : sayiTr(top.borc_tl, 0)}</td>
              <td><Rozet n={top.nitelik} /></td><td className="mono">—</td><td style={{ ...sol, whiteSpace: "normal" }} className="soluk">{o.toplam_etiket}</td></tr>
            {digerleri.length > 0 && <tr><td colSpan={7} className="etiket-ust" style={{ ...sol, paddingTop: 14 }}>Toplama girmeyen satırlar</td></tr>}
            {digerleri.map((b) => <BilesenSatiri key={b.kod} b={b} />)}
          </tbody>
        </table></div>
        <details className="aciklama">
          <summary>Satırların notları ve neden farklı oldukları</summary>
          <ul className="not-listesi">
            {o.bilesenler.filter((b) => b.notlar.length > 0).map((b) => <li key={b.kod}><b>{b.ad}:</b> {b.notlar.join(" ")}</li>)}
            {uz.notlar.map((n) => <li key={n}>{n}</li>)}
            {o.gelir.notlar.map((n) => <li key={n}>{n}</li>)}
          </ul>
        </details>
      </Kart>
      <div className="ızgara-cift">
        <Kart baslik="Resmî bildirimle karşılaştırma" alt="Ay döneminde EPİAŞ uzlaştırma bildiriminin dengesizlik ve KGÜP sapma kalemleri, PVQuant hesabıyla yan yana. Bildirim esastır."
          sag={r.guvenilirlik?.etiket ? <span className="rozet rozet-kucuk rozet-notr">{r.guvenilirlik.etiket}</span> : undefined}>
          {r.bilesenler.length === 0 ? (
            <div className="bos-durum"><div className="bos-bas">{o.donem.tur === "ay" ? "Bu dönem için bildirim yok" : "Resmî karşılık aylık bildirimde"}</div><p>{r.not ?? "Bu dönem için karşılaştırılacak resmî kalem bulunmadı."}</p></div>
          ) : (
            <>
              <div className="grafik-kaydir"><table className="veri sayisal dar">
                <thead><tr><th style={sol}>Kalem</th><th>PVQuant (TL)</th><th>EPİAŞ (TL)</th><th>Fark (TL)</th><th style={sol}>Durum</th></tr></thead>
                <tbody>
                  {([["Enerji dengesizlik tutarı", hesEdt, resmiEdt, r.fark.dengesizlik, r.durum?.dengesizlik], ["KGÜP sapma tutarı", hesKupst, resmiKupst, r.fark.kupst, r.durum?.kupst]] as const).map(([ad, h, rs, fark, durum]) => rs && (
                    <tr key={ad}><td style={sol}>{ad}</td><td className="mono">{yaz(h?.tutar_tl)}</td><td className="mono">{yaz(rs.tutar_tl)}</td><td className="mono">{isaretli(fark)}</td>
                      <td style={sol}><span className={`rozet rozet-kucuk ${durum === "uyumlu" ? "rozet-ok" : durum === "fark" ? "rozet-uyari" : "rozet-notr"}`}>{rs.notlar[0]?.replace("Mutabakat durumu: ", "").replace(/\.$/, "") ?? "—"}</span></td></tr>))}
                </tbody>
              </table></div>
              <ul className="not-listesi">
                {r.fark_etiket && <li>Fark: {r.fark_etiket}.</li>}
                {r.bildirim?.surum_etiket && <li>Bildirim: {r.bildirim.surum_etiket}, yükleme {saatYaz(r.bildirim.zaman)}.</li>}
                {r.saatlik_detay?.yuklu && r.saatlik_detay.toplam?.edt_net_fark_tl != null && <li>Saatlik detay yüklü: {sayiTr(r.saatlik_detay.ortak_saat)} ortak saatte dengesizlik farkı {isaretli(r.saatlik_detay.toplam.edt_net_fark_tl, 2)} TL (eş kapsamlı).</li>}
                {r.bilesenler.flatMap((b) => b.notlar.slice(1)).map((n) => <li key={n}>{n}</li>)}
                {r.eylem && <li><b>Ne yapmalı:</b> {r.eylem}</li>}
              </ul>
            </>)}
        </Kart>
        <Kart baslik="Ne yapmalı" alt="Bu dönemin verisinden türeyen gözlemler. Eylem: var olan bir sayfada yapılabilir; öneri: değerlendirin; bilgi: hesabın sınırı. PVQuant piyasaya teklif vermez, santralı işletmez.">
          {o.oneriler.length === 0 ? <div className="bos-durum"><div className="bos-bas">Dikkat gerektiren bir gözlem yok</div><p>Program, ölçüm, fiyat verisi ve bildirim bu dönem için yeterli; hesap tam kapsamlı.</p></div> : (
            <ul className="not-listesi">
              {o.oneriler.map((x) => (
                <li key={x.kod} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                  <span className={`rozet rozet-kucuk ${ONERI_SINIF[x.tur] ?? "rozet-notr"}`} style={{ flex: "0 0 auto", marginTop: 2 }}>{x.tur_ad}</span>
                  <span>{x.metin}{x.dayanak ? <span className="soluk"> ({x.dayanak})</span> : null}{x.sayfa && SAYFA_AD[x.sayfa] ? <> <a href={`#${x.sayfa}/${plantId}`}>{SAYFA_AD[x.sayfa]} sayfasına git</a></> : null}</span>
                </li>))}
            </ul>)}
        </Kart>
      </div>
      <div className="ızgara-cift">
        <Kart baslik="Üretim düşüklüğü" alt="Beklenen üretim ile gerçekleşen arasındaki fark, nedenine göre. TL karşılığı satış fiyatıyla gelir kaybı tahminidir; uzlaştırma kalemi değildir ve dengesizlik satırıyla toplanmaz.">
          <dl className="kunye">
            <div><dt>Program farkı</dt><dd>{th.n_saat ? <>eksik {sayiTr(th.eksik_mwh ?? 0, 1)} MWh, fazla {sayiTr(th.fazla_mwh ?? 0, 1)} MWh <span className="kunye-not">({th.program}; mali karşılığı dengesizlik satırında)</span></> : <span className="kunye-durum eksik">Hesaplanamadı</span>}</dd></div>
            <div><dt>Tahmin hatası</dt><dd>{th.wmape != null ? <span className="kunye-sayi">%{sayiTr(th.wmape, 1)}</span> : <span className="kunye-durum eksik">Hesaplanamadı</span>}{th.wmape != null && <span className="kunye-not"> saatlik toplam hata oranı, bağımsız doğrulama (Doğruluk sayfası)</span>}</dd></div>
            <div><dt>Enerji performansı</dt><dd>{du.kayip?.epi != null ? <span className="kunye-sayi">{sayiTr(du.kayip.epi * 100, 1)}</span> : <span className="kunye-durum eksik">Hesaplanamadı</span>}{du.kayip?.epi != null && <span className="kunye-not"> gerçekleşen / beklenen, yüzde</span>}</dd></div>
          </dl>
          {du.kayip?.durum === "ok" ? (
            <div className="grafik-kaydir" style={{ marginTop: 10 }}><table className="veri sayisal dar">
              <thead><tr><th style={sol}>Neden sınıfı</th><th>Saat</th><th>Kayıp (kWh)</th><th>Gelir kaybı (TL)</th></tr></thead>
              <tbody>{du.siniflar.filter((s) => s.saat > 0).map((s) => <tr key={s.kod}><td style={{ ...sol, whiteSpace: "normal" }}>{s.ad}</td><td className="mono">{sayiTr(s.saat)}</td><td className="mono">{s.kayip_kwh == null ? "—" : sayiTr(s.kayip_kwh, 0)}</td><td className="mono">{s.kayip_tl == null ? "—" : sayiTr(s.kayip_tl, 0)}</td></tr>)}</tbody>
            </table></div>
          ) : <p className="soluk" style={{ margin: "10px 0 0", fontSize: 13.5 }}>{du.kayip?.durum === "yetersiz" ? "Dönemde üretim mümkün saat yetersiz; neden ayrışımı yapılmadı." : "Beklenen üretim verisi olmadığından neden ayrışımı yapılmadı."}</p>}
          <ul className="not-listesi">
            {du.bilesenler.map((b) => <li key={b.kod}><b>{b.ad}:</b> {b.tutar_tl == null ? b.notlar[0] ?? "hesaplanmadı" : `${yaz(b.tutar_tl)} TL`} <Rozet n={b.nitelik} /></li>)}
            {du.sozlesme?.not && <li className="soluk">{du.sozlesme.not}</li>}
          </ul>
        </Kart>
        <Kart baslik="Önümüzdeki günler" alt="Gelecek günlerin programı ile son dönemin planlanan MWh başına net uzlaştırma oranının çeyreklerinden türeyen aralık. Senaryodur; vaat değildir."
          sag={<span className="cip"><Meta items={[`${sayiTr(ma.ufuk.gun)} gün`, ma.gecmis_gun > 0 && `son ${sayiTr(ma.gecmis_gun)} günün oranı`, ma.program_mwh != null && `${sayiTr(ma.program_mwh, 1)} MWh program`]} /></span>}>
          {ma.nitelik !== "senaryo" || !ma.aralik_tl ? (
            <div className="bos-durum"><div className="bos-bas">Aralık hesaplanamadı</div><p>{ma.notlar.slice(1).join(" ") || "Gelecek günler için program ya da yeterli geçmiş yok."}</p></div>
          ) : (
            <>
              <div className="ızgara satir-3" style={{ marginBottom: 10 }}>
                <Kpi etiket="Temkinli (çeyrek 1)" deger={binTl(ma.aralik_tl.p25)} birim="bin TL" alt={`${isaretli(ma.oran_tl_mwh?.p25, 0)} TL/MWh`} />
                <Kpi etiket="Orta (ortanca)" deger={binTl(ma.aralik_tl.p50)} birim="bin TL" alt={`${isaretli(ma.oran_tl_mwh?.p50, 0)} TL/MWh`} />
                <Kpi etiket="İyimser (çeyrek 3)" deger={binTl(ma.aralik_tl.p75)} birim="bin TL" alt={`${isaretli(ma.oran_tl_mwh?.p75, 0)} TL/MWh`} />
              </div>
              <ul className="not-listesi">
                <li>Program kaynağı: {Object.entries(ma.kaynak).map(([k, v]) => `${v} saat ${k === "bildirilen" ? "bildirilen KGÜP" : "son tahmin"}`).join(", ") || "yok"}; dönem {gunYaz(ma.ufuk.bas)} – {gunYaz(ma.ufuk.bit)}.</li>
                <li>{ma.notlar[0]}</li>
              </ul>
            </>)}
        </Kart>
      </div>
      <Kart baslik="Hesap bilgileri" alt="Bu sonucun hangi varsayımlarla üretildiği; aynı varsayımlarla yeniden üretilebilir.">
        <dl className="kunye">
          <div><dt>Dönem</dt><dd className="kunye-sayi">{gunYaz(o.donem.bas)} – {gunYaz(o.donem.bit)}{o.donem.kirpildi && <span className="kunye-not"> süren dönem, bugüne kadar</span>}</dd></div>
          <div><dt>Hesap durumu</dt><dd>{durumMetni}{o.kayitli ? <span className="kunye-not"> kayıtlı sonuç; yeni hesap yeni kayıt olur, eski kayıt silinmez</span> : <span className="kunye-not"> kaydedilmedi</span>}</dd></div>
          <div><dt>Üretim girdisi</dt><dd>{u.gerceklesen.secim_etiket}<span className="kunye-not"> {u.gerceklesen.sinir_etiket}</span></dd></div>
          <div><dt>Program</dt><dd>{u.planlanan.kaynak_etiket}<span className="kunye-not"> {sayiTr(u.planlanan.bildirilen_saat)} saat bildirilen, {sayiTr(u.planlanan.oneri_saat)} saat öneri</span></dd></div>
          <div><dt>Fiyat</dt><dd>{uz.fiyat.senaryo_saat > 0 ? <>{sayiTr(uz.fiyat.epias_saat)} saat EPİAŞ, {sayiTr(uz.fiyat.senaryo_saat)} saat senaryo</> : "EPİAŞ saatlik PTF, SMF ve sistem yönü"}</dd></div>
          <div><dt>Uzlaştırma kuralı</dt><dd><span className="kunye-sayi">{m.kural_surumu_tam ?? uz.kural_surumu ?? "—"}</span>{m.kural_sicili_sha && <span className="kunye-not">kural sicili {m.kural_sicili_surumu ?? ""} · {m.kural_sicili_sha}</span>}</dd></div>
          {/* v2.605 (F4-K): yeniden üretim için damgalar — fiyat sürümü (F4-G), tahmin kayıtları (F4-B arşivi), girdi ve ayar damgaları, çıktı sürümü */}
          {m.girdi?.fiyat && <div><dt>Fiyat sürümü</dt><dd><span className="kunye-sayi">{m.girdi.fiyat.sha16}</span><span className="kunye-not">{m.girdi.fiyat.itibariyle ? `${saatYaz(m.girdi.fiyat.itibariyle)} itibarıyla geçerli fiyatlar` : "hesap anındaki fiyatlar"}; {sayiTr(m.girdi.fiyat.epias_saat)} saat EPİAŞ, {sayiTr(m.girdi.fiyat.senaryo_saat)} saat senaryo</span></dd></div>}
          {m.girdi?.program && <div><dt>Tahmin kayıtları</dt><dd>{m.girdi.program.kosular.length ? <><span className="kunye-sayi">{sayiTr(m.girdi.program.kosular.length)}</span> kayıt<span className="kunye-not">{m.girdi.program.kosular.slice(0, 2).map((k) => k.slice(0, 8)).join(", ")}{m.girdi.program.kosular.length > 2 ? ", …" : ""}; arşivdeki tahmin kimlikleri</span></> : <><span className="kunye-durum eksik">Bildirilen program</span><span className="kunye-not">arşiv tahmini kullanılmadı</span></>}</dd></div>}
          {m.girdi?.sha16 && <div><dt>Girdi damgası</dt><dd><span className="kunye-sayi">{m.girdi.sha16}</span><span className="kunye-not">ölçüm, program, fiyat, ayar ve sözlüklerin bileşik özeti; aynı damga aynı sonucu verir{m.ayar_sha ? `; santral ayarı ${m.ayar_sha}` : ""}</span></dd></div>}
          <div><dt>Satış tarifesi</dt><dd>{o.gelir.tarife.etiket}{o.gelir.tarife.ortalama_fiyat_tl_mwh != null && <span className="kunye-not"> ortalama {sayiTr(o.gelir.tarife.ortalama_fiyat_tl_mwh, 0)} TL/MWh</span>}</dd></div>
          <div><dt>Piyasa pozisyonu</dt><dd>{m.pozisyon.kaynak === "uretim" ? "üretildiği kadar satış" : m.pozisyon.kaynak === "sabit" ? `sabit ${sayiTr(m.pozisyon.sabit_mwh ?? 0, 2)} MWh/saat` : "satış programa eşit"}</dd></div>
          <div><dt>Hesap sözlüğü</dt><dd className="kunye-sayi">{m.sozluk_surumu}{m.yazilim_surumu ? `, yazılım ${m.yazilim_surumu}` : ""}{m.cikti_surumu ? `, çıktı ${m.cikti_surumu}` : ""}</dd></div>
        </dl>
        <details className="aciklama" onToggle={gecmisAc}>
          <summary>Kayıtlı sürümler ve varsayımların geçmişi</summary>
          {gecmis === undefined ? <YerTutucu yukseklik={48} /> : gecmis === null ? <p className="soluk">Sürüm listesi alınamadı.</p> : gecmis.surumler.length === 0 ? <p className="soluk" style={{ margin: 0 }}>Bu dönem için kayıtlı sürüm yok; gece hesabı ilk kaydı oluşturur.</p> : (
            <div className="grafik-kaydir"><table className="veri sayisal dar">
              <thead><tr><th style={sol}>Hesap zamanı</th><th>Toplam (TL)</th><th style={sol}>Nitelik</th><th style={sol}>Üretim girdisi</th><th style={sol}>Kural</th></tr></thead>
              <tbody>{gecmis.surumler.map((s) => <tr key={s.id}><td style={sol}>{saatYaz(s.hesap_zamani)}</td><td className="mono">{yaz(s.toplam?.tutar_tl)}</td><td style={sol}><Rozet n={s.toplam?.nitelik ?? "eksik"} /></td><td style={sol}>{s.uretim_girdisi === "sayac" ? "sayaç" : "SCADA"}</td><td style={sol} className="mono">{String((s.varsayimlar as { kural_surumu?: string | null }).kural_surumu ?? "—")}</td></tr>)}</tbody>
            </table></div>)}
        </details>
        <details className="aciklama">
          <summary>Nasıl hesaplanır</summary>
          <p>Dönemin bütün saatleri tek küme olarak alınır; program, ölçüm, fiyat ve kalemler aynı saatlerden türer. Enerji satışı gerçekleşen üretimin tarifeyle çarpımıdır.
            Enerji dengesizlik tutarı ve KGÜP sapma tutarı, Doğruluk ve Mutabakat sayfalarıyla aynı saatlik hesaptan gelir; alacak ve borç 19.10.2026'dan itibaren ayrı toplanır.
            Toplam yalnız bu üç satırdır. Resmî bildirim satırları, DSG içi tutar, teminat ve YEKDEM göstergeleri, üretim düşüklüğü ve ileriye dönük aralık yan yana gösterilir, toplanmaz; aksi hâlde aynı sapma iki kez sayılırdı.
            Senaryo fiyatlı ya da sistem yönü varsayılan saat varsa satır senaryo niteliği alır; eksik satır toplamın niteliğini düşürür. Santralin taşımadığı kalemler (lisanssız dağıtım, öz tüketim) bilgi amaçlı kalır.</p>
        </details>
      </Kart>
    </Sayfa>
  );
}
