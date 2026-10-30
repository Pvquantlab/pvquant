import { useEffect, useRef, useState } from "react";
import { api, bellektenOku, dsgYolu, kupstYolu } from "../../api/client";
import type { DsgAnahtar, Portfoy as PortfoyT, PortfoyAnahtar, PortfoyDsg, PortfoyKupst, PortfoyTahmin } from "../../api/types";
import { Bilgi, Kart, Kpi, Sayfa, sayiTr, gucTr, enerjiTr, SayfaIskeleti, YerTutucu } from "./parcalar";
import { Meta } from "../../lib/Meta";

/** 23.10 sekizinci tur — «76,3 MWh» gibi birimli dizgiyi sayı + soluk birim olarak basar; dizgi aynen (enerjiTr). */
function DegerBirim({ metin }: { metin: string }) {
  const i = metin.lastIndexOf(" ");
  if (i < 0) return <>{metin}</>;
  return <>{metin.slice(0, i)} <span className="birim">{metin.slice(i + 1)}</span></>;
}
/** «22.10.2026 23:00» → tarih ve saat ayrı parçalar; dar sütunda yalnız ikisinin arasında kırılır. */
function TarihSaat({ metin }: { metin: string }) {
  const i = metin.lastIndexOf(" ");
  if (i < 0) return <>{metin}</>;
  return <><span className="parca">{metin.slice(0, i)}</span> <span className="parca">{metin.slice(i + 1)}</span></>;
}

/** v2.263 (Dalga 5.15) — Portföy: kiracının tüm santralleri tek tabloda; toplamlar dürüst
 *  (bir santralin beklentisi yoksa toplam da yok). Satıra tıklayınca o santrala geçilir. */
export function Portfoy({ onSec }: { onSec: (id: string) => void }) {   // 26.10 Faz 6: santralYenile Kuruluş'a taşındı (arşiv orada)
  // 24.10 Portföy geçiş turu — üç istek BAĞIMSIZ ve BAYAT-ÖNCE. Canlıda (Deneme Lab, konteyner içi sıcak) ölçüldü:
  // /v1/portfoy ≈ 0,25–0,27 s, /portfoy/tahmin ≈ 0,4 s (sonra 500), /portfoy/dsg ≈ 0,85–1,1 s. v2.324'ün «tek kapı»sı
  // KPI'ları ve santral tablosunu en yavaş olan DSG'ye bekletiyordu; 60 sn bellek dolunca her dönüş iskeletten başlıyordu.
  // Şimdi: (1) bellekte son yanıt varsa sayfa onunla ANINDA çizilir, başlık çipi «güncelleniyor» der, taze yanıt gelince
  // değerler yenilenir (SWR; tarih/tazelik alanları verinin kendisinden gelir, uydurulmaz); (2) KPI + tablo /portfoy
  // gelir gelmez, tahmin ve DSG kartları kendi yanıtlarıyla dolar — yerleri boyutlu tutulur (kayma yok); (3) üç istek
  // useState başlatıcısında yola çıkar: çocuk bölümlerin (dış erişim, paylaşım, ekip, arşiv) effect'leri ebeveynden önce
  // koştuğundan eskiden 8 ikincil istek çekirdek üçünün ÖNÜNE geçiyordu; (4) sunucu hatası «veri yok»tan ayrı söylenir.
  // API sözleşmesi, hesaplar ve yetkiler değişmedi. undefined = henüz bilinmiyor, null = yok.
  type Durum = "bekliyor" | "tamam" | "hata";
  const [p, setP] = useState<PortfoyT | null | undefined>(() => bellektenOku<PortfoyT>("/v1/portfoy"));
  const [dsg, setDsg] = useState<PortfoyDsg | null | undefined>(() => bellektenOku<PortfoyDsg>("/v1/portfoy/dsg?gun=30"));   // v2.276
  const [pt, setPt] = useState<PortfoyTahmin | null | undefined>(() => bellektenOku<PortfoyTahmin>("/v1/portfoy/tahmin?gun=7"));   // v2.280
  const [pD, setPD] = useState<Durum>("bekliyor");
  const [ptD, setPtD] = useState<Durum>("bekliyor");
  const [dsgD, setDsgD] = useState<Durum>("bekliyor");
  const [istekler] = useState(() => ({ p: hatirlayarak("/v1/portfoy", api.portfoy), pt: hatirlayarak("/v1/portfoy/tahmin?gun=7", api.portfoyTahmin), dsg: hatirlayarak("/v1/portfoy/dsg?gun=30", api.portfoyDsg) }));
  useEffect(() => {
    let acik = true;
    // hata: bayat değer varsa yerinde kalır (çip «güncellenemedi» der), yoksa null + «sunucu hatası» metni
    istekler.p.then((v) => { if (acik) { setP(v); setPD("tamam"); } }, () => { if (acik) { setP((e) => e ?? null); setPD("hata"); } });
    istekler.pt.then((v) => { if (acik) { setPt(v); setPtD("tamam"); } }, () => { if (acik) { setPt((e) => e ?? null); setPtD("hata"); } });
    istekler.dsg.then((v) => { if (acik) { setDsg(v); setDsgD("tamam"); } }, () => { if (acik) { setDsg((e) => e ?? null); setDsgD("hata"); } });
    return () => { acik = false; };
  }, [istekler]);
  // 29.10: üyelere dağıtım anahtarı (sözleşmesel) — seçim değişince DSG yeniden çekilir; varsayılan yol bellek anahtarıyla aynı
  const [anahtar, setAnahtar] = useState<DsgAnahtar>("sapma");
  const ilkAnahtar = useRef(true);
  useEffect(() => {
    if (ilkAnahtar.current) { ilkAnahtar.current = false; return; }   // ilk yükleme istekler.dsg ile geldi; «sapma»ya geri dönüş de yeniden çeker
    let acik = true; setDsgD("bekliyor");
    hatirlayarak(dsgYolu(30, anahtar), () => api.portfoyDsg(30, anahtar)).then((v) => { if (acik) { setDsg(v); setDsgD("tamam"); } }, () => { if (acik) { setDsgD("hata"); } });
    return () => { acik = false; };
  }, [anahtar]);
  // v2.511 (04 #14): toplayıcı/GTŞ portföyü KÜPST — UEVÇB bazında; anahtar değişince yeniden çekilir
  const [kupst, setKupst] = useState<PortfoyKupst | null | undefined>(() => bellektenOku<PortfoyKupst>(kupstYolu(30)));
  const [kupstD, setKupstD] = useState<"bekliyor" | "tamam" | "hata">("bekliyor");
  const [kAnahtar, setKAnahtar] = useState<PortfoyAnahtar>("sapma");
  useEffect(() => {
    let acik = true; setKupstD("bekliyor");
    hatirlayarak(kupstYolu(30, kAnahtar), () => api.portfoyKupst(30, kAnahtar)).then((v) => { if (acik) { setKupst(v); setKupstD("tamam"); } }, () => { if (acik) { setKupst((e) => e ?? null); setKupstD("hata"); } });
    return () => { acik = false; };
  }, [kAnahtar]);
  const hazir = p !== undefined || pD !== "bekliyor";
  const tazeleniyor = hazir && (pD === "bekliyor" || ptD === "bekliyor" || dsgD === "bekliyor");
  const t = p?.toplam ?? null;
  // v2.362: santraller listesi de ölçekle konuşur (bulgu 14 — 0,0 MWh kalıntısı)
  const kwhYaz = (v: number | null | undefined) => v == null ? "—" : enerjiTr(v);
  // v2.360: KPI'da birim değerin yanında ölçekle gelir (küçükte kWh, büyükte MWh)
  const enj = (v: number | null | undefined) => v == null ? "—" : enerjiTr(v);
  const tarih = (s: string | null) => s ? new Date(s).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "—";
  if (!hazir) return (
    <Sayfa baslik="Portföy" alt="Tüm santraller bir bakışta; sayılar kurulu güçle ağırlıklıdır, hesaplanamayan değerler — ile gösterilir.">
      <SayfaIskeleti kpi={4} kart={2} />
    </Sayfa>
  );
  return (
    <Sayfa baslik="Portföy" alt="Tüm santraller bir bakışta; sayılar kurulu güçle ağırlıklıdır, hesaplanamayan değerler — ile gösterilir."
      sag={<span className="cip">{p ? <Meta items={[`${sayiTr(p.santraller.length)} santral`, new Date(p.gun + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "short" }), tazeleniyor && "güncelleniyor", pD === "hata" && "güncellenemedi"]} /> : "—"}</span>}>
      <div className="ızgara satir-4" style={{ marginBottom: 14 }}>
        {/* v2.360: küçük portföyde MWp "0,00" okunuyordu — birim ölçekle gelir */}
        <Kpi etiket="Toplam kurulu güç"
             deger={t ? (t.kapasite_kwp < 100 ? gucTr(t.kapasite_kwp) : sayiTr(t.kapasite_kwp / 1000, 2)) : "—"}
             birim={t && t.kapasite_kwp < 100 ? "kWp" : "MWp"} alt={t ? `${sayiTr(t.santral)} santral` : ""} />
        {/* 22.10 (v2.463): iki değer tek birimle — «1.754,1 MWh · 1.755,1 MWh» kartta kesiliyordu;
            birim Kpi'nin kendi alanında bir kez yazılır, ölçek büyük olana göre seçilir. */}
        {/* 23.10 yedinci tur: «1.914,2 · 1.827,6 MWh» iki sayı tek noktalamayla okunmuyordu — bugün ana değer, yarın
            kendi etiketiyle ikinci satır (Kpi.ikinci); ölçek yine büyük olana göre ortak. */}
        {(() => {
          const ikisi = !!t && t.bugun_kwh != null && t.yarin_kwh != null;
          const kucuk = ikisi && Math.max(Math.abs(t!.bugun_kwh!), Math.abs(t!.yarin_kwh!)) < 10_000;
          const b = kucuk ? "kWh" : "MWh";
          const yaz = (v: number) => kucuk ? sayiTr(v, 0) : sayiTr(v / 1000, 1);
          return <Kpi etiket="Bugün beklenen üretim"
             deger={ikisi ? yaz(t!.bugun_kwh!) : t ? enj(t.bugun_kwh) : "—"}
             birim={ikisi ? b : undefined}
             ikinci={t ? { etiket: "Yarın", deger: ikisi ? yaz(t.yarin_kwh!) : enj(t.yarin_kwh), birim: ikisi ? b : undefined } : undefined}
             alt={t && (t.bugun_kwh == null || t.yarin_kwh == null) ? "bir santralde tahmin yok; toplam gösterilmez" : "tüm santrallerin beklenen (P50) toplamı"} />;
        })()}
        <Kpi etiket="30 günlük tahmin hatası (WMAPE)" deger={t?.wmape_agirlikli != null ? `%${sayiTr(t.wmape_agirlikli, 1)}` : "—"}
             alt={t ? `${sayiTr(t.wmape_kapsanan_kwp / 1000, 2)} MWp değerlendirmede` : ""} />
        <Kpi etiket="Açık alarm" deger={t ? sayiTr(t.acik_alarm) : "—"}
             ikinci={t ? { etiket: "Veri gecikmiş", deger: sayiTr(t.veri_gecikmis), birim: "santral" } : undefined}
             alt={t && t.santral > 0 ? "alarm: son 7 günde okunmamış kayıt; gecikme: son ölçüm 2 günden eski" : ""} ton={t && (t.acik_alarm > 0 || t.veri_gecikmis > 0) ? "uyari" : undefined} />
      </div>
      {/* 29.10 (05 §3, 08 #10): operasyon kararı ilk ekranda — yarının programı hazır mı; yalnız program yükümlülüğü olan
          santraller «hazır/eksik» alır; yükümlülüğü olmayana zorunlu operasyon gibi sunulmaz; segment seçilmemişse söylenir */}
      {p && p.santraller.length > 0 && p.santraller.some((r) => r.program) && (
        <Kart baslik="Yarının üretim programı, KGÜP" alt="EPİAŞ bildirim penceresi 14:00–15:30; program, 15:30 kesiminden önce verilmiş son tahminden üretilir"
          sag={<span className="cip">{t && t.program_yukumlu != null ? <Meta items={[`${sayiTr(t.program_hazir ?? 0)} / ${sayiTr(t.program_yukumlu)} hazır`, (t.program_bildirilen ?? 0) > 0 && `${sayiTr(t.program_bildirilen ?? 0)} bildirildi`, (t.program_segment_yok ?? 0) > 0 && `${sayiTr(t.program_segment_yok ?? 0)} santralde segment seçilmedi`]} /> : "—"}</span>}>
          <ul className="tanim-listesi program-listesi">
            {p.santraller.map((r) => {
              const pr = r.program;
              if (!pr) return null;
              const rozet = pr.yukumlu === null ? ["rozet-notr", "segment seçilmedi"]
                : pr.yukumlu === false ? ["rozet-notr", "program yükümlülüğü yok"]
                : pr.hazir === true ? ["rozet-ok", "hazır"]
                : pr.hazir === false ? ["rozet-uyari", "15:30 öncesi tahmin yok"]
                : ["rozet-notr", "kontrol edilemedi"];
              // tek hücre: rozet + notlar (tanim-listesi iki sütunlu ızgaradır; birden çok çocuk hücrelere dağılıyordu)
              return (
                <li key={r.id}><b>{r.ad}</b>
                  <span>
                    <span className={`rozet ${rozet[0]} rozet-kucuk`}>{rozet[1]}</span>
                    {pr.bildirilen && <span className="rozet rozet-ok rozet-kucuk" style={{ marginLeft: 6 }} title="Panele yüklenen, TPYS'ye bildirildiği beyan edilen dosya; TPYS kabulü doğrulanmaz">bildirildi</span>}
                    {pr.hazir && pr.run_at && <span className="soluk"> · tahmin {tarih(pr.run_at)}</span>}
                    {pr.bildirilen && pr.bildirim_zamani && <span className="soluk"> · dosya {tarih(pr.bildirim_zamani)}</span>}
                    {pr.not && pr.yukumlu === true && pr.hazir !== false && <span className="soluk"> · {pr.not}</span>}
                    {pr.yukumlu === false && r.segment && <span className="soluk"> · dengesizliği tedarikçi/toplayıcı portföyü taşır</span>}
                    {pr.yukumlu && <span className="soluk"> · bildirim penceresi {pr.teslim.durum === "pencere_acik" ? `açık, ${sayiTr(pr.teslim.dakika_kaldi)} dk kaldı` : pr.teslim.durum === "erken" ? "henüz açılmadı" : "kapandı"}</span>}
                  </span>
                </li>);
            })}
          </ul>
        </Kart>
      )}
      {/* 23.10 sekizinci tur — kurumsal veri tablosu: veri sütunları içerik genişliğinde (width:1%) ve 28 px oluklu, ad
          sütunu kalan alanı alır; birimler soluk küçük (.birim); ölçüm tarihi üstte, «N gün eski» rozeti altta (eşik aynı:
          kesinti_gun > 2); alarm sayısı >0 rozet; «satıra tıkla» çipi kalktı — tıklanabilirlik hover/odak zemini,
          imleç ve satır sonundaki ok ile; ilk sütun dar ekranda yapışkan; dipnot üç tanım satırı. onClick/onKeyDown ve
          onSec aynen; veri/eşik/biçim değişmedi. */}
      <Kart baslik="Santraller" alt={p && p.santraller.length > 0 ? `${sayiTr(p.santraller.length)} santral, satır santral sayfasını açar` : undefined}>
        {!p && pD === "hata" ? <p className="soluk" style={{ margin: 0 }}>Portföy özeti şu anda alınamadı (sunucu hatası); sayfayı yenileyin.</p>
         : !p || p.santraller.length === 0 ? <p className="soluk" style={{ margin: 0 }}>Bu hesapta santral yok.</p>
         : (
          <div className="grafik-kaydir santral-tablo">
            <table className="veri sayisal santral">
              <thead><tr>
                <th>Santral</th><th>Kurulu güç <span className="birim">kWp</span></th><th>Segment</th><th className="tarih-saat">Son ölçüm</th>
                <th>Hata 30 g <span className="birim">WMAPE</span></th><th>Bugün</th><th>Yarın</th><th>Alarm</th><th className="tarih-saat">Son tahmin</th><th aria-hidden="true" />
              </tr></thead>
              <tbody>
                {p.santraller.map((r) => {
                  const eski = r.kesinti_gun != null && r.kesinti_gun > 2;
                  return (
                  <tr key={r.id} className="satir-tikla" onClick={() => onSec(r.id)} tabIndex={0}
                      aria-label={`${r.ad}, santral sayfasını aç`}
                      onKeyDown={(e) => { if (e.key === "Enter") onSec(r.id); }}>
                    <td className="ad">{r.ad}</td>
                    <td>{sayiTr(r.kapasite_kwp)}</td>
                    <td>{r.segment ?? <span className="bos" title="Piyasa segmenti seçilmedi">—</span>}</td>
                    <td>
                      <div className="tarih-saat"><TarihSaat metin={tarih(r.son_olcum)} /></div>
                      {eski && <div className="hucre-alt"><span className="rozet rozet-uyari rozet-kucuk" title="Son ölçüm 2 günden eski">{sayiTr(r.kesinti_gun!)} gün eski</span></div>}
                    </td>
                    <td>{r.wmape_30g != null ? `%${sayiTr(r.wmape_30g, 1)}` : <span className="bos" title="Son 30 günde karşılaştırılmış gün yok">—</span>}</td>
                    <td><DegerBirim metin={kwhYaz(r.bugun_kwh)} /></td>
                    <td><DegerBirim metin={kwhYaz(r.yarin_kwh)} /></td>
                    <td>{r.acik_alarm > 0
                      ? <span className="rozet rozet-uyari rozet-kucuk" title="Son 7 günde okunmamış kayıt">{sayiTr(r.acik_alarm)}</span>
                      : <span className="bos">0</span>}</td>
                    <td className="tarih-saat"><TarihSaat metin={tarih(r.son_kosu)} /></td>
                    <td className="satir-ok" aria-hidden="true">
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="m5 3 4 4-4 4" /></svg>
                    </td>
                  </tr>);
                })}
              </tbody>
            </table>
          </div>
        )}
        <ul className="tanim-listesi">
          <li><b>Bugün, yarın</b>son tahminin yerel gün toplamı (beklenen, P50); 20 saatten az kapsanan gün gösterilmez.</li>
          <li><b>Hata 30 g</b>son 30 günün 0–24 saat tahmin hatası (WMAPE).</li>
          <li><b>Alarm</b>son 7 günde okunmamış kayıt.</li>
        </ul>
      </Kart>
      {/* v2.280 (Tablo 3.2 satır 11): hiyerarşik uzlaştırılmış portföy tahmini — toplam santral tahminleriyle tutarlı */}
      <Kart baslik="Portföyün günlük üretim tahmini" sag={<span className="cip">{pt?.durum === "ok" ? <Meta items={[pt.yontem, pt.tutarli === false && "tutarsız", ptD === "bekliyor" && "güncelleniyor", ptD === "hata" && "güncellenemedi"]} /> : "—"}</span>}>
        {/* 23.10 yedinci tur: cümle başı tire kalktı — tire yalnız değer yerinde (tablo/KPI hücresi) */}
        {/* 24.10: bekliyor → boyutlu yer tutucu; sunucu hatası → açıkça söylenir (eskiden «Henüz tahmin yok» ile karışıyordu) */}
        {pt === undefined && ptD === "bekliyor" ? <YerTutucu yukseklik={168} />
         : ptD === "hata" && (!pt || pt.durum !== "ok") ? <p className="soluk" style={{ margin: 0 }}>Portföy tahmini şu anda alınamadı (sunucu hatası); santral tahminleri Tahminler sayfasında.</p>
         : !pt || pt.durum !== "ok" ? <p className="soluk" style={{ margin: 0 }}>Henüz tahmin yok.</p> : (
          <>
            <div className="grafik-kaydir">
              <table className="veri" style={{ fontSize: 13.5 }}>
                {/* v2.362: küçük portföyde günlük toplamlar kWh konuşur (bulgu 14) */}
                {(() => { const kucukP = !(pt.gunler ?? []).some((g) => (g.p90_mwh ?? 0) >= 10);
                  const b = kucukP ? "kWh" : "MWh";
                  const yaz = (v: number) => kucukP ? sayiTr(v * 1000, 0) : sayiTr(v, 1);
                  return (<>
                <thead><tr><th>Gün</th><th>P10 ({b})</th><th>P50 ({b})</th><th>P90 ({b})</th><th>Saat</th></tr></thead>
                <tbody className="mono">
                  {(pt.gunler ?? []).map((g) => (
                    <tr key={g.gun}><td>{new Date(g.gun + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "short" })}</td>
                      <td>{yaz(g.p10_mwh)}</td><td style={{ fontWeight: 600 }}>{yaz(g.p50_mwh)}</td><td>{yaz(g.p90_mwh)}</td><td>{sayiTr(g.saat)}</td></tr>))}
                </tbody>
                  </>); })()}
              </table>
            </div>
            <p className="soluk" style={{ fontSize: 14, margin: "10px 0 0" }}>Santral tahminleri toplanır; toplam, santral tahminleriyle çelişmez. {pt.not}{pt.artik_gun ? ` Düzeltme geçmişi ${sayiTr(pt.artik_gun)} gün.` : ""}</p>
          </>
        )}
      </Kart>
      {/* v2.276 (Dalga 5): DSG/toplayıcı netleştirmesi — portföy tek dengesizlik hesabına girerse ne kazanılır */}
      {/* v2.502 (F-08): DSG netleşmesi yürürlükteki kuralla — üye eşiği × PH grupta, aşan kısım bireysel; KÜPST üye bazında, netleşmez.
          Eski sunucu (gosterge !== false) hâlâ «gösterge» rozeti alır. */}
      <Kart baslik={dsg?.gosterge === false ? "Dengeden Sorumlu Grup (DSG) hesabı — santrallerinizin enerji dengesizlik tutarı: tek başına ve DSG içinde netleştirilmiş" : "Dengeden Sorumlu Grup (DSG) göstergesi — yalnız enerji dengesizlik tutarı, eşik uygulanmadan"}
        sag={<>{dsg?.gosterge !== false && <span className="rozet rozet-notr rozet-kucuk" title="Yürürlükteki %5 üye eşiği (Karar 13869) ve KÜPST'ün netleşmemesi bu görünümde uygulanmaz; varsayımsal yeniden hesap">gösterge</span>}
          {dsg?.gosterge === false && dsg.esik != null && <span className="cip" title={`Her santralin sapmasının bu oran ile PH çarpımı kadarı DSG içinde netleşir; aşan kısım santralin kendisinde kalır. ${dsg.esik_kaynak ?? ""}`}>üye eşiği %{sayiTr(dsg.esik * 100, 0)}</span>}
          <span className="cip" title={dsg && dsg.fiyat.senaryo_saat > 0 ? "Senaryo fiyatı: EPİAŞ piyasa fiyatı bağlı olmadığından EPDK yıllık ortalaması kullanılmış, sistem yönü dengede varsayılmıştır." : "Saatlik PTF, SMF ve sistem yönü EPİAŞ verisinden alınır."}>{dsg ? <Meta items={[`son ${sayiTr(dsg.pencere_gun)} gün`, dsg.fiyat.senaryo_saat > 0 ? "senaryo fiyatı" : "piyasa fiyatı (EPİAŞ)", dsgD === "bekliyor" && "güncelleniyor", dsgD === "hata" && "güncellenemedi"]} /> : "—"}</span></>}>
        {dsg === undefined && dsgD === "bekliyor" ? <YerTutucu yukseklik={124} />
         : !dsg && dsgD === "hata" ? <p className="soluk" style={{ margin: 0 }}>Dengeden Sorumlu Grup hesabı şu anda alınamadı; sunucu hatası.</p>
         : !dsg ? <p className="soluk" style={{ margin: 0 }}>Veri yok.</p> : dsg.ayri_tl == null ? (
          <p className="soluk" style={{ margin: 0 }}>{dsg.not === "ortak saat yetersiz" ? "Santrallerin ortak ölçüm saati henüz yeterli değil; en az 24 saat gerekir, ölçümler biriktikçe hesaplanır." : dsg.not === "portföyde dengesizlik taşıyan üye yok" ? "Portföyde dengesizliğini kendisi taşıyan santral bulunmuyor; DSG hesabı bu segmentlerde uygulanmaz." : dsg.not ?? "Santrallerin ortak ölçüm saati henüz yeterli değil."}</p>
        ) : (
          <>
            <div className="ızgara satir-3" style={{ marginBottom: 10 }}>
              <Kpi etiket="Tek başına dengesizlik maliyeti" bilgi="Her santralin kendi dengesizliğini tek başına ödemesi hâlinde oluşacak toplam maliyet. Enerji dengesizlik tutarı, EDT, yürürlükteki kuralla yeniden hesaplanır." deger={sayiTr(dsg.ayri_tl / 1000, 1)} birim="bin TL" alt={`${sayiTr(dsg.santral)} santral · ${sayiTr(dsg.sapma_ayri_mwh ?? 0, 1)} MWh sapma`} />
              <Kpi etiket="DSG içinde netleştirilmiş maliyet" bilgi="Santrallerin sapmaları Dengeden Sorumlu Grup içinde birbirini kısmen karşılar; geriye kalan dengesizliğin maliyetidir." deger={sayiTr((dsg.net_tl ?? 0) / 1000, 1)} birim="bin TL" alt={`${sayiTr(dsg.sapma_net_mwh ?? 0, 1)} MWh net sapma`} />
              <Kpi etiket="Netleşme farkı · varsayımsal" bilgi="Tek başına maliyet ile DSG içindeki maliyet arasındaki fark. Yürürlükteki kuralla yapılan yeniden hesaptır; EPİAŞ uzlaştırma sonucu değildir." deger={sayiTr((dsg.kazanc_tl ?? 0) / 1000, 1)} birim="bin TL" alt={dsg.kazanc_pct != null ? `tek başına maliyetin %${sayiTr(dsg.kazanc_pct, 1)}'i${dsg.gosterge === false ? " · eşik kuralı uygulandı" : " · eşik uygulanmadan, gösterge"}` : "—"} />
            </div>
            {dsg.gosterge === false && (
              <div className="ızgara satir-3" style={{ marginBottom: 10 }}>
                <Kpi etiket="Enerji dengesizlik tutarı · tek başına" bilgi="EPİAŞ uzlaştırmasındaki enerji dengesizlik tutarı, EDT: eksik üretim borç, fazla üretim alacak yazar; gösterilen değer ikisinin netidir. Eksi tutar santralin ödediği, artı tutar aldığı tutardır." deger={sayiTr((dsg.edt_tek_tl ?? 0) / 1000, 1)} birim="bin TL" alt="eksi = santral öder · artı = santral alır" />
                <Kpi etiket="Enerji dengesizlik tutarı · DSG içinde" bilgi="DSG içinde netleşen kısmın tutarı ile eşiği aşıp santralin kendisinde kalan kısmın tutarının toplamı; grubun net ödeyeceği ya da alacağı tutardır." deger={sayiTr((dsg.edt_dsg_tl ?? 0) / 1000, 1)} birim="bin TL" alt={`DSG içinde netleşen ${sayiTr((dsg.edt_grup_tl ?? 0) / 1000, 1)} + santralde kalan ${sayiTr((dsg.edt_bireysel_tl ?? 0) / 1000, 1)} bin TL`} />
                <Kpi etiket="KGÜP sapma tutarı · KÜPST" bilgi="Kesinleşmiş gün öncesi üretim programından tolerans üstü sapmanın tutarı, KÜPST. Her santral kendi uzlaştırmaya esas veriş çekiş birimi için öder; DSG içinde netleşmez ve enerji dengesizlik tutarından ayrı bir kalemdir." deger={dsg.kupst_uye_tl != null ? sayiTr(dsg.kupst_uye_tl / 1000, 1) : "—"} birim={dsg.kupst_uye_tl != null ? "bin TL" : undefined} alt={dsg.kupst_uye_tl != null ? "üyelerin toplamı · santral başına ödenir · DSG içinde netleşmez" : "üyelerin toplamı · segment seçilmedi; hesaplanamadı"} />
              </div>
            )}
            {dsg.gosterge === false && dsg.uyeler && Object.keys(dsg.uyeler).length > 1 && (
              <details className="aciklama genis" style={{ marginBottom: 10 }}>
                <summary>DSG maliyetinin üyelere dağılımı — {dsg.dagitim_etiket ?? "sapma payına göre"}</summary>
                <div style={{ display: "flex", margin: "8px 0", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                  <label className="soluk" htmlFor="dsg-anahtar">Dağıtım anahtarı<Bilgi metin="Grubun net enerji dengesizlik tutarı üyelere bu anahtarla paylaştırılır. Anahtar DSG sözleşmesinde belirlenir; mevzuat sabitlemez. Sapma payına göre: netleşen sapmadaki pay. Eşit: her santrale aynı pay. Üretime göre: gerçekleşen üretim oranı." /></label>
                  <select id="dsg-anahtar" className="girdi" value={anahtar} onChange={(e) => setAnahtar(e.target.value as DsgAnahtar)} aria-label="DSG üyelere dağıtım anahtarı">
                    <option value="sapma">sapma payına göre</option>
                    <option value="esit">eşit</option>
                    <option value="uretim">üretime göre</option>
                  </select>
                </div>
                <div style={{ overflowX: "auto" }}>
                  <table className="veri" style={{ fontSize: 13.5 }}>
                    <thead><tr><th>Santral</th><th>Sapma (MWh)</th><th>Pay</th><th>Tek başına EDT</th><th>DSG içinde EDT</th><th>Fark</th></tr></thead>
                    <tbody>
                      {Object.entries(dsg.uyeler).map(([ad, u]) => (
                        <tr key={ad}><td>{ad}</td><td>{sayiTr(u.sapma_mwh, 1)}</td><td>{u.pay_pct != null ? `%${sayiTr(u.pay_pct, 1)}` : "—"}</td>
                          <td>{sayiTr(u.edt_tek_tl / 1000, 1)} <span className="birim">bin TL</span></td>
                          <td>{u.edt_dsg_tl != null ? sayiTr(u.edt_dsg_tl / 1000, 1) : "—"} <span className="birim">bin TL</span></td>
                          <td>{u.netlesme_farki_tl != null ? sayiTr(u.netlesme_farki_tl / 1000, 1) : "—"} <span className="birim">bin TL</span></td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="soluk" style={{ fontSize: 13, margin: "6px 0 0" }}>DSG içinde EDT, santralde kalan kısım ile grubun net tutarından alınan payın toplamıdır. Fark, DSG içindeki tutar ile tek başına tutar arasındaki farktır; eksi tutar santralin ödediği tutardır. Santrallerin toplamı grup toplamına eşittir. Bu hesap varsayımsaldır; EPİAŞ uzlaştırma sonucu değildir.</p>
              </details>
            )}
            {dsg.gosterge === false && ((dsg.disi?.length ?? 0) > 0 || (dsg.segment_yok?.length ?? 0) > 0) && (
              <p className="soluk" style={{ fontSize: 13.5, margin: "0 0 8px" }}>
                {(dsg.disi?.length ?? 0) > 0 && `DSG kapsamı dışındaki santraller, dengesizliğini kendisi taşımayanlar: ${dsg.disi!.join(", ")}. `}
                {(dsg.segment_yok?.length ?? 0) > 0 && `Segmenti seçilmemiş santraller, lisanslı güneş varsayıldı ve KÜPST hesaplanamadı; Santralim › Santral ayarlarından seçilir: ${dsg.segment_yok!.join(", ")}.`}
              </p>
            )}
            <p className="soluk" style={{ fontSize: 14, margin: 0 }}>{dsg.not}</p>
          </>
        )}
      </Kart>
      {/* v2.511 (04 #14): toplayıcı/GTŞ portföyü — dağıtıma bağlı lisanssız santrallerin KÜPST'si UEVÇB bazında (DUY m.69(11), m.110(6)(b)(3);
          Karar 14907 0,25 / 0,01, 1.11.2026'dan). Santrallere dağılım mevzuatta tanımsız → kullanıcı anahtarı, etiketli. */}
      {kupst && kupst.santral > 0 && (
        <Kart baslik="Toplayıcı / görevli tedarik şirketi portföyü — KGÜP sapma tutarı (KÜPST), uzlaştırmaya esas veriş çekiş birimi bazında"
          sag={<span className="cip" title={kupst.fiyat.senaryo_saat > 0 ? "Senaryo fiyatı: EPİAŞ piyasa fiyatı bağlı olmadığından EPDK yıllık ortalaması kullanılmıştır." : "Saatlik PTF ve SMF EPİAŞ verisinden alınır."}><Meta items={[`son ${sayiTr(kupst.pencere_gun)} gün`, kupst.fiyat.senaryo_saat > 0 ? "senaryo fiyatı" : "piyasa fiyatı (EPİAŞ)", kupstD === "bekliyor" && "güncelleniyor", kupstD === "hata" && "güncellenemedi"]} /></span>}>
          {kupst.uevcbler.length === 0 ? <p className="soluk" style={{ margin: 0 }}>{kupst.not === "ortak saat yetersiz" ? "Santrallerin ölçüm saati henüz yeterli değil; en az 24 saat gerekir." : kupst.not}</p> : (
            <>
              <div className="ızgara satir-3" style={{ marginBottom: 10 }}>
                <Kpi etiket="KGÜP sapma tutarı · KÜPST, birim toplamı" bilgi="Dağıtım sistemine bağlı lisanssız santrallerde KÜPST santralin kendisinde değil, görevli tedarik şirketi ya da toplayıcı adına açılan uzlaştırmaya esas veriş çekiş biriminde hesaplanır; birimdeki santrallerin programı ve üretimi toplanır, sapma brüt alınır." deger={kupst.kupst_toplam_tl != null ? sayiTr(kupst.kupst_toplam_tl / 1000, 1) : "—"} birim={kupst.kupst_toplam_tl != null ? "bin TL" : undefined} alt={kupst.kupst_toplam_tl != null ? `${sayiTr(kupst.uevcbler.length)} birim · ${sayiTr(kupst.santral)} santral` : "1.11.2026 öncesi katsayı belirsiz; hesaplanmadı"} />
                <Kpi etiket="Tolerans üstü sapma" bilgi="Birim toplamında |üretim − program| toplamından toleransın (programın %25'i) düşülmüş kısmı; KÜPST bu miktar üzerinden hesaplanır." deger={sayiTr(kupst.uevcbler.reduce((a, u) => a + (u.kupsm_mwh ?? 0), 0), 1)} birim="MWh" alt={`brüt sapma ${sayiTr(kupst.uevcbler.reduce((a, u) => a + (u.udups_mwh ?? 0), 0), 1)} MWh`} />
                <Kpi etiket="Kural" bilgi={kupst.uevcbler[0]?.kural_dayanak ?? ""} deger="0,25 / 0,01" alt="tolerans / fiyat katsayısı · Karar 14907 · 1.11.2026'dan" />
              </div>
              {kupst.uevcbler.map((u) => (
                <details key={u.kod} className="aciklama genis" style={{ marginBottom: 10 }}>
                  <summary>{u.kod_tanimsiz ? "UEVÇB kodu girilmedi (tek birim varsayıldı)" : `UEVÇB ${u.kod}`} — {u.santraller.length} santral · {u.kupst_tl != null ? `${sayiTr(u.kupst_tl / 1000, 1)} bin TL` : "hesaplanamadı"} — santrallere dağılım {kupst.dagitim_etiket}</summary>
                  <div style={{ display: "flex", margin: "8px 0", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                    <label className="soluk" htmlFor={`kupst-anahtar-${u.kod}`}>Dağıtım anahtarı<Bilgi metin="Birimin KÜPST'si santrallere bu anahtarla paylaştırılır. Mevzuatta bir anahtar tanımlı değildir; paylaşım sözleşmeye bağlıdır ve seçilen anahtar bir hak doğurmaz. Sapma payına göre: |üretim − program| oranı. Üretim payına göre: gerçekleşen üretim oranı. Kurulu güç payına göre: kurulu güç oranı. Eşit: her santrale aynı pay." /></label>
                    <select id={`kupst-anahtar-${u.kod}`} className="girdi" value={kAnahtar} onChange={(e) => setKAnahtar(e.target.value as PortfoyAnahtar)} aria-label="KÜPST santrallere dağılım anahtarı">
                      <option value="sapma">sapma payına göre</option>
                      <option value="uretim">üretim payına göre</option>
                      <option value="kurulu">kurulu güç payına göre</option>
                      <option value="esit">eşit</option>
                    </select>
                    <span className="rozet rozet-notr rozet-kucuk" title={kupst.etiket}>mevzuatta tanımsız · sözleşmeye bağlı</span>
                  </div>
                  {u.uyeler && (
                    <div style={{ overflowX: "auto" }}>
                      <table className="veri" style={{ fontSize: 13.5 }}>
                        <thead><tr><th>Santral</th><th>Kurulu güç (MW)</th><th>Üretim (MWh)</th><th>Sapma (MWh)</th><th>Pay</th><th>KÜPST payı</th></tr></thead>
                        <tbody>
                          {Object.entries(u.uyeler).map(([ad, m]) => (
                            <tr key={ad}><td>{ad}</td><td>{sayiTr(m.kurulu_mw, 2)}</td><td>{sayiTr(m.uretim_mwh, 1)}</td><td>{sayiTr(m.sapma_mwh, 1)}</td><td>%{sayiTr(m.pay_pct, 1)}</td>
                              <td>{m.kupst_tl != null ? sayiTr(m.kupst_tl / 1000, 1) : "—"} <span className="birim">bin TL</span></td></tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <p className="soluk" style={{ fontSize: 13, margin: "6px 0 0" }}>Birim toplamı: brüt sapma {sayiTr(u.udups_mwh ?? 0, 1)} MWh, tolerans üstü {sayiTr(u.kupsm_mwh ?? 0, 1)} MWh, {sayiTr(u.n_saat)} saat{(u.hesaplanamayan_saat ?? 0) > 0 ? `, ${sayiTr(u.hesaplanamayan_saat ?? 0)} saat hesaplanamadı (1.11.2026 öncesi katsayı belirsiz)` : ""}. Santral paylarının toplamı birim toplamına eşittir.</p>
                </details>
              ))}
              <p className="soluk" style={{ fontSize: 14, margin: 0 }}>{kupst.not}</p>
            </>
          )}
        </Kart>
      )}
      {/* 26.10 Faz 6: Dış erişim, Kuruluşlar arası paylaşım, Hesap ve ekip, Santral arşivi → «Kuruluş» sayfası (Kurulus.tsx) */}
    </Sayfa>
  );
}

/** 24.10 — başarısız GET'in KISA hafızası (15 sn, yalnız Portföy'ün üç çekirdek isteği): getir 500'ü belleğe almaz, bu
 *  yüzden canlıda 500 dönen /portfoy/tahmin her Portföy açılışında (hızlı ardışık geçişlerde de) yeniden gidiyordu.
 *  Yakın zamanda başarısız olduysa kart hemen «sunucu hatası» der; 15 sn sonra yeniden denenir. Başarı kaydı siler. */
const sonHata = new Map<string, number>();
function hatirlayarak<T>(yol: string, fn: () => Promise<T>): Promise<T> {
  const t = sonHata.get(yol);
  const soz = t !== undefined && Date.now() - t < 15_000
    ? Promise.reject(new Error(`yakın zamanda başarısız: ${yol}`))
    : fn().then((v) => { sonHata.delete(yol); return v; }, (e: unknown) => { sonHata.set(yol, Date.now()); throw e; });
  // işleyiciler effect'te (bir mikro görev sonra) bağlanır; atılan render'da hiç bağlanmaz → «işlenmemiş ret» olmasın
  soz.catch(() => {});
  return soz;
}

/* 24.10 Faz 2: GelenTalepler (vitrin başvuruları) PLATFORM yüzüne taşındı (/yonetim → Başvurular); müşteri panelinde yeri yok. */
