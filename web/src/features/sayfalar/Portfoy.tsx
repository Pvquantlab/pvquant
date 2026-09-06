import { useEffect, useState } from "react";
import { api, rolum } from "../../api/client";
import type { Portfoy as PortfoyT, PortfoyDsg, PortfoyTahmin, ApiAnahtar, Webhook } from "../../api/types";
import { Kart, Kpi, Sayfa, sayiTr } from "./parcalar";

/** v2.263 (Dalga 5.15) — Portföy: kiracının tüm santralleri tek tabloda; toplamlar dürüst
 *  (bir santralin beklentisi yoksa toplam da yok). Satıra tıklayınca o santrala geçilir. */
export function Portfoy({ onSec }: { onSec: (id: string) => void }) {
  const [p, setP] = useState<PortfoyT | null | undefined>(undefined);
  useEffect(() => { api.portfoy().then(setP).catch(() => setP(null)); }, []);
  const [dsg, setDsg] = useState<PortfoyDsg | null>(null);   // v2.276
  const [pt, setPt] = useState<PortfoyTahmin | null>(null);   // v2.280
  useEffect(() => { api.portfoyTahmin().then(setPt).catch(() => {}); }, []);
  useEffect(() => { api.portfoyDsg().then(setDsg).catch(() => {}); }, []);
  const t = p?.toplam ?? null;
  const kwhYaz = (v: number | null | undefined) => v == null ? "—" : `${sayiTr(v / 1000, 1)} MWh`;
  const mwh = (v: number | null | undefined) => v == null ? "—" : sayiTr(v / 1000, 1);
  const tarih = (s: string | null) => s ? new Date(s).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "—";
  return (
    <Sayfa baslik="Portföy" alt="Tüm santraller bir bakışta — sayılar kapasite ile ağırlıklı, eksikler tire."
      sag={<span className="cip">{p ? `${sayiTr(p.santraller.length)} santral · ${new Date(p.gun + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "short" })}` : "yükleniyor"}</span>}>
      <div className="ızgara satir-4" style={{ marginBottom: 14 }}>
        <Kpi etiket="Toplam kurulu güç" deger={t ? sayiTr(t.kapasite_kwp / 1000, 2) : "—"} birim="MWp" alt={t ? `${sayiTr(t.santral)} santral` : ""} />
        <Kpi etiket="Bugün beklenen · yarın" deger={t ? `${mwh(t.bugun_kwh)} · ${mwh(t.yarin_kwh)}` : "—"} birim="MWh"
             alt={t && (t.bugun_kwh == null || t.yarin_kwh == null) ? "bir santralde beklenti yok → toplam yazılmaz" : "tüm santrallerin P50 toplamı"} />
        <Kpi etiket="30 günlük WMAPE (ağırlıklı)" deger={t?.wmape_agirlikli != null ? `%${sayiTr(t.wmape_agirlikli, 1)}` : "—"}
             alt={t ? `${sayiTr(t.wmape_kapsanan_kwp / 1000, 2)} MWp karneli` : ""} />
        <Kpi etiket="Açık alarm · veri gecikmiş" deger={t ? `${sayiTr(t.acik_alarm)} · ${sayiTr(t.veri_gecikmis)}` : "—"}
             alt="son 7 gün okunmamış · 2 günden eski ölçüm" ton={t && (t.acik_alarm > 0 || t.veri_gecikmis > 0) ? "uyari" : undefined} />
      </div>
      <Kart baslik="Santraller" sag={<span className="cip">satıra tıkla → santral</span>}>
        {p === undefined ? <p className="soluk" style={{ margin: 0 }}>Yükleniyor…</p>
         : !p || p.santraller.length === 0 ? <p className="soluk" style={{ margin: 0 }}>Bu hesapta santral yok.</p>
         : (
          <div className="grafik-kaydir">
            <table className="veri" style={{ fontSize: 12.5 }}>
              <thead><tr><th>Santral</th><th>kWp</th><th>Segment</th><th>Son ölçüm</th><th>WMAPE 30g</th><th>Bugün</th><th>Yarın</th><th>Alarm</th><th>Son koşu</th></tr></thead>
              <tbody className="mono">
                {p.santraller.map((r) => (
                  <tr key={r.id} style={{ cursor: "pointer" }} onClick={() => onSec(r.id)} tabIndex={0}
                      onKeyDown={(e) => { if (e.key === "Enter") onSec(r.id); }}>
                    <td style={{ fontWeight: 600 }}>{r.ad}</td><td>{sayiTr(r.kapasite_kwp)}</td><td>{r.segment ?? "—"}</td>
                    <td style={{ color: r.kesinti_gun != null && r.kesinti_gun > 2 ? "var(--uyari)" : undefined }}>{tarih(r.son_olcum)}{r.kesinti_gun != null && r.kesinti_gun > 2 ? ` (${sayiTr(r.kesinti_gun)} g)` : ""}</td>
                    <td>{r.wmape_30g != null ? `%${sayiTr(r.wmape_30g, 1)}` : "—"}</td><td>{kwhYaz(r.bugun_kwh)}</td><td>{kwhYaz(r.yarin_kwh)}</td>
                    <td style={{ color: r.acik_alarm > 0 ? "var(--uyari)" : undefined }}>{sayiTr(r.acik_alarm)}</td><td>{tarih(r.son_kosu)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="soluk" style={{ fontSize: 12.5, margin: "10px 0 0" }}>
          Bugün/yarın = son koşunun yerel-gün P50 toplamı (20 saatten az kapsanan gün yazılmaz); WMAPE = son 30 günün 0–24 saat karnesi;
          alarm = son 7 günde okunmamış kayıt. Hiyerarşik uzlaştırma (portföy toplamının santral tahminleriyle tutarlı hale getirilmesi) sonraki dalga.
        </p>
      </Kart>
      {/* v2.280 (Tablo 3.2 satır 11): hiyerarşik uzlaştırılmış portföy tahmini — toplam santral tahminleriyle tutarlı */}
      <Kart baslik="Portföy tahmini — uzlaştırılmış günlük toplamlar" sag={<span className="cip">{pt?.durum === "ok" ? `${pt.yontem}${pt.tutarli === false ? " · tutarsız!" : ""}` : "—"}</span>}>
        {!pt ? <p className="soluk" style={{ margin: 0 }}>Yükleniyor…</p> : pt.durum !== "ok" ? <p className="soluk" style={{ margin: 0 }}>— koşu yok</p> : (
          <>
            <div className="grafik-kaydir">
              <table className="veri" style={{ fontSize: 12.5 }}>
                <thead><tr><th>Gün</th><th>P10 (MWh)</th><th>P50 (MWh)</th><th>P90 (MWh)</th><th>Saat</th></tr></thead>
                <tbody className="mono">
                  {(pt.gunler ?? []).map((g) => (
                    <tr key={g.gun}><td>{new Date(g.gun + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "short" })}</td>
                      <td>{sayiTr(g.p10_mwh, 1)}</td><td style={{ fontWeight: 600 }}>{sayiTr(g.p50_mwh, 1)}</td><td>{sayiTr(g.p90_mwh, 1)}</td><td>{sayiTr(g.saat)}</td></tr>))}
                </tbody>
              </table>
            </div>
            <p className="soluk" style={{ fontSize: 12.5, margin: "10px 0 0" }}>{pt.not}{pt.artik_gun ? ` Artık geçmişi ${sayiTr(pt.artik_gun)} gün.` : ""}</p>
          </>
        )}
      </Kart>
      {/* v2.276 (Dalga 5): DSG/toplayıcı netleştirmesi — portföy tek dengesizlik hesabına girerse ne kazanılır */}
      <Kart baslik="DSG netleştirmesi — portföy dengesizliği" sag={<span className="cip">{dsg ? `${sayiTr(dsg.pencere_gun)} gün · ${dsg.fiyat.senaryo_saat > 0 ? "senaryo fiyat" : "EPİAŞ fiyat"}` : "—"}</span>}>
        {!dsg ? <p className="soluk" style={{ margin: 0 }}>Yükleniyor…</p> : dsg.ayri_tl == null ? (
          <p className="soluk" style={{ margin: 0 }}>— {dsg.not ?? "ortak saat yetersiz"}</p>
        ) : (
          <>
            <div className="ızgara satir-3" style={{ marginBottom: 10 }}>
              <Kpi etiket="Santraller ayrı ayrı" deger={sayiTr(dsg.ayri_tl / 1000, 1)} birim="bin TL" alt={`${sayiTr(dsg.santral)} santral · ${sayiTr(dsg.sapma_ayri_mwh ?? 0, 1)} MWh sapma`} />
              <Kpi etiket="Portföy netleşmiş" deger={sayiTr((dsg.net_tl ?? 0) / 1000, 1)} birim="bin TL" alt={`${sayiTr(dsg.sapma_net_mwh ?? 0, 1)} MWh net sapma`} />
              <Kpi etiket="Netleşme kazancı" deger={sayiTr((dsg.kazanc_tl ?? 0) / 1000, 1)} birim="bin TL" alt={dsg.kazanc_pct != null ? `ayrı maliyetin %${sayiTr(dsg.kazanc_pct, 1)}'i` : "—"} />
            </div>
            <p className="soluk" style={{ fontSize: 12.5, margin: 0 }}>{dsg.not}</p>
          </>
        )}
      </Kart>
      {rolum() === "admin" && <DisErisim santraller={p?.santraller.map((s) => ({ id: s.id, ad: s.ad })) ?? []} />}
    </Sayfa>
  );
}

/** v2.264 (Dalga 5.16) — Dış erişim: API anahtarları + webhook alıcıları. Yalnız admin görür.
 *  Anahtar ve webhook sırrı YALNIZ üretildiği anda gösterilir; sunucu sırrı geri veremez. */
function DisErisim({ santraller }: { santraller: { id: string; ad: string }[] }) {
  const [anahtarlar, setAnahtarlar] = useState<ApiAnahtar[]>([]);
  const [kapsamlar, setKapsamlar] = useState<string[]>([]);
  const [webhooklar, setWebhooklar] = useState<Webhook[]>([]);
  const [ad, setAd] = useState(""); const [secili, setSecili] = useState<string[]>(["tahmin:oku"]);
  const [yeniAnahtar, setYeniAnahtar] = useState<string | null>(null);
  const [url, setUrl] = useState(""); const [whSantral, setWhSantral] = useState<string>("");
  const [yeniSir, setYeniSir] = useState<string | null>(null);
  const [hata, setHata] = useState<string | null>(null); const [mesaj, setMesaj] = useState<string | null>(null);
  const yenile = () => {
    api.apiAnahtarlari().then((r) => { setAnahtarlar(r.anahtarlar); setKapsamlar(r.kapsamlar); }).catch((e) => setHata(String(e.message ?? e)));
    api.webhooklar().then((r) => setWebhooklar(r.webhooklar)).catch(() => {});
  };
  useEffect(yenile, []);
  const tarih = (s: string | null) => s ? new Date(s).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "—";
  const dene = async (fn: () => Promise<unknown>) => { setHata(null); setMesaj(null); try { await fn(); yenile(); } catch (e) { setHata(String((e as Error).message ?? e)); } };
  const docs = api.docsAdresi();
  return (
    <Kart baslik="Dış erişim"
          sag={<span style={{ display: "flex", gap: 6 }}><span className="cip">yalnız yönetici</span>
                {docs ? <a className="cip" href={docs} target="_blank" rel="noreferrer">OpenAPI şeması ↗</a> : <span className="cip">örnek kip</span>}</span>}>
      <p className="soluk" style={{ margin: "0 0 10px", fontSize: 12.5 }}>
        Müşteri sistemleri tahmini <span className="mono">X-API-Key</span> başlığıyla çeker; sabah koşusundan sonra webhook alıcılarına imzalı bildirim gider.
        Anahtar ve sır yalnız üretildiği anda görünür — sunucu yalnız özetini saklar.
      </p>
      {hata && <p style={{ color: "var(--uyari)", fontSize: 12.5, margin: "0 0 8px" }}>{hata}</p>}
      {mesaj && <p className="soluk" style={{ fontSize: 12.5, margin: "0 0 8px" }}>{mesaj}</p>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 16 }}>
        <div>
          <div className="mono" style={{ fontSize: 11, fontWeight: 600, letterSpacing: ".04em", textTransform: "uppercase", color: "var(--soluk)", marginBottom: 6 }}>API anahtarları</div>
          {anahtarlar.length === 0 ? <p className="soluk" style={{ fontSize: 12.5, margin: 0 }}>Henüz anahtar yok.</p> : (
            <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 12 }}>
              <thead><tr><th>Ad</th><th>Önek</th><th>Kapsam</th><th>Son kullanım</th><th>Durum</th><th></th></tr></thead>
              <tbody className="mono">{anahtarlar.map((k) => (
                <tr key={k.id} style={{ opacity: k.iptal ? 0.5 : 1 }}>
                  <td>{k.ad ?? "—"}</td><td>pvq_{k.prefix}…</td><td>{k.kapsamlar.join(", ")}</td><td>{tarih(k.son_kullanim)}</td>
                  <td>{k.iptal ? "iptal" : k.expires_at && new Date(k.expires_at) < new Date() ? "süresi doldu" : "etkin"}</td>
                  <td>{!k.iptal && <button className="dugme" style={{ fontSize: 11.5 }} onClick={() => dene(() => api.apiAnahtarIptal(k.id))}>İptal et</button>}</td>
                </tr>))}</tbody>
            </table></div>
          )}
          <form style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginTop: 10 }}
                onSubmit={(e) => { e.preventDefault(); dene(async () => { const r = await api.apiAnahtarUret(ad, secili, null); setYeniAnahtar(r.anahtar); setAd(""); }); }}>
            <input value={ad} onChange={(e) => setAd(e.target.value)} placeholder="ad (ör. ticaret masası)" aria-label="Anahtar adı"
                   style={{ fontSize: 12.5, padding: "5px 8px", border: "1px solid var(--kenar)", borderRadius: 6, background: "var(--yuzey)", color: "var(--metin)" }} />
            {kapsamlar.map((k) => (
              <label key={k} style={{ fontSize: 12.5, display: "flex", gap: 4, alignItems: "center" }}>
                <input type="checkbox" checked={secili.includes(k)} onChange={(e) => setSecili(e.target.checked ? [...secili, k] : secili.filter((x) => x !== k))} />
                <span className="mono">{k}</span>
              </label>))}
            <button className="dugme" type="submit" disabled={secili.length === 0}>Anahtar üret</button>
          </form>
          {yeniAnahtar && (
            <div style={{ marginTop: 10, padding: 10, border: "1px solid var(--kenar)", borderRadius: 8, background: "var(--yuzey2)" }}>
              <div style={{ fontSize: 12, marginBottom: 4 }}>Yeni anahtar — <strong>bir daha gösterilmez</strong>, şimdi kopyalayın:</div>
              <code className="mono" style={{ fontSize: 12.5, wordBreak: "break-all", userSelect: "all" }}>{yeniAnahtar}</code>
              <div style={{ marginTop: 6 }}><button className="dugme" style={{ fontSize: 11.5 }} onClick={() => { navigator.clipboard?.writeText(yeniAnahtar).then(() => setMesaj("Anahtar panoya kopyalandı.")).catch(() => {}); }}>Kopyala</button>
                <button className="dugme" style={{ fontSize: 11.5, marginLeft: 6 }} onClick={() => setYeniAnahtar(null)}>Kapat</button></div>
            </div>)}
        </div>
        <div>
          <div className="mono" style={{ fontSize: 11, fontWeight: 600, letterSpacing: ".04em", textTransform: "uppercase", color: "var(--soluk)", marginBottom: 6 }}>Webhook alıcıları <span className="soluk">(tahmin.yeni)</span></div>
          {webhooklar.length === 0 ? <p className="soluk" style={{ fontSize: 12.5, margin: 0 }}>Henüz alıcı yok.</p> : (
            <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 12 }}>
              <thead><tr><th>Adres</th><th>Santral</th><th>Son gönderim</th><th>Durum</th><th></th></tr></thead>
              <tbody className="mono">{webhooklar.map((w) => (
                <tr key={w.id}>
                  <td style={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={w.url}>{w.url}</td>
                  <td>{w.santral ?? "tümü"}</td><td>{tarih(w.son_gonderim)}</td>
                  <td style={{ color: w.son_durum != null && !(w.son_durum >= 200 && w.son_durum < 300) ? "var(--uyari)" : undefined }}>
                    {w.son_durum == null ? "—" : w.son_durum === 0 ? "ulaşılamadı" : `HTTP ${w.son_durum}`}{w.hata_sayisi > 0 ? ` · ${sayiTr(w.hata_sayisi)} hata` : ""}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <button className="dugme" style={{ fontSize: 11.5 }} onClick={() => dene(async () => { const r = await api.webhookDene(w.id); setMesaj(r.ok ? `Deneme ulaştı (HTTP ${r.durum}).` : `Deneme başarısız (${r.durum === 0 ? "ulaşılamadı" : "HTTP " + r.durum}).`); })}>Dene</button>
                    <button className="dugme" style={{ fontSize: 11.5, marginLeft: 4 }} onClick={() => dene(() => api.webhookSil(w.id))}>Sil</button>
                  </td>
                </tr>))}</tbody>
            </table></div>
          )}
          <form style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginTop: 10 }}
                onSubmit={(e) => { e.preventDefault(); dene(async () => { const r = await api.webhookEkle(url, whSantral || null); setYeniSir(r.secret); setUrl(""); }); }}>
            <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…/pvquant-webhook" aria-label="Webhook adresi" required
                   style={{ fontSize: 12.5, padding: "5px 8px", border: "1px solid var(--kenar)", borderRadius: 6, background: "var(--yuzey)", color: "var(--metin)", minWidth: 220 }} />
            <select value={whSantral} onChange={(e) => setWhSantral(e.target.value)} aria-label="Webhook santrali"
                    style={{ fontSize: 12.5, padding: "5px 8px", border: "1px solid var(--kenar)", borderRadius: 6, background: "var(--yuzey)", color: "var(--metin)" }}>
              <option value="">tüm santraller</option>
              {santraller.map((s) => <option key={s.id} value={s.id}>{s.ad}</option>)}
            </select>
            <button className="dugme" type="submit">Alıcı ekle</button>
          </form>
          {yeniSir && (
            <div style={{ marginTop: 10, padding: 10, border: "1px solid var(--kenar)", borderRadius: 8 }}>
              <div style={{ fontSize: 12, marginBottom: 4 }}>İmza sırrı — <strong>bir daha gösterilmez</strong>; alıcı <span className="mono">X-PVQ-Signature</span> başlığını bununla doğrular:</div>
              <code className="mono" style={{ fontSize: 12.5, wordBreak: "break-all", userSelect: "all" }}>{yeniSir}</code>
              <div style={{ marginTop: 6 }}><button className="dugme" style={{ fontSize: 11.5 }} onClick={() => setYeniSir(null)}>Kapat</button></div>
            </div>)}
        </div>
      </div>
      <p className="soluk" style={{ fontSize: 12, margin: "10px 0 0" }}>
        Uçlar: <span className="mono">/v1/dis/santraller</span>, <span className="mono">/v1/dis/santral/{"{id}"}/tahmin</span> (ETag ile 304),
        <span className="mono"> /v1/dis/santral/{"{id}"}/kgup</span>. Oran sınırı dakikada 120 istek. Ayrıntı: docs/api/dis-api.md.
      </p>
    </Kart>
  );
}
