import { useEffect, useState } from "react";
import { yonetim, zamanTr, yasTr, type Plan, type SistemOzet, type Kiraci, type KiraciDetay, type Kullanici, type Operator, type Basvuru, type DenetimKaydi, type Ben } from "../../api/yonetim";
import { Kart, Kpi, Sayfa, SayfaIskeleti, sayiTr, gucTr } from "../sayfalar/parcalar";
import { Meta } from "../../lib/Meta";
import { KullanimKarti } from "./Kullanim";
import { Zaman, AyrintiCipleri, LimitRozet } from "./ortak";
import { temsilAc } from "./temsil";

/** 24.10 Faz 2 — platform sayfaları. Dil: müşteri panelinin bileşen dili (Kart/Kpi/Sayfa, table.veri.santral, .form-izgara,
 *  rozet, Meta). Sayılar uydurulmaz: her değer uçtan; boş durum .bos-durum; hata metni açık. */

function Hata({ m }: { m: string | null }) { return m ? <p role="alert" className="giris-hata" style={{ marginTop: 10 }}>{m}</p> : null; }
function Bos({ bas, alt }: { bas: string; alt?: string }) { return <div className="bos-durum"><div className="bos-bas">{bas}</div>{alt && <p>{alt}</p>}</div>; }
const mesajCikar = (e: unknown) => String((e as Error).message ?? e);
function DurumRozet({ durum }: { durum: string }) {
  return <span className={`rozet rozet-kucuk ${durum === "active" ? "rozet-ok" : "rozet-uyari"}`}>{durum === "active" ? "etkin" : durum === "suspended" ? "askıda" : durum}</span>;
}
const ROL_AD: Record<string, string> = { admin: "Yönetici", editor: "Editör", viewer: "İzleyici", sahip: "Sahip", operator: "Operatör" };

/** Bir kez gösterilen sır (geçici parola, davet bağlantısı): kapatınca bir daha getirilemez. */
function TekSeferlik({ baslik, deger, not }: { baslik: string; deger: string; not?: string }) {
  const [kopya, setKopya] = useState("");
  return (
    <div className="plat-tek-seferlik" role="status">
      <div className="etiket-ust">{baslik}</div>
      <code className="plat-anahtar plat-anahtar--kucuk">{deger}</code>
      <div className="dugme-sira" style={{ marginTop: 8 }}>
        <button className="dugme kucuk" onClick={() => { navigator.clipboard?.writeText(deger).then(() => setKopya("kopyalandı"), () => setKopya("kopyalanamadı")); }}>Kopyala</button>
        {kopya && <span className="cip">{kopya}</span>}
      </div>
      <p className="soluk" style={{ fontSize: 13.5, margin: "8px 0 0" }}>{not ?? "Yalnız bu ekranda görünür; denetim izine yazılmaz."}</p>
    </div>
  );
}

// ---------------- Genel bakış ----------------
/** 26.10 D5 — sağlık şeridi: Sistem özetinden üç hüküm (zamanlayıcı, gece turu, yedek); tıklayınca Sistem sayfası. Hükümler uçtan. */
function SaglikSeridi({ sis, git }: { sis: SistemOzet | null | "hata"; git: () => void }) {
  if (sis === null) return <div className="plat-saglik" aria-busy="true"><span className="soluk">sistem durumu alınıyor…</span></div>;
  if (sis === "hata") return <div className="plat-saglik"><span className="rozet rozet-kucuk rozet-uyari">sistem durumu alınamadı</span></div>;
  const yedekSorun = sis.yedek.bayat || (sis.yedek.son_deneme ? !sis.yedek.son_deneme.tamam : false);
  const R = ({ ok, ad, deger }: { ok: boolean; ad: string; deger: string }) => (
    <span className={`rozet rozet-kucuk ${ok ? "rozet-ok" : "rozet-uyari"}`}>{ad}: {deger}</span>);
  return (
    <button type="button" className="plat-saglik plat-saglik--tikla" onClick={git} title="Sistem sayfasını aç">
      <R ok={sis.nabiz.durum === "calisiyor"} ad="zamanlayıcı" deger={sis.nabiz.durum === "calisiyor" ? "çalışıyor" : sis.nabiz.durum === "sessiz" ? "sessiz" : "nabız yok"} />
      <R ok={sis.gece_turu.taze} ad="gece turu" deger={sis.gece_turu.taze ? "taze" : "bayat"} />
      <R ok={!yedekSorun} ad="yedek" deger={yasTr(sis.yedek.son_basarili)} />
      <span className="soluk" style={{ fontSize: 13 }}>Sistem →</span>
    </button>
  );
}
export function GenelBakis({ git }: { git: (s: "musteriler" | "basvurular" | "denetim" | "sistem") => void }) {
  const [k, setK] = useState<Kiraci[] | null>(null);
  const [sis, setSis] = useState<SistemOzet | null | "hata">(null);   // 26.10 D5: sağlık şeridi (aynı /sistem ucu)
  const [b, setB] = useState<Basvuru[] | null>(null);
  const [d, setD] = useState<DenetimKaydi[] | null>(null);
  const [hata, setHata] = useState<string | null>(null);
  useEffect(() => {
    yonetim.sistem().then(setSis).catch(() => setSis("hata"));
    Promise.allSettled([yonetim.kiracilar(), yonetim.basvurular(), yonetim.denetim({ limit: 12, eylem_haric: "kiraci_goruntule" })]).then(([rk, rb, rd]) => {
      setK(rk.status === "fulfilled" ? rk.value.kiracilar : []); setB(rb.status === "fulfilled" ? rb.value.basvurular : []);
      setD(rd.status === "fulfilled" ? rd.value.kayitlar : []);
      const h = [rk, rb, rd].find((r) => r.status === "rejected") as PromiseRejectedResult | undefined; if (h) setHata(mesajCikar(h.reason));
    });
  }, []);
  if (!k || !b || !d) return <Sayfa baslik="Genel bakış"><SayfaIskeleti kpi={4} kart={1} /></Sayfa>;
  const etkin = k.filter((x) => x.durum === "active");
  const kwp = k.reduce((a, x) => a + x.kurulu_guc_kwp, 0);
  return (
    <Sayfa baslik="Genel bakış" alt="Kiracılar, santraller ve son işlemler; tüm sayılar canlı veritabanından.">
      <Hata m={hata} />
      <SaglikSeridi sis={sis} git={() => git("sistem")} />
      <div className="ızgara satir-4" style={{ marginBottom: 14 }}>
        <Kpi etiket="Kiracı" deger={sayiTr(k.length)} alt={`${sayiTr(etkin.length)} etkin, ${sayiTr(k.length - etkin.length)} askıda`} />
        <Kpi etiket="Etkin santral" deger={sayiTr(k.reduce((a, x) => a + x.santral, 0))} alt={kwp ? `${gucTr(kwp)} kWp kurulu güç` : "kurulu güç yok"} />
        <Kpi etiket="Etkin kullanıcı" deger={sayiTr(k.reduce((a, x) => a + x.kullanici, 0))} alt="tüm kiracılar" />
        <Kpi etiket="Okunmamış başvuru" deger={sayiTr(b.filter((x) => !x.okundu).length)} alt={`${sayiTr(b.length)} toplam`} ton={b.some((x) => !x.okundu) ? "uyari" : undefined} />
      </div>
      <Kart baslik="Son işlemler" alt="Denetim izinin son 12 kaydı; görüntüleme izleri (kiraci_goruntule) yalnız Denetim izi sayfasında" sag={<button className="dugme kucuk" onClick={() => git("denetim")}>Tümü</button>}>
        {d.length === 0 ? <Bos bas="Henüz kayıt yok." /> : <DenetimTablosu kayitlar={d} />}
      </Kart>
    </Sayfa>
  );
}

// ---------------- Müşteriler ----------------
export function Musteriler({ sahip = false }: { sahip?: boolean }) {
  const [liste, setListe] = useState<Kiraci[] | null>(null);
  const [planlar, setPlanlar] = useState<Record<string, Plan>>({});   // 26.10 Faz 5: limit rozetleri (uyarı kipi)
  const [secili, setSecili] = useState<string | null>(null);
  const [hata, setHata] = useState<string | null>(null);
  const [firma, setFirma] = useState(""); const [eposta, setEposta] = useState(""); const [plan, setPlan] = useState("pilot");
  const [sonuc, setSonuc] = useState<{ tenant_id: string; davet_gonderildi: boolean; davet_baglantisi?: string } | null>(null);
  const [mesgul, setMesgul] = useState(false);
  const yenile = () => yonetim.kiracilar().then((r) => setListe(r.kiracilar)).catch((e) => setHata(mesajCikar(e)));
  useEffect(() => { void yenile(); yonetim.planlar().then((r) => setPlanlar(Object.fromEntries(r.planlar.map((p) => [p.ad, p])))).catch(() => {}); }, []);
  if (secili) return <MusteriDetay id={secili} geri={() => { setSecili(null); void yenile(); }} sahip={sahip} />;
  async function olustur() {
    setHata(null); setSonuc(null); setMesgul(true);
    try { const r = await yonetim.kiraciOlustur(firma, eposta, plan); setSonuc(r); setFirma(""); setEposta(""); void yenile(); }
    catch (e) { setHata(mesajCikar(e)); }
    setMesgul(false);
  }
  return (
    <Sayfa baslik="Müşteriler" alt="Kiracı kuruluşlar; satır detayı açar." sag={liste ? <span className="cip"><Meta items={[`${sayiTr(liste.length)} kiracı`]} /></span> : undefined}>
      <Hata m={hata} />
      <Kart baslik="Kiracılar" alt={liste ? "ad, plan, durum, santral, kurulu güç, etkin kullanıcı, son giriş" : undefined}>
        {!liste ? <SayfaIskeleti kpi={0} kart={1} /> : liste.length === 0 ? <Bos bas="Henüz kiracı yok." alt="Aşağıdaki formla ilk kiracıyı açın." /> : (
          <div className="grafik-kaydir"><table className="veri sayisal santral">
            <thead><tr><th>Kiracı</th><th>Plan</th><th>Durum</th><th>Santral</th><th>Kurulu güç<span className="birim">kWp</span></th><th>Kullanıcı</th><th>Son giriş</th><th>Oluşturma</th><th aria-hidden="true"></th></tr></thead>
            <tbody>{liste.map((k) => (
              <tr key={k.id} className="satir-tikla" tabIndex={0} onClick={() => setSecili(k.id)} onKeyDown={(e) => { if (e.key === "Enter") setSecili(k.id); }}>
                <td className="ad">{k.ad}</td><td>{k.plan}</td><td><DurumRozet durum={k.durum} /></td>
                <td><LimitRozet kullanim={k.santral} limit={planlar[k.plan]?.santral_limit} /></td>
                <td>{k.kurulu_guc_kwp ? gucTr(k.kurulu_guc_kwp) : <span className="bos">—</span>}</td>
                <td><LimitRozet kullanim={k.kullanici} limit={planlar[k.plan]?.kullanici_limit} /></td>
                <td><Zaman s={k.son_giris} /></td><td><Zaman s={k.olusturma} /></td>
                <td><svg className="satir-ok" width="14" height="14" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M7 4l6 6-6 6"/></svg></td>
              </tr>))}</tbody>
          </table></div>)}
      </Kart>
      <Kart baslik="Yeni kiracı" alt="Firma ve ilk yönetici; yönetici parolasını davet bağlantısıyla kendisi belirler (72 saat)">
        <form className="form-izgara" onSubmit={(e) => { e.preventDefault(); void olustur(); }}>
          <label className="girdi-etiket">Firma adı<input className="girdi" value={firma} onChange={(e) => setFirma(e.target.value)} placeholder="ör. Güneş Enerji A.Ş." required /></label>
          <label className="girdi-etiket">İlk yönetici e-postası<input className="girdi" type="email" value={eposta} onChange={(e) => setEposta(e.target.value)} placeholder="yonetici@firma.com" required /></label>
          <label className="girdi-etiket">Plan<select className="girdi" value={plan} onChange={(e) => setPlan(e.target.value)}><option value="pilot">pilot</option><option value="standart">standart</option><option value="kurumsal">kurumsal</option></select></label>
          <button className="dugme dugme-ana" type="submit" disabled={mesgul}>{mesgul ? "Açılıyor…" : "Kiracıyı aç"}</button>
        </form>
        {sonuc && (sonuc.davet_gonderildi
          ? <p className="giris-bilgi">Kiracı açıldı; davet e-postası gönderildi.</p>
          : <TekSeferlik baslik="Davet bağlantısı (e-posta gönderilemedi, elden iletin)" deger={sonuc.davet_baglantisi ?? ""} />)}
      </Kart>
    </Sayfa>
  );
}

function MusteriDetay({ id, geri, sahip }: { id: string; geri: () => void; sahip: boolean }) {
  const [d, setD] = useState<KiraciDetay | null>(null);
  const [hata, setHata] = useState<string | null>(null); const [mesaj, setMesaj] = useState<string | null>(null);
  const [notlar, setNotlar] = useState(""); const [onay, setOnay] = useState(false);
  const [sir, setSir] = useState<{ baslik: string; deger: string } | null>(null);
  const yenile = () => yonetim.kiraci(id).then((r) => { setD(r); setNotlar(r.notlar ?? ""); }).catch((e) => setHata(mesajCikar(e)));
  useEffect(() => { void yenile(); }, [id]);   // eslint-disable-line react-hooks/exhaustive-deps
  const dene = async (fn: () => Promise<unknown>, m: string) => { setHata(null); setMesaj(null); setSir(null); try { await fn(); setMesaj(m); await yenile(); } catch (e) { setHata(mesajCikar(e)); } };
  if (!d) return <Sayfa baslik="Müşteri"><SayfaIskeleti kpi={3} kart={2} /></Sayfa>;
  const askida = d.durum !== "active";
  return (
    <Sayfa baslik={d.ad} alt={`${d.plan} planı; oluşturma ${zamanTr(d.olusturma)}`} sag={<span className="cip"><Meta items={[askida ? "askıda" : "etkin", `${sayiTr(d.santraller.filter((s) => !s.arsivli).length)} santral`, `${sayiTr(d.kullanicilar.length)} kullanıcı`, ...(d.yonetici_2fa_zorunlu ? ["yönetici 2FA zorunlu"] : [])]} /></span>}>
      <button className="giris-bag" onClick={geri}>← Müşteriler</button>
      <Hata m={hata} />{mesaj && <p className="giris-bilgi" style={{ marginTop: 10 }}>{mesaj}</p>}
      {sir && <TekSeferlik baslik={sir.baslik} deger={sir.deger} />}
      <Kart baslik="Durum ve plan" alt="Askıya alma kiracının tüm oturumlarını bir dakika içinde düşürür; giriş «hesap askıda» der">
        <div className="dugme-sira">
          {askida
            ? <button className="dugme dugme-ana" onClick={() => dene(() => yonetim.kiraciGuncelle(id, { durum: "active" }), "Kiracı yeniden etkin.")}>Etkinleştir</button>
            : onay
              ? <><button className="dugme dugme-tehlike" onClick={() => { setOnay(false); void dene(() => yonetim.kiraciGuncelle(id, { durum: "suspended" }), "Kiracı askıya alındı."); }}>Eminim, askıya al</button><button className="dugme" onClick={() => setOnay(false)}>Vazgeç</button></>
              : <button className="dugme dugme-tehlike" onClick={() => setOnay(true)}>Askıya al</button>}
          {sahip && !askida && <button className="dugme" title="Kiracıyı müşteri gözüyle, salt okunur, 15 dakika; denetim izine yazılır"
            onClick={() => dene(async () => { temsilAc(await yonetim.temsil(id)); }, "Görüntüleme oturumu yeni sekmede açıldı (15 dk, salt okunur).")}>Müşteri gözüyle aç</button>}
          <label className="girdi-etiket" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>Plan
            <select className="girdi kucuk" value={d.plan} onChange={(e) => dene(() => yonetim.kiraciGuncelle(id, { plan: e.target.value }), "Plan güncellendi.")}>
              {["pilot", "standart", "kurumsal", d.plan].filter((v, i, a) => a.indexOf(v) === i).map((p) => <option key={p} value={p}>{p}</option>)}
            </select></label>
        </div>
        <div className="alt-bolum">
          <label className="girdi-etiket">Notlar (yalnız platform görür)
            <textarea className="girdi" rows={3} value={notlar} onChange={(e) => setNotlar(e.target.value)} /></label>
          <button className="dugme kucuk" style={{ marginTop: 8 }} onClick={() => dene(() => yonetim.kiraciGuncelle(id, { notlar }), "Notlar kaydedildi.")}>Notları kaydet</button>
        </div>
      </Kart>
      <Kart baslik="Kullanıcılar" alt="Rol, durum, 2FA, son giriş; işlemler kiracı kuralına tabidir (son etkin yönetici düşürülemez)">
        <KullaniciTablosu satirlar={d.kullanicilar.map((u) => ({ ...u, tenant_id: id, firma: d.ad }))} firmaGoster={false}
          islem={(fn, m) => dene(fn, m)} sirGoster={(b, v) => setSir({ baslik: b, deger: v })} />
      </Kart>
      <KullanimKarti tenantId={id} />
      <Kart baslik="Santraller" alt="Kapasite, saat dilimi, son SCADA verisi, son tahmin koşusu">
        {d.santraller.length === 0 ? <Bos bas="Santral yok." /> : (
          <div className="grafik-kaydir"><table className="veri sayisal santral">
            <thead><tr><th>Santral</th><th>Kapasite<span className="birim">kWp</span></th><th>Saat dilimi</th><th>Son SCADA</th><th>Son koşu</th><th>Durum</th></tr></thead>
            <tbody>{d.santraller.map((s) => (<tr key={s.id}><td className="ad">{s.ad}</td><td>{gucTr(s.kapasite_kwp)}</td><td>{s.tz}</td><td><Zaman s={s.son_scada} /></td><td><Zaman s={s.son_kosu} /></td>
              <td>{s.arsivli ? <span className="rozet rozet-kucuk rozet-notr">arşivde</span> : <span className="rozet rozet-kucuk rozet-ok">etkin</span>}</td></tr>))}</tbody>
          </table></div>)}
      </Kart>
    </Sayfa>
  );
}

function KullaniciTablosu({ satirlar, firmaGoster, islem, sirGoster }:
  { satirlar: Kullanici[]; firmaGoster: boolean; islem: (fn: () => Promise<unknown>, mesaj: string) => Promise<void>; sirGoster: (baslik: string, deger: string) => void }) {
  if (satirlar.length === 0) return <Bos bas="Kullanıcı yok." />;
  return (
    <div className="grafik-kaydir"><table className="veri sayisal santral">
      <thead><tr><th>E-posta</th>{firmaGoster && <th>Kiracı</th>}<th>Rol</th><th>Durum</th><th>2FA</th><th>Son giriş</th><th>İşlem</th></tr></thead>
      <tbody>{satirlar.map((u) => (
        <tr key={u.id}><td className="ad">{u.email}</td>{firmaGoster && <td>{u.firma}</td>}<td>{ROL_AD[u.rol] ?? u.rol}</td>
          <td>{u.aktif ? <span className="rozet rozet-kucuk rozet-ok">etkin</span> : <span className="rozet rozet-kucuk rozet-notr">pasif</span>}</td>
          <td>{u.totp_aktif ? "açık" : <span className="bos">kapalı</span>}</td><td><Zaman s={u.son_giris} /></td>
          <td><div className="dugme-sira">
            <button className="dugme kucuk" onClick={() => islem(async () => { const r = await yonetim.kullaniciParolaBaglantisi(u.id); if (!r.gonderildi && r.baglanti) sirGoster("Parola belirleme bağlantısı (e-posta gönderilemedi)", r.baglanti); }, "Parola bağlantısı hazırlandı.")}>Parola bağlantısı</button>
            {u.totp_aktif && <button className="dugme kucuk" onClick={() => islem(() => yonetim.kullaniciIkiAdimSifirla(u.id), "2FA sıfırlandı.")}>2FA sıfırla</button>}
            <button className={`dugme kucuk${u.aktif ? " dugme-tehlike" : ""}`} onClick={() => islem(() => yonetim.kullaniciGuncelle(u.id, { aktif: !u.aktif }), u.aktif ? "Kullanıcı pasifleştirildi." : "Kullanıcı yeniden etkin.")}>{u.aktif ? "Pasifleştir" : "Etkinleştir"}</button>
          </div></td></tr>))}</tbody>
    </table></div>
  );
}

// ---------------- Kullanıcılar ----------------
export function Kullanicilar() {
  const [q, setQ] = useState(""); const [liste, setListe] = useState<Kullanici[] | null>(null);
  const [hata, setHata] = useState<string | null>(null); const [mesaj, setMesaj] = useState<string | null>(null);
  const [sir, setSir] = useState<{ baslik: string; deger: string } | null>(null);
  const ara = (s: string) => yonetim.kullanicilar(s).then((r) => setListe(r.kullanicilar)).catch((e) => setHata(mesajCikar(e)));
  useEffect(() => { void ara(""); }, []);
  const islem = async (fn: () => Promise<unknown>, m: string) => { setHata(null); setMesaj(null); setSir(null); try { await fn(); setMesaj(m); await ara(q); } catch (e) { setHata(mesajCikar(e)); } };
  return (
    <Sayfa baslik="Kullanıcılar" alt="Tüm kiracıların kullanıcıları; e-posta ya da firma adıyla arayın." sag={liste ? <span className="cip"><Meta items={[`${sayiTr(liste.length)} kullanıcı`]} /></span> : undefined}>
      <form className="form-izgara" style={{ maxWidth: 560, marginBottom: 14 }} onSubmit={(e) => { e.preventDefault(); void ara(q); }}>
        <label className="girdi-etiket">Ara<input className="girdi" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e-posta ya da firma" /></label>
        <button className="dugme" type="submit">Ara</button>
      </form>
      <Hata m={hata} />{mesaj && <p className="giris-bilgi" style={{ marginTop: 0 }}>{mesaj}</p>}
      {sir && <TekSeferlik baslik={sir.baslik} deger={sir.deger} />}
      <Kart baslik="Sonuçlar">{!liste ? <SayfaIskeleti kpi={0} kart={1} /> : <KullaniciTablosu satirlar={liste} firmaGoster islem={islem} sirGoster={(b, v) => setSir({ baslik: b, deger: v })} />}</Kart>
    </Sayfa>
  );
}

// ---------------- Başvurular ----------------
export function Basvurular() {
  const [liste, setListe] = useState<Basvuru[] | null>(null); const [hata, setHata] = useState<string | null>(null);
  const yenile = () => yonetim.basvurular().then((r) => setListe(r.basvurular)).catch((e) => setHata(mesajCikar(e)));
  useEffect(() => { void yenile(); }, []);
  const acik = (liste ?? []).filter((b) => !b.okundu).length;
  return (
    <Sayfa baslik="Başvurular" alt="Vitrindeki «Karnenizi başlatın» formundan gelenler; dönüş e-postayla elden yapılır." sag={liste ? <span className="cip"><Meta items={[`${sayiTr(acik)} okunmamış`, `${sayiTr(liste.length)} toplam`]} /></span> : undefined}>
      <Hata m={hata} />
      <Kart baslik="Gelen talepler">
        {!liste ? <SayfaIskeleti kpi={0} kart={1} /> : liste.length === 0 ? <Bos bas="Henüz başvuru yok." /> : (
          <div className="grafik-kaydir"><table className="veri sayisal santral">
            <thead><tr><th>E-posta</th><th>Santral</th><th>Kurulu güç<span className="birim">kWp</span></th><th>Tarih</th><th>Durum</th><th>İşlem</th></tr></thead>
            <tbody>{liste.map((b) => (<tr key={b.id}><td className="ad">{b.eposta}</td><td>{b.santral_adi ?? <span className="bos">—</span>}</td>
              <td>{b.kurulu_guc_kwp != null ? gucTr(b.kurulu_guc_kwp) : <span className="bos">—</span>}</td><td><Zaman s={b.created_at} /></td>
              <td>{b.okundu ? <span className="rozet rozet-kucuk rozet-notr">okundu</span> : <span className="rozet rozet-kucuk rozet-uyari">yeni</span>}</td>
              <td>{!b.okundu && <button className="dugme kucuk" onClick={() => yonetim.basvuruOkundu(b.id).then(yenile).catch((e) => setHata(mesajCikar(e)))}>Okundu işaretle</button>}</td></tr>))}</tbody>
          </table></div>)}
      </Kart>
    </Sayfa>
  );
}

// ---------------- Denetim izi ----------------
function DenetimTablosu({ kayitlar }: { kayitlar: DenetimKaydi[] }) {
  return (
    <div className="grafik-kaydir"><table className="veri santral">
      <thead><tr><th>Zaman</th><th>Kapsam</th><th>Eylem</th><th>Aktör</th><th>Kiracı</th><th>Nesne</th><th>IP</th><th className="plat-ayrinti-sutun">Ayrıntı</th></tr></thead>
      <tbody>{kayitlar.map((k) => (<tr key={k.id}><td className="ad"><Zaman s={k.zaman} /></td><td>{k.kapsam === "musteri" ? "müşteri" : k.kapsam}</td><td><span className="cip-kod">{k.eylem}</span></td>
        <td className="plat-aktor">{k.aktor_eposta ?? (k.aktor_id ? k.aktor_id.slice(0, 8) : "—")}</td>
        <td>{k.kiraci_ad ?? (k.tenant_id ? <span className="mono" title={k.tenant_id}>{k.tenant_id.slice(0, 8)}</span> : "—")}</td>
        <td>{k.nesne_tur ? <>{k.nesne_tur}{k.nesne_id && <span className="mono soluk" title={k.nesne_id} style={{ display: "block", fontSize: 12 }}>{k.nesne_id.slice(0, 8)}</span>}</> : "—"}</td>
        <td className="mono">{k.ip ?? "—"}</td><td className="plat-ayrinti-sutun"><AyrintiCipleri a={k.ayrinti} /></td></tr>))}</tbody>
    </table></div>
  );
}
export function Denetim() {
  const [kapsam, setKapsam] = useState(""); const [eylem, setEylem] = useState(""); const [tenant, setTenant] = useState("");
  const [liste, setListe] = useState<DenetimKaydi[] | null>(null); const [hata, setHata] = useState<string | null>(null);
  const [kiracilar, setKiracilar] = useState<Kiraci[]>([]);
  useEffect(() => { yonetim.kiracilar().then((r) => setKiracilar(r.kiracilar)).catch(() => {}); }, []);
  const getir = (onceId?: number) => yonetim.denetim({ kapsam: kapsam || undefined, eylem: eylem || undefined, tenant_id: tenant || undefined, limit: 100, once_id: onceId })
    .then((r) => setListe((e) => onceId && e ? [...e, ...r.kayitlar] : r.kayitlar)).catch((e) => setHata(mesajCikar(e)));
  useEffect(() => { void getir(); }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <Sayfa baslik="Denetim izi" alt="Platform ve müşteri eylemleri; sırlar hiçbir zaman yazılmaz.">
      <form className="form-izgara" style={{ maxWidth: 760, marginBottom: 14 }} onSubmit={(e) => { e.preventDefault(); void getir(); }}>
        <label className="girdi-etiket">Kapsam<select className="girdi" value={kapsam} onChange={(e) => setKapsam(e.target.value)}><option value="">tümü</option><option value="platform">platform</option><option value="musteri">müşteri</option></select></label>
        <label className="girdi-etiket">Eylem<input className="girdi" value={eylem} onChange={(e) => setEylem(e.target.value)} placeholder="ör. giris, kiraci_guncelle" /></label>
        <label className="girdi-etiket">Kiracı<select className="girdi" value={tenant} onChange={(e) => setTenant(e.target.value)}>
          <option value="">tümü</option>{kiracilar.map((k) => <option key={k.id} value={k.id}>{k.ad}</option>)}</select></label>
        <button className="dugme" type="submit">Süz</button>
      </form>
      <Hata m={hata} />
      <Kart baslik="Kayıtlar" alt={liste ? `${sayiTr(liste.length)} kayıt gösteriliyor` : undefined}>
        {!liste ? <SayfaIskeleti kpi={0} kart={1} /> : liste.length === 0 ? <Bos bas="Süzgece uyan kayıt yok." /> : (<>
          <DenetimTablosu kayitlar={liste} />
          {liste.length >= 100 && <button className="dugme kucuk" style={{ marginTop: 12 }} onClick={() => getir(liste[liste.length - 1].id)}>Daha eski</button>}
        </>)}
      </Kart>
    </Sayfa>
  );
}

// ---------------- Operatörler (sahip) ----------------
export function Operatorler({ ben }: { ben: Ben | null }) {
  const [liste, setListe] = useState<Operator[] | null>(null); const [hata, setHata] = useState<string | null>(null); const [mesaj, setMesaj] = useState<string | null>(null);
  const [eposta, setEposta] = useState(""); const [rol, setRol] = useState("operator"); const [gecici, setGecici] = useState<{ email: string; parola: string } | null>(null);
  const yenile = () => yonetim.operatorler().then((r) => setListe(r.operatorler)).catch((e) => setHata(mesajCikar(e)));
  useEffect(() => { void yenile(); }, []);
  const dene = async (fn: () => Promise<unknown>, m: string) => { setHata(null); setMesaj(null); try { await fn(); setMesaj(m); await yenile(); } catch (e) { setHata(mesajCikar(e)); } };
  return (
    <Sayfa baslik="Operatörler" alt="Platform personeli; yalnız sahip yönetir. Son etkin sahip düşürülemez.">
      <Hata m={hata} />{mesaj && <p className="giris-bilgi" style={{ marginTop: 0 }}>{mesaj}</p>}
      {gecici && <TekSeferlik baslik={`${gecici.email} için geçici parola`} deger={gecici.parola} not="Yalnız bu ekranda görünür; operatör ilk girişte parolasını değiştirir ve 2FA kurar." />}
      <Kart baslik="Personel">
        {!liste ? <SayfaIskeleti kpi={0} kart={1} /> : (
          <div className="grafik-kaydir"><table className="veri sayisal santral">
            <thead><tr><th>E-posta</th><th>Rol</th><th>Durum</th><th>2FA</th><th>Son giriş</th><th>İşlem</th></tr></thead>
            <tbody>{liste.map((o) => (<tr key={o.id}><td className="ad">{o.email}{o.id === ben?.id && <span className="rozet rozet-kucuk rozet-notr" style={{ marginLeft: 8 }}>siz</span>}</td>
              <td><select className="girdi kucuk" value={o.rol} disabled={o.id === ben?.id} onChange={(e) => dene(() => yonetim.operatorGuncelle(o.id, { rol: e.target.value }), "Rol güncellendi.")}><option value="operator">Operatör</option><option value="sahip">Sahip</option></select></td>
              <td>{o.aktif ? <span className="rozet rozet-kucuk rozet-ok">etkin</span> : <span className="rozet rozet-kucuk rozet-notr">pasif</span>}</td>
              <td>{o.totp_aktif ? "açık" : <span className="bos">kapalı</span>}</td><td><Zaman s={o.son_giris} /></td>
              <td>{o.id === ben?.id ? <span className="bos" title="Kendi hesabınız: rol ve durum başka bir sahip tarafından değiştirilir; parola ve 2FA Hesabım'da">—</span> : <div className="dugme-sira">
                {o.totp_aktif && o.id !== ben?.id && <button className="dugme kucuk" onClick={() => dene(() => yonetim.operatorGuncelle(o.id, { iki_adim_sifirla: true }), "2FA sıfırlandı; operatör girişte yeniden kurar.")}>2FA sıfırla</button>}
                {o.id !== ben?.id && <button className={`dugme kucuk${o.aktif ? " dugme-tehlike" : ""}`} onClick={() => dene(() => yonetim.operatorGuncelle(o.id, { aktif: !o.aktif }), o.aktif ? "Pasifleştirildi." : "Yeniden etkin.")}>{o.aktif ? "Pasifleştir" : "Etkinleştir"}</button>}
              </div>}</td></tr>))}</tbody>
          </table></div>)}
      </Kart>
      <Kart baslik="Yeni operatör" alt="Geçici parola yalnız bir kez gösterilir">
        <form className="form-izgara" onSubmit={(e) => { e.preventDefault(); void dene(async () => { const r = await yonetim.operatorEkle(eposta, rol); setGecici({ email: r.email, parola: r.gecici_parola }); setEposta(""); }, "Operatör eklendi."); }}>
          <label className="girdi-etiket">E-posta<input className="girdi" type="email" value={eposta} onChange={(e) => setEposta(e.target.value)} required /></label>
          <label className="girdi-etiket">Rol<select className="girdi" value={rol} onChange={(e) => setRol(e.target.value)}><option value="operator">Operatör</option><option value="sahip">Sahip</option></select></label>
          <button className="dugme dugme-ana" type="submit">Ekle</button>
        </form>
      </Kart>
    </Sayfa>
  );
}

// ---------------- Hesabım ----------------
export function Hesap({ ben }: { ben: Ben | null }) {
  const [eski, setEski] = useState(""); const [yeni, setYeni] = useState(""); const [hata, setHata] = useState<string | null>(null); const [mesaj, setMesaj] = useState<string | null>(null);
  return (
    <Sayfa baslik="Hesabım" alt={ben ? `${ben.email}, ${ben.rol === "sahip" ? "sahip" : "operatör"}; 2FA ${ben.totp_aktif ? "açık" : "kapalı"}` : undefined}>
      <Kart baslik="Parolamı değiştir" alt="Değişince diğer oturumlarınız kapanır; bu oturum yeni jetonla sürer">
        <form className="form-izgara" style={{ maxWidth: 640 }} onSubmit={(e) => { e.preventDefault(); setHata(null); setMesaj(null);
          yonetim.parolaDegistir(eski, yeni).then(() => { setMesaj("Parolanız değiştirildi."); setEski(""); setYeni(""); return yonetim.oturumYenile(); }).catch((er) => setHata(mesajCikar(er))); }}>
          <label className="girdi-etiket">Mevcut parola<input className="girdi" type="password" value={eski} autoComplete="current-password" onChange={(e) => setEski(e.target.value)} /></label>
          <label className="girdi-etiket">Yeni parola (en az 12 karakter)<input className="girdi" type="password" value={yeni} autoComplete="new-password" onChange={(e) => setYeni(e.target.value)} /></label>
          <button className="dugme" type="submit">Değiştir</button>
        </form>
        <Hata m={hata} />{mesaj && <p className="giris-bilgi">{mesaj}</p>}
      </Kart>
      <Kart baslik="İki adımlı doğrulama" alt="Platformda zorunludur">
        <p className="soluk" style={{ margin: 0 }}>{ben?.totp_aktif ? "Açık. Telefonunuzu kaybederseniz başka bir sahip sıfırlar; sonra yeniden kurarsınız." : "Kapalı: bu durumda panel açılmamalıydı; çıkıp yeniden girin."}</p>
      </Kart>
    </Sayfa>
  );
}
