import { useEffect, useMemo, useState } from "react";
import { useDamgaSurumu } from "../../shell/damgaOlay";
import type { EChartsOption } from "echarts";
import { api, bellekten, ayniysaEskisi } from "../../api/client";
import type { Karne, HataDagilimi, KonformalAyar, Backtest, Dengesizlik, DengesizlikGeriTest, DengesizlikSaatlik, Guvenilirlik, Yekdem } from "../../api/types";
import { EChart } from "../../lib/EChart";
import { useTema } from "../../lib/useTema";
import { BilgiliEtiket, Kpi, Kart, Sayfa, sayiTr, SayfaIskeleti, YerTutucu } from "./parcalar";
import { Meta } from "../../lib/Meta";

const AY = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
            "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"];
// 23.10 yedinci tur: geçersiz tarih (örnek kipte günlük satırlar «15 Nis» etiketli) «NaN undefined» basıyordu —
// çözümlenemeyen tarihte tire; çağıran taraf önce geçerli sınır tarihe düşer.
const tarihGecerli = (s: string | null | undefined): s is string =>
  !!s && !Number.isNaN(new Date(s).getTime());
const donemYaz = (a: string | null, b: string | null) => {
  if (!tarihGecerli(a) || !tarihGecerli(b)) return "—";
  const x = new Date(a), y = new Date(b);
  return x.getMonth() === y.getMonth()
    ? `${x.getDate()} – ${y.getDate()} ${AY[y.getMonth()]} ${y.getFullYear()}`
    : `${x.getDate()} ${AY[x.getMonth()]} – ${y.getDate()} ${AY[y.getMonth()]} ${y.getFullYear()}`;
};

/** 29.10 — her TL alanının yanındaki kaynak/kural etiketi (F_PRD §4.1: etiketsiz TL yok). */
/** v2.517 (P2a, B12): saatlik uzlaştırma dökümü — kart açılınca son 48 satır önizlenir; CSV (Türkçe Excel) ve XLSX (Saatlik + Aylar) indirilir.
 *  Yeniden hesaptır; EPİAŞ uzlaştırma sonucu değildir. */
function SaatlikDokum({ plantId, gun }: { plantId: string; gun: number }) {
  const [sd, setSd] = useState<DengesizlikSaatlik | null | undefined>(undefined);
  const [mesaj, setMesaj] = useState<string | null>(null);
  const indir = (fmt: "csv" | "xlsx") => { setMesaj(null); api.dengesizlikSaatlikIndir(plantId, fmt, gun).catch((e) => setMesaj(String((e as Error).message ?? e))); };
  const say = (v: string | number | null | undefined, hane = 2) => (v == null || v === "" ? "—" : typeof v === "number" ? sayiTr(v, hane) : String(v));
  // dil: API kodları müşteri diline (sistem yönü ve saat durumu); sözlükte olmayan kod olduğu gibi
  const YON: Record<string, string> = { acik: "enerji açığı", fazla: "enerji fazlası", dengede: "dengede" };
  const DURUM: Record<string, string> = { ok: "hesaplandı", yon_eksik: "sistem yönü verisi eksik", kupst_hesaplanamaz: "KÜPST katsayısı yok" };
  const kod = (v: string | number | null | undefined, s: Record<string, string>) => (v == null || v === "" ? "—" : (s[String(v)] ?? String(v)));
  // v2.520 (P5a): lisanslı YEKDEM'de uç dört sütun daha döner — YEK fiyatı, m.23(6) işareti, YEKDEM dışı MWh ve fark tutarı
  const yekdemli = !!sd && sd.kolonlar.includes("m23_6");
  const M23: Record<string, string> = { evet: "YEKDEM dışı", hayir: "—", ptf_yek_ustu: "PTF ≥ YEK fiyatı", fiyat_yok: "fiyat yok", kapsam_disi: "kapsam dışı" };
  return (
    <details className="aciklama genis" style={{ marginTop: 10 }} onToggle={(e) => { if ((e.currentTarget as HTMLDetailsElement).open && sd === undefined) api.dengesizlikSaatlik(plantId, gun).then((v) => setSd(v), () => setSd(null)); }}>
      <summary>Saatlik döküm — program, gerçekleşen, fiyat, yön, EDT ve KÜPST saat saat; CSV / XLSX</summary>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", margin: "8px 0" }}>
        <button className="dugme kucuk" onClick={() => indir("csv")}>CSV indir</button>
        <button className="dugme kucuk" onClick={() => indir("xlsx")}>XLSX indir</button>
        {sd && <span className="soluk" style={{ fontSize: 13 }}>{sayiTr(sd.satir)} saat; son {sayiTr(sd.satirlar.length)} satır aşağıda{sd.program ? `; ${sayiTr(sd.program.bildirilen_saat)} saat bildirilen program` : ""}</span>}
        {mesaj && <span className="ayar-durum hata">{mesaj}</span>}
      </div>
      {sd === undefined ? <p className="soluk">Yükleniyor…</p> : sd === null ? <p className="soluk">Döküm alınamadı.</p> : sd.satirlar.length === 0 ? <p className="soluk">Henüz karşılaştırılan saat yok.</p> : (
        <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 13 }}>
          <thead><tr><th>Saat</th><th>Program (MWh)</th><th>Kaynak</th><th>Gerçekleşen (MWh)</th><th>Sapma (MWh)</th><th>PTF (TL/MWh)</th><th>SMF (TL/MWh)</th><th>Yön</th><th>EDT borç (TL)</th><th>EDT alacak (TL)</th><th title="KGÜP sapma miktarı: toleransın (m × program) üstündeki sapma">KÜPSM (MWh)</th><th title="KGÜP sapma tutarı">KÜPST (TL)</th>{yekdemli && <><th title="O saatin YEK fiyatı (+ yerli katkı)">YEK fiyatı (TL/MWh)</th><th title="YEK Yön. m.23(6): düşük fiyat ve sistem fazlası saatinde program üstü üretim; EPİAŞ uygulaması belirsiz">m.23(6)</th><th>YEKDEM dışı (MWh)</th><th title="YEKDEM dışı MWh × (YEK fiyatı − 0,98 × PTF)">Fark (TL)</th></>}<th>Durum</th></tr></thead>
          <tbody className="mono">{sd.satirlar.map((r, i) => (
            <tr key={i}><td>{say(r.zaman)}</td><td>{say(r.program_mwh, 3)}</td><td>{r.program_kaynak === "bildirilen" ? <span className="rozet rozet-ok rozet-kucuk">bildirilen</span> : "öneri"}</td>
              <td>{say(r.gerceklesen_mwh, 3)}</td><td>{say(r.sapma_mwh, 3)}</td><td>{say(r.ptf_tl_mwh)}</td><td>{say(r.smf_tl_mwh)}</td><td>{kod(r.yon, YON)}</td>
              <td>{say(r.edt_borc_tl)}</td><td>{say(r.edt_alacak_tl)}</td><td>{say(r.kupsm_mwh, 3)}</td><td>{say(r.kupst_tl)}</td>
              {yekdemli && <><td>{say(r.yek_fiyat_tl_mwh)}</td><td>{r.m23_6 === "evet" ? <span className="rozet rozet-uyari rozet-kucuk">YEKDEM dışı</span> : kod(r.m23_6, M23)}</td><td>{say(r.yekdem_disi_mwh, 3)}</td><td>{say(r.yekdem_disi_tl)}</td></>}
              <td>{r.durum === "ok" ? DURUM.ok : <span className="rozet rozet-uyari rozet-kucuk">{kod(r.durum, DURUM)}</span>}</td></tr>))}</tbody>
        </table></div>)}
      {sd && <p className="soluk" style={{ fontSize: 13, margin: "6px 0 0" }}>Yeniden hesaptır; EPİAŞ uzlaştırma sonucu değildir. Kaynak «bildirilen»: TPYS'ye bildirdiğinizi beyan ederek yüklediğiniz KGÜP (TPYS kabulü doğrulanmaz); «öneri»: PVQuant'ın bir gün önce 15:30'dan önceki son tahmininin P50'si. Sapma = gerçekleşen − pozisyon; KÜPSM = toleransı (m × program) aşan sapma miktarı; EDT alacak düşük fiyat saatinde eksi olabilir. Saatler Türkiye saatidir; indirilen dosyada {sayiTr(sd.kolonlar.length)} sütunun tümü ve bu not yer alır.{yekdemli && " YEKDEM sütunları: YEK fiyatı o saatin fiyatı (+ yerli katkı); m.23(6) «YEKDEM dışı» = PTF ya da SMF taban değerin altında ve sistem fazlası saatinde program üstü üretim, PTF < YEK fiyatı (EPİAŞ uygulaması belirsiz; talimat saatleri sayılmadı)."}</p>}
    </details>
  );
}

/** v2.520 (P5a): YEKDEM katmanı — fiyat rejimi (işletmeye giriş tarihinden), bugünün YEK fiyatı (Cetvel I: ¢ × günün TCMB kuru; 7189: ayın EPİAŞ
 *  ilanı + yerli katkı, USD band konumu) ve YEK Yön. m.23(6) saat işareti (belirsiz). Yalnız lisanslı YEKDEM segmentinde çizilir; yeniden hesaptır. */
function YekdemKarti({ plantId, gun }: { plantId: string; gun: number }) {
  const [yk, setYk] = useState<Yekdem | null | undefined>(undefined);
  useEffect(() => { let acik = true; setYk(undefined); api.yekdem(plantId, gun).then((v) => { if (acik) setYk(v); }); return () => { acik = false; }; }, [plantId, gun]);
  const BANT: Record<string, string> = { icinde: "sınırlar içinde", tabanda: "alt sınırda (kırpma)", tavanda: "üst sınırda (kırpma)", kur_yok: "kur verisi yok" };
  const AYAD = (ay: string) => { const [y, m] = ay.split("-").map(Number); return `${AY[m - 1]} ${y}`; };
  // «2026-10-20 11:00» (uçtan, Türkiye saati) → «20 Eki 2026 11:00»
  const saatTr = (v: string | null) => { if (!v) return "—"; const [g, h] = v.split(" "); const d = new Date(g); return Number.isNaN(d.getTime()) ? v : `${d.getDate()} ${AY[d.getMonth()].slice(0, 3)} ${d.getFullYear()} ${h}`; };
  const sol = { textAlign: "left" as const };
  const rejimAlt = (r: Yekdem["rejim"]) => r.kaynak_turu === "hesaplanan" ? `işletmeye giriş ${r.isletmeye_giris ? new Date(r.isletmeye_giris).toLocaleDateString("tr-TR") : "—"} tarihinden`
    : r.kaynak_turu === "kullanici" ? "Santral ayarları › Satış tarifesi'nde seçildi" : "işletmeye giriş tarihi girilmedi; Takvim › Santral tarihleri";
  return (
    <Kart baslik="YEKDEM — fiyat rejimi, günlük YEK fiyatı ve m.23(6) saatleri"
      sag={<span className="cip">{yk ? <Meta items={[yk.rejim.etiket, `${sayiTr(yk.pencere_gun)} gün`]} /> : yk === null ? "alınamadı" : "hesaplanıyor"}</span>}>
      {yk === undefined ? <YerTutucu yukseklik={220} /> : yk === null ? <p className="soluk" style={{ margin: 0 }}>YEKDEM bilgisi alınamadı.</p> : (
        <>
          <div className="ızgara satir-4" style={{ marginBottom: 12 }}>
            <Kpi etiket="Fiyat rejimi" deger={yk.rejim.rejim === "cetvel1" ? "Cetvel I" : yk.rejim.rejim === "7189" ? "7189 sayılı CK" : "belirsiz"} ton={yk.rejim.rejim ? undefined : "uyari"}
              alt={yk.rejim.rejim === "cetvel1" ? `ABD senti/kWh × günün TCMB alış kuru; ${rejimAlt(yk.rejim)}` : yk.rejim.rejim === "7189" ? `TL fiyat, aylık EPİAŞ ilanı; ${rejimAlt(yk.rejim)}` : yk.rejim.kaynak} />
            <Kpi etiket={`YEK fiyatı (${yk.fiyat ? new Date(yk.fiyat.gun).toLocaleDateString("tr-TR") : "bugün"})`} deger={yk.fiyat?.toplam_tl_mwh != null ? sayiTr(yk.fiyat.toplam_tl_mwh, 0) : "—"} birim="TL/MWh"
              ton={yk.fiyat?.toplam_tl_mwh != null ? undefined : "uyari"}
              alt={yk.fiyat?.toplam_tl_mwh != null ? `${yk.fiyat.kaynak_etiket}${yk.fiyat.yerli_tl_mwh ? `; yerli katkı ${sayiTr(yk.fiyat.yerli_tl_mwh, 0)} TL/MWh dâhil` : ""}` : yk.fiyat ? yk.fiyat.kaynak_etiket : "rejim belirsiz; fiyat hesaplanmaz"} />
            {yk.rejim.rejim === "cetvel1"
              ? <Kpi etiket="TCMB alış kuru" deger={yk.fiyat?.kur != null ? sayiTr(yk.fiyat.kur, 4) : "—"} birim="TL/USD"
                  alt={yk.fiyat?.kur_gunu ? `${new Date(yk.fiyat.kur_gunu).toLocaleDateString("tr-TR")} bülteni${yk.fiyat.onceki_gun ? " (önceki iş günü; tatil/hafta sonu)" : ""}; ${sayiTr(yk.sabitler.cetvel1_cent, 1)} ¢/kWh` : yk.kur?.son_gun ? `arşivde son bülten ${new Date(yk.kur.son_gun).toLocaleDateString("tr-TR")}` : "kur arşivi boş"} />
              : <Kpi etiket="Aylık ilan" deger={yk.fiyat?.ay_fiyat_kr_kwh != null ? sayiTr(yk.fiyat.ay_fiyat_kr_kwh, 2) : "—"} birim="kr/kWh"
                  alt={(() => { const son = [...yk.aylar].reverse().find((a) => a.durum === "ilan"); return son ? `son ilan ${AYAD(son.ay)}${son.bant ? `; USD sınır kontrolü: ${BANT[son.bant.durum] ?? son.bant.durum}${son.bant.usd_cent != null ? ` (${sayiTr(son.bant.usd_cent, 2)} ¢/kWh)` : ""}` : ""}` : "ilan yok"; })()} />}
            <Kpi etiket="YEKDEM dışı üretim (m.23(6))" deger={yk.m23_6 ? sayiTr(yk.m23_6.yekdem_disi_mwh, 1) : "—"} birim="MWh" ton={yk.m23_6 && yk.m23_6.saat > 0 ? "uyari" : undefined}
              alt={yk.m23_6 ? `${sayiTr(yk.m23_6.saat)} saat; fark ${sayiTr(yk.m23_6.yekdem_disi_tl / 1000, 1)} bin TL; EPİAŞ uygulaması belirsiz` : yk.uygulanir ? "tarife YEKDEM seçilmedi" : "segment lisanslı YEKDEM değil"} />
          </div>
          {yk.rejim.rejim === "7189" && yk.aylar.length > 0 && (
            <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 13 }}>
              <thead><tr><th style={sol}>Ay</th><th>Fiyat (kr/kWh)</th><th>Yerli katkı (kr/kWh)</th><th title="Bir önceki ayın ortalama TCMB USD alış kuruyla">USD karşılığı (¢/kWh)</th><th style={sol} title="7189 sayılı CK: fiyat, bir önceki ayın ortalama TCMB USD alış kuruyla ¢/kWh'a çevrilip alt–üst sınıra kırpılır">USD sınır kontrolü ({sayiTr(yk.sabitler.bant_cent[0], 2)}–{sayiTr(yk.sabitler.bant_cent[1], 2)} ¢)</th><th style={sol}>Kaynak</th></tr></thead>
              <tbody>{yk.aylar.map((a) => (
                <tr key={a.ay}><td style={sol}>{AYAD(a.ay)}</td><td className="mono">{a.fiyat_kr_kwh != null ? sayiTr(a.fiyat_kr_kwh, 2) : "—"}</td><td className="mono">{a.yerli_katki_kr_kwh != null ? sayiTr(a.yerli_katki_kr_kwh, 2) : "—"}</td>
                  <td className="mono">{a.bant?.usd_cent != null ? sayiTr(a.bant.usd_cent, 2) : "—"}</td>
                  <td style={sol}>{a.durum !== "ilan" ? <span className="soluk">henüz ilan edilmedi</span> : a.bant && a.bant.durum !== "kur_yok" ? <span className={`rozet rozet-kucuk ${a.bant.durum === "icinde" ? "rozet-ok" : "rozet-uyari"}`} title={`${AYAD(a.bant.kur_ayi)} ortalama USD alış kuru ${sayiTr(a.bant.kur_ortalama ?? 0, 4)} TL`}>{BANT[a.bant.durum]}</span> : <span className="soluk">{a.bant ? `${AYAD(a.bant.kur_ayi)} kuru arşivde yok; kontrol yapılamadı` : "kur verisi yok"}</span>}</td>
                  <td style={{ ...sol, whiteSpace: "normal", minWidth: 220 }}>{a.kaynak ?? "—"}</td></tr>))}</tbody>
            </table></div>)}
          {yk.m23_6 && yk.m23_6.saat > 0 && <p style={{ margin: "10px 0 0", fontSize: 13.5 }}>
            Son {sayiTr(yk.m23_6.pencere_gun)} günde {sayiTr(yk.m23_6.saat)} saatte program üstü üretim YEKDEM dışı sayıldı: {sayiTr(yk.m23_6.yekdem_disi_mwh, 1)} MWh, fark {sayiTr(yk.m23_6.yekdem_disi_tl)} TL (ilk {saatTr(yk.m23_6.ilk_saat)}, son {saatTr(yk.m23_6.son_saat)}).
            {yk.m23_6.bildirilmemis_saat > 0 && <> Bu saatlerin {sayiTr(yk.m23_6.bildirilmemis_saat)} tanesinde bildirilen KGÜP yoktu; PVQuant önerisi program sayıldı.</>}
            {/* v2.532 (DK-301): KGÜP = 0 okuması sayıyla — dosya yüklenmedi ≠ EPİAŞ'a bildirilmedi; iki okuma yan yana */}
            {(yk.m23_6.kgup0_saat ?? 0) > 0 && <> Bildirilen KGÜP yüklenmemiş saatlerde KGÜP hiç bildirilmediyse mevzuat KGÜP'ü 0 sayar: o okumayla {sayiTr(yk.m23_6.kgup0_saat ?? 0)} saatte üretimin tamamı ({sayiTr(yk.m23_6.kgup0_mwh ?? 0, 1)} MWh, fark {sayiTr(yk.m23_6.kgup0_tl ?? 0)} TL) YEKDEM dışı kalır; bildirdiyseniz dosyayı yükleyin, hesap ona göre yapılır.</>}
          </p>}
          <p className="soluk" style={{ margin: "8px 0 0", fontSize: 13 }}>
            {yk.not ? yk.not + " " : ""}Yeniden hesaptır; EPİAŞ YEKDEM uzlaştırması değildir.
          </p>
          <details className="aciklama">
            <summary>m.23(6) dayanağı ve hesap yöntemi</summary>
            <p style={{ margin: "6px 0 0" }}>{yk.m23_6 ? yk.m23_6.not : "m.23(6) işareti yalnız lisanslı YEKDEM segmentinde ve satış tarifesi YEKDEM seçiliyken üretilir. YEK Yön. m.23(6) (RG 19.10.2026-8): PTF ya da SMF taban değerin (V) altında ve sistem yönü enerji fazlası olan saatte programın üstündeki üretim, PTF o saatin YEK fiyatından düşükse YEKDEM dışında kalır."}</p>
          </details>
        </>)}
    </Kart>
  );
}

function fiyatEtiketi(dz: Dengesizlik): string {
  const yon = (dz.fiyat.yon_eksik_saat ?? 0) > 0 ? ` · ${sayiTr(dz.fiyat.yon_eksik_saat ?? 0)} saatte sistem yönü verisi yok` : "";
  return dz.fiyat.senaryo_saat > 0
    ? `senaryo fiyatı (${sayiTr(dz.fiyat.senaryo_saat)} saat) · sistem yönü dengede varsayıldı${yon}`
    : `EPİAŞ saatlik fiyat ve sistem yönü ile${yon}`;
}
function kupstEtiketi(dz: Dengesizlik): string {
  if (dz.toplam?.kupst_tl == null) {
    if (!dz.segment.segment) return "segment seçilmedi; hesaplanamaz";
    if (dz.segment.segment === "lisanssiz_dagitim") return "tedarikçi/toplayıcı portföyünde hesaplanır";
    return "katsayı doğrulanamadı; hesaplanamaz";
  }
  const k = dz.kural; const p = dz.program;
  // v2.532 (DK-180/195): net sapmada UEÇM kaynağı açıkça — sayaç çekişi yoksa «0 varsayıldı» (net sapma = brüt sapma)
  const uecm = k?.kupst_net_sapma ? (p?.uecm_saat ? `; UEÇM ${sayiTr(p.uecm_saat)} saatte sayaç çekişinden` : "; UEÇM verisi yok, 0 varsayıldı") : "";
  return k && k.kupst_m != null && k.kupst_n != null
    ? `tolerans %${sayiTr(k.kupst_m * 100, 0)} · katsayı n ${sayiTr(k.kupst_n, 2)} · ${k.kupst_net_sapma ? `net sapma (Karar 14907${uecm})` : "brüt sapma"}`
    : "kural tablosundan";
}

export function Dogruluk({ plantId }: { plantId: string }) {
  const ds = useDamgaSurumu();   // 26.10 eşzamanlama
  // 24.10 açık tema geçiş turu — YEDİ İSTEK BAĞIMSIZ, BAYAT-ÖNCE (Portföy kalıbı, v2.476). v2.326'nın tek kapısı sayfayı en
  // yavaş isteğe (geriye dönük sınav, güvenilirlik) bekletiyor; her dönüşte 60 sn dolunca iskelet geliyordu. Şimdi: karne
  // (iki kova) gelir gelmez başlık + KPI'lar; her kart kendi yanıtını boyutlu yer tutucuyla bekler (kayma yok); bellekte son
  // karne varsa sayfa onunla ANINDA çizilir, çip «güncelleniyor» der. undefined = henüz bilinmiyor, null = yok/alınamadı.
  // Değerler ve hesaplar aynı; yalnız bekleme biçimi değişti.
  const [donem, setDonem] = useState<30 | 60 | 90>(60);
  type Durum = "bekliyor" | "tamam" | "hata";
  const [k, setK] = useState<Karne | null | undefined>(() => bellekten.karne(plantId, 60));
  const [kD, setKD] = useState<Durum>("bekliyor");
  const [hd, setHd] = useState<HataDagilimi | null | undefined>(undefined);
  const { n, oku } = useTema();
  const [kf, setKf] = useState<KonformalAyar | undefined>(undefined);   // v2.252
  const [bt, setBt] = useState<Backtest | null | undefined>(undefined);   // v2.253
  const [dz, setDz] = useState<Dengesizlik | null | undefined>(undefined);   // v2.259
  const [gv, setGv] = useState<Guvenilirlik | null | undefined>(undefined);   // v2.271
  const [gt, setGt] = useState<DengesizlikGeriTest | null | undefined>(undefined);   // v2.503 (F-07): 12 ay geri test, kart açılınca
  // Dönem segmenti yalnız karneyi tazeler (v2.230 kararı korunur); santral değişince hepsi yeniden kurulur.
  useEffect(() => {
    let acik = true;
    setK(bellekten.karne(plantId, donem)); setKD("bekliyor");
    setHd(undefined); setKf(undefined); setBt(undefined); setDz(undefined); setGv(undefined); setGt(undefined);
    // Denendi, alınmadı (24.10, perf/analiz/acik-tema/deney): yanıt yazımlarını startTransition'a almak 4× CPU'da «tam»
    // süresini uzattı (sıcak 211 → 471 ms); düz setState kaldı.
    api.karne(plantId, donem).then((v) => { if (acik) { setK((e) => ayniysaEskisi(e, v)); setKD("tamam"); } }, () => { if (acik) { setK((e) => e ?? null); setKD("hata"); } });
    api.konformal(plantId).then((v) => { if (acik) setKf(v); }, () => { if (acik) setKf({ aktif: false }); });
    api.dengesizlik(plantId).then((v) => { if (acik) setDz(v); }, () => { if (acik) setDz(null); });
    api.backtest(plantId).then((v) => { if (acik) setBt(v); }, () => { if (acik) setBt(null); });
    api.guvenilirlik(plantId).then((v) => { if (acik) setGv(v); }, () => { if (acik) setGv(null); });
    api.hataDagilimi(plantId).then((v) => { if (acik) setHd(v); }, () => { if (acik) setHd(null); });
    return () => { acik = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- donem bilerek dışarıda: istekler yalnız santral (ya da damga) değişince kurulur
  }, [plantId, ds]);
  const [ilkDonem, setIlkDonem] = useState(true);
  useEffect(() => {
    if (ilkDonem) { setIlkDonem(false); return; }   // ilk değer kapıda çekildi
    api.karne(plantId, donem).then(setK);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [donem]);
  // v2.271: güvenilirlik diyagramı — x nominal τ, y gözlenen P(y ≤ q_τ); köşegen ideal. Ham ince/soluk, kalibre kalın mavi.
  const gvOption = useMemo<EChartsOption | null>(() => {
    if (!gv || gv.durum !== "ok" || !gv.guvenilirlik) return null;
    const kenar = oku("--kenar"), soluk = oku("--soluk"), mono = oku("--mono"), mavi = oku("--chart-p50-future");
    const seri = (ad: string, rows: { tau: number; gozlenen: number }[], renk: string, kalin: number) => ({
      name: ad, type: "line" as const, data: rows.map((r) => [r.tau, r.gozlenen]), symbol: "circle", symbolSize: 8,
      lineStyle: { color: renk, width: kalin }, itemStyle: { color: renk } });
    return {
      animation: false, grid: { left: 44, right: 12, top: 26, bottom: 34 },
      legend: { top: 0, right: 0, textStyle: { color: soluk, fontSize: 13 }, itemWidth: 14 },
      tooltip: { trigger: "axis", backgroundColor: oku("--kart"), borderColor: kenar, borderWidth: 0.5, textStyle: { color: oku("--metin"), fontSize: 13 },
        valueFormatter: (v: unknown) => `%${sayiTr(Number(v) * 100, 0)}` },
      xAxis: { type: "value", min: 0, max: 1, name: "nominal", nameTextStyle: { color: soluk, fontSize: 12 },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 12, formatter: (v: number) => `P${Math.round(v * 100)}` }, splitLine: { lineStyle: { color: oku("--izgara") } } },
      yAxis: { type: "value", min: 0, max: 1, name: "gözlenen", nameTextStyle: { color: soluk, fontSize: 12 },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 12, formatter: (v: number) => `%${Math.round(v * 100)}` }, splitLine: { lineStyle: { color: oku("--izgara") } } },
      series: [
        { name: "ideal", type: "line", data: [[0, 0], [1, 1]], symbol: "none", showSymbol: false, itemStyle: { color: soluk },
          lineStyle: { color: soluk, type: "dashed", width: 1 }, silent: true },
        seri("ham aralık", gv.guvenilirlik.ham, oku("--ch-dusuk"), 1.5),
        seri("ayarlı aralık", gv.guvenilirlik.kalibre, mavi, 2.5),
      ],
    };
  }, [gv, n, oku]);   // eslint-disable-line react-hooks/exhaustive-deps
  const pitOption = useMemo<EChartsOption | null>(() => {
    if (!gv || gv.durum !== "ok" || !gv.pit) return null;
    const soluk = oku("--soluk"), mono = oku("--mono");
    return {
      animation: false, grid: { left: 40, right: 12, top: 18, bottom: 30 },
      tooltip: { trigger: "axis", backgroundColor: oku("--kart"), borderColor: oku("--kenar"), borderWidth: 0.5, textStyle: { color: oku("--metin"), fontSize: 13 },
        valueFormatter: (v: unknown) => `%${sayiTr(Number(v) * 100, 0)}` },
      xAxis: { type: "category", data: gv.pit.map((p) => p.kutu), axisLabel: { color: soluk, fontFamily: mono, fontSize: 12, interval: 1 }, axisTick: { show: false } },
      yAxis: { type: "value", min: 0, axisLabel: { color: soluk, fontFamily: mono, fontSize: 12, formatter: (v: number) => `%${Math.round(v * 100)}` }, splitLine: { lineStyle: { color: oku("--izgara") } } },
      series: [{ type: "bar", data: gv.pit.map((p) => p.oran), itemStyle: { color: oku("--ch-cubuk") }, barMaxWidth: 26,
        markLine: { silent: true, symbol: "none", lineStyle: { color: soluk, type: "dashed" }, data: [{ yAxis: 0.1 }], label: { show: false } } }],
    };
  }, [gv, n, oku]);   // eslint-disable-line react-hooks/exhaustive-deps
  // v2.326: hataDagilimi tek kapının içinde çekiliyor (yukarıda). 04.11 v2.532: saat × gün hata haritası kaldırıldı; saat profili Kalibrasyon'da.

  // v2.225 (H "Rapor Dili"): Solargis grameri — gunluk degerler NOKTA,
  // 7 gun egilimi TEK kalin cizgi, naif INCE gri cizgi (alan degil).
  // Hiyerarsi: nokta < gri cizgi < egilim; ic ice cizgi karmasasi biter.
  const wmapePanel = useMemo(() => {
    const izgara = oku("--izgara"), soluk = oku("--soluk");
    const kenar = oku("--kenar"), mono = oku("--mono");
    const marka = oku("--marka"), dusuk = oku("--ch-dusuk");
    const markaKoyu = oku("--marka-koyu");
    const g = k?.gunluk ?? [];
    const tarihler = [...new Set(g.map((r) => r.tarih))].sort();
    const bul = (t: string, kova: string) =>
      g.find((r) => r.tarih === t && r.kova === kova);
    // 7 gun hareketli ortalama — pencerede en az 3 gercek deger yoksa "—"
    const ho7 = (xs: (number | null)[]) => xs.map((_, i) => {
      const p = xs.slice(Math.max(0, i - 6), i + 1)
        .filter((x): x is number => typeof x === "number");
      return p.length >= 3 ? p.reduce((a, b) => a + b, 0) / p.length : null;
    });
    return (kova: string): EChartsOption => {
      const gunluk = tarihler.map((t) => bul(t, kova)?.wmape ?? null);
      const naif = tarihler.map((t) => bul(t, kova)?.naif_wmape ?? null);
      const egilim = ho7(gunluk);
      const tepe = Math.max(10,
        ...gunluk.filter((v): v is number => v !== null),
        ...naif.filter((v): v is number => v !== null));
      const ymax = Math.min(100, Math.ceil((tepe * 1.12) / 10) * 10);
      let si = -1;
      egilim.forEach((v, i) => { if (v !== null) si = i; });
      return {
        grid: { left: 40, right: 14, top: 18, bottom: 26 }, animation: false,
        tooltip: { trigger: "axis", backgroundColor: oku("--kart"), borderColor: kenar,
          borderWidth: 0.5, textStyle: { color: oku("--metin"), fontSize: 13 },
          valueFormatter: (v: unknown) => (v == null ? "—" : `%${sayiTr(Number(v), 1)}`) },
        xAxis: { type: "category", data: tarihler, axisTick: { show: false },
          axisLine: { lineStyle: { color: kenar } },
          // v2.231: sabit 13 araligi 30g penceresinde tek etiket birakiyordu —
          // hedef ~4 etiket, pencereye gore olceklenir
          axisLabel: { color: soluk, fontFamily: mono, fontSize: 12,
            interval: Math.max(1, Math.ceil(tarihler.length / 4) - 1) } },
        yAxis: { type: "value", max: ymax, splitLine: { lineStyle: { color: izgara } },
          axisLine: { show: false },
          axisLabel: { color: soluk, fontFamily: mono, fontSize: 12,
                       formatter: (v: number) => `%${v}` } },
        series: [
          { name: "Referans tahmin", type: "line", symbol: "none", z: 1,
            lineStyle: { color: dusuk, width: 1.4 },
            data: naif, connectNulls: true },
          { name: "Günlük", type: "scatter", z: 2, symbolSize: 4.5,
            itemStyle: { color: marka, opacity: 0.42 }, data: gunluk },
          {
            name: "7 gün eğilimi", type: "line", symbol: "none", z: 3,
            lineStyle: { color: marka, width: 2.6, cap: "round", join: "round" },
            data: egilim, connectNulls: true,
            ...(si >= 0 ? { markPoint: {
              silent: true, symbol: "circle", symbolSize: 7,
              itemStyle: { color: marka, borderColor: oku("--kart"), borderWidth: 1.5 },
              label: { show: true, position: "top", distance: 6, color: markaKoyu,
                fontFamily: "monospace", fontSize: 12, fontWeight: "bold",
                formatter: () => `%${sayiTr(egilim[si] as number, 1)}` },
              data: [{ coord: [tarihler[si], egilim[si]] }],
            } } : {}),
          } as unknown as NonNullable<EChartsOption["series"]>,
        ] as EChartsOption["series"],
      };
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [k, n]);
  // 24.10: iki ufuk seçeneği MEMO — önceden wmapePanel("0-24") her render'da yeni nesne üretiyor, EChart her state
  // değişiminde (dönem, kart verisi gelişi) iki grafiği notMerge ile baştan kuruyordu. Seçenek yalnız karne/tema değişince değişir.
  const wmape024 = useMemo(() => wmapePanel("0-24"), [wmapePanel]);
  const wmape2472 = useMemo(() => wmapePanel("24-72"), [wmapePanel]);


  // v2.225 (H): cubuklar TAHMIN MAVISI (sapma tahminin urunudur; amber
  // yalniz gerceklesene ayrili), yesil egri kumulatif pay (sag eksen),
  // P10-P90 acik bant + duz medyan cizgisi (Solargis Fig 7.5 dili).
  // API p25/p75 vermez \u2014 ic bant cizilmez (tire ilkesinin alan hali).
  const dagOption = useMemo<EChartsOption>(() => {
    const kenar = oku("--kenar"), soluk = oku("--soluk"), mono = oku("--mono");
    const marka = oku("--marka"), markaKoyu = oku("--marka-koyu");
    const mavi = oku("--chart-p50-future");
    const kutular = hd?.kutular ?? [];
    // v2.232: TR sayi bicimi + bosluklu ayrac — "-1.5-–1" yigilmasi biter
    const ond = kutular.some((x) => !Number.isInteger(x.lo) || !Number.isInteger(x.hi)) ? 1 : 0;
    const etiket = kutular.map((x) => `${sayiTr(x.lo, ond)} \u2013 ${sayiTr(x.hi, ond)}`);
    const kutuGen = kutular.length ? kutular[0].hi - kutular[0].lo : 1;
    const xi = (v: number) => (v - (kutular[0]?.lo ?? 0)) / kutuGen - 0.5;
    const toplam = kutular.reduce((a, b) => a + b.adet, 0);
    let birikim = 0;
    const kdf = kutular.map((b) => {
      birikim += b.adet;
      return toplam ? Math.round((1000 * birikim) / toplam) / 10 : 0;
    });
    return {
      grid: { left: 46, right: 46, top: 24, bottom: 44 }, animation: false,
      tooltip: { trigger: "axis", backgroundColor: oku("--kart"), borderColor: kenar,
        borderWidth: 0.5, textStyle: { color: oku("--metin"), fontSize: 13 },
        valueFormatter: (v: unknown) => `${v}` },
      xAxis: [
        { type: "category", data: etiket, name: "MWh/g\u00fcn (tahmin \u2212 ger\u00e7ekle\u015fen)",
          nameLocation: "middle", nameGap: 26,
          nameTextStyle: { color: soluk, fontSize: 13 },
          axisTick: { show: false },
          axisLine: { lineStyle: { color: oku("--chart-baseline") || kenar } },
          axisLabel: { color: soluk, fontFamily: mono, fontSize: 13 } },
        // v2.232: KDF icin gizli deger ekseni — kutu KENARLARI (kumulatif pay
        // kutunun SONUNDA birikir; Solargis Fig 7.5 egriyi kenardan gecirir)
        { type: "value", min: -0.5, max: Math.max(0.5, kutular.length - 0.5),
          show: false },
      ],
      yAxis: [
        { type: "value", splitLine: { lineStyle: { color: oku("--izgara") } },
          axisLine: { show: false }, axisTick: { show: false },
          axisLabel: { color: soluk, fontFamily: mono, fontSize: 13 } },
        { type: "value", min: 0, max: 100, splitLine: { show: false },
          axisLine: { show: false }, axisTick: { show: false },
          axisLabel: { color: markaKoyu, fontFamily: mono, fontSize: 13,
                       formatter: (v: number) => `%${v}` } },
      ],
      series: [
        { name: "G\u00fcn say\u0131s\u0131", type: "bar", barWidth: "58%",
          data: kutular.map((b) => b.adet),
          itemStyle: { color: mavi, opacity: 0.88, borderRadius: [2, 2, 0, 0] },
          z: 2,
          markLine: hd?.p50 != null
            // v2.232: medyan etiketi dikeyken cubugun icinde kayboluyordu —
            // yatay, cizginin tepesinde (rotate 0, position end)
            ? { symbol: "none", animation: false, silent: true,
                data: [{ name: "medyan", xAxis: xi(hd.p50),
                  lineStyle: { color: soluk, type: "solid" as const, width: 1.4 },
                  label: { color: soluk, fontSize: 12, fontFamily: mono,
                    position: "end" as const, distance: 6, rotate: 0,
                    formatter: () => `medyan ${sayiTr(hd.p50 as number, 2)}` } }] as never }
            : undefined },
        // v2.235: P10/P90 sinirlari — gri BANT zemini ikiye boluyordu
        // (kullanici karari: zemin tek renk); ince kesikli cizgilere cevrildi,
        // degerler baslik cipinde. Sinir-koordinat dersi geregi deger ekseninde.
        ...(hd?.p10 != null && hd?.p90 != null
          ? [hd.p10, hd.p90].map((v) => ({
              name: "__sinir", type: "line" as const,
              xAxisIndex: 1, yAxisIndex: 1, z: 1,
              silent: true, symbol: "none",
              data: [[xi(v), 0], [xi(v), 100]],
              lineStyle: { color: soluk, type: [4, 4] as never, width: 1 },
              tooltip: { show: false } }))
          : []),
        // v2.234: sifir cizgisi — markLine kutu SINIRINDAKI kesirli koordinati
        // cizmedi (medyan kutu icinde cizilirken sinirdaki 2.5 sessizce dustu);
        // gizli deger ekseninde iki noktali seri kesin cizilir. Yalniz 0
        // pencere icindeyse.
        ...(kutular.length && kutular[0].lo <= 0 &&
            kutular[kutular.length - 1].hi >= 0
          ? [{ name: "__sifir", type: "line" as const,
               xAxisIndex: 1, yAxisIndex: 1, z: 1,
               silent: true, symbol: "none",
               data: [[xi(0), 0], [xi(0), 100]],
               lineStyle: { color: oku("--chart-baseline") || kenar,
                            type: "solid" as const, width: 1.6 },
               tooltip: { show: false } }]
          : []),
        { name: "Birikimli pay", type: "line", xAxisIndex: 1, yAxisIndex: 1, z: 3,
          symbol: "none",
          data: [[-0.5, 0], ...kdf.map((v, i) => [i + 0.5, v])],
          lineStyle: { color: marka, width: 2.2 } },
      ],
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hd, n]);

  // v2.225 (H): WMAPE delta cipi — API'de donem kiyasi yok; DURUST yol:
  // gunluk karneden son 30 gun vs onceki 30 gun ortalamasi TURETILIR.
  // Iki pencere de yeterince dolu degilse cip hic gorunmez (uydurma yok).
  const delta = useMemo(() => {
    const g = (k?.gunluk ?? []).filter(
      (r) => r.kova === "0-24" && typeof r.wmape === "number");
    const tarihler = [...new Set(g.map((r) => r.tarih))].sort();
    if (tarihler.length < 28) return null;
    const ort = (ts: string[]) => {
      const v = ts
        .map((t) => g.find((r) => r.tarih === t)?.wmape)
        .filter((x): x is number => typeof x === "number");
      return v.length >= 14 ? v.reduce((a, b) => a + b, 0) / v.length : null;
    };
    const son = ort(tarihler.slice(-30));
    const once = ort(tarihler.slice(-60, -30));
    if (son === null || once === null) return null;
    return son - once;
  }, [k]);

  const hazir = k !== undefined || kD !== "bekliyor";
  const tazeleniyor = hazir && kD === "bekliyor";   // bayat karne ekranda, taze yanıt yolda
  if (!hazir) return <SayfaIskeleti kpi={4} kart={2} />;
  if (!k) return <div style={{ color: "var(--soluk)" }}>Doğruluk verisi alınamadı; sayfayı yenileyin.</div>;

  const OK = ({ yukari }: { yukari: boolean }) => (
    <svg width="9" height="9" viewBox="0 0 10 10" aria-hidden="true">
      <path d={yukari ? "M5 8V2M2.4 4.6 5 2l2.6 2.6" : "M5 2v6M2.4 5.4 5 8l2.6-2.6"}
        fill="none" stroke="currentColor" strokeWidth="1.5"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
  const deltaCip = delta === null ? "gündüz saatleri, geçerli ölçümlerle"
    : Math.abs(delta) < 0.05 ? (
      <span className="kpi-delta notr" role="status">
        önceki 30 güne göre değişim yok
      </span>
    ) : (
      <span className={`kpi-delta ${delta < 0 ? "iyi" : "notr"}`} role="status">
        <OK yukari={delta > 0} />
        önceki 30 güne göre {sayiTr(Math.abs(delta), 1)} puan
      </span>
    );

  const ol = k.olasiliksal;   // v2.248: bant sinavi (undefined = eski API)
  // v2.247: normalize olcut yazimi — null → "—"; nMBE isaretli (+ fazla tahmin).
  const sfaYaz = (v: number | null | undefined, isaret = false) => {
    if (v == null) return "—";
    const y = Math.round(v * 10) / 10;                 // canlı teyit: -0,09 → "+0,0" yazıyordu
    return `%${isaret && y > 0 ? "+" : ""}${sayiTr(y, 1)}`;
  };

  // v2.76: karne gunu + kapsanan donem TUM kovalardan (Streamlit tanimi:
  // sk["date"].nunique() ve sk min/max — kova filtresiz).
  const tumTarihler = [...new Set(k.gunluk.map((r) => r.tarih))].sort();
  const donemIlk = tarihGecerli(tumTarihler[0]) ? tumTarihler[0] : k.ilk_tarih;
  const donemSon = tarihGecerli(tumTarihler[tumTarihler.length - 1]) ? tumTarihler[tumTarihler.length - 1] : k.son_tarih;

  return (
    <Sayfa baslik="Doğruluk karnesi"
      alt="Tahminler her gece gerçekleşen üretimle karşılaştırılır; sonuçlar burada birikir."
      sag={<>
        <span className="seg" role="group" aria-label="Karne dönemi">
          {([30, 60, 90] as const).map((g) => (
            <button key={g} aria-pressed={donem === g}
              onClick={() => setDonem(g)}>{g}g</button>
          ))}
        </span>
        <span className="cip"><Meta items={[`Kapsanan dönem: ${donemYaz(donemIlk, donemSon)}`, tazeleniyor && "güncelleniyor", kD === "hata" && "güncellenemedi"]} /></span>
      </>}>
      <div className="ızgara satir-4" style={{ marginBottom: 14 }}>
        {/* v2.311: ?? 0 yokluğu ÖLÇÜME çeviriyordu — eşleşmiş gün yokken kanıt
            sayfasının en tepesi "%0,0 WMAPE" ile kusursuzluk ilan ediyordu.
            İki KPI ayrı denetlenir: backend kova ve skill_vs_naive'i bağımsız
            hesaplıyor, tek bayrak dolu-WMAPE + null-naif vakasını kaçırır. */}
        <Kpi etiket={k.wmape_ort == null ? "Tahmin hatası (WMAPE), 0–24 saat" : `Tahmin hatası (WMAPE), 0–24 saat, ${k.gun_sayisi} gün ort.`}
             deger={k.wmape_ort == null ? "—" : `%${sayiTr(k.wmape_ort, 1)}`}
             alt={k.wmape_ort == null
               ? "henüz karşılaştırılmış gün yok; gece değerlendirmesinde birikiyor" : deltaCip} />
        <Kpi etiket="Referans tahmine göre iyileşme"
             deger={k.naife_ustunluk_pct == null ? "—" : `%${sayiTr(k.naife_ustunluk_pct)}`}
             alt={k.naife_ustunluk_pct == null
               ? "karşılaştırma için yeterli gün birikmedi"
               : "referans tahmin: dün aynı saat, gök açıklığına göre ölçekli"} />
        <Kpi etiket="Değerlendirilen gün" deger={sayiTr(new Set(k.gunluk.map((g) => g.tarih)).size)}
             birim="gün" alt="kesintisiz değerlendirme geçmişi" />
        {/* 23.10 yedinci tur: ortalama ana değer, standart sapma kendi etiketiyle ikinci satır (iki sayı tek noktalamayla değil) */}
        <Kpi etiket="Günlük sapma (ortalama)"
             deger={hd?.mu != null ? sayiTr(hd.mu, 2) : "—"}
             birim={hd?.mu != null ? "MWh" : undefined}
             ikinci={hd?.sd != null ? { etiket: "Standart sapma", deger: sayiTr(hd.sd, 2), birim: "MWh" } : undefined}
             alt={hd?.mu != null
               ? "hedef: sıfıra yakın ortalama, dar dağılım"
               : hd === undefined ? "hesaplanıyor" : "yeterli gün birikmedi"} />
      </div>
      {/* v2.247 (Dalga 1.2): kapasiteye normalize standart ölçütler — WMAPE'nin
          yanına, yerine değil. Eski kayıtlarda kolon boş → tire + neden. */}
      {/* 24.10 sekizinci tur: tek çipe sıkışan 6 bilgi → ölçüt grubu (.olcut-grup): başlık + niteleyici, etiket/değer
          çiftleri, ayrı durum satırı. Değer yoksa «—» (sıfır uydurulmaz); durum yalnız null ise yazılır. Hesap aynı. */}
      <div className="olcut-serit">
        <section className="olcut-grup" aria-label="Kurulu güce göre ölçütler">
          <div className="olcut-bas">Kurulu güce göre ölçütler<span className="olcut-not">sektör standardı, 0–24 saat</span></div>
          <dl className="olcut-liste">
            <div><dt>nMAE</dt><dd className={k.nmae_ort == null ? "bos" : undefined}>{sfaYaz(k.nmae_ort)}</dd></div>
            <div><dt>nRMSE</dt><dd className={k.nrmse_ort == null ? "bos" : undefined}>{sfaYaz(k.nrmse_ort)}</dd></div>
            <div><dt>nMBE</dt><dd className={k.nmbe_ort == null ? "bos" : undefined}>{sfaYaz(k.nmbe_ort, true)}</dd></div>
          </dl>
          {k.nmae_ort == null && <p className="olcut-durum">Henüz değer yok; gece değerlendirmesinde birikiyor.</p>}
        </section>
        {/* v2.279: sıkı referans — iklim + persistans optimal birleşimi; naiften daha zor geçilir */}
        <section className="olcut-grup" aria-label="Sektör referansına göre iyileşme"
                 title="Sektör referansı: iklim ortalaması ile son günlerin en iyi ağırlıklı birleşimi; tahmin becerisi iddiasının ölçütü">
          <div className="olcut-bas">Sektör referansına göre iyileşme<span className="olcut-not">iklim ortalaması ve son günlerin birleşimi</span></div>
          <dl className="olcut-liste">
            <div><dt>İyileşme</dt><dd className={k.cliper_ustunluk_pct == null ? "bos" : undefined}>{k.cliper_ustunluk_pct == null ? "—" : `%${sayiTr(k.cliper_ustunluk_pct, 1)}`}</dd></div>
            {k.cliper_wmape_ort != null && <div><dt>Referans WMAPE</dt><dd>%{sayiTr(k.cliper_wmape_ort, 1)}</dd></div>}
          </dl>
          {k.cliper_ustunluk_pct == null && <p className="olcut-durum">Henüz değer yok; gece değerlendirmesinde birikiyor.</p>}
        </section>
      </div>
      <Kart baslik="Günlük tahmin hatası (WMAPE) — referans tahminle karşılaştırma"
        sag={<span className="cip"><Meta items={["nokta: günlük", "kalın: 7 gün eğilimi", "ince gri: referans tahmin"]} /></span>}>
        {/* 22.10 üçüncü tur: hiç karşılaştırılmış gün yokken 2×240 px boş grafik yerine kompakt boş durum
            (veri yokluğu gizlenmez; seri/hesap değişmez — yalnız sunum) */}
        {(k?.gunluk ?? []).length === 0 ? (
          <p className="soluk" style={{ margin: 0, fontSize: 14.5 }}>
            Henüz karşılaştırılmış gün yok. İlk gece değerlendirmesinden sonra 0–24 ve 24–72 saat ufukları için
            günlük tahmin hatası burada çizilir; referans tahminle kıyas aynı grafikte görünür.
          </p>
        ) : (
        <div className="ızgara" style={{ gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)" }}>
          <div>
            <p style={{ fontSize: 14.5, fontWeight: 600, color: "var(--metin)",
                        margin: "0 0 4px" }}>0–24 saat ufku</p>
            <EChart option={wmape024} height={240}
              ariaLabel="0–24 saat ufku günlük tahmin hatası (WMAPE), referans tahminle" />
          </div>
          <div>
            <p style={{ fontSize: 14.5, fontWeight: 600, color: "var(--metin)",
                        margin: "0 0 4px" }}>24–72 saat ufku</p>
            <EChart option={wmape2472} height={240}
              ariaLabel="24–72 saat ufku günlük tahmin hatası (WMAPE), referans tahminle" />
          </div>
        </div>
        )}
        <p style={{ fontSize: 13, color: "var(--soluk)", margin: "12px 0 0" }}>
          <b style={{ color: "var(--ikincil)" }}>Ne gösterir:</b>{" "}
          her nokta bir günün tahmin hatasıdır (WMAPE); kalın yeşil çizgi 7 günlük eğilim,
          ince gri çizgi referans tahmindir (dün aynı saat).{" "}
          <b style={{ color: "var(--ikincil)" }}>Neye bakmalı:</b> yeşil çizgi grinin
          altında kaldıkça PVQuant'ın katkısı o kadar büyüktür. 24–72 saat ufkunda hatanın
          biraz daha yüksek olması normaldir; önemli olan farkın kontrollü kalmasıdır.
        </p>
      </Kart>
      {/* v2.248 (Dalga 1.3): P10–P90 bandının sınavı — bant genişliği değil, bandın
          TUTUP TUTMADIĞI. Üç çubuk: hedef işareti (%10 / %80 / %90) ile gözlenen oran. */}
      <Kart baslik="Tahmin aralığının güvenilirliği (P10–P90)"
        sag={<>
          <span className="cip">{ol?.gun_sayisi ? <Meta items={[`${sayiTr(ol.gun_sayisi)} gün`, "0–24 saat"]} /> : "henüz birikmedi"}</span>
          {/* v2.252: bant kalibrasyonu durumu — q̂ negatifse bant daraltılıyor, pozitifse genişletiliyor */}
          <span className="cip" title="Yayımlanan P10–P90 aralığı, son dönemin sonuçlarından öğrenilen düzeltmeyle ayarlanır">
            {kf === undefined ? "aralık ayarı: hesaplanıyor" : kf.aktif
              ? kf.kova_ort_q_kw && Object.keys(kf.kova_ort_q_kw).length > 0
                /* v2.296: q̂ artık ufka göre — kova başına yön ve büyüklük tek çipte */
                ? `aralık ayarı ufka göre: ${Object.entries(kf.kova_ort_q_kw)
                    .map(([k, v]) => `${k} s ${v < 0 ? "−" : "+"}${sayiTr(Math.abs(v), 0)} kW`).join(", ")}`
                : `aralık ayarı: ${kf.ort_q_kw != null && kf.ort_q_kw < 0 ? "daraltıyor" : "genişletiyor"} (ort. ${sayiTr(Math.abs(kf.ort_q_kw ?? 0), 0)} kW, ${sayiTr(kf.pencere_gun ?? 0)} gün)`
              : "aralık ayarı: henüz yok"}
          </span>
        </>}>
        {ol?.gun_sayisi ? (
          <div className="ızgara satir-3" style={{ gap: 12 }}>
            {([
              ["Aralık içinde kalan günler (P10–P90)", ol.picp80, 0.80, "hedef: günlerin %80'i"],
              ["P10'un altında kalan", ol.kapsama_p10, 0.10, "hedef %10; azsa alt sınır fazla temkinli"],
              ["P90'ın altında kalan", ol.kapsama_p90, 0.90, "hedef %90; fazlaysa üst sınır fazla temkinli"],
            ] as [string, number | null, number, string][]).map(([et, v, hedef, not_]) => (
              <div key={et} className="kpi">
                <div className="kpi-et">{et}</div>
                <div className="kpi-dg mono">{v == null ? "—" : `%${sayiTr(v * 100, 0)}`}
                  <span style={{ fontSize: 13, color: "var(--soluk)", marginLeft: 6 }}>hedef %{sayiTr(hedef * 100, 0)}</span></div>
                <div style={{ position: "relative", height: 6, background: "var(--yuzey2)", borderRadius: 3, margin: "8px 0 6px" }}>
                  <div style={{ width: `${Math.min(100, (v ?? 0) * 100)}%`, height: "100%", borderRadius: 3,
                    background: v != null && Math.abs(v - hedef) <= 0.05 ? "var(--basari)" : "var(--chart-p50-future)" }} />
                  <div style={{ position: "absolute", left: `${hedef * 100}%`, top: -3, width: 2, height: 12, background: "var(--metin)" }} />
                </div>
                <div className="kpi-alt">{not_}</div>
              </div>
            ))}
          </div>
        ) : (
          <p className="soluk" style={{ margin: 0 }}>Aralık değerlendirmesi, P10–P90 kaydedilen tahminlerle gece değerlendirmesinde birikir; ilk gün tamamlanınca burada görünür.</p>
        )}
        <p className="soluk" style={{ marginTop: 10, marginBottom: 0, fontSize: 14 }}>
          Ne gösterir: gerçekleşen üretimin, önceden verilen P10–P90 aralığı içinde kaldığı günlerin oranı.
          Neye bakmalı: yeşil çubuk hedefe ±5 puan yakın demektir; düşükse aralık dar (fazla iddialı), yüksekse aralık geniş (fazla temkinli).
          {ol?.crps != null && ` Aralık kalitesi (CRPS): ${sayiTr(ol.crps, 0)} kW; ortalama aralık genişliği kurulu gücün %${sayiTr((ol.bant_n ?? 0) * 100, 0)}'i.`}
        </p>
        {/* v2.253: kayan-başlangıç geriye dönük sınav — q̂ yalnız önceki günlerden, sonraki haftaya uygulanır (sızıntı yok) */}
        {bt && bt.pencere > 0 && (
          <div className="grafik-kaydir" style={{ marginTop: 12 }}>
            <div className="cip" style={{ display: "inline-block", marginBottom: 6 }}>
              <Meta items={["Geriye dönük değerlendirme", `${sayiTr(bt.pencere)} dönem`, `ham %${sayiTr((bt.picp_ham_ort ?? 0) * 100, 0)} → ayarlı %${sayiTr((bt.picp_kal_ort ?? 0) * 100, 0)} (hedef %80)`, bt.hukum]} />
            </div>
            <table className="veri" style={{ fontSize: 13.5 }}>
              <thead><tr><th>Başlangıç</th><th>Test saati</th><th>Ham kapsama</th><th>Ayarlı kapsama</th><th>Aralık genişliği (ham → ayarlı)</th></tr></thead>
              <tbody className="mono">
                {bt.satirlar.map((r) => (
                  <tr key={r.baslangic}><td>{r.baslangic}</td><td>{sayiTr(r.n_test)}</td>
                    <td>%{sayiTr(r.picp_ham * 100, 0)}</td><td>%{sayiTr(r.picp_kal * 100, 0)}</td>
                    <td>%{sayiTr(r.bant_ham_n * 100, 0)} → %{sayiTr(r.bant_kal_n * 100, 0)}</td></tr>
                ))}
              </tbody>
            </table>
            {/* v2.297: ufuk kovası sınavı — kova q̂ uzak ufkun kapsamasını hedefe yaklaştırıyor mu? */}
            {bt.kova_sinav && bt.kova_sinav.pencere > 0 && bt.kova_sinav.kovalar.length > 0 && (
              <>
                <div className="cip" style={{ display: "inline-block", margin: "12px 0 6px" }}>
                  <Meta items={["Ufka göre değerlendirme", `${sayiTr(bt.kova_sinav.pencere)} dönem`, bt.kova_sinav.hukum]} />
                </div>
                <table className="veri" style={{ fontSize: 13.5 }}>
                  <thead><tr><th>Ufuk</th><th>Test saati</th><th>Ham</th><th>Tek düzeltme</th><th>Ufka göre düzeltme</th></tr></thead>
                  <tbody className="mono">
                    {bt.kova_sinav.kovalar.map((k) => (
                      <tr key={k.kova}><td>{k.kova} s</td><td>{sayiTr(k.n)}</td>
                        <td>%{sayiTr(k.picp_ham * 100, 0)}</td><td>%{sayiTr(k.picp_tek * 100, 0)}</td>
                        <td>%{sayiTr(k.picp_kova * 100, 0)}</td></tr>
                    ))}
                  </tbody>
                </table>
                <p className="soluk" style={{ fontSize: 14, margin: "6px 0 0" }}>
                  Hedef %80. "Tek düzeltme" eski yöntemdir (aynı düzeltme her ufka uygulanır);
                  "ufka göre" her ufuk için ayrı öğrenilir. Hedefe yakın olan iyidir.
                </p>
              </>
            )}
          </div>
        )}
        {/* v2.271 (Dalga 1 tamamlayıcısı): kantil güvenilirliği + PIT + keskinlik — ham ↔ kalibre */}
        {gv === undefined && <div style={{ marginTop: 14 }}><YerTutucu yukseklik={1060} /></div>}
        {gv && (gv.durum === "ok" && gvOption && pitOption ? (
          <div style={{ marginTop: 14 }}>
            {/* 24.10: beş çip → üç ölçüt grubu (örneklem · aralık ayarının etkisi · seviyeler); sayılar ve kaynak aynı */}
            <div className="olcut-serit" style={{ marginBottom: 12 }}>
              <section className="olcut-grup" aria-label="Güvenilirlik örneklemi">
                <div className="olcut-bas">Örneklem</div>
                <dl className="olcut-liste">
                  <div><dt>Gündüz saati</dt><dd>{sayiTr(gv.n_saat)}</dd></div>
                  <div><dt>Gün</dt><dd>{sayiTr(gv.gun_sayisi ?? 0)}</dd></div>
                </dl>
              </section>
              <section className="olcut-grup" aria-label="Aralık ayarının etkisi">
                <div className="olcut-bas">Aralık ayarının etkisi<span className="olcut-not">ham → ayarlı</span></div>
                <dl className="olcut-liste">
                  <div><dt>Genişlik</dt><dd>%{sayiTr((gv.keskinlik?.ham ?? 0) * 100, 0)} → %{sayiTr((gv.keskinlik?.kalibre ?? 0) * 100, 0)}</dd><span className="olcut-not">kurulu gücün</span></div>
                  <div><dt>Aralık puanı</dt><dd>{sayiTr((gv.aralik_skoru_n?.ham ?? 0) * 100, 1)} → {sayiTr((gv.aralik_skoru_n?.kalibre ?? 0) * 100, 1)}</dd><span className="olcut-not">küçük iyi</span></div>
                  <div><dt>PIT en büyük sapma</dt><dd>{sayiTr((gv.pit_max_sapma ?? 0) * 100, 0)}</dd><span className="olcut-not">puan</span></div>
                </dl>
              </section>
              <section className="olcut-grup" aria-label="Seviyelerde gözlenen kapsama">
                <div className="olcut-bas">Seviyeler<span className="olcut-not">gözlenen, hedef parantezde</span></div>
                <dl className="olcut-liste">
                  {(gv.guvenilirlik?.kalibre ?? []).map((r) => (
                    <div key={r.tau}><dt>P{Math.round(r.tau * 100)} altı</dt><dd>%{sayiTr(r.gozlenen * 100, 0)}</dd><span className="olcut-not">(%{Math.round(r.tau * 100)})</span></div>))}
                </dl>
              </section>
            </div>
            <div className="ızgara satir-2" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(300px, 100%), 1fr))", gap: 14 }}>
              <div><div className="etiket-ust" style={{ marginBottom: 2 }}>Güvenilirlik diyagramı</div><p className="kart-alt" style={{ margin: "0 0 6px" }}>Gözlenen ve hedeflenen kapsama</p>
                <EChart option={gvOption} height={220} /></div>
              <div><div className="etiket-ust" style={{ marginBottom: 2 }}>PIT histogramı</div><p className="kart-alt" style={{ margin: "0 0 6px" }}>Gerçekleşenin aralık içindeki yüzdeliği (düz = iyi ayarlı)</p>
                <EChart option={pitOption} height={220} /></div>
            </div>
            <p className="soluk" style={{ marginTop: 8, marginBottom: 0, fontSize: 14 }}>
              Nasıl okunur: nokta köşegenin altındaysa o seviye olması gerekenden düşük, üstündeyse yüksek demektir.
              P10 için düşük kalmak alt sınırın, P90 için yüksek kalmak üst sınırın fazla temkinli olduğunu gösterir; ikisi birden aralığın fazla geniş olduğunu söyler.
              PIT sütunları %10 çizgisine yakın olmalıdır: ortada tepe aralık fazla geniş, kenarlarda tepe aralık fazla dar demektir. Aralık puanı, genişlik ile aralık dışı kalma puanının toplamıdır.
            </p>
          </div>
        ) : gv.durum !== "ok" ? (
          <p className="soluk" style={{ marginTop: 10, marginBottom: 0, fontSize: 14 }}>
            Güvenilirlik diyagramı için en az {sayiTr(gv.min_saat ?? 72)} gündüz saati gerekir (şu an {sayiTr(gv.n_saat)}).
          </p>
        ) : null)}
      </Kart>
      {/* 29.10 (F-01/F-02/F-03/F-09): uzlaştırma kalemleri — EDT ve KÜPST AYRI, tek sayı yok; her TL'nin yanında kural sürümü ve
          fiyat kaynağı; hesaplanamayan saat (yön eksik / segment yok) açıkça; «tasarruf/ceza» yok; teminat sadeleştirilmiş gösterge */}
      <Kart baslik="Uzlaştırma kalemleri — enerji dengesizlik tutarı ve KGÜP sapma tutarı, son dönem"
        sag={<>
          {/* v2.517 (P2a): program kaynağı — bildirilen KGÜP (müşteri beyanı) varsa o, yoksa öneri; pozisyon ayarı */}
          <span className="cip" title={dz?.program ? `${sayiTr(dz.program.bildirilen_saat)} saat bildirilen KGÜP, ${sayiTr(dz.program.oneri_saat)} saat PVQuant önerisi; ${dz.program.pozisyon.etiket}` : undefined}>{dz === undefined ? "hesaplanıyor" : dz && dz.gun_sayisi ? <Meta items={[`${sayiTr(dz.gun_sayisi)} gün`,
            dz.program && dz.program.bildirilen_saat > 0 ? `program: ${sayiTr(dz.program.bildirilen_gun)} gün bildirilen KGÜP, kalanı öneri` : "program: PVQuant önerisi (bir gün önce 15:30'dan önceki tahmin, P50)",
            dz.program && dz.program.pozisyon.kaynak !== "program" && (dz.program.pozisyon.kaynak === "uretim" ? "pozisyon: üretildiği kadar satış" : `pozisyon: sabit ${sayiTr(dz.program.pozisyon.sabit_mwh ?? 0, 1)} MWh/saat`)]} /> : "henüz karşılaştırılan gün yok"}</span>
          {dz?.kural && <span className="cip" title={`${dz.kural.edt_dayanak}; KÜPST: ${dz.kural.kupst_dayanak}`}>kural: DUY m.110 ({dz.kural.rejim}){dz.kural.V != null ? ` · V ${sayiTr(dz.kural.V)} TL/MWh` : ""}</span>}
          {/* 29.10: rozet metni kısa (375 px'te başlık satırı taşıyordu); ayrıntı title ve KPI alt etiketinde */}
          {dz && <span className={`rozet ${dz.fiyat.senaryo_saat > 0 ? "rozet-uyari" : "rozet-ok"} rozet-kucuk`} title={dz.fiyat.senaryo_saat > 0 ? "Senaryo fiyatı: EPİAŞ kimliği tanımlı değil. " + dz.not : dz.not}>{dz.fiyat.senaryo_saat > 0 ? "senaryo fiyatı" : "fiyat: EPİAŞ"}</span>}
        </>}>
        {dz === undefined ? <YerTutucu yukseklik={411} /> : dz && dz.toplam ? (
          <>
            <div className="ızgara satir-4" style={{ gap: 12 }}>
              <div className="kpi"><div className="kpi-et"><BilgiliEtiket metin="Dengesizlik maliyeti · EDT" bilgi="Gerçekleşen üretim ile saatlik piyasa pozisyonu (varsayılanı üretim programı; Santralim › Program sınırları) arasındaki farkın EPİAŞ uzlaştırmasındaki karşılığı, enerji dengesizlik tutarı: eksik üretim borç, fazla üretim alacak yazar; gösterilen değer net maliyettir." /></div>
                <div className="kpi-dg mono">{dz.toplam.dengesizlik_tl != null ? <>{sayiTr(dz.toplam.dengesizlik_tl / 1000, 1)} <small>bin TL</small></> : "—"}</div>
                <div className="kpi-alt">{fiyatEtiketi(dz)}</div></div>
              <div className="kpi"><div className="kpi-et"><BilgiliEtiket metin="KGÜP sapma tutarı · KÜPST" bilgi="Kesinleşmiş gün öncesi üretim programından tolerans üstü sapmanın tutarı. Enerji dengesizlik tutarından ayrı bir kalemdir; alacakla netleşmez." /></div>
                <div className="kpi-dg mono">{dz.toplam.kupst_tl != null ? <>{sayiTr(dz.toplam.kupst_tl / 1000, 1)} <small>bin TL</small></> : "—"}</div>
                <div className="kpi-alt">{kupstEtiketi(dz)}</div></div>
              <div className="kpi"><div className="kpi-et"><BilgiliEtiket metin="Uzlaştırma kalemleri toplamı" bilgi="Dengesizlik maliyeti ile KÜPST toplamı. KÜPST hesaplanamıyorsa toplam verilmez." /></div>
                <div className="kpi-dg mono">{dz.toplam.pvquant_tl != null ? <>{sayiTr(dz.toplam.pvquant_tl / 1000, 1)} <small>bin TL</small></> : "—"}</div>
                <div className="kpi-alt">{dz.toplam.pvquant_tl != null ? `dengesizlik maliyeti + KÜPST${dz.toplam.gelir_oran_pct != null ? ` · gelirin %${sayiTr(dz.toplam.gelir_oran_pct, 2)}'i` : ""}` : "KÜPST hesaplanamadığı için toplam verilmez"}</div></div>
              <div className="kpi"><div className="kpi-et"><BilgiliEtiket metin="Referans programa göre fark · varsayımsal" bilgi="Dünün aynı saatteki üretimini program kabul eden basit referansın aynı kuralla maliyeti ile PVQuant programının maliyeti arasındaki fark. Varsayımsal bir karşılaştırmadır." /></div>
                <div className="kpi-dg mono">{dz.toplam.kurtarilan_tl != null ? <>{sayiTr(dz.toplam.kurtarilan_tl / 1000, 1)} <small>bin TL</small></> : "—"}</div>
                <div className="kpi-alt">referans: dün aynı saat{dz.toplam.naif_tl != null ? `, ${sayiTr(dz.toplam.naif_tl / 1000, 1)} bin TL` : ""}</div></div>
            </div>
            <p className="soluk" style={{ marginTop: 8, marginBottom: 0, fontSize: 13.5 }}>
              {dz.segment.santral_tasir === false ? `Bu segmentte dengesizliği ${dz.segment.dengesizlik_sahibi} taşır; tutarlar santral sahibine yansımaz.`
                : dz.segment.segment ? "Dengesizliği santral taşır; tutarlar santral sahibine yansır." : "Segment seçilmedi; Santralim › Santral ayarlarından seçilir. KÜPST hesaplanamaz."}
              {(dz.hesaplanamayan_saat ?? 0) > 0 && ` ${sayiTr(dz.hesaplanamayan_saat ?? 0)} saat hesaplanamadı; neden: ${(dz.fiyat.yon_eksik_saat ?? 0) > 0 ? "sistem yönü verisi eksik" : "KÜPST katsayısı yok"}. Bu saatler toplama 0 olarak alınmadı.`}
            </p>
            <div className="grafik-kaydir" style={{ marginTop: 12 }}>
              <table className="veri" style={{ fontSize: 13.5 }}>
                <thead><tr><th>Ay</th><th>Üretim (MWh)</th><th>Sapma (MWh)</th><th>EDT borç (TL)</th><th>EDT alacak (TL)</th><th>Dengesizlik maliyeti (TL)</th><th>KÜPST (TL)</th><th title="KGÜP sapma tutarı doğuran saat sayısı: sapmanın toleransı (m × program) aştığı saatler">Tolerans dışı saat</th><th title="KGÜP sapma miktarı (KÜPSM): toleransın üstündeki sapma toplamı, MWh">KÜPSM (MWh)</th><th>Toplam (TL)</th><th>Referans (TL)</th><th>Fark (TL)</th><th>Hesaplanamayan saat</th></tr></thead>
                <tbody className="mono">
                  {dz.aylar.map((a) => (
                    <tr key={a.ay} title={a.kural_surumu ? `kural: ${a.kural_surumu}` : undefined}><td>{a.ay}</td><td>{sayiTr(a.uretim_mwh, 1)}</td><td>{sayiTr(a.sapma_mwh, 1)}</td>
                      <td>{a.edtb_tl != null ? sayiTr(a.edtb_tl) : "—"}</td><td>{a.edta_tl != null ? sayiTr(a.edta_tl) : "—"}</td>
                      <td>{a.dengesizlik_tl != null ? sayiTr(a.dengesizlik_tl) : "—"}</td>
                      <td>{a.kupst_tl != null ? sayiTr(a.kupst_tl) : "—"}</td>
                      <td>{a.tolerans_disi_saat != null ? sayiTr(a.tolerans_disi_saat) : "—"}</td><td>{a.kupsm_mwh != null ? sayiTr(a.kupsm_mwh, 1) : "—"}</td>
                      <td>{a.pvquant_tl != null ? sayiTr(a.pvquant_tl) : "—"}</td>
                      <td>{a.naif_tl != null ? sayiTr(a.naif_tl) : "—"}</td><td>{a.kurtarilan_tl != null ? sayiTr(a.kurtarilan_tl) : "—"}</td>
                      <td>{a.hesaplanamayan_saat ? sayiTr(a.hesaplanamayan_saat) : "0"}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
            <SaatlikDokum plantId={plantId} gun={dz.pencere_gun} />
            <p style={{ marginTop: 10, marginBottom: 0, fontSize: 13.5 }}>
              {dz.toplam?.teminat && (dz.toplam.teminat.tutar_tl != null
                ? <>Dengesizlik teminatı göstergesi: <b>{sayiTr(dz.toplam.teminat.tutar_tl / 1000, 1)} bin TL</b> ({sayiTr(dz.toplam.teminat.edm_neg_max_mwh ?? 0, 1)} MWh en yüksek aylık negatif dengesizlik
                    miktarı ({dz.toplam.teminat.edm_ay}) × {sayiTr(dz.toplam.teminat.smf_ort_tl_mwh ?? 0, 0)} TL/MWh {sayiTr(dz.toplam.teminat.smf_ay_sayisi)} aylık ortalama SMF × risk katsayısı {sayiTr(dz.toplam.teminat.risk_katsayisi ?? 0, 2)};
                    EPİAŞ dengesizlik teminatı tanımı, doğrulanmamış gösterge; EPYS ve Takasbank tutarları esastır). </>
                : <>Dengesizlik teminatı göstergesi: risk katsayısı girilmedi (Santralim › Üretim programı sınırları); formül {dz.toplam.teminat.formul}{dz.toplam.teminat.edm_neg_max_mwh != null
                    ? `; ${sayiTr(dz.toplam.teminat.edm_neg_max_mwh, 1)} MWh (${dz.toplam.teminat.edm_ay}) × ${sayiTr(dz.toplam.teminat.smf_ort_tl_mwh ?? 0, 0)} TL/MWh` : ""}. </>)}
              {dz.oneri && (dz.oneri.durum === "ok" && dz.oneri.kantil
                ? <>Önerilen program seviyesi: <b>{dz.oneri.kantil.toUpperCase()}</b> (saatlerin
                    %{sayiTr((dz.oneri.acik_saat_orani ?? 0) * 100, 0)}'inde sistem enerji açığındaydı); eksik üretimin birim maliyeti ile fazla üretimin birim maliyetinin dengesidir.</>
                : <span className="soluk">Önerilen program seviyesi: — ({dz.oneri.not})</span>)}
            </p>
            <p className="soluk" style={{ marginTop: 8, marginBottom: 0, fontSize: 14 }}>
              Bu kart yürürlükteki kuralla yapılan bir yeniden hesaptır; EPİAŞ uzlaştırma sonucu değildir. Referans sütunu, dünün aynı saatteki üretimini program kabul eden basit referansın aynı kuralla maliyetidir; fark varsayımsaldır.
              {dz.fiyat.senaryo_saat > 0 && " Senaryo fiyatı: EPİAŞ piyasa fiyatı bağlı olmadığından EPDK 2025 yıllık ortalaması kullanılmış, sistem yönü dengede varsayılmıştır; piyasa kimliği tanımlandığında gerçek saatlik fiyat ve yönle hesaplanır."}
              {dz.kural?.belirsiz_2027 && " 1.1.2027 sonrası kural metni hukuken belirsiz; 2026 kuralı sürdürüldü."}
            </p>
            <details className="aciklama">
              <summary>Hesap yöntemi ve formüller</summary>
              <p style={{ margin: "6px 0 0" }}>
              Gerçekleşen üretim ile saatlik piyasa pozisyonu (varsayılanı üretim programı) arasındaki farkın, {dz.kural?.rejim === "2026"
                ? <>1.1.2026'dan yürürlükteki DUY m.110 formülüyle TL karşılığı: eksik üretimde max(V, PTF, SMF)×(1+k), tavanda AFL×1,05×(1+k);
                    fazla üretimde min(PTF, SMF)×(1−l), fiyat V'nin altındaysa −B×(1+l) (fazla üretim borç doğurur); k ve l sistem yönüne göre
                    (açık 0,06/0,03; fazla 0,03/0,06; dengede 0,03). KÜPST: tolerans üstü sapma × max(750; PTF; SMF) × n{dz.kural.kupst_net_sapma ? ", net sapma (1.11.2026'dan: |(üretim − UEÇM) − program|; UEÇM sayaç çekişinden, yoksa 0)" : ""}.</>
                : <>2025 formülüyle TL karşılığı: fazla üretim min(PTF, SMF)×0,97; eksik üretim max(PTF, SMF)×1,03; KÜPST tolerans üstü sapma × max(750; PTF; SMF) × n.</>}
              {dz.fiyat.senaryo_saat > 0 && " Senaryo fiyatında k = l = 0,03 varsayıldı."} Kısaltmalar: PTF piyasa takas fiyatı, SMF sistem marjinal fiyatı, V ve B DUY m.110 taban/borç parametreleri, AFL aylık fiyat limiti, k ve l sistem yönüne bağlı katsayılar, n KÜPST katsayısı.
              </p>
            </details>
          </>
        ) : (
          <p className="soluk" style={{ margin: 0 }}>Bir gün önce 15:30'dan önce verilmiş tahmin ile gerçekleşen üretimin karşılaştırılabildiği gün henüz yok; tahminler ve ölçümler biriktikçe burada görünür.</p>
        )}
      </Kart>
      {/* v2.520 (P5a): YEKDEM katmanı — yalnız lisanslı YEKDEM segmentinde (öbür segmentlerde fiyat yalnız tarife gelirine girer) */}
      {dz?.segment.segment === "lisansli_yekdem" && <YekdemKarti plantId={plantId} gun={dz.pencere_gun} />}
      {/* v2.503 (F-07): 12 aylık geri test — aylık tablo + karşı-olgu sütunları; istek yalnız kart açılınca (ağır sorgu) */}
      <Kart baslik="Uzlaştırma kalemleri geri testi — son 12 ay, varsayımsal yeniden hesap"
        sag={<span className="cip">{gt ? <Meta items={[`${sayiTr(gt.gun_sayisi)} gün`, gt.mekanizma && gt.mekanizma.senaryo_saat > 0 ? `senaryo fiyatı ${sayiTr(gt.mekanizma.senaryo_saat)} saat` : "fiyat: EPİAŞ"]} /> : gt === null ? "alınamadı" : "kapalı"}</span>}>
        <details className="aciklama genis" onToggle={(e) => { if ((e.currentTarget as HTMLDetailsElement).open && gt === undefined) api.dengesizlikGeriTest(plantId).then((v) => setGt(v), () => setGt(null)); }}>
          <summary>Aylık tablo ve kural karşılaştırmaları</summary>
          {gt === undefined ? <p className="soluk">açılınca hesaplanır…</p>
           : gt === null ? <p className="soluk">Geri test alınamadı (sunucu hatası ya da örnek kip).</p>
           : !gt.toplam || gt.aylar.length === 0 ? <p className="soluk">Karşılaştırılabilir gün yok; tahmin ve ölçüm biriktikçe oluşur.</p>
           : (
            <>
              <p className="soluk" style={{ fontSize: 13.5, margin: "0 0 8px" }}>{gt.baslik} Kural: {gt.kural_surumu ?? "—"}.</p>
              <div className="ızgara satir-4" style={{ gap: 12, marginBottom: 10 }}>
                <div className="kpi"><div className="kpi-et"><BilgiliEtiket metin="Yürürlükteki kuralla toplam" bilgi="Her saat, o gün yürürlükte olan kuralla hesaplanan dengesizlik maliyeti ile KÜPST toplamı." /></div><div className="kpi-dg mono">{gt.toplam.toplam_tl != null ? <>{sayiTr(gt.toplam.toplam_tl / 1000, 1)} <small>bin TL</small></> : "—"}</div>
                  <div className="kpi-alt">eksik {gt.toplam.eksik_tl != null ? sayiTr(gt.toplam.eksik_tl / 1000, 1) : "—"} · fazla {gt.toplam.fazla_tl != null ? sayiTr(gt.toplam.fazla_tl / 1000, 1) : "—"} · KÜPST {gt.toplam.kupst_tl != null ? sayiTr(gt.toplam.kupst_tl / 1000, 1) : "—"} bin TL</div></div>
                <div className="kpi"><div className="kpi-et"><BilgiliEtiket metin="2026 kuralı tüm döneme uygulansaydı" bilgi="Varsayımsal karşılaştırma: 2025 saatleri de 1.1.2026 formülüyle hesaplanır." /></div><div className="kpi-dg mono">{gt.toplam.karsi_2026_tl != null ? <>{sayiTr(gt.toplam.karsi_2026_tl / 1000, 1)} <small>bin TL</small></> : "—"}</div><div className="kpi-alt">varsayımsal karşılaştırma</div></div>
                <div className="kpi"><div className="kpi-et"><BilgiliEtiket metin="1.11.2026 kuralı, V = 100, tüm döneme" bilgi="Varsayımsal karşılaştırma: taban parametresi V = 100 TL/MWh olan 1.11.2026 kuralı bütün döneme uygulanır." /></div><div className="kpi-dg mono">{gt.toplam.karsi_v100_tl != null ? <>{sayiTr(gt.toplam.karsi_v100_tl / 1000, 1)} <small>bin TL</small></> : "—"}</div><div className="kpi-alt">varsayımsal karşılaştırma</div></div>
                <div className="kpi"><div className="kpi-et"><BilgiliEtiket metin="Referans programa göre fark · varsayımsal" bilgi="Dünün aynı saatteki üretimini program kabul eden basit referansın maliyeti ile PVQuant programının maliyeti arasındaki fark; varsayımsaldır." /></div><div className="kpi-dg mono">{gt.toplam.referans_fark_tl != null ? <>{sayiTr(gt.toplam.referans_fark_tl / 1000, 1)} <small>bin TL</small></> : "—"}</div><div className="kpi-alt">referans: dün aynı saat{gt.toplam.referans_tl != null ? `, ${sayiTr(gt.toplam.referans_tl / 1000, 1)} bin TL` : ""}</div></div>
              </div>
              <div className="grafik-kaydir">
                <table className="veri" style={{ fontSize: 13 }}>
                  <thead><tr><th>Ay</th><th>Gün</th><th>Üretim (MWh)</th><th>Sapma (MWh)</th><th>Eksik üretim (TL)</th><th>Fazla üretim (TL)</th><th>KÜPST (TL)</th><th>Toplam (TL)</th><th>2026 kuralı tüm döneme</th><th>V = 100 kuralı</th><th>Referans (TL)</th><th>Hesaplanamayan saat</th></tr></thead>
                  <tbody className="mono">
                    {gt.aylar.map((a) => (
                      <tr key={a.ay} title={`kural: ${a.kural_surumu}`}><td>{a.ay}</td><td>{sayiTr(a.gun)}</td><td>{sayiTr(a.uretim_mwh, 1)}</td><td>{sayiTr(a.sapma_mwh, 1)}</td>
                        <td>{a.eksik_tl != null ? sayiTr(a.eksik_tl) : "—"}</td><td>{a.fazla_tl != null ? sayiTr(a.fazla_tl) : "—"}</td><td>{a.kupst_tl != null ? sayiTr(a.kupst_tl) : "—"}</td>
                        <td>{a.toplam_tl != null ? sayiTr(a.toplam_tl) : "—"}</td><td>{a.karsi_2026_tl != null ? sayiTr(a.karsi_2026_tl) : "—"}</td><td>{a.karsi_v100_tl != null ? sayiTr(a.karsi_v100_tl) : "—"}</td>
                        <td>{a.referans_tl != null ? sayiTr(a.referans_tl) : "—"}</td><td>{a.hesaplanamayan_saat ? sayiTr(a.hesaplanamayan_saat) : "0"}</td></tr>))}
                  </tbody>
                </table>
              </div>
              {gt.duyarlilik && gt.duyarlilik.seviyeler.length > 0 && (
                <details className="aciklama genis" style={{ marginTop: 10 }}>
                  <summary>Hata duyarlılığı · varsayımsal (gerçek WMAPE %{sayiTr(gt.duyarlilik.wmape_gercek, 1)})</summary>
                  <p className="soluk" style={{ fontSize: 13.5, margin: "0 0 8px" }}>Aynı fiyat ve sistem yönü geçmişinde tahmin hatası farklı bir seviyede olsaydı uzlaştırma kalemleri ne olurdu: santralin kendi saatlik hata deseni hedef seviyeye ölçeklenir, rastgele üretim yoktur. Gelecek için öngörü ya da taahhüt değildir.</p>
                  <div className="grafik-kaydir">
                    <table className="veri" style={{ fontSize: 13 }}>
                      <thead><tr><th>WMAPE hedef</th><th>Elde edilen</th><th>Eksik üretim (TL)</th><th>Fazla üretim (TL)</th><th>KÜPST (TL)</th><th>Toplam (TL)</th><th>TL/MWh</th></tr></thead>
                      <tbody className="mono">
                        {gt.duyarlilik.seviyeler.map((r) => (
                          <tr key={r.wmape_hedef} style={r.gercek ? { fontWeight: 600 } : undefined}>
                            <td>%{sayiTr(r.wmape_hedef, 1)}{r.gercek ? " (gerçek)" : ""}</td><td>%{sayiTr(r.wmape_elde, 1)}</td>
                            <td>{r.eksik_tl != null ? sayiTr(r.eksik_tl) : "—"}</td><td>{r.fazla_tl != null ? sayiTr(r.fazla_tl) : "—"}</td>
                            <td>{r.kupst_tl != null ? sayiTr(r.kupst_tl) : "—"}</td><td>{r.toplam_tl != null ? sayiTr(r.toplam_tl) : "—"}</td>
                            <td>{r.tl_per_mwh != null ? sayiTr(r.tl_per_mwh, 1) : "—"}</td></tr>))}
                      </tbody>
                    </table>
                  </div>
                  <p className="soluk" style={{ fontSize: 13, margin: "6px 0 0" }}>Yöntem: {gt.duyarlilik.yontem}. Elde edilen WMAPE, 0 ile kurulu güç arasına kırpma yüzünden hedeften biraz sapabilir.</p>
                </details>
              )}
              {gt.mekanizma && (
                <p className="soluk" style={{ fontSize: 13.5, margin: "8px 0 0" }}>
                  Saat dağılımı: {sayiTr(gt.mekanizma.saat)} saat; sistem enerji açığında {sayiTr(gt.mekanizma.acik_saat)}, fazlasında {sayiTr(gt.mekanizma.fazla_saat)}, dengede {sayiTr(gt.mekanizma.dengede_saat)}.
                  Fazla üretimin borç yazdığı saat, B dalı: {sayiTr(gt.mekanizma.b_dali_saat)}{gt.mekanizma.b_dali_tl != null ? `, ${sayiTr(gt.mekanizma.b_dali_tl)} TL` : ""}. Aylık fiyat limiti AFL'nin uygulandığı saat: {sayiTr(gt.mekanizma.afl_dali_saat)}.
                  Taban fiyat V'nin uygulandığı saat: {sayiTr(gt.mekanizma.v_tabani_saat)}.{gt.mekanizma.yon_varsayilan_saat > 0 ? ` Senaryo fiyatlı ${sayiTr(gt.mekanizma.yon_varsayilan_saat)} saatte sistem yönü dengede varsayıldı.` : ""}{gt.mekanizma.yon_eksik_saat > 0 ? ` ${sayiTr(gt.mekanizma.yon_eksik_saat)} saatte sistem yönü verisi yok, hesaplanmadı.` : ""}
                </p>
              )}
            </>
          )}
        </details>
      </Kart>
      <Kart baslik="Günlük sapma dağılımı (tahmin − gerçekleşen)"
        sag={<span className="cip">
          {/* v2.311: μ ve σ burada sayiTr'siz basılıyordu — aynı sayı KPI'da
              "-0,03", çipte "-0.03". Türkçe ondalık ayracı kaybolup panel iki
              farklı sayı yazımı gösteriyordu. */}
          <Meta items={[`${hd ? sayiTr(hd.ndays) : "—"} geçerli gün`, `ortalama ${hd?.mu != null ? `${sayiTr(hd.mu, 2)} MWh` : "—"}`,
            `std. sapma ${hd?.sd != null ? `${sayiTr(hd.sd, 2)} MWh` : "—"}`,
            hd?.p10 != null && hd?.p90 != null && `P10–P90: ${sayiTr(hd.p10, 2)} – ${sayiTr(hd.p90, 2)} MWh`]} />
        </span>}>
        {hd === undefined ? <YerTutucu yukseklik={353} /> : hd && hd.kutular.length > 0 ? (
          <>
            <EChart option={dagOption} height={280}
              ariaLabel="Günlük tahmin sapması histogramı, yüzdelik çizgileriyle" />
            <p style={{ fontSize: 13, color: "var(--soluk)", margin: "12px 0 0" }}>
              <b style={{ color: "var(--ikincil)" }}>Ne gösterir:</b>{" "}
              her mavi çubuk, günlük toplam sapması (tahmin − gerçekleşen, MWh) o aralığa
              düşen gün sayısını verir; sıfırın solu eksik, sağı fazla tahmindir. Kesikli
              çizgiler günlerin %80'inin arasında kaldığı P10 ve P90 sınırları, düz
              çizgi medyan, yeşil eğri birikimli paydır (sağ eksen).{" "}
              <b style={{ color: "var(--ikincil)" }}>Neye bakmalı:</b> gövde sıfır
              çevresinde ne kadar dar toplanırsa tahmin o kadar güvenilirdir; sola ya da
              sağa kayma sistematik eksik ya da fazla tahminin işaretidir.
            </p>
          </>
        ) : (
          <p style={{ fontSize: 14, color: "var(--soluk)", margin: 0 }}>
            Dağılım için henüz yeterli eşleşmiş gün birikmedi.
          </p>
        )}
      </Kart>
    </Sayfa>
  );
}
