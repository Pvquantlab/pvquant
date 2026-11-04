import { useEffect, useState } from "react";
import { useDamgaSurumu } from "../../shell/damgaOlay";
import { api } from "../../api/client";
import type { Takvim as TakvimTipi, TakvimOlay, TakvimBakim, KunyeTarihler } from "../../api/types";
import { Bilgi, Kart, Sayfa, sayiTr, SayfaIskeleti } from "./parcalar";
import { Meta } from "../../lib/Meta";
import { tarihBicimi } from "../../lib/bicim";
import { segmentKisa } from "../../lib/sozluk";

/** v2.518 (P3a) — Takvim: uzlaştırma, nakit ve mevzuat tarihleri santralın segmentine göre. Hesap sunucuda (ext/turkiye/takvim);
 *  burada yalnız gösterim ve santral tarihleri formu. Her tarih «mevzuat / hesaplanan / duyuru / santral tarihi» etiketi taşır; EPİAŞ
 *  duyurusuyla değişebilir. 01.11 incelemesi: günlük tabloya «Günler» sütunu (program/EAK her gün, avans/teminat iş günü), aylık tabloda
 *  adım dayanağı mevzuat öncelikli, lisans süresi satırı (−6 ay türetmesi kaldırıldı), geçmiş tarih etiketi. */
const AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
const gunAdi = (iso: string) => tarihBicimi("tr-TR", { weekday: "short" }).format(new Date(iso + "T00:00:00"));
const tarihKisa = (iso: string) => tarihBicimi("tr-TR", { day: "numeric", month: "short", year: "numeric" }).format(new Date(iso + "T00:00:00"));
const donemAdi = (d: string | null) => { if (!d) return ""; const [y, m] = d.split("-"); return `${AYLAR[Number(m) - 1]} ${y}`; };
const KAYNAK_TURU: Record<string, string> = { mevzuat: "mevzuat", hesaplanan: "hesaplanan", duyuru: "duyuru", kunye: "santral tarihi" };
const KAYNAK_ACIKLAMA: Record<string, string> = { mevzuat: "Metinde yazılı gün ya da saat", hesaplanan: "İş günü kaydırması ya da gün ekleme hesabı",
  duyuru: "EPİAŞ ya da EPDK'nın fiilî yayım kalıbı", kunye: "Santral tarihleri formuna girdiğiniz tarih ya da ondan türeyen" };
const gunKalan = (n: number) => `${sayiTr(n)} gün${n > 730 ? ` (${sayiTr(n / 365.25, 1)} yıl)` : ""}`;

const ISLEM_SINIF: Record<string, string> = { islem: "rozet-dikkat", takip: "rozet-notr", mevzuat: "rozet-notr", dogrulama: "rozet-uyari" };
const ISLEM_AD: Record<string, string> = { islem: "işlem gerekli", takip: "takip", mevzuat: "mevzuat değişikliği", dogrulama: "doğrulama gerekli" };
/** v2.524 (P3b): satırın sınıfı — işlem gerekli (santral), takip (başkasının adımı), mevzuat değişikliği, doğrulama gerekli (koşul kayıtlı değil) */
function IslemRozeti({ o }: { o: TakvimOlay }) {
  if (!o.islem) return null;
  return <span className={`rozet rozet-kucuk ${ISLEM_SINIF[o.islem]}`} title={`${ISLEM_AD[o.islem]}${o.sorumlu ? ` · ${o.sorumlu}` : ""}${o.not ? `: ${o.not}` : ""}`}>{ISLEM_AD[o.islem]}</span>;
}
/** ad + (varsa) not ipucu — uzun açıklama satırı yerine bilgi simgesi */
function OlayAdi({ o }: { o: TakvimOlay }) {
  return <>{o.ad}{o.not ? <Bilgi metin={o.not} /> : null}</>;
}

function KaynakRozeti({ o }: { o: TakvimOlay }) {
  // v2.535: ipucuna Resmî Gazete yayımı (tarih-sayı) — kaynak metni maddeyi, yayım satırı metnin hangi RG ile geldiğini söyler
  return <span className={`rozet rozet-kucuk ${o.kaynak_turu === "mevzuat" ? "rozet-ok" : "rozet-notr"}`} title={`${KAYNAK_ACIKLAMA[o.kaynak_turu]}: ${o.kaynak}${o.dayanak?.length ? `\n\nYayım: ${o.dayanak.join(" · ")}` : ""}`}>{KAYNAK_TURU[o.kaynak_turu]}</span>;
}

function GunUyarisi({ o }: { o: TakvimOlay }) {
  if (o.kaydirma === "belirsiz" && (o.hafta_sonu || o.tatil))
    return <span className="rozet rozet-uyari rozet-kucuk" title={o.not ?? "Hafta sonuna denk geliyor; metinde kaydırma kuralı yok"}>{o.tatil ? "tatil" : "hafta sonu"}</span>;
  if (o.kaydirma === "is_gunu" && o.not) return <span className="rozet rozet-notr rozet-kucuk" title={o.not}>iş gününe kaydırıldı</span>;
  return null;
}

const KUNYE_SIRA = ["lisans_yururluk", "lisans_bitis", "kabul_tarihi", "tam_kabul_tarihi", "isletmeye_giris", "yekdem_baslangic_yili", "police_bitis", "ced_karar_tarihi",
  "baglanti_anlasmasi", "toplayici_giris", "toplayici_cikis", "isg_son_kontrol", "ortaklik_degisikligi", "izin_iptali"];   // v2.524 (P3b): +4
const saatTr = (iso: string | null | undefined) => iso ? tarihBicimi("tr-TR", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(iso)) : "—";

function KunyeFormu({ plantId, kunye, bugun, onKaydet }: { plantId: string; kunye: KunyeTarihler; bugun: string; onKaydet: (k: KunyeTarihler) => void }) {
  const [v, setV] = useState<Record<string, string>>(() => Object.fromEntries(KUNYE_SIRA.map((k) => [k, kunye.alanlar[k] == null ? "" : String(kunye.alanlar[k])])));
  const [durum, setDurum] = useState<string | null>(null);
  const [hata, setHata] = useState<string | null>(null);
  useEffect(() => { setV(Object.fromEntries(KUNYE_SIRA.map((k) => [k, kunye.alanlar[k] == null ? "" : String(kunye.alanlar[k])]))); }, [kunye]);
  const kaydet = () => {
    setDurum("kaydediliyor…"); setHata(null);
    const g: Record<string, string | number | null> = {};
    for (const k of KUNYE_SIRA) g[k] = v[k] === "" ? null : k === "yekdem_baslangic_yili" ? Number(v[k]) : v[k];
    api.kunyeTarihler(plantId, g).then((r) => { setDurum("kaydedildi"); onKaydet(r.kunye); }).catch((e) => { setDurum(null); setHata(String((e as Error).message ?? e)); });
  };
  const t = kunye.turetilen;
  const lisansBitis = kunye.alanlar.lisans_bitis == null ? null : String(kunye.alanlar.lisans_bitis);
  const gecti = (iso: string) => iso < bugun;   // ISO tarih karşılaştırması
  return (
    <>
      <div className="form-izgara">
        {KUNYE_SIRA.map((k) => (
          <label key={k} className="girdi-etiket">{kunye.etiketler[k] ?? k}
            {k === "yekdem_baslangic_yili"
              ? <input className="girdi" inputMode="numeric" placeholder="ör. 2017" value={v[k]} onChange={(e) => setV({ ...v, [k]: e.target.value })} />
              : <input className="girdi" type="date" value={v[k]} onChange={(e) => setV({ ...v, [k]: e.target.value })} />}
          </label>))}
        <label className="girdi-etiket">&nbsp;
          <button className="dugme kucuk" onClick={kaydet}>Kaydet</button></label>
      </div>
      {durum && <div className="ayar-durum">{durum}</div>}
      {hata && <div className="ayar-durum hata">{hata}</div>}
      <dl className="kunye" style={{ marginTop: 12 }}>
        <div><dt>Lisans süresi</dt><dd>{lisansBitis && t.lisans_kalan_gun != null
          ? <><span className="kunye-sayi">{t.lisans_kalan_gun < 0 ? "doldu" : `${gunKalan(t.lisans_kalan_gun)} kaldı`}</span><span className="kunye-not">{tarihKisa(lisansBitis)} tarihinde kendiliğinden sona erer (Lisans Yönetmeliği m.26(1)(a)); süresinden önce sona erdirmek için istenen tarihten en az 6 ay önce EPDK'ya başvurulur (m.26(2))</span></>
          : <><span className="kunye-durum eksik">Belirtilmedi</span><span className="kunye-not">lisans bitiş tarihini girin</span></>}</dd></div>
        <div><dt>Lisans bedeli muafiyetinin sonu</dt><dd>{t.lisans_bedeli_muafiyet_bitis
          ? <><span className="kunye-sayi">{tarihKisa(t.lisans_bedeli_muafiyet_bitis)}{gecti(t.lisans_bedeli_muafiyet_bitis) ? " (geçti)" : ""}</span><span className="kunye-not">ilk kabulden sonraki 8 yıl alınmaz (yıl sayımı metinde açık değil); sonra her yıl Şubat, Haziran ve Ekim'in ilk 5 iş gününde üç taksit (Lisans Yönetmeliği m.43)</span></>
          : <><span className="kunye-durum eksik">Belirtilmedi</span><span className="kunye-not">ilk kabul tarihini girin</span></>}</dd></div>
        <div><dt>YEKDEM süresi</dt><dd>{t.yekdem
          ? <><span className="kunye-sayi">{t.yekdem.ilk_yil}–{t.yekdem.son_yil}{Number(bugun.slice(0, 4)) > t.yekdem.son_yil ? " (bitti)" : ""}</span><span className="kunye-not">{t.yekdem.kaynak}{t.yekdem.yerli_katki_bitis ? `; yerli katkı ${tarihKisa(t.yekdem.yerli_katki_bitis)}'e kadar` : ""}; sonrası serbest piyasa (dengesizlik ve KÜPST sorumluluğu)</span></>
          : <><span className="kunye-durum eksik">Belirtilmedi</span><span className="kunye-not">işletmeye giriş tarihini ya da YEKDEM başlangıç yılını girin</span></>}</dd></div>
        <div><dt>Sigorta poliçesi</dt><dd>{t.police_kalan_gun != null
          ? <><span className="kunye-sayi">{t.police_kalan_gun < 0 ? `${sayiTr(-t.police_kalan_gun)} gün önce bitti` : `${sayiTr(t.police_kalan_gun)} gün kaldı`}</span><span className="kunye-not">tesis varlıklarının doğal afet, yangın, kaza, hırsızlık, mali sorumluluk, terör ve sabotaja karşı teminat altına alınması zorunlu (Lisans Yönetmeliği m.47)</span></>
          : <><span className="kunye-durum eksik">Belirtilmedi</span><span className="kunye-not">poliçe bitiş tarihini girin</span></>}</dd></div>
        <div><dt>İlerleme raporu</dt><dd>{t.ilerleme_raporu_yukumlu === false
          ? <><span className="kunye-sayi">yükümlülük bitti</span><span className="kunye-not">kurulu gücün tamamı kabul edildi (tam kabul tarihi girildi)</span></>
          : <><span className="kunye-sayi">her yıl Ocak ve Temmuz sonu</span><span className="kunye-not">kurulu gücün tamamı kabul edilene kadar (Lisans Yönetmeliği m.30(2)(ç)); tamamı kabul edildiyse tam kabul tarihini girin</span></>}</dd></div>
        <div><dt>İSG periyodik kontrol</dt><dd>{t.isg_sonraki_kontrol
          ? <><span className="kunye-sayi">{tarihKisa(t.isg_sonraki_kontrol)}{gecti(t.isg_sonraki_kontrol) ? " (geçti)" : ""}</span><span className="kunye-not">elektrik, topraklama, yıldırımdan korunma, trafo ve akü tesisatı yılda bir (İş Ekipmanları Yönetmeliği Ek-III)</span></>
          : <><span className="kunye-durum eksik">Belirtilmedi</span><span className="kunye-not">son periyodik kontrol tarihini girin</span></>}</dd></div>
      </dl>
    </>
  );
}

export function Takvim({ plantId }: { plantId: string }) {
  const ds = useDamgaSurumu();
  const [t, setT] = useState<TakvimTipi | null | undefined>(undefined);
  useEffect(() => { let acik = true; setT(undefined); api.takvim(plantId, 90).then((v) => { if (acik) setT(v); }, () => { if (acik) setT(null); }); return () => { acik = false; }; }, [plantId, ds]);
  if (t === undefined) return <SayfaIskeleti kpi={0} kart={3} />;
  if (t === null) return (
    <Sayfa baslik="Takvim" alt="Uzlaştırma, nakit ve mevzuat tarihleri.">
      <Kart baslik="Takvim alınamadı"><div className="bos-durum"><div className="bos-bas">Sunucudan yanıt alınamadı</div><p>Sayfayı yenileyin.</p></div></Kart>
    </Sayfa>);
  const segmentAdi = t.segment ? segmentKisa(t.segment) : "segment seçilmedi";
  const olayKodlari = Array.from(new Set(t.donemler.flatMap((d) => d.olaylar.filter((o) => !t.segment || o.kapsam.includes(t.segment)).map((o) => o.kod))));
  // Adım satırının dayanağı: kuralın kendisi (mevzuat) öncelikli; iş günü kaydırması hücrede rozetle gösterilir, satırı «hesaplanan» yapmaz
  const hepsi = t.donemler.flatMap((d) => d.olaylar);
  const ilkOlay = (kod: string) => hepsi.find((o) => o.kod === kod && o.kaynak_turu === "mevzuat") ?? hepsi.find((o) => o.kod === kod)!;
  const yillar = t.tatil_yillari.length === 2 ? t.tatil_yillari.join(" ve ") : t.tatil_yillari.join(", ");
  const yaklasan = t.yaklasan_piyasa ?? t.yaklasan;   // v2.524: uyum tarihleri yalnız Uyum kartında
  return (
    <Sayfa baslik="Takvim" alt="Uzlaştırma, nakit ve mevzuat tarihleri; santralinizin segmentine göre.">
      <Kart baslik="Yaklaşan son tarihler" alt={`Önümüzdeki ${sayiTr(t.pencere_gun)} gün: uzlaştırma, nakit ve piyasa tarihleri. Lisans ve uyum tarihleri aşağıdaki Uyum takviminde.`}
            sag={<Meta items={[`bugün ${tarihKisa(t.bugun)}`, segmentAdi, t.segment ? undefined : "tüm segmentlerin tarihleri gösteriliyor"]} />}>
        {yaklasan.length === 0 ? <div className="bos-durum"><div className="bos-bas">Bu pencerede tarih yok</div><p>Takvim boş; segment ve santral tarihleri girildikçe dolar.</p></div> : (
          <div className="grafik-kaydir"><table className="veri takvim">
            <thead><tr><th>Tarih</th><th>Saat</th><th className="esnek">Ne</th><th title="Adımı yapan taraf">Kim</th><th>Dönem</th><th>Dayanak</th><th>Kalan</th></tr></thead>
            <tbody>{yaklasan.map((o, i) => (
              <tr key={`${o.kod}-${o.tarih}-${i}`} style={(o.kalan_gun ?? 99) <= 7 ? { fontWeight: 500 } : undefined}>
                <td><span className="kunye-sayi">{tarihKisa(o.tarih)}</span> <span className="soluk">{gunAdi(o.tarih)}</span> <GunUyarisi o={o} /></td>
                <td>{o.saat ?? "—"}</td>
                <td className="esnek"><OlayAdi o={o} /> <IslemRozeti o={o} /></td>
                <td className="soluk">{o.sorumlu ?? "—"}</td>
                <td>{o.donem ? donemAdi(o.donem) : "—"}</td>
                <td><KaynakRozeti o={o} /></td>
                <td>{o.kalan_gun === 0 ? "bugün" : `${sayiTr(o.kalan_gun ?? 0)} gün`}</td></tr>))}</tbody>
          </table></div>)}
        {/* v2.535 Takvim doğrulama turu: etiket/kaydırma açıklaması açılır alanda; bayramı tanımsız yıl uyarısı gizlenmez */}
        {(t.tatil_eksik_yillar?.length ?? 0) > 0 && (
          <p style={{ fontSize: 13, margin: "8px 0 0" }}><span className="rozet rozet-uyari rozet-kucuk">tatil takvimi eksik</span> {t.tatil_eksik_yillar!.join(", ")} yılı dinî bayramları henüz tanımlı değil; o yıla düşen iş günü hesapları bayram günlerini iş günü sayar.</p>)}
        <details className="aciklama" style={{ marginTop: 8 }}>
          <summary>Etiketler, kaydırma kuralları ve tatil takvimi</summary>
          <p className="soluk" style={{ fontSize: 13, margin: "6px 0 0" }}>{t.not} {t.tatil_kaynak}{t.tatil_yillari.length ? ` Dinî bayramlar ${yillar} için tanımlı.` : ""}</p>
        </details>
      </Kart>

      <Kart baslik="Uyum takvimi" alt="Önümüzdeki 12 ay: lisans ve bildirim yükümlülükleri, santral tarihlerinden türeyenler, olay kaydındaki planlı bakımların bildirim son anı."
            sag={<Meta items={[`${sayiTr(t.uyum.length)} tarih`, t.bakim.length ? `${sayiTr(t.bakim.length)} planlı bakım` : undefined]} />}>
        {t.uyum.length === 0 ? <div className="bos-durum"><div className="bos-bas">Bu segment için uyum tarihi yok</div><p>Santral tarihleri girildikçe liste dolar.</p></div> : (
          <div className="grafik-kaydir"><table className="veri takvim">
            <thead><tr><th>Tarih</th><th className="esnek">Ne</th><th title="Adımı yapan taraf">Kim</th><th>Dayanak</th><th title="Yükümlülük kaçırılınca ilgili madde ve ihtar süresi; bent eşlemesi Kurul takdirine bağlı («çıkarım»), tutar yazılmaz; tam metin ipucunda">Aykırılıkta</th><th>Kalan</th></tr></thead>
            <tbody>{t.uyum.map((o, i) => (
              <tr key={`${o.kod}-${o.tarih}-${i}`} style={(o.kalan_gun ?? 99) <= 14 ? { fontWeight: 500 } : undefined}>
                <td><span className="kunye-sayi">{tarihKisa(o.tarih)}</span> <span className="soluk">{gunAdi(o.tarih)}</span> <GunUyarisi o={o} /></td>
                <td className="esnek" title={o.kaynak}><OlayAdi o={o} /> <IslemRozeti o={o} /></td>
                <td className="soluk">{o.sorumlu ?? "—"}</td>
                <td><KaynakRozeti o={o} /></td>
                <td className="soluk" style={{ fontSize: 12.5, whiteSpace: "nowrap" }} title={o.sonuc ?? undefined}>{o.sonuc_kisa ?? o.sonuc ?? "—"}</td>
                <td>{o.kalan_gun === 0 ? "bugün" : `${sayiTr(o.kalan_gun ?? 0)} gün`}</td></tr>))}</tbody>
          </table></div>)}
        {t.bakim.length > 0 && (
          <div className="grafik-kaydir" style={{ marginTop: 10 }}><table className="veri takvim">
            <thead><tr><th>Planlı bakım</th><th>Süre</th><th className="esnek">Bildirim kuralı</th><th>Bildirim son anı</th></tr></thead>
            <tbody>{t.bakim.map((b: TakvimBakim) => (
              <tr key={b.olay_id} style={b.gecti ? { opacity: 0.7 } : undefined}>
                <td><span className="kunye-sayi">{saatTr(b.baslangic)}</span>{b.etkilenen_kw != null ? <span className="soluk"> · {sayiTr(b.etkilenen_kw)} kW</span> : null}</td>
                <td className="mono">{b.sure_saat != null ? `${sayiTr(b.sure_saat, 1)} sa` : "—"}</td>
                <td className="esnek" title={b.kaynak}>{b.kural}</td>
                <td>{b.son_an ? <><span className="kunye-sayi">{saatTr(b.son_an)}</span>{b.gecti ? <span className="soluk"> (geçti)</span> : null}</> : <span className="soluk">yıllık plan / süre yok</span>}</td></tr>))}</tbody>
          </table></div>)}
        <details className="aciklama" style={{ marginTop: 8 }}>
          <summary>Sınıflar, dayanaklar ve kapsam dışı olanlar</summary>
          <p className="soluk" style={{ fontSize: 13, margin: "6px 0 0" }}>{t.uyum_not}{t.bakim.length ? ` ${t.bakim_kaynak}.` : ""}</p>
        </details>
      </Kart>

      <Kart baslik="Aylık uzlaştırma ve fatura takvimi" alt="Fatura dönemi takvim ayıdır; adımlar izleyen ayda (DUY m.132, m.133; lisanssızda LÜY m.23, m.25, m.26).">
        {olayKodlari.length === 0 ? <p className="soluk">Bu segment için aylık uzlaştırma adımı yok.</p> : (
          <div className="grafik-kaydir"><table className="veri takvim">
            <thead><tr><th className="esnek">Adım</th>{t.donemler.map((d) => <th key={d.donem}>{donemAdi(d.donem)} dönemi</th>)}<th>Dayanak</th></tr></thead>
            <tbody>{olayKodlari.map((kod) => {
              const ornek = ilkOlay(kod);
              return (
                <tr key={kod}>
                  <td className="esnek" title={ornek.kaynak}>{ornek.ad}{ornek.sorumlu ? <span className="soluk"> · {ornek.sorumlu}</span> : null}</td>
                  {t.donemler.map((d) => { const o = d.olaylar.find((x) => x.kod === kod); return (
                    <td key={d.donem}>{o ? <><span className="kunye-sayi">{tarihKisa(o.tarih)}</span> <span className="soluk">{gunAdi(o.tarih)}</span>{(o.saat || (o.kaydirma === "belirsiz" && (o.hafta_sonu || o.tatil)) || (o.kaydirma === "is_gunu" && o.not)) ? <span className="hucre-alt">{o.saat ? <span className="kunye-sayi">{o.saat}</span> : null}{o.saat ? " " : ""}<GunUyarisi o={o} /></span> : null}</> : "—"}</td>); })}
                  <td><KaynakRozeti o={ornek} /></td>
                </tr>); })}</tbody>
          </table></div>)}
        <ul className="tanim-listesi">
          <li><b>Kaydırma</b><span>Nihai bildirim hafta sonu ya da tatile denk gelirse izleyen iş gününe kayar (m.132/A(1)); itiraz son anı (12'si 17:30) ve itiraz sonucu (14'ü 16:00) için metinde kaydırma kuralı yoktur, EPİAŞ duyurusuna bakın.</span></li>
          <li><b>Ödeme günü</b><span>Ödeme günleri iş günü sayımıyla hesaplanır: borçlu tebliği izleyen 6. iş günü, EPİAŞ alacaklıya en geç 7. iş günü ve tahsilat oranında öder; itiraz ödemeyi durdurmaz.</span></li>
          <li><b>Tutarlar</b><span>Avans, teminat ve fatura tutarları burada hesaplanmaz; EPYS bildirimi ve Takasbank dekontu esastır.</span></li>
        </ul>
      </Kart>

      <Kart baslik="Günlük piyasa saatleri" alt="Türkiye saati. Program ve EAK adımları her gün, avans ve teminat adımları iş günlerinde (hafta sonu ve tatilde izleyen ilk iş günü).">
        <div className="grafik-kaydir"><table className="veri takvim">
          <thead><tr><th>Saat</th><th>Günler</th><th className="esnek">Ne</th><th className="sar">Dayanak</th></tr></thead>
          <tbody>{t.gunluk.map((g, i) => <tr key={i}>
            <td>{/^\d\d:\d\d$/.test(g.saat) ? <span className="kunye-sayi">{g.saat}</span> : g.saat}</td>
            <td className="soluk">{g.gunler}</td>
            <td className="esnek" title={g.not ?? undefined}>{g.ad}{g.not ? <span className="soluk"> ({g.not})</span> : null}</td>
            {/* v2.535: madde atfı açılır metinde — satır kısa, tam dayanak tıklayınca */}
            <td className="sar soluk" style={{ fontSize: 12.5, minWidth: 160, maxWidth: 360 }}><details><summary style={{ cursor: "pointer" }}>{g.kaynak.split(/[;:(]/)[0].trim()}</summary><div style={{ marginTop: 4 }}>{g.kaynak}</div></details></td></tr>)}</tbody>
        </table></div>
      </Kart>

      <Kart baslik="Santral tarihleri" alt="Lisans, kabul, işletmeye giriş, poliçe, İSG kontrolü, ortaklık değişikliği ve izin iptali tarihleri; türeyen son tarihler yukarıdaki listelere «santral tarihi» etiketiyle girer.">
        <KunyeFormu plantId={plantId} kunye={t.kunye} bugun={t.bugun} onKaydet={(k) => { setT({ ...t, kunye: k }); api.takvim(plantId, 90).then((v) => setT(v), () => {}); }} />
      </Kart>
    </Sayfa>
  );
}
