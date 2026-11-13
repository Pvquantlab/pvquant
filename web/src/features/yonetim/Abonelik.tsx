import { useEffect, useState } from "react";
import { yonetim, zamanTr, type Abonelik, type AbonelikGuncelle, type KotaAlani } from "../../api/yonetim";
import { HizmetDurumu as Rozet, Kart, SayfaIskeleti, sayiTr } from "../sayfalar/parcalar";
import { KotaRozet } from "./ortak";

/** v2.609 (Faz 6 F6-C) — Müşteri detayı «Abonelik» kartı: plan, durum, tarihler, etkin modüller, kota/kullanım, sözleşme istisnaları, geçmiş;
 *  eylemler (plan, tarih, modül ek/çıkar, kota ezme, sözleşme notu/teklif, askıya al / etkinleştir / feshet [sahip]) tek uca, GEREKÇE ZORUNLU.
 *  Hükümler ve sözcükler uçtan; ödeme altyapısı yok → «tahsilat panel dışında» etiketi (sahte düğme yok). Uyarı kipinde müşteri kısıtı yok. */
const mesajCikar = (e: unknown) => String((e as Error).message ?? e);
const KOTA_SIRA: (KotaAlani | "api_rpm")[] = ["santral", "kullanici", "portfoy", "ac_mw", "aylik_dis_api", "aylik_rapor", "aylik_isleme_saat", "api_rpm"];
const ROZET_DURUM: Record<string, string> = { pilot: "veri_bekleniyor", aktif: "saglikli", sona_eriyor: "dikkat", yenileme_bekliyor: "dikkat", askida: "kritik", sona_erdi: "kritik", feshedildi: "uygulanmiyor" };
const gunTr = (iso: string | null) => iso ? new Date(iso + "T00:00:00").toLocaleDateString("tr-TR") : "—";

export function AbonelikKarti({ tenantId, sahip, onDegisti }: { tenantId: string; sahip: boolean; onDegisti?: () => void }) {
  const [a, setA] = useState<Abonelik | null | "hata">(null);
  const [hata, setHata] = useState<string | null>(null); const [mesaj, setMesaj] = useState<string | null>(null);
  const [acik, setAcik] = useState(false);
  const [f, setF] = useState<{ plan: string; bitis: string; pilot_bitis: string; modul_ek: string[]; modul_cikar: string[]; kota_ezme: Record<string, string>; sozlesme_notu: string; teklif_ref: string; gerekce: string }>({
    plan: "", bitis: "", pilot_bitis: "", modul_ek: [], modul_cikar: [], kota_ezme: {}, sozlesme_notu: "", teklif_ref: "", gerekce: "" });
  const [onay, setOnay] = useState<"askida" | "feshedildi" | null>(null);
  const yenile = () => yonetim.abonelik(tenantId).then((r) => {
    setA(r);
    setF({ plan: r.plan.ad, bitis: r.tarihler.bitis ?? "", pilot_bitis: r.tarihler.pilot_bitis ?? "", modul_ek: r.sozlesme.modul_ek, modul_cikar: r.sozlesme.modul_cikar,
      kota_ezme: Object.fromEntries(Object.entries(r.sozlesme.kota_ezme).map(([k, v]) => [k, v == null ? "" : String(v)])), sozlesme_notu: r.sozlesme.notu ?? "", teklif_ref: r.sozlesme.teklif_ref ?? "", gerekce: "" });
  }).catch(() => setA("hata"));
  useEffect(() => { setA(null); void yenile(); }, [tenantId]);   // eslint-disable-line react-hooks/exhaustive-deps
  const gonder = async (g: AbonelikGuncelle, m: string) => {
    setHata(null); setMesaj(null); setOnay(null);
    try { const r = await yonetim.abonelikGuncelle(tenantId, g); setMesaj(Object.keys(r.degisen).length ? m : "Değişiklik yok."); await yenile(); onDegisti?.(); }
    catch (e) { setHata(mesajCikar(e)); }
  };
  if (a === null) return <Kart baslik="Abonelik"><SayfaIskeleti kpi={0} kart={1} /></Kart>;
  if (a === "hata") return <Kart baslik="Abonelik"><p className="soluk" style={{ margin: 0 }}>Abonelik bilgisi alınamadı.</p></Kart>;
  const moduller = Object.entries(a.moduller);
  const kaydet = () => {
    const g: AbonelikGuncelle = { gerekce: f.gerekce };
    if (f.plan !== a.plan.ad) g.plan = f.plan;
    if ((f.bitis || null) !== a.tarihler.bitis) g.bitis = f.bitis || null;
    if ((f.pilot_bitis || null) !== a.tarihler.pilot_bitis) g.pilot_bitis = f.pilot_bitis || null;
    if (f.modul_ek.join() !== a.sozlesme.modul_ek.join()) g.modul_ek = f.modul_ek;
    if (f.modul_cikar.join() !== a.sozlesme.modul_cikar.join()) g.modul_cikar = f.modul_cikar;
    const ke: Record<string, number | null> = {}; for (const [k, v] of Object.entries(f.kota_ezme)) if (v.trim() !== "") ke[k] = Number(v.replace(",", "."));
    if (JSON.stringify(ke) !== JSON.stringify(a.sozlesme.kota_ezme)) g.kota_ezme = ke;
    if ((f.sozlesme_notu || null) !== a.sozlesme.notu) g.sozlesme_notu = f.sozlesme_notu || null;
    if ((f.teklif_ref || null) !== a.sozlesme.teklif_ref) g.teklif_ref = f.teklif_ref || null;
    void gonder(g, "Abonelik güncellendi.");
  };
  const istisna = (kod: string, hedef: "modul_ek" | "modul_cikar", ac: boolean) =>
    setF((x) => ({ ...x, modul_ek: hedef === "modul_ek" ? (ac ? [...new Set([...x.modul_ek, kod])] : x.modul_ek.filter((m) => m !== kod)) : x.modul_ek.filter((m) => m !== kod),
      modul_cikar: hedef === "modul_cikar" ? (ac ? [...new Set([...x.modul_cikar, kod])] : x.modul_cikar.filter((m) => m !== kod)) : x.modul_cikar.filter((m) => m !== kod) }));
  return (
    <Kart baslik="Abonelik" alt={`${a.plan.baslik} planı; durum ve kotalar uçtan (zorlama kipi: ${a.zorlama === "zorla" ? "zorla" : "uyarı — kısıt yok"}); ödeme altyapısı entegre değil, tahsilat panel dışında`}
      sag={<span className="dugme-sira"><Rozet durum={ROZET_DURUM[a.durum] ?? "dogrulanamadi"} etiket={a.durum_etiketi} />
        <button className="dugme kucuk" onClick={() => setAcik((v) => !v)} aria-expanded={acik}>{acik ? "Düzenlemeyi kapat" : "Düzenle"}</button></span>}>
      {hata && <p role="alert" className="giris-hata" style={{ marginTop: 0 }}>{hata}</p>}{mesaj && <p className="giris-bilgi" style={{ marginTop: 0 }}>{mesaj}</p>}
      <div className="ızgara-cift">
        <dl className="kunye">
          <div><dt>Plan</dt><dd>{a.plan.baslik}</dd></div>
          <div><dt>Durum</dt><dd>{a.durum_etiketi}{a.tarihler.kalan_gun != null && <span className="kunye-not">{a.tarihler.kalan_gun >= 0 ? `${sayiTr(a.tarihler.kalan_gun)} gün kaldı` : `${sayiTr(-a.tarihler.kalan_gun)} gün geçti`}</span>}</dd></div>
          <div><dt>Başlangıç</dt><dd>{gunTr(a.tarihler.baslangic)}</dd></div>
          <div><dt>Bitiş</dt><dd>{gunTr(a.tarihler.bitis)}{!a.tarihler.bitis && <span className="kunye-not">süresiz (sözleşme tarihi girilmedi)</span>}</dd></div>
          {a.tarihler.pilot_bitis && <div><dt>Pilot bitişi</dt><dd>{gunTr(a.tarihler.pilot_bitis)}</dd></div>}
          <div><dt>Sözleşme notu</dt><dd>{a.sozlesme.notu ?? "—"}{a.sozlesme.teklif_ref && <span className="kunye-not">teklif {a.sozlesme.teklif_ref}</span>}</dd></div>
          <div><dt>Son değişiklik</dt><dd>{a.sozlesme.guncelleme ? zamanTr(a.sozlesme.guncelleme) : "—"}{a.sozlesme.guncelleyen && <span className="kunye-not">{a.sozlesme.guncelleyen}</span>}</dd></div>
        </dl>
        <dl className="kunye">
          {KOTA_SIRA.map((k) => { const d = a.kotalar[k]; return d ? <div key={k}><dt>{d.ad}</dt><dd><KotaRozet k={d} />{d.not_ && <span className="kunye-not">{d.not_}</span>}</dd></div> : null; })}
        </dl>
      </div>
      <div className="etiket-ust" style={{ marginTop: 12 }}>Etkin modüller</div>
      <div className="dugme-sira" style={{ flexWrap: "wrap", gap: 6 }}>
        {moduller.filter(([, m]) => m.dahil).map(([kod, m]) => <span key={kod} className="cip" title={`${m.durum_etiketi}${m.kaynak === "ek" ? " · sözleşmeyle eklendi" : ""}`}>{m.ad}{m.kaynak === "ek" ? " *" : ""}</span>)}
        {moduller.filter(([, m]) => !m.dahil && m.kaynak === "cikar").map(([kod, m]) => <span key={kod} className="cip soluk" title="sözleşmeyle çıkarıldı" style={{ textDecoration: "line-through" }}>{m.ad}</span>)}
      </div>
      {a.uyarilar.length > 0 && <ul className="not-listesi uyari" style={{ marginTop: 10 }}>{a.uyarilar.map((u) => <li key={u}>{u}</li>)}</ul>}
      {acik && (
        <div className="alt-bolum">
          <div className="form-izgara">
            <label className="girdi-etiket">Plan
              <select className="girdi" value={f.plan} onChange={(e) => setF({ ...f, plan: e.target.value })}>{["pilot", "standart", "kurumsal", a.plan.ad].filter((v, i, x) => x.indexOf(v) === i).map((p) => <option key={p} value={p}>{p}</option>)}</select></label>
            <label className="girdi-etiket">Bitiş (boş = süresiz)<input className="girdi" type="date" value={f.bitis} onChange={(e) => setF({ ...f, bitis: e.target.value })} /></label>
            <label className="girdi-etiket">Pilot bitişi<input className="girdi" type="date" value={f.pilot_bitis} onChange={(e) => setF({ ...f, pilot_bitis: e.target.value })} /></label>
            <label className="girdi-etiket">Teklif referansı<input className="girdi" value={f.teklif_ref} maxLength={64} onChange={(e) => setF({ ...f, teklif_ref: e.target.value })} /></label>
            <label className="girdi-etiket form-tam">Sözleşme notu (yalnız platform görür)<textarea className="girdi" rows={2} value={f.sozlesme_notu} onChange={(e) => setF({ ...f, sozlesme_notu: e.target.value })} /></label>
            <div className="form-tam etiket-ust">Modül istisnaları (plan varsayılanının üstüne)</div>
            <div className="form-tam" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 4 }}>
              {moduller.map(([kod, m]) => (
                <div key={kod} className="dugme-sira" style={{ gap: 10, fontSize: 13 }}>
                  <span style={{ minWidth: 180 }}>{m.ad}<span className="soluk"> · plan: {m.kaynak === "plan" || m.kaynak === "cikar" ? "dâhil" : "dâhil değil"}</span></span>
                  <label className="ayar-onay"><input type="checkbox" checked={f.modul_ek.includes(kod)} onChange={(e) => istisna(kod, "modul_ek", e.target.checked)} /> ekle</label>
                  <label className="ayar-onay"><input type="checkbox" checked={f.modul_cikar.includes(kod)} onChange={(e) => istisna(kod, "modul_cikar", e.target.checked)} /> çıkar</label>
                </div>))}
            </div>
            <div className="form-tam etiket-ust">Kota ezme (boş = plan limiti; sözleşme istisnası, gerekçeyle izlenir)</div>
            {KOTA_SIRA.filter((k) => k !== "api_rpm").map((k) => (
              <label key={k} className="girdi-etiket">{a.kotalar[k]?.ad} <span className="soluk">{a.kotalar[k]?.birim}</span>
                <input className="girdi" inputMode="decimal" placeholder={a.kotalar[k]?.limit == null ? "plan: sınırsız" : `plan: ${sayiTr(a.kotalar[k].limit ?? 0, k === "ac_mw" ? 1 : 0)}`} value={f.kota_ezme[k] ?? ""}
                  onChange={(e) => setF({ ...f, kota_ezme: { ...f.kota_ezme, [k]: e.target.value } })} /></label>))}
            <label className="girdi-etiket form-tam">Gerekçe (zorunlu; geçmişe ve denetim izine yazılır)
              <input className="girdi" value={f.gerekce} maxLength={200} placeholder="ör. yıllık sözleşme imzalandı, teklif T-2026-07" onChange={(e) => setF({ ...f, gerekce: e.target.value })} /></label>
            <div className="form-tam dugme-sira">
              <button className="dugme dugme-ana" disabled={!f.gerekce.trim()} onClick={kaydet}>Kaydet</button>
              {a.durum === "askida"
                ? <button className="dugme" disabled={!f.gerekce.trim()} onClick={() => gonder({ durum: "aktif", gerekce: f.gerekce }, "Abonelik etkinleştirildi.")}>Etkinleştir</button>
                : a.durum !== "feshedildi" && (onay === "askida"
                  ? <><button className="dugme dugme-tehlike" onClick={() => gonder({ durum: "askida", gerekce: f.gerekce }, "Abonelik askıya alındı.")}>Eminim, askıya al</button><button className="dugme" onClick={() => setOnay(null)}>Vazgeç</button></>
                  : <button className="dugme dugme-tehlike" disabled={!f.gerekce.trim()} onClick={() => setOnay("askida")}>Askıya al</button>)}
              {sahip && a.durum !== "feshedildi" && (onay === "feshedildi"
                ? <><button className="dugme dugme-tehlike" onClick={() => gonder({ durum: "feshedildi", gerekce: f.gerekce }, "Abonelik feshedildi.")}>Eminim, feshet</button><button className="dugme" onClick={() => setOnay(null)}>Vazgeç</button></>
                : <button className="dugme dugme-tehlike" disabled={!f.gerekce.trim()} title="Geri alınamaz; hesap askıya alınır, veri silinmez" onClick={() => setOnay("feshedildi")}>Feshet</button>)}
            </div>
          </div>
        </div>)}
      <details className="aciklama genis" style={{ marginTop: 12 }}>
        <summary>Geçmiş{a.gecmis.length ? ` (${sayiTr(a.gecmis.length)} kayıt)` : ""}</summary>
        {a.gecmis.length === 0 ? <p className="soluk">Kayıt yok.</p> : (
          <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 13 }}>
            <thead><tr><th>Zaman</th><th>Eylem</th><th>Değişen</th><th>Gerekçe</th><th>Kim</th></tr></thead>
            <tbody>{a.gecmis.slice(0, 20).map((g) => (
              <tr key={g.id}><td>{zamanTr(g.zaman)}</td><td>{({ olusturma: "oluşturma", senkron: "eşzamanlama", guncelle: "güncelleme", turetme: "gece türetme", geri_doldurma: "geri doldurma" } as Record<string, string>)[g.eylem] ?? g.eylem}</td>
                <td style={{ whiteSpace: "normal" }}>{g.yeni ? Object.entries(g.yeni).map(([k, v]) => `${k}: ${g.eski && k in g.eski ? `${String(g.eski[k] ?? "—")} → ` : ""}${v == null ? "—" : typeof v === "object" ? JSON.stringify(v) : String(v)}`).join(" · ") : "—"}</td>
                <td style={{ whiteSpace: "normal" }}>{g.gerekce ?? "—"}</td><td className="soluk">{g.aktor ?? "—"}</td></tr>))}</tbody>
          </table></div>)}
      </details>
    </Kart>
  );
}
