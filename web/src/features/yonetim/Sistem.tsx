import { useEffect, useState } from "react";
import { SOZLUK, isDurumu, tazelik, sorunAdi, segmentKisa } from "../../lib/sozluk";
import { SEGMENTLER } from "../../api/types";
import { yonetim, yasTr, type SistemSagligi, type HizmetSagligi, type HsSantral, type IsKaydi, type SantralEnvanter, type Kiraci, type YekdemYonetim } from "../../api/yonetim";
import { hizmetDurumu } from "../../lib/durum";   // v2.608 (F5-D): hizmet durumu sözlüğü (müşteri paneliyle aynı)
import { Zaman } from "./ortak";
import { HizmetDurumu as Rozet, Kart, Kpi, Sayfa, SayfaIskeleti, sayiTr, gucTr } from "../sayfalar/parcalar";
import { Meta } from "../../lib/Meta";

/** 25.10 Faz 3 — SİSTEM: zamanlayıcı nabzı, gece turu tazeliği, hava/piyasa/yedek yaşı; müşteriler arası iş kayıtları (hata
 *  AYRINTISIYLA — müşteri panelinde bilerek yok); santral envanteri (sorun süzgeci); meteoroloji arşivi.
 *  Bayatlık hükümleri (durum/taze/bayat) ve eşikler uçtan gelir; arayüz yalnız okur ve renklendirir. Her sayı gerçek. */

const mesajCikar = (e: unknown) => String((e as Error).message ?? e);
function Hata({ m }: { m: string | null }) { return m ? <p role="alert" className="giris-hata" style={{ marginTop: 10 }}>{m}</p> : null; }
function Bos({ bas, alt }: { bas: string; alt?: string }) { return <div className="bos-durum"><div className="bos-bas">{bas}</div>{alt && <p>{alt}</p>}</div>; }
const boyutTr = (bayt: number) => bayt >= 1024 ** 3 ? `${sayiTr(bayt / 1024 ** 3, 2)} GB` : `${sayiTr(bayt / 1024 ** 2, 1)} MB`;
const sureTr = (sn: number | null) => sn == null ? "—" : sn >= 60 ? `${sayiTr(sn / 60, 1)} dk` : `${sayiTr(sn, 1)} sn`;
// 26.10 ortak sözlük: sorun adları, tazelik ve iş durumu sözcükleri lib/sozluk'tan (müşteri paneliyle aynı dil)
const sol = { textAlign: "left" as const };
/** Ayrıntı sütunu: .santral tablosunda öbür sütunlar 1 % (içerik genişliği); hata metni okunacak gerçek yer ister. */
const AYRINTI = { textAlign: "left" as const, whiteSpace: "normal" as const, width: "38%", minWidth: 240 };
const tarihTr = (s: string | null | undefined) => s ? new Date(s).toLocaleDateString("tr-TR") : "—";
// Meteo arşivi tablosu yarım kartta: .grafik-kaydir > table 620 px tabanı orada 440 (1440'ta kaydırmasız, 375'te kayar).

const BOLUM_ANAHTAR = "pvq_platform_sistem_bolum";
const BOYUT_AD: Record<string, string> = { veri: "Veri", tahmin: "Tahmin", kgup: "Program (KGÜP)", mutabakat: "Mutabakat", alarm: "Alarm / olay" };
const sureTrK = (sn: number | null) => sn == null ? "—" : sn < 60 ? `${sayiTr(sn, 1)} sn` : `${sayiTr(sn / 60, 1)} dk`;

/** v2.608 (Faz 5 F5-D) — SİSTEM iki bağımsız görünüm: SİSTEM SAĞLIĞI (altyapı sinyalleri: zamanlayıcı, gece işleri, hava verisi, EPİAŞ, veritabanı/yedek,
 *  sunucu; /sistem-sagligi) ve MÜŞTERİ HİZMET SAĞLIĞI (santral × veri/tahmin/program/mutabakat/alarm; /hizmet-sagligi). Teknik başarı hizmet
 *  başarısı sayılmaz: iki uç ayrı hesaplar, sayfa ikisini yan yana koymaz, sekmeyle ayırır. Hükümler uçtan; arayüz yalnız sözlükten sözcük basar. */
export function Sistem() {
  // başlatıcı yalnız OKUR (StrictMode iki kez çağırır); anahtar takıldıktan sonra silinir — hedefli açılış («Müşteri hizmet sağlığı →») tek seferliktir
  const [bolum, setBolum] = useState<"sistem" | "hizmet">(() => { try { return sessionStorage.getItem(BOLUM_ANAHTAR) === "hizmet" ? "hizmet" : "sistem"; } catch { return "sistem"; } });
  useEffect(() => { try { sessionStorage.removeItem(BOLUM_ANAHTAR); } catch { /* gizli pencere */ } }, []);
  const [sg, setSg] = useState<SistemSagligi | null>(null);
  const [hata, setHata] = useState<string | null>(null);
  const [sayac, setSayac] = useState(0);
  const [secSantral, setSecSantral] = useState<{ id: string; ad: string } | null>(null);   // 26.10 D2: envanterden «son hata» → iş kayıtları süzgeci
  useEffect(() => { yonetim.sistemSagligi().then(setSg).catch((e) => setHata(mesajCikar(e))); }, [sayac]);
  const o = sg?.ham ?? null;
  if (!o && !hata) return <Sayfa baslik="Sistem"><SayfaIskeleti kpi={6} kart={2} /></Sayfa>;
  return (
    <Sayfa baslik="Sistem" alt={bolum === "sistem" ? "Altyapı sinyalleri: zamanlayıcı, gece işlemleri, hava verisi, EPİAŞ, veritabanı ve yedek, sunucu; tüm müşterilerin iş kayıtları."
                                              : "PVQuant bu müşteriye şu an kullanılabilir sonuç üretiyor mu? Santral × veri, tahmin, program, mutabakat, alarm; kuruluş ve portföy toplamları."}
      sag={<span className="dugme-sira">
        <div className="sekme" role="group" aria-label="Sağlık görünümü">   {/* .sekme kalıbı: aria-pressed düğmeler (Tahminler ufuk seçici gibi) */}
          <button type="button" aria-pressed={bolum === "sistem"} onClick={() => setBolum("sistem")}>Sistem sağlığı</button>
          <button type="button" aria-pressed={bolum === "hizmet"} onClick={() => setBolum("hizmet")}>Müşteri hizmet sağlığı</button>
        </div>
        {o && <span className="cip"><Meta items={[`veritabanı ${boyutTr(o.db.boyut_bayt)}`, `${sayiTr(o.santral.etkin)} etkin santral`, `${sayiTr(o.santral.arsivli)} arşivli`]} /></span>}
        <button className="dugme kucuk" onClick={() => { setSg(null); setHata(null); setSayac((x) => x + 1); }}>Yenile</button></span>}>
      <Hata m={hata} />
      {bolum === "hizmet" ? <HizmetSagligiBolumu santralSec={(id, ad) => { setSecSantral({ id, ad }); setBolum("sistem"); window.setTimeout(() => document.getElementById("is-kayitlari")?.scrollIntoView({ behavior: "smooth", block: "start" }), 50); }} />
       : o && sg && <>
        {/* v2.608 (F5-D): altı bileşen, hüküm uçtan (durum sözlüğü); sinyali olmayan bileşen «doğrulanamadı» — yeşil değil */}
        <div className="plat-saglik" style={{ gap: 10 }}>
          <Rozet durum={sg.durum} etiket={`sistem: ${sg.etiket.toLocaleLowerCase("tr")}`} />
          <span className="soluk" style={{ fontSize: 13 }}>{sg.not}</span>
        </div>
        <div className="ızgara satir-3" style={{ marginBottom: 14 }}>
          {(["zamanlayici", "gece_isleri", "hava", "epias", "veritabani", "sunucu"] as const).map((k) => { const b = sg.bilesenler[k]; const AD = { zamanlayici: "Zamanlayıcı", gece_isleri: "Gece işlemleri", hava: "Hava verisi", epias: "EPİAŞ bağlantısı", veritabani: "Veritabanı ve yedek", sunucu: "Sunucu" }[k];
            return <div key={k} className="kpi"><div className="kpi-et">{AD}</div><div style={{ margin: "6px 0" }}><Rozet durum={b.durum} /></div><div className="kpi-br">{b.neden}</div></div>; })}
        </div>
        <div className="ızgara-cift" style={{ marginBottom: 14 }}>
          <Kart baslik="Dört zaman: bağlantı, veri alımı, en yeni kayıt, kullanılabilirlik" alt="Başarılı bağlantı yeni kayıt getirmemiş olabilir; dördü ayrı okunur">
            <dl className="kunye">
              <div><dt>Hava verisi: son indirme işi</dt><dd>{sg.bilesenler.hava.son_is ? <><Zaman s={sg.bilesenler.hava.son_is.zaman} /> <Rozet durum={sg.bilesenler.hava.son_is.tamam ? "saglikli" : "dikkat"} etiket={isDurumu(sg.bilesenler.hava.son_is.tamam)} /></> : "—"}</dd></div>
              <div><dt>Hava verisi: son indirme</dt><dd><Zaman s={sg.bilesenler.hava.son_indirme} /></dd></div>
              <div><dt>Hava verisi: en yeni tahmin koşusu</dt><dd><Zaman s={sg.bilesenler.hava.en_yeni_kosu} sar /><span className="kunye-not">arşivdeki en ileri saat; indirme başarılı olsa da bu eskiyse hava verisi eskidir</span></dd></div>
              <div><dt>EPİAŞ: son istek</dt><dd>{sg.bilesenler.epias.son_baglanti ? <><Zaman s={sg.bilesenler.epias.son_baglanti.zaman} /> <Rozet durum={sg.bilesenler.epias.son_baglanti.tamam ? "saglikli" : "dikkat"} etiket={isDurumu(sg.bilesenler.epias.son_baglanti.tamam)} />{sg.bilesenler.epias.son_baglanti.ayrinti && <span className="kunye-not">{sg.bilesenler.epias.son_baglanti.ayrinti}</span>}</> : "—"}</dd></div>
              <div><dt>EPİAŞ: son veri alımı</dt><dd><Zaman s={sg.bilesenler.epias.son_veri_alimi} /></dd></div>
              <div><dt>EPİAŞ: en yeni fiyat saati</dt><dd><Zaman s={sg.bilesenler.epias.en_yeni_kayit} /><span className="kunye-not">gerçekleşen PTF/SMF; ileri fiyat değil</span></dd></div>
              <div><dt>EPİAŞ: kullanılabilirlik (sistem yönü)</dt><dd><Zaman s={sg.bilesenler.epias.yon_son} /><span className="kunye-not">son 7 günde {sayiTr(sg.bilesenler.epias.yon_saat_7g)} saat yön; gün öncesi PTF <Zaman s={sg.bilesenler.epias.gop_son} /></span></dd></div>
              <div><dt>EPİAŞ: kimlik</dt><dd>{sg.bilesenler.epias.kimlik === true ? "tanımlı" : sg.bilesenler.epias.kimlik === false ? "tanımlı değil" : "okunamadı"}</dd></div>
            </dl>
          </Kart>
          <Kart baslik="Veritabanı, yedek ve sunucu" alt="yedek doğrulaması ve hata günlüğü sinyalsiz: «doğrulanamadı»">
            <dl className="kunye">
              <div><dt>Bağlantı</dt><dd><Rozet durum={sg.bilesenler.veritabani.baglanti.durum} /><span className="kunye-not">{sg.bilesenler.veritabani.baglanti.neden}; boyut {boyutTr(sg.bilesenler.veritabani.baglanti.boyut_bayt)}</span></dd></div>
              <div><dt>Yedek</dt><dd><Rozet durum={sg.bilesenler.veritabani.yedek.durum} /><span className="kunye-not">{sg.bilesenler.veritabani.yedek.neden}</span></dd></div>
              <div><dt>Yedek doğrulaması</dt><dd><Rozet durum={sg.bilesenler.veritabani.yedek_dogrulama.durum} /><span className="kunye-not">{sg.bilesenler.veritabani.yedek_dogrulama.neden}</span></dd></div>
              <div><dt>API</dt><dd><Rozet durum={sg.bilesenler.sunucu.api.durum} /><span className="kunye-not">{sg.bilesenler.sunucu.api.neden}</span></dd></div>
              <div><dt>Hata günlüğü</dt><dd><Rozet durum={sg.bilesenler.sunucu.hata_gunlugu.durum} /><span className="kunye-not">{sg.bilesenler.sunucu.hata_gunlugu.neden}</span></dd></div>
              <div><dt>İş hataları (24 sa)</dt><dd><Rozet durum={sg.bilesenler.sunucu.is_hatalari.durum} /><span className="kunye-not">{sg.bilesenler.sunucu.is_hatalari.neden}</span></dd></div>
            </dl>
          </Kart>
        </div>
        {/* 25.10 Faz 3 KPI'ları aynen: tonlar uçtan gelen durum/taze/bayat alanlarını okur */}
        <div className="ızgara satir-3" style={{ marginBottom: 14 }}>
          <Kpi etiket={SOZLUK.kaynak.zamanlayici} deger={o.nabiz.durum === "calisiyor" ? "çalışıyor" : o.nabiz.durum === "sessiz" ? "sessiz" : "nabız yok"}
            ton={o.nabiz.durum === "calisiyor" ? undefined : "uyari"}
            alt={o.nabiz.son ? `son nabız ${yasTr(o.nabiz.son)}; her ${sayiTr(o.nabiz.aralik_dk)} dk beklenir` : "worker henüz nabız yazmadı (eski imaj ya da kapalı)"} />
          {/* v2.516 (#3): hüküm = üretici işler (müşteri ölçütü) + izlenen uzlaştırma/piyasa/bakım işleri (her biri kendi eşiğiyle) */}
          <Kpi etiket={SOZLUK.kaynak.geceIsleri} deger={tazelik(!o.gece_turu.taze || (o.izlenen?.bayat.length ?? 0) > 0)}
            ton={o.gece_turu.taze && !(o.izlenen?.bayat.length) ? undefined : "uyari"}
            alt={!o.gece_turu.taze ? `${o.gece_turu.esik_saat} saattir koşmayan: ${o.gece_turu.bayat_isler.join(", ")}`
              : o.izlenen && o.izlenen.bayat.length > 0 ? `eşiğini aşan izlenen iş: ${o.izlenen.bayat.join(", ")}`
              : `son üretici iş ${yasTr(o.gece_turu.son)}${o.izlenen ? "; izlenen işlerde eşik aşımı yok" : ""}`} />
          <Kpi etiket="İşler" deger={sayiTr(o.isler_24.hata)} birim="hata" ton={o.isler_24.hata > 0 ? "uyari" : undefined}
            alt={`son 24 saatte ${sayiTr(o.isler_24.toplam)} iş kaydı`} />
          <Kpi etiket="Hava verisi" deger={o.meteo.kaynaklar.length ? yasTr(en_yeni(o.meteo.kaynaklar.map((k) => k.son_indirme))) : "arşiv yok"}
            ton={o.meteo.kaynaklar.length === 0 || o.meteo.kaynaklar.some((k) => k.bayat) ? "uyari" : undefined}
            alt={o.meteo.kaynaklar.length === 0 ? "meteo_arsiv tablosu boş"
              : o.meteo.kaynaklar.some((k) => k.bayat) ? `eski: ${o.meteo.kaynaklar.filter((k) => k.bayat).map((k) => `${k.kaynak} (${k.yas_saat == null ? "hiç" : sayiTr(k.yas_saat, 0) + " saat"})`).join(", ")}`
              : `${sayiTr(o.meteo.kaynaklar.length)} kaynak; ${o.meteo.esik_saat} saatten eskisi eski sayılır`} />
          {/* v2.516 (#4): yön kapsamı ve EPİAŞ kimliği de hükme girer — 29.10'da yön 0 saatti, kart «güncel» duruyordu */}
          <Kpi etiket={SOZLUK.kaynak.piyasaKisa} deger={yasTr(o.piyasa.son_guncelleme)}
            ton={o.piyasa.bayat || o.piyasa.kimlik === false || o.piyasa.yon_bayat ? "uyari" : undefined}
            alt={o.piyasa.kimlik === false ? "EPİAŞ kimliği tanımlı değil: fiyat ve yön çekilemez, uzlaştırma senaryo fiyatıyla hesaplanır"
              : !o.piyasa.son_ts ? "piyasa_fiyat tablosu boş"
              : `gerçekleşen PTF/SMF ${tarihTr(o.piyasa.son_ts)} gününe kadar (ileri fiyat değil); yön ${o.piyasa.yon_son ? `${tarihTr(o.piyasa.yon_son)} gününe kadar` : "yok"}${o.piyasa.yon_bayat ? " (eksik)" : ""}, son 7 günde ${sayiTr(o.piyasa.yon_saat_7g ?? 0)} saat${o.piyasa.gop_son ? `; gün öncesi PTF ${tarihTr(o.piyasa.gop_son)}` : ""}`} />
          <Kpi etiket={SOZLUK.kaynak.yedek} deger={yasTr(o.yedek.son_basarili)} ton={o.yedek.bayat || (o.yedek.son_deneme ? !o.yedek.son_deneme.tamam : false) ? "uyari" : undefined}
            alt={o.yedek.son_deneme ? (o.yedek.son_deneme.tamam ? `son deneme başarılı; ${o.yedek.esik_saat} saatten eskisi eski sayılır` : `son deneme başarısız: ${o.yedek.son_deneme.ayrinti ?? "ayrıntı yok"}`) : "henüz yedek kaydı yok"} />
        </div>
        <IsKayitlari santral={secSantral} temizle={() => setSecSantral(null)} />
        <Kart baslik="İş süreleri — son 7 gün, platform geneli" alt={`en uzun süreli ${sayiTr(sg.sureler.length)} iş; koşu sayısı, ortalama ve en uzun süre, başarısız sayısı; iş kayıtlarından, bitiş damgasız satır sayılmaz; listede olmayan iş ya hiç koşmadı ya kısa sürdü`} style={{ marginBottom: 14 }}>
          {sg.sureler.length === 0 ? <Bos bas="Son 7 günde biten iş kaydı yok." /> : (
            <div className="grafik-kaydir"><table className="veri sayisal" style={{ minWidth: 0 }}>
              <thead><tr><th style={sol}>İş</th><th>Koşu</th><th>Başarısız</th><th>Ortalama</th><th>En uzun</th><th style={sol}>Son</th></tr></thead>
              <tbody>{sg.sureler.map((u) => (
                <tr key={u.kod}><td style={sol}><span title={u.kod}>{u.is}</span></td><td>{sayiTr(u.n)}</td><td>{u.hata > 0 ? <span className="rozet rozet-uyari">{sayiTr(u.hata)}</span> : "0"}</td>
                  <td>{sureTrK(u.ort_sn)}</td><td>{sureTrK(u.en_uzun_sn)}</td><td style={sol}><Zaman s={u.son} /></td></tr>))}</tbody>
            </table></div>)}
        </Kart>
        <YekdemFiyatlari />
        <div className="ızgara-cift">
          <Kart baslik="Üretici ve izlenen işler" alt={`üretici işler (müşteri ölçütü): son başarılı koşu ${o.gece_turu.esik_saat} saatten yeni; izlenen işler kendi eşiğiyle`}>
            <div className="grafik-kaydir"><table className="veri sayisal" style={{ minWidth: 0 }}>
              <thead><tr><th style={sol}>İş</th><th style={sol}>Son başarılı koşu</th><th>Durum</th></tr></thead>
              <tbody>{o.gece_turu.uretici_isler.map((u) => { const bayat = o.gece_turu.bayat_isler.includes(u.is); return (
                <tr key={u.kod}><td style={sol}><span title={u.kod}>{u.is}</span></td><td style={sol}><Zaman s={u.son_ok} /></td>
                  <td><span className={`rozet ${bayat ? "rozet-uyari" : "rozet-ok"}`}>{tazelik(bayat)}</span></td></tr>); })}</tbody>
            </table></div>
            {/* v2.516 (#3): izlenen işler — uzlaştırma, piyasa ve bakım; durum kodu uçtan (ok / esik_asimi / henuz_yok / beklenmiyor), sözcük sözlükten */}
            {o.izlenen && <>
              <p className="soluk" style={{ fontSize: 13, margin: "14px 0 6px" }}>İzlenen işler: gün içi 30, günlük 36 saat, aylık 35 gün eşiği; müşteri hükmüne girmez, platform kartını uyarır.</p>
              <div className="grafik-kaydir"><table className="veri sayisal" style={{ minWidth: 0 }}>
                <thead><tr><th style={sol}>İş</th><th style={sol}>Sıklık</th><th style={sol}>Son başarılı koşu</th><th>Durum</th></tr></thead>
                <tbody>{o.izlenen.isler.map((u) => (
                  <tr key={u.kod}><td style={{ ...sol, whiteSpace: "normal", minWidth: 150 }}><span title={u.kod}>{u.is}</span></td><td style={sol}>{u.siklik}</td>
                    <td style={sol}><Zaman s={u.son_ok} /></td>
                    <td>{u.durum === "ok" ? <span className="rozet rozet-ok">{SOZLUK.tazelik.guncel}</span>
                      : u.durum === "esik_asimi" ? <span className="rozet rozet-uyari" title={u.son_ok ? `${sayiTr(u.yas_saat ?? 0, 0)} saat önce; eşik ${sayiTr(u.esik_saat)} saat` : "hiç başarılı koşu yok"}>{SOZLUK.tazelik.eski}</span>
                      : <span className="rozet rozet-notr" title={u.not ?? undefined}>{u.durum === "henuz_yok" ? "henüz koşmadı" : "beklenmiyor"}</span>}</td></tr>))}</tbody>
              </table></div></>}
          </Kart>
          <Kart baslik="Meteoroloji arşivi" alt="kaynak başına son indirme, nokta ve satır sayısı, kapsam">
            {o.meteo.kaynaklar.length === 0 ? <Bos bas="Arşivde kayıt yok." /> : (
              <div className="grafik-kaydir"><table className="veri sayisal" style={{ minWidth: 440 }}>
                <thead><tr><th style={sol}>Kaynak</th><th style={sol}>Son indirme</th><th>Nokta</th><th>Satır</th><th style={sol}>Kapsam</th></tr></thead>
                <tbody>{o.meteo.kaynaklar.map((k) => (
                  <tr key={k.kaynak}><td style={sol}>{k.kaynak}{k.bayat && <span className="rozet rozet-uyari" style={{ marginLeft: 8 }}>{SOZLUK.tazelik.eski}</span>}</td>
                    <td style={sol}><Zaman s={k.son_indirme} sar /></td><td>{k.nokta == null ? "—" : sayiTr(k.nokta)}</td>
                    <td>{k.satir == null ? "—" : sayiTr(k.satir)}</td>
                    <td style={sol}><span style={{ whiteSpace: "nowrap" }}>{tarihTr(k.ilk)}</span><br /><span style={{ whiteSpace: "nowrap" }}>→ {tarihTr(k.son_ts)}</span></td></tr>))}</tbody>
              </table></div>)}
          </Kart>
        </div>
      </>}
    </Sayfa>
  );
}

// ---------------- v2.520 (P5a): YEKDEM aylık fiyat ilanı (7189 sayılı CK) + TCMB kur arşivi ----------------
/** EPİAŞ'ın aylık ilanı elle girilir (EPİAŞ'ta uç yok); band konumu uçtan (bir önceki ayın ortalama USD alış kuru). Kur arşivi worker'la (16:05 TSİ)
 *  dolar; eksik iş günleri buradan tamamlanır. Müşteri panelindeki YEKDEM fiyatı ve m.23(6) işareti bu tablolardan beslenir. */
function YekdemFiyatlari() {
  const [o, setO] = useState<YekdemYonetim | null>(null); const [hata, setHata] = useState<string | null>(null); const [mesaj, setMesaj] = useState<string | null>(null);
  const [form, setForm] = useState({ ay: "", tesis_tipi: "gunes", fiyat: "", yerli: "", kaynak: "" });
  const [kur, setKur] = useState({ bas: "", bit: "" });
  const yukle = () => yonetim.yekdem().then((v) => { setO(v); setHata(null); }).catch((e) => setHata(mesajCikar(e)));
  useEffect(() => { void yukle(); }, []);
  const sayiOku = (t: string): number | null => { const x = t.trim(); if (x === "") return null; const n = Number(x.includes(",") ? x.replace(/\./g, "").replace(",", ".") : x); return Number.isFinite(n) ? n : NaN; };
  const kaydet = () => {
    setMesaj(null); const f = sayiOku(form.fiyat); const y = sayiOku(form.yerli);
    if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(form.ay)) { setMesaj("Geçerli dönem YYYY-AA biçiminde olmalı (ör. 2026-11)."); return; }
    if (f == null || Number.isNaN(f) || Number.isNaN(y)) { setMesaj("Fiyat (ve varsa yerli katkı) sayı olmalı; ör. 289,74."); return; }
    if (!/\d{1,2}\.\d{1,2}\.\d{4}/.test(form.kaynak)) { setMesaj("Kaynak alanına duyurunun adı ve tarihi yazılmalı; ör. «EPİAŞ duyurusu 01.10.2026»."); return; }
    yonetim.yekdemFiyat({ ay: form.ay, tesis_tipi: form.tesis_tipi, fiyat_kr_kwh: f, yerli_katki_kr_kwh: y, kaynak: form.kaynak.trim() })
      .then((r) => { setMesaj(`Kaydedildi: ${AYAD(r.ay)} ${o?.tesis_etiket[r.tesis_tipi] ?? r.tesis_tipi} ${sayiTr(r.fiyat_kr_kwh, 2)} kuruş/kWh.`); setForm({ ...form, fiyat: "", yerli: "", kaynak: "" }); void yukle(); })
      .catch((e) => setMesaj(mesajCikar(e)));
  };
  const doldur = () => {
    setMesaj(null);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(kur.bas) || !/^\d{4}-\d{2}-\d{2}$/.test(kur.bit)) { setMesaj("Başlangıç ve bitiş YYYY-AA-GG biçiminde olmalı."); return; }
    yonetim.kurDoldur(kur.bas, kur.bit).then((r) => { setMesaj(`${sayiTr(r.yazilan)} bülten yazıldı${r.bulunamayan.length ? `; TCMB'de bülteni olmayan iş günü: ${r.bulunamayan.map(tarihTr).join(", ")}` : ""}.`); void yukle(); })
      .catch((e) => setMesaj(mesajCikar(e)));
  };
  const AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  const AYAD = (ay: string) => { const [y, m] = ay.split("-").map(Number); return m >= 1 && m <= 12 ? `${AYLAR[m - 1]} ${y}` : ay; };
  const SINIR: Record<string, string> = { icinde: "sınırlar içinde", tabanda: "alt sınırda (kırpma)", tavanda: "üst sınırda (kırpma)" };
  const KAYIT: Record<string, string> = { resmi: "resmî duyuru", elle: "elle giriş", dogrulanmamis: "doğrulanmadı" };
  return (
    <Kart baslik="YEKDEM fiyatları ve döviz kuru" alt="7189 sayılı CK kapsamındaki tesisler için EPİAŞ'ın aylık ilan ettiği fiyat (kuruş/kWh) ve TCMB gösterge alış kuru arşivi; müşteri panelindeki YEKDEM fiyatı ve m.23(6) işareti bu kayıtlardan hesaplanır">
      <Hata m={hata} />
      {!o && !hata ? <p className="soluk" style={{ margin: 0 }}>Yükleniyor…</p> : o && <>
        <p style={{ fontSize: 13.5, margin: "0 0 8px" }}>
          Resmî kaynaklar: <a href={o.kaynaklar.epias_url} target="_blank" rel="noreferrer">EPİAŞ fiyat duyurusu</a> · <a href={o.kaynaklar.tcmb_url} target="_blank" rel="noreferrer">TCMB gösterge kurları</a> · {o.kaynaklar.mevzuat}.
        </p>
        <p className="soluk" style={{ fontSize: 13.5, margin: "0 0 10px" }}>
          Kayıt durumu kaynağın tarihinden türetilir: «resmî duyuru» = EPİAŞ duyurusu, tarihli, dönemle ve kayıt zamanıyla tutarlı; «doğrulanmadı» = kaynak ya da tarih eksik, tarih gelecekte, dönemden önce ya da kayıttan sonra.
          {o.bekleyen.length > 0 && <> <span className="rozet rozet-notr">bekleyen</span> {o.bekleyen.map((b) => `${AYAD(b.ay)} ${o.tesis_etiket[b.tesis_tipi] ?? b.tesis_tipi}`).join(", ")}: EPİAŞ ilanı henüz girilmedi; müşteri paneli önceki ayın fiyatını işaretli olarak taşır.</>}
        </p>
        <div className="grafik-kaydir"><table className="veri sayisal" style={{ minWidth: 0 }}>
          <thead><tr><th style={sol}>Geçerli dönem</th><th style={sol}>Tesis tipi</th><th>Fiyat (kuruş/kWh)</th><th>Yerli katkı (kuruş/kWh)</th><th title="Bir önceki ayın ortalama TCMB USD alış kuruyla">USD karşılığı (¢/kWh)</th><th style={sol} title="7189 sayılı CK Ek-2: fiyat alt–üst sınır dışına çıkarsa kırpılır">USD sınır kontrolü</th><th style={sol}>Kaynak</th><th style={sol}>Kayıt durumu</th><th style={sol}>Kayıt zamanı</th></tr></thead>
          <tbody>{o.fiyatlar.length === 0 ? <tr><td colSpan={9} style={sol}>İlan girilmedi.</td></tr> : o.fiyatlar.map((f) => (
            <tr key={`${f.ay}/${f.tesis_tipi}`}><td style={sol}>{AYAD(f.ay)}</td><td style={sol}>{o.tesis_etiket[f.tesis_tipi] ?? f.tesis_tipi}</td><td>{sayiTr(f.fiyat_kr_kwh, 2)}</td>
              <td>{f.yerli_katki_kr_kwh != null ? sayiTr(f.yerli_katki_kr_kwh, 2) : "—"}</td><td>{f.bant.usd_cent != null ? sayiTr(f.bant.usd_cent, 2) : "—"}</td>
              <td style={sol}>{f.bant.durum === "kur_yok" ? <span className="soluk" title="Kur arşivini doldurun; worker ilk koşuda 13 ayı tamamlar">{AYAD(f.bant.kur_ayi)} kuru arşivde yok</span>
                : <span className={`rozet ${f.bant.durum === "icinde" && !(f.bant.kur_eksik_gun?.length) ? "rozet-ok" : "rozet-uyari"}`} title={`${sayiTr(f.bant.taban_cent, 2)}–${sayiTr(f.bant.tavan_cent, 2)} ¢/kWh; ${AYAD(f.bant.kur_ayi)} ortalama USD alış kuru ${f.bant.kur_ortalama != null ? sayiTr(f.bant.kur_ortalama, 4) : "—"} TL (${sayiTr(f.bant.kur_gun ?? 0)}/${sayiTr(f.bant.kur_beklenen ?? 0)} bülten)`}>{SINIR[f.bant.durum] ?? f.bant.durum}{f.bant.kur_eksik_gun?.length ? ` (kur arşivi ${sayiTr(f.bant.kur_eksik_gun.length)} gün eksik)` : ""}</span>}</td>
              <td style={{ ...sol, whiteSpace: "normal", minWidth: 180 }} title={f.kaynak ?? undefined}>{(f.kaynak ?? "—").replace(/\s*\(7189 sayılı CK Ek-2 aylık güncelleme\)/, "")}</td>
              <td style={sol}><span className={`rozet ${f.kayit.durum === "resmi" ? "rozet-ok" : f.kayit.durum === "elle" ? "rozet-notr" : "rozet-uyari"}`} title={f.kayit.neden}>{KAYIT[f.kayit.durum]}</span></td>
              <td style={sol}><Zaman s={f.guncelleme} /></td></tr>))}</tbody>
        </table></div>
        <p className="etiket-ust" style={{ margin: "14px 0 6px" }}>Aylık ilan girişi</p>
        <div className="form-izgara">
          <label className="girdi-etiket">Geçerli dönem (YYYY-AA)<input className="girdi" value={form.ay} placeholder="2026-11" onChange={(e) => setForm({ ...form, ay: e.target.value })} /></label>
          <label className="girdi-etiket">Tesis tipi<select className="girdi" value={form.tesis_tipi} onChange={(e) => setForm({ ...form, tesis_tipi: e.target.value })}>
            {o.tesis_tipleri.map((t) => <option key={t} value={t}>{o.tesis_etiket[t] ?? t}</option>)}</select></label>
          <label className="girdi-etiket">Fiyat (kuruş/kWh)<input className="girdi" inputMode="decimal" value={form.fiyat} placeholder="ör. 289,74" onChange={(e) => setForm({ ...form, fiyat: e.target.value })} /></label>
          <label className="girdi-etiket">Yerli katkı (kuruş/kWh, isteğe bağlı)<input className="girdi" inputMode="decimal" value={form.yerli} placeholder="ör. 78,74" onChange={(e) => setForm({ ...form, yerli: e.target.value })} /></label>
          <label className="girdi-etiket">Kaynak (duyurunun adı ve tarihi, zorunlu)<input className="girdi" value={form.kaynak} placeholder="EPİAŞ duyurusu 01.10.2026" onChange={(e) => setForm({ ...form, kaynak: e.target.value })} /></label>
          <div className="form-tam dugme-sira"><button className="dugme" onClick={kaydet}>İlanı kaydet</button></div>
        </div>
        <p className="etiket-ust" style={{ margin: "14px 0 6px" }}>Kur arşivi</p>
        <p className="soluk" style={{ fontSize: 13.5, margin: "0 0 8px" }}>
          {o.kur.son_gun ? <>Son bülten {tarihTr(o.kur.son_gun)} (USD alış {o.kur.son_usd_alis != null ? sayiTr(o.kur.son_usd_alis, 4) : "—"} TL); {sayiTr(o.kur.gun_sayisi)} bülten{o.kur.ilk_gun ? `, ${tarihTr(o.kur.ilk_gun)} tarihinden` : ""}.</> : "Arşiv boş; worker ilk koşuda son 13 ayı TCMB'den tamamlar."}
          {" "}Son 30 günde TCMB bülteni eksik iş günü: {o.kur.eksik_is_gunu_30.length ? o.kur.eksik_is_gunu_30.map(tarihTr).join(", ") : "yok"}. Hafta sonu, resmî tatil ve arefe yarım günlerinde bülten yayımlanmaz; o günler için önceki iş gününün kuru uygulanır.
        </p>
        <div className="form-izgara">
          <label className="girdi-etiket">Başlangıç (YYYY-AA-GG)<input className="girdi" value={kur.bas} placeholder="2026-08-01" onChange={(e) => setKur({ ...kur, bas: e.target.value })} /></label>
          <label className="girdi-etiket">Bitiş (YYYY-AA-GG)<input className="girdi" value={kur.bit} placeholder="2026-10-31" onChange={(e) => setKur({ ...kur, bit: e.target.value })} /></label>
          <div className="form-tam dugme-sira"><button className="dugme" onClick={doldur}>Eksik iş günlerini TCMB'den doldur</button>
            {mesaj && <span className={`ayar-durum ${mesaj.startsWith("Kayded") || /bülten yazıldı/.test(mesaj) ? "ok" : "hata"}`}>{mesaj}</span>}</div>
        </div>
        <p className="soluk" style={{ fontSize: 13.5, margin: "10px 0 0" }}>Alt–üst sınır: güneş {sayiTr(o.bant_cent.gunes[0], 2)}–{sayiTr(o.bant_cent.gunes[1], 2)}, bütünleşik depolamalı {sayiTr(o.bant_cent.gunes_depolamali[0], 2)}–{sayiTr(o.bant_cent.gunes_depolamali[1], 2)} ¢/kWh; başlangıç fiyatları {sayiTr(o.baslangic_kr.gunes[0], 2)} / {sayiTr(o.baslangic_kr.gunes_depolamali[0], 2)} kuruş/kWh (7189 sayılı CK Ek-1). Birimler: fiyat kuruş/kWh (×10 = TL/MWh); USD karşılığı = kuruş/kWh ÷ bir önceki ayın ortalama TL/USD alış kuru. Her kayıt denetim izine düşer; aynı dönem ve tesis tipi için yeni kayıt eskisinin üzerine yazar.</p>
      </>}
    </Kart>
  );
}

const en_yeni = (zamanlar: (string | null)[]): string | null =>
  zamanlar.filter((z): z is string => !!z).sort().at(-1) ?? null;

// ---------------- iş kayıtları (müşteriler arası, hata ayrıntısıyla) ----------------
function IsKayitlari({ santral, temizle }: { santral: { id: string; ad: string } | null; temizle: () => void }) {
  const [saat, setSaat] = useState(48); const [yalnizHata, setYalnizHata] = useState(false); const [job, setJob] = useState(""); const [tenant, setTenant] = useState("");
  const [liste, setListe] = useState<IsKaydi[] | null>(null); const [turler, setTurler] = useState<{ kod: string; is: string }[]>([]);
  const [kiracilar, setKiracilar] = useState<Kiraci[]>([]); const [hata, setHata] = useState<string | null>(null);
  const getir = (ek: { saat?: number; yalniz_hata?: boolean; plant?: string | null } = {}) => yonetim.isler({ saat: ek.saat ?? saat, yalniz_hata: ek.yalniz_hata ?? yalnizHata, job: job || undefined,
      tenant_id: tenant || undefined, limit: 200, plant_id: ek.plant === undefined ? santral?.id : ek.plant ?? undefined })
    .then((r) => { setListe(r.isler); setTurler(r.is_turleri); }).catch((e) => setHata(mesajCikar(e)));
  useEffect(() => { void getir(); yonetim.kiracilar().then((r) => setKiracilar(r.kiracilar)).catch(() => {}); }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  // 26.10 D2: envanterden santral seçilince son 30 gün + yalnız başarısız; temizlenince varsayılan pencere
  useEffect(() => { if (santral) { setSaat(720); setYalnizHata(true); void getir({ saat: 720, yalniz_hata: true }); } }, [santral]);   // eslint-disable-line react-hooks/exhaustive-deps
  const hataSayisi = liste ? liste.filter((x) => !x.tamam).length : 0;
  return (
    <Kart baslik="İş kayıtları" alt="tüm müşteriler; başarısız işin ayrıntısı burada görünür, müşteri panelinde görünmez" id="is-kayitlari"
      sag={<span className="dugme-sira">{santral && <span className="rozet rozet-uyari">santral: {santral.ad} <button type="button" className="plat-rozet-kapat" aria-label="santral süzgecini kaldır" onClick={() => { temizle(); setSaat(48); setYalnizHata(false); void getir({ saat: 48, yalniz_hata: false, plant: null }); }}>×</button></span>}
        {liste && <span className="cip"><Meta items={[`${sayiTr(liste.length)} kayıt`, `${sayiTr(hataSayisi)} hata`]} /></span>}</span>}>
      <form className="form-izgara" style={{ maxWidth: 900, marginBottom: 12 }} onSubmit={(e) => { e.preventDefault(); void getir(); }}>
        <label className="girdi-etiket">Pencere<select className="girdi" value={saat} onChange={(e) => setSaat(Number(e.target.value))}>
          <option value={24}>son 24 saat</option><option value={48}>son 48 saat</option><option value={72}>son 72 saat</option><option value={168}>son 7 gün</option><option value={720}>son 30 gün</option></select></label>
        <label className="girdi-etiket">Durum<select className="girdi" value={yalnizHata ? "hata" : ""} onChange={(e) => setYalnizHata(e.target.value === "hata")}>
          <option value="">tümü</option><option value="hata">yalnız başarısız</option></select></label>
        <label className="girdi-etiket">İş<select className="girdi" value={job} onChange={(e) => setJob(e.target.value)}>
          <option value="">tümü</option>{turler.map((t) => <option key={t.kod} value={t.kod}>{t.is}</option>)}</select></label>
        <label className="girdi-etiket">Müşteri<select className="girdi" value={tenant} onChange={(e) => setTenant(e.target.value)}>
          <option value="">tümü</option>{kiracilar.map((k) => <option key={k.id} value={k.id}>{k.ad}</option>)}</select></label>
        <button className="dugme" type="submit">Süz</button>
      </form>
      <Hata m={hata} />
      {!liste ? <SayfaIskeleti kpi={0} kart={1} /> : liste.length === 0 ? <Bos bas="Süzgece uyan iş kaydı yok." /> : (
        <div className="grafik-kaydir"><table className="veri santral">
          <thead><tr><th>İş</th><th>Zaman</th><th>Müşteri</th><th>Santral</th><th>Süre</th><th>Durum</th><th style={AYRINTI}>Ayrıntı</th></tr></thead>
          <tbody>{liste.map((x) => (
            <tr key={x.id}><td className="ad">{x.is}</td><td style={{ whiteSpace: "nowrap" }}><Zaman s={x.zaman} /></td>
              <td style={{ whiteSpace: "nowrap" }}>{x.kiraci ?? (x.tenant_id ? x.tenant_id.slice(0, 8) : "—")}</td>
              <td style={{ whiteSpace: "nowrap" }}>{x.santral ?? (x.plant_id ? x.plant_id.slice(0, 8) : "—")}</td><td style={{ whiteSpace: "nowrap" }}>{sureTr(x.sure_sn)}</td>
              <td><span className={`rozet ${x.tamam ? "rozet-ok" : "rozet-uyari"}`}>{isDurumu(x.tamam)}</span></td>
              <td style={{ ...AYRINTI, fontSize: 13.5, color: x.tamam ? "var(--ikincil)" : undefined }}>{x.ayrinti ?? "—"}</td></tr>))}</tbody>
        </table></div>)}
    </Kart>
  );
}

// ---------------- v2.608 (Faz 5 F5-D): MÜŞTERİ HİZMET SAĞLIĞI ----------------
/** Kuruluş × boyut ısı tablosu, santral listesi (yalnız sorunlu / kuruluş süzgeci), ardından mevcut santral envanteri. Veri tek uçtan (/hizmet-sagligi);
 *  hükümler ve sözcükler sözlükten. TPYS kabulü ve EPİAŞ uzlaştırma durumu burada da «doğrulanamadı» olarak görünür. */
function HizmetSagligiBolumu({ santralSec }: { santralSec: (id: string, ad: string) => void }) {
  const [sorunlu, setSorunlu] = useState(false);
  const [tenant, setTenant] = useState<string>("");
  const [v, setV] = useState<HizmetSagligi | null>(null);
  const [hata, setHata] = useState<string | null>(null);
  useEffect(() => { setV(null); yonetim.hizmetSagligi({ tenant_id: tenant || undefined, yalniz_sorunlu: sorunlu }).then(setV).catch((e) => setHata(mesajCikar(e))); }, [tenant, sorunlu]);
  const BOYUTLAR = ["veri", "tahmin", "kgup", "mutabakat", "alarm"] as const;
  return (
    <>
      <Hata m={hata} />
      {!v ? <SayfaIskeleti kpi={5} kart={2} /> : <>
        <div className="plat-saglik" style={{ gap: 10 }}>
          <Rozet durum={v.ozet.durum} etiket={`müşteri hizmeti: ${v.ozet.etiket.toLocaleLowerCase("tr")}`} />
          <span className="soluk" style={{ fontSize: 13 }}><Meta items={[`${sayiTr(v.ozet.santral)} santral`, `${sayiTr(v.ozet.kurulus ?? v.kuruluslar.length)} kuruluş`, `${sayiTr(v.ozet.dikkat_kurulus ?? 0)} kuruluşta dikkat`, v.yarin ? `program günü ${v.yarin}` : null, v.donem ? `mutabakat dönemi ${v.donem}` : null].filter(Boolean) as string[]} /></span>
        </div>
        <div className="ızgara satir-5" style={{ marginBottom: 14 }}>
          {BOYUTLAR.map((b) => { const d = v.ozet.boyut[b]; const s = d?.sayim ?? {};
            return <div key={b} className="kpi"><div className="kpi-et">{BOYUT_AD[b]}</div><div style={{ margin: "6px 0" }}>{d ? <Rozet durum={d.durum} /> : "—"}</div>
              <div className="kpi-br">{sayiTr(s.kritik ?? 0)} kritik · {sayiTr(s.dikkat ?? 0)} dikkat · {sayiTr(s.saglikli ?? 0)} sağlıklı{(s.dogrulanamadi ?? 0) > 0 ? ` · ${sayiTr(s.dogrulanamadi)} doğrulanamadı` : ""}</div></div>; })}
        </div>
        <Kart baslik="Kuruluşlar × boyut" alt="satırda kuruluşun en kötü hükmü; hücrede boyutun kuruluş içindeki en kötü hükmü ve sayımı; satıra tıklayınca santral listesi süzülür" style={{ marginBottom: 14 }}>
          {v.kuruluslar.length === 0 ? <Bos bas="Etkin santrali olan kuruluş yok." /> : (
            <div className="grafik-kaydir"><table className="veri sayisal" style={{ minWidth: 0 }}>
              <thead><tr><th style={sol}>Kuruluş</th><th>Santral</th><th>Hüküm</th>{BOYUTLAR.map((b) => <th key={b}>{BOYUT_AD[b]}</th>)}<th style={sol}>Dikkat gereken</th></tr></thead>
              <tbody>{v.kuruluslar.map((k) => (
                <tr key={k.id} className="satir-tikla" onClick={() => setTenant(tenant === k.id ? "" : k.id)} aria-selected={tenant === k.id}>
                  <td style={sol}>{k.ad}</td><td>{sayiTr(k.santral)}</td><td><Rozet durum={k.durum} /></td>
                  {BOYUTLAR.map((b) => { const d = k.boyut[b]; return <td key={b}>{d ? <Rozet durum={d.durum} title={Object.entries(d.sayim).filter(([, n]) => n > 0).map(([ad, n]) => `${hizmetDurumu(ad).etiket} ${n}`).join(" · ")} /> : "—"}</td>; })}
                  <td style={{ ...sol, whiteSpace: "normal", minWidth: 180 }}>{k.dikkat_santral.length === 0 ? <span className="soluk">yok</span> : k.dikkat_santral.slice(0, 4).map((x) => x.ad).join(", ") + (k.dikkat_santral.length > 4 ? ` +${sayiTr(k.dikkat_santral.length - 4)}` : "")}</td>
                </tr>))}</tbody>
            </table></div>)}
        </Kart>
        <Kart baslik="Santraller" alt="her santralın beş boyutu; rozetin üstünde neden; «son iş hatası» iş kayıtlarına götürür" style={{ marginBottom: 14 }}
          sag={<span className="dugme-sira">{tenant && <span className="rozet rozet-uyari">kuruluş: {v.kuruluslar.find((k) => k.id === tenant)?.ad ?? tenant} <button type="button" className="plat-rozet-kapat" aria-label="kuruluş süzgecini kaldır" onClick={() => setTenant("")}>×</button></span>}
            <label className="ayar-onay" style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 13.5, cursor: "pointer" }}><input type="checkbox" checked={sorunlu} onChange={(e) => setSorunlu(e.target.checked)} />yalnız sorunlu</label></span>}>
          {v.santraller.length === 0 ? <Bos bas={sorunlu ? "Sorunlu santral yok." : "Etkin santral yok."} /> : (
            <div className="grafik-kaydir"><table className="veri sayisal santral plat-envanter">
              <thead><tr><th>Müşteri</th><th>Santral</th><th>Hüküm</th>{BOYUTLAR.map((b) => <th key={b}>{BOYUT_AD[b]}</th>)}<th style={sol}>Eylem gereken</th></tr></thead>
              <tbody>{v.santraller.map((p: HsSantral) => (
                <tr key={p.id}><td className="ad">{p.kiraci}</td><td>{p.ad}<div className="kunye-not">{p.kapasite_kwp ? `${gucTr(p.kapasite_kwp)} kWp` : "kurulu güç girilmemiş"}{p.segment ? ` · ${segmentKisa(p.segment)}` : " · segment seçilmedi"}</div></td>
                  <td><Rozet durum={p.durum} /></td>
                  {BOYUTLAR.map((b) => { const d = p.boyutlar[b]; return <td key={b}>{d ? <Rozet durum={d.durum} title={d.neden} /> : "—"}</td>; })}
                  <td style={{ ...sol, whiteSpace: "normal", minWidth: 220 }}>{p.eylem_gereken.length === 0 ? <span className="soluk">yok</span> : p.eylem_gereken.map((b) => `${BOYUT_AD[b] ?? b}: ${p.boyutlar[b]?.neden ?? ""}`).join(" · ")}
                    {p.boyutlar.alarm?.son_is_hatasi ? <div className="kunye-not"><button type="button" className="plat-baglanti" onClick={() => santralSec(p.id, p.ad)}>son iş hatası {yasTr(String(p.boyutlar.alarm.son_is_hatasi))}</button></div> : null}</td>
                </tr>))}</tbody>
            </table></div>)}
          <p className="soluk" style={{ fontSize: 13.5, margin: "10px 0 0" }}>{v.not}</p>
        </Kart>
      </>}
      <SantralEnvanteri santralSec={santralSec} />
    </>
  );
}

// ---------------- santral envanteri ----------------
function SantralEnvanteri({ santralSec }: { santralSec: (id: string, ad: string) => void }) {
  const [sorunlu, setSorunlu] = useState(false);
  const [veri, setVeri] = useState<{ santraller: SantralEnvanter[]; esik: { scada_saat: number; kosu_saat: number }; toplam: number; yarin?: string } | null>(null);
  const [hata, setHata] = useState<string | null>(null);
  useEffect(() => { setVeri(null); yonetim.santraller(sorunlu).then(setVeri).catch((e) => setHata(mesajCikar(e))); }, [sorunlu]);
  return (
    <Kart baslik="Santral envanteri" alt={veri ? `SCADA ${veri.esik.scada_saat} saatten, tahmin koşusu ${veri.esik.kosu_saat} saatten eskiyse sorun sayılır` : undefined}
      sag={<label className="ayar-onay" style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 13.5, cursor: "pointer" }}>
        <input type="checkbox" checked={sorunlu} onChange={(e) => setSorunlu(e.target.checked)} />yalnız sorunlu</label>}>
      <Hata m={hata} />
      {!veri ? <SayfaIskeleti kpi={0} kart={1} /> : veri.santraller.length === 0 ? <Bos bas={sorunlu ? "Sorunlu santral yok." : "Etkin santral yok."} alt={sorunlu ? `${sayiTr(veri.toplam)} etkin santralin hepsi veri alıyor ve koşuyor.` : undefined} /> : (
        <div className="grafik-kaydir"><table className="veri sayisal santral plat-envanter">
          <thead><tr><th>Müşteri</th><th>Santral<span className="birim">kurulu güç kWp</span></th>
            <th title="Piyasa segmenti ve altında UEVÇB kodu (müşteri Santralim › Santral ayarları'ndan seçer); segment yoksa KÜPST/DSG hesaplanamaz">Segment<span className="birim">UEVÇB</span></th>
            <th title={veri.yarin ? `Yarının (${veri.yarin}) teslim günü için KGÜP arşivi: PVQuant önerisi sürümü, müşterinin bildirdiğini beyan ettiği dosya, EAK dosyası` : undefined}>KGÜP<span className="birim">yarın</span></th>
            <th>Son veri<span className="birim">SCADA</span></th><th>Son tahmin</th><th>Sorun<span className="birim">son hata</span></th></tr></thead>
          <tbody>{veri.santraller.map((p) => (
            <tr key={p.id}><td className="ad">{p.kiraci}</td><td>{p.ad}<div className="kunye-not">{p.kapasite_kwp ? `${gucTr(p.kapasite_kwp)} kWp` : "kurulu güç girilmemiş"}</div></td>
              {/* v2.515 (yönetim boşlukları #1): segment + UEVÇB tek hücrede, yarının KGÜP arşivi — müşteri panelinin uzlaştırma katmanı platform gözünden */}
              <td>{p.segment ? <span title={SEGMENTLER.find((x) => x.deger === p.segment)?.etiket ?? p.segment}>{segmentKisa(p.segment)}</span> : <span className="bos">—</span>}
                {p.uevcb && <div className="kunye-not kod-duz">{p.uevcb}</div>}</td>
              <td className="plat-cipler plat-kgup">{p.kgup_yukumlu === false ? <span className="soluk">yükümlü değil</span>
                : !p.kgup_yarin || (p.kgup_yarin.oneri_surum == null && !p.kgup_yarin.bildirilen && !p.kgup_yarin.eak) ? <span className="bos">—</span>
                : <span className="dugme-sira">
                    {p.kgup_yarin.oneri_surum != null && <span className="rozet rozet-notr" title="PVQuant'ın ürettiği ve indirilen KGÜP dosyası (son sürüm)">öneri v{p.kgup_yarin.oneri_surum}</span>}
                    {p.kgup_yarin.bildirilen && <span className="rozet rozet-ok" title="Müşterinin TPYS'ye bildirdiğini beyan ettiği dosya; TPYS kabulü doğrulanmaz">bildirildi</span>}
                    {p.kgup_yarin.eak && <span className="rozet rozet-notr" title="TPYS EAK.csv biçiminde EAK dosyası indirildi">EAK</span>}
                  </span>}</td>
              <td><Zaman s={p.son_scada} /></td><td><Zaman s={p.son_kosu} /></td>
              {/* v2.515 inceleme: «Kurulu güç» santral adının, «Son hata» sorun çiplerinin altına künye olarak indi — 1440 px'te dokuz sütun kaydırıyordu */}
              <td className="plat-cipler plat-sorun">{p.sorunlar.length === 0 ? <span className="rozet rozet-ok">yok</span>
                : <span className="dugme-sira">{p.sorunlar.map((s) => <span key={s} className="rozet rozet-uyari">{sorunAdi(s)}</span>)}</span>}
                {p.son_hata && <div className="kunye-not"><button type="button" className="plat-baglanti" title="İş kayıtlarında bu santralin hatalarını göster (başarısız biten son iş)" onClick={() => santralSec(p.id, p.ad)}
                  style={Date.now() - new Date(p.son_hata).getTime() > 7 * 86400000 ? { color: "var(--soluk)" } : undefined}>son hata {yasTr(p.son_hata)}</button></div>}</td></tr>))}</tbody>
        </table></div>)}
      {veri && sorunlu && veri.santraller.length > 0 && <p className="soluk" style={{ fontSize: 13.5, margin: "10px 0 0" }}>{sayiTr(veri.santraller.length)} / {sayiTr(veri.toplam)} etkin santralde sorun var.</p>}
    </Kart>
  );
}
