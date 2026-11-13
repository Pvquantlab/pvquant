import { useEffect, useState } from "react";
import { api, rolum, bellektenOku } from "../../api/client";
import type { PaylasimListesi, PaylasilanVeri, SantralKisa } from "../../api/types";
import { Kart, Sayfa, sayiTr, SayfaIskeleti } from "./parcalar";
import { ModulNotu } from "./Abonelik";   // v2.609 (Faz 6 F6-D): kapalı özellik notu (uyarı kipi)
import { Meta } from "../../lib/Meta";

/** v2.608 (Faz 5 F5-A) — PAYLAŞIM sayfası: «Kuruluşlar arası paylaşım» kartı Ayarlar'dan (Kurulus.tsx) TAŞINDI — bileşen ve mantığı
 *  aynen (bayat-önce liste, izin seçenekleri uçtan, yazma yalnız yönetici); Yönetim grubunda kendi hedefi, Ayarlar'da kalmadı (çift hedef yok). */
export function Paylasim() {
  const [santraller, setSantraller] = useState<{ id: string; ad: string }[]>([]);
  useEffect(() => { api.santraller().then((l: SantralKisa[]) => setSantraller(l.map((s) => ({ id: s.id, ad: s.name })))).catch(() => {}); }, []);
  return (
    <Sayfa baslik="Paylaşım" alt="Kuruluşlar arası veri paylaşımı: başka bir kuruluşa verdiğiniz ve sizinle paylaşılan santral verileri, izinler ve süreler.">
      <ModulNotu kod="paylasim" />
      <Paylasimlar santraller={santraller} />
    </Sayfa>
  );
}

/** v2.289: kuruluşlar arası paylaşım — verdiklerimiz (kurmak yalnız yönetici) + aldıklarımız (herkes görür). */
function Paylasimlar({ santraller }: { santraller: { id: string; ad: string }[] }) {
  const [liste, setListe] = useState<PaylasimListesi | null>(() => bellektenOku<PaylasimListesi>("/v1/paylasimlar") ?? null);   // 24.10: bayat-önce
  const [santral, setSantral] = useState(""); const [eposta, setEposta] = useState("");
  const [izinler, setIzinler] = useState<string[]>(["tahmin:oku"]);
  const [bitis, setBitis] = useState(""); const [takmaAd, setTakmaAd] = useState("");
  const [hata, setHata] = useState<string | null>(null); const [mesaj, setMesaj] = useState<string | null>(null);
  const [acik, setAcik] = useState<{ id: string; tur: string; veri: PaylasilanVeri } | null>(null);
  const yenile = () => { api.paylasimlar().then(setListe).catch((e) => setHata(String((e as Error).message ?? e))); };
  useEffect(yenile, []);
  const dene = async (fn: () => Promise<unknown>) => { setHata(null); setMesaj(null); try { await fn(); yenile(); } catch (e) { setHata(String((e as Error).message ?? e)); } };
  const etiket = (i: string) => liste?.izin_secenekleri.find((x) => x.deger === i)?.etiket ?? i;
  const yonetici = rolum() === "admin";
  if (liste === null) return <SayfaIskeleti kpi={0} kart={1} />;
  if (!yonetici && liste.verilenler.length === 0 && liste.alinanlar.length === 0)
    return <div className="bos-durum"><div className="bos-bas">Paylaşım yok.</div><p>Kuruluşunuzun verdiği ya da aldığı paylaşım bulunmuyor; paylaşım açmak yönetici yetkisi ister.</p></div>;
  return (
    <Kart baslik="Kuruluşlar arası paylaşım" sag={<span className="cip"><Meta items={["yalnız okuma", "zaman sınırlı"]} /></span>}>
      <p className="soluk" style={{ margin: "0 0 10px", fontSize: 14 }}>
        Bir santralin tahmin, karne ya da gerçekleşen özetini başka bir kuruluşa (toplayıcı, danışman, alıcı) açar.
        Karşı taraf yalnız seçtiğiniz kapsamı, günlük toplam düzeyinde görür; istenirse santral adı takma adla gizlenir.
        Her erişim denetim iziyle kayda geçer.
      </p>
      {hata && <p className="ayar-durum hata" style={{ margin: "0 0 8px" }}>{hata}</p>}
      {mesaj && <p className="ayar-durum ok" style={{ margin: "0 0 8px" }}>{mesaj}</p>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(340px, 100%), 1fr))", gap: 16 }}>
        <div>
          <div className="etiket-ust">Verdiklerimiz</div>
          {liste.verilenler.length === 0 ? <p className="soluk" style={{ fontSize: 14, margin: 0 }}>Henüz paylaşım yok.</p> : (
            <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 13 }}>
              <thead><tr><th>Santral</th><th>Kuruluş</th><th>Kapsam</th><th>Bitiş</th><th>Durum</th><th></th></tr></thead>
              <tbody>{liste.verilenler.map((x) => (
                <tr key={x.id} style={{ opacity: x.aktif ? 1 : 0.5 }}>
                  <td>{x.santral}{x.takma_ad ? <span className="soluk"> → “{x.takma_ad}”</span> : null}</td>
                  <td>{x.karsi_kurulus}</td><td>{x.izinler.map(etiket).join(", ")}</td>
                  <td>{x.bitis ? new Date(x.bitis).toLocaleDateString("tr-TR") : "süresiz"}</td>
                  <td>{x.iptal ? "iptal" : x.aktif ? "etkin" : "süresi doldu"}</td>
                  <td>{yonetici && x.aktif && <button className="dugme" style={{ fontSize: 13 }}
                        onClick={() => dene(async () => { await api.paylasimIptal(x.id); setMesaj("Paylaşım iptal edildi."); })}>İptal et</button>}</td>
                </tr>))}</tbody>
            </table></div>
          )}
        </div>
        <div>
          <div className="etiket-ust">Aldıklarımız</div>
          {liste.alinanlar.length === 0 ? <p className="soluk" style={{ fontSize: 14, margin: 0 }}>Bize açılmış paylaşım yok.</p> : (
            <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 13 }}>
              <thead><tr><th>Santral</th><th>Kuruluş</th><th>Bitiş</th><th>Görüntüle</th></tr></thead>
              <tbody>{liste.alinanlar.map((x) => (
                <tr key={x.id} style={{ opacity: x.aktif ? 1 : 0.5 }}>
                  <td>{x.santral}</td><td>{x.karsi_kurulus}</td>
                  <td>{x.bitis ? new Date(x.bitis).toLocaleDateString("tr-TR") : "süresiz"}</td>
                  <td style={{ whiteSpace: "nowrap" }}>{x.aktif ? x.izinler.map((i) => (
                    <button key={i} className="dugme" style={{ fontSize: 13, marginRight: 4 }}
                            onClick={() => dene(async () => setAcik({ id: x.id, tur: i.split(":")[0], veri: await api.paylasimVeri(x.id, i.split(":")[0]) }))}>{etiket(i)}</button>
                  )) : <span className="soluk">kapandı</span>}</td>
                </tr>))}</tbody>
            </table></div>
          )}
          {acik && (
            <div style={{ marginTop: 10, padding: 10, border: "1px solid var(--kenar)", borderRadius: 8, background: "var(--yuzey2)" }}>
              <div style={{ fontSize: 13, marginBottom: 6, display: "flex", justifyContent: "space-between", gap: 8 }}>
                <span><Meta items={[<strong key="ad">{acik.veri.santral}</strong>, etiket(`${acik.tur}:oku`)]} /></span>
                <button className="dugme" style={{ fontSize: 13 }} onClick={() => setAcik(null)}>Kapat</button>
              </div>
              {acik.tur === "karne" ? (
                <table className="veri" style={{ fontSize: 13 }}><tbody>
                  <tr><td>Değerlendirilen gün</td><td className="mono">{sayiTr(acik.veri.gun ?? 0)}</td></tr>
                  <tr><td>Ağırlıklı hata (WMAPE)</td><td className="mono">{acik.veri.wmape_pct == null ? "—" : `%${sayiTr(acik.veri.wmape_pct, 1)}`}</td></tr>
                  <tr><td>Kurulu güce göre hata (nMAE)</td><td className="mono">{acik.veri.nmae_pct == null ? "—" : `%${sayiTr(acik.veri.nmae_pct, 1)}`}</td></tr>
                  <tr><td>Tahmin aralığı isabeti (P10–P90)</td><td className="mono">{acik.veri.picp80 == null ? "—" : `%${sayiTr(acik.veri.picp80 * 100, 1)}`}</td></tr>
                </tbody></table>
              ) : (acik.veri.gunler?.length ?? 0) === 0 ? <p className="soluk" style={{ fontSize: 14, margin: 0 }}>{acik.veri.not ?? "Veri yok."}</p> : (
                <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 13 }}>
                  <thead>{acik.tur === "tahmin"
                    ? <tr><th>Gün</th><th>P50 (kWh)</th><th>P10–P90 (kWh)</th></tr>
                    : <tr><th>Gün</th><th>Üretim (kWh)</th></tr>}</thead>
                  <tbody className="mono">{acik.veri.gunler!.map((g) => (
                    <tr key={g.gun}>
                      <td>{new Date(g.gun).toLocaleDateString("tr-TR", { day: "numeric", month: "short" })}</td>
                      {acik.tur === "tahmin"
                        ? <><td>{g.p50_kwh == null ? "—" : sayiTr(g.p50_kwh, 0)}</td>
                            <td>{g.p10_kwh == null || g.p90_kwh == null ? "—" : `${sayiTr(g.p10_kwh, 0)} – ${sayiTr(g.p90_kwh, 0)}`}</td></>
                        : <td>{g.kwh == null ? "—" : sayiTr(g.kwh, 0)}</td>}
                    </tr>))}</tbody>
                </table></div>
              )}
            </div>
          )}
        </div>
      </div>
      {/* 23.10 beşinci tur: yeni paylaşım formu iki listenin ALTINDA tam satır (önce yarım sütuna sıkışıp sağda boşluk
          bırakıyordu) — soldan sağa: santral, karşı taraf, kapsam, bitiş, takma ad, Paylaş; isteğe bağlı alanlar
          etiketinde işaretli; gönderilen parametreler ve doğrulamalar aynı */}
      {yonetici && (
        <div className="alt-bolum">
          <div className="etiket-ust">Yeni paylaşım</div>
          <form className="form-izgara" style={{ marginTop: 6 }}
                onSubmit={(e) => { e.preventDefault(); dene(async () => {
                  const r = await api.paylasimEkle({ plant_id: santral || santraller[0]?.id, hedef_eposta: eposta,
                    izinler, bitis: bitis || null, takma_ad: takmaAd || null });
                  setMesaj(`Paylaşım kuruldu: ${r.hedef_kurulus}.`); setEposta(""); setTakmaAd(""); }); }}>
            <label className="girdi-etiket">Santral
              <select className="girdi" value={santral || santraller[0]?.id || ""} onChange={(e) => setSantral(e.target.value)}>
                {santraller.map((x) => <option key={x.id} value={x.id}>{x.ad}</option>)}
              </select></label>
            <label className="girdi-etiket">Karşı tarafın e-postası
              <input className="girdi" type="email" value={eposta} onChange={(e) => setEposta(e.target.value)} required /></label>
            <div className="girdi-etiket">Kapsam
              <div className="onay-grubu">
                {liste.izin_secenekleri.map((k) => (
                  <label key={k.deger} className="ayar-onay">
                    <input type="checkbox" checked={izinler.includes(k.deger)}
                           onChange={(e) => setIzinler(e.target.checked ? [...izinler, k.deger] : izinler.filter((x) => x !== k.deger))} />
                    <span>{k.etiket}</span>
                  </label>))}
              </div>
            </div>
            <label className="girdi-etiket">Bitiş (isteğe bağlı)
              <input className="girdi" type="date" value={bitis} onChange={(e) => setBitis(e.target.value)} /></label>
            <label className="girdi-etiket">Takma ad (isteğe bağlı)
              <input className="girdi" value={takmaAd} onChange={(e) => setTakmaAd(e.target.value)} placeholder="ör. GES-A" /></label>
            <button className="dugme" type="submit" disabled={izinler.length === 0 || santraller.length === 0}>Paylaş</button>
          </form>
        </div>
      )}
    </Kart>
  );
}
