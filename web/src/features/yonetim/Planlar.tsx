import { useEffect, useState } from "react";
import { yonetim, type Plan, type PlanLimitAlani } from "../../api/yonetim";
import { Kart, Sayfa, SayfaIskeleti, sayiTr } from "../sayfalar/parcalar";
import { Zaman } from "./ortak";

/** 26.10 Faz 5 — PLANLAR (sahip): limitler UYARI kipi — rozetleri besler, hiçbir müşteri ucunu kısıtlamaz. Boş alan = sınırsız. */
const ALANLAR: { k: PlanLimitAlani; ad: string; birim: string }[] = [
  { k: "santral_limit", ad: "Santral", birim: "adet" }, { k: "kullanici_limit", ad: "Kullanıcı", birim: "adet" },
  { k: "api_rpm_limit", ad: "Dış API hızı", birim: "istek/dk" }, { k: "aylik_rapor_limit", ad: "Rapor", birim: "adet/ay" },
  { k: "aylik_dis_api_limit", ad: "Dış API aylık", birim: "istek/ay" },
  // v2.609 (Faz 6 F6-B): üç yeni kota — portföy, yönetilen güç (MW, ondalıklı), işlenen üretim verisi
  { k: "portfoy_limit", ad: "Portföy", birim: "adet" }, { k: "ac_mw_limit", ad: "Yönetilen güç", birim: "MW" }, { k: "aylik_isleme_saat_limit", ad: "İşlenen üretim verisi", birim: "saat/ay" }];
const mesajCikar = (e: unknown) => String((e as Error).message ?? e);
// v2.609 (F6-C): modül sırası (yetki_service.MODULLER sırası); ad uçtan gelir, yedek yalnız fixture/eski yanıt için
const MODUL_SIRA = ["tahmin", "dogruluk", "veri", "alarm", "kgup", "finansal_etki", "mutabakat", "rapor_gelismis", "paylasim", "portfoy_dsg", "dis_api", "santral_yetki", "sozlesme", "entegrasyon", "destek_oncelik"];

export function Planlar() {
  const [liste, setListe] = useState<Plan[] | null>(null); const [hata, setHata] = useState<string | null>(null); const [mesaj, setMesaj] = useState<string | null>(null);
  const [taslak, setTaslak] = useState<Record<string, Record<string, string>>>({});
  const [modulTaslak, setModulTaslak] = useState<Record<string, Record<string, boolean>>>({});   // v2.609 (F6-C): plan → modül dahil taslağı
  async function modulKaydet(p: Plan) {
    setHata(null); setMesaj(null);
    const t = modulTaslak[p.ad] ?? {};
    const g = Object.fromEntries(Object.entries(t).map(([kod, dahil]) => [kod, { dahil, sinir: p.moduller?.[kod]?.sinir ?? null }]));
    try { await yonetim.planModulGuncelle(p.ad, g); setMesaj(`${p.baslik} modülleri güncellendi.`); setModulTaslak((m) => ({ ...m, [p.ad]: {} })); await yenile(); } catch (e) { setHata(mesajCikar(e)); }
  }
  const yenile = () => yonetim.planlar().then((r) => { setListe(r.planlar); setTaslak({}); }).catch((e) => setHata(mesajCikar(e)));
  useEffect(() => { void yenile(); }, []);
  const deger = (p: Plan, k: PlanLimitAlani) => taslak[p.ad]?.[k] ?? (p[k] == null ? "" : String(p[k]));
  async function kaydet(p: Plan) {
    setHata(null); setMesaj(null);
    const t = taslak[p.ad] ?? {}; const g: Partial<Record<PlanLimitAlani, number>> & { sinirsiz?: PlanLimitAlani[] } = { sinirsiz: [] };
    for (const a of ALANLAR) { if (!(a.k in t)) continue; const v = t[a.k].trim(); if (v === "") g.sinirsiz!.push(a.k); else g[a.k] = Number(v); }
    try { await yonetim.planGuncelle(p.ad, g); setMesaj(`${p.baslik} güncellendi.`); await yenile(); } catch (e) { setHata(mesajCikar(e)); }
  }
  return (
    <Sayfa baslik="Planlar" alt="Limitler uyarı kipinde: Müşteriler ve Kullanım sayfalarında rozet olarak görünür, hiçbir uç kısıtlanmaz. Boş alan sınırsız. Modül varsayılanları plan başına; müşteriye özel istisnalar Müşteri detayında.">
      {hata && <p role="alert" className="giris-hata" style={{ marginTop: 10 }}>{hata}</p>}{mesaj && <p className="giris-bilgi" style={{ marginTop: 0 }}>{mesaj}</p>}
      {!liste ? <SayfaIskeleti kpi={0} kart={2} /> : liste.map((p) => (
        <Kart key={p.ad} baslik={p.baslik} alt={`${p.ad}; ${sayiTr(p.kiraci)} müşteri`}
          sag={<span className="cip" title="son değişiklik"><Zaman s={p.guncelleme} /></span>}>   {/* tek tarih, yerel saat (UTC kesiti çiple çelişiyordu) */}
          <form className="form-izgara" onSubmit={(e) => { e.preventDefault(); void kaydet(p); }}>
            {ALANLAR.map((a) => (
              <label key={a.k} className="girdi-etiket"><span>{a.ad} <span className="soluk">{a.birim}</span></span>   {/* 26.10 görsel uyum: etiket+birim tek satır (flex sütununda ayrı satıra düşüyordu) */}
                <input className="girdi" type="number" min={0} step={a.k === "ac_mw_limit" ? 0.1 : 1} inputMode={a.k === "ac_mw_limit" ? "decimal" : "numeric"} placeholder="sınırsız" value={deger(p, a.k)}
                  onChange={(e) => setTaslak((t) => ({ ...t, [p.ad]: { ...(t[p.ad] ?? {}), [a.k]: e.target.value } }))} /></label>))}
            <button className="dugme dugme-ana" type="submit" disabled={!taslak[p.ad]}>Kaydet</button>
          </form>
          {/* v2.609 (Faz 6 F6-C): plan → modül varsayılanları düzenlenir (dahil aç/kapa; sınır salt okunur); müşteri istisnaları etkilenmez */}
          <div className="etiket-ust" style={{ marginTop: 12 }}>Dâhil modüller</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 4 }}>
            {MODUL_SIRA.map((kod) => { const m = p.moduller?.[kod]; const secili = modulTaslak[p.ad]?.[kod] ?? !!m?.dahil; return (
              <label key={kod} className="ayar-onay" title={m?.sinir ? Object.entries(m.sinir).map(([a, v]) => `${a}: ${String(v)}`).join(" · ") : undefined}>
                <input type="checkbox" checked={secili} onChange={(e) => setModulTaslak((t) => ({ ...t, [p.ad]: { ...(t[p.ad] ?? {}), [kod]: e.target.checked } }))} />
                <span>{m?.ad ?? kod}{m?.sinir ? <span className="soluk"> · sınırlı</span> : null}{m?.durum && m.durum !== "mevcut" ? <span className="soluk"> · {m.durum_etiketi}</span> : null}</span>
              </label>); })}
          </div>
          <button className="dugme kucuk" style={{ marginTop: 8 }} disabled={!modulTaslak[p.ad]} onClick={() => void modulKaydet(p)}>Modülleri kaydet</button>
        </Kart>))}
    </Sayfa>
  );
}
