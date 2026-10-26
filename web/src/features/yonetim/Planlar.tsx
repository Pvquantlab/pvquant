import { useEffect, useState } from "react";
import { yonetim, type Plan, type PlanLimitAlani } from "../../api/yonetim";
import { Kart, Sayfa, SayfaIskeleti, sayiTr } from "../sayfalar/parcalar";
import { Zaman } from "./ortak";

/** 26.10 Faz 5 — PLANLAR (sahip): limitler UYARI kipi — rozetleri besler, hiçbir müşteri ucunu kısıtlamaz. Boş alan = sınırsız. */
const ALANLAR: { k: PlanLimitAlani; ad: string; birim: string }[] = [
  { k: "santral_limit", ad: "Santral", birim: "adet" }, { k: "kullanici_limit", ad: "Kullanıcı", birim: "adet" },
  { k: "api_rpm_limit", ad: "Dış API hızı", birim: "istek/dk" }, { k: "aylik_rapor_limit", ad: "Rapor", birim: "adet/ay" },
  { k: "aylik_dis_api_limit", ad: "Dış API aylık", birim: "istek/ay" }];
const mesajCikar = (e: unknown) => String((e as Error).message ?? e);

export function Planlar() {
  const [liste, setListe] = useState<Plan[] | null>(null); const [hata, setHata] = useState<string | null>(null); const [mesaj, setMesaj] = useState<string | null>(null);
  const [taslak, setTaslak] = useState<Record<string, Record<string, string>>>({});
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
    <Sayfa baslik="Planlar" alt="Limitler yalnız uyarı: Müşteriler ve Kullanım sayfalarında rozet olarak görünür, hiçbir uç kısıtlanmaz. Boş alan sınırsız.">
      {hata && <p role="alert" className="giris-hata" style={{ marginTop: 10 }}>{hata}</p>}{mesaj && <p className="giris-bilgi" style={{ marginTop: 0 }}>{mesaj}</p>}
      {!liste ? <SayfaIskeleti kpi={0} kart={2} /> : liste.map((p) => (
        <Kart key={p.ad} baslik={p.baslik} alt={`${p.ad}; ${sayiTr(p.kiraci)} müşteri`}
          sag={<span className="cip" title="son değişiklik"><Zaman s={p.guncelleme} /></span>}>   {/* tek tarih, yerel saat (UTC kesiti çiple çelişiyordu) */}
          <form className="form-izgara" onSubmit={(e) => { e.preventDefault(); void kaydet(p); }}>
            {ALANLAR.map((a) => (
              <label key={a.k} className="girdi-etiket"><span>{a.ad} <span className="soluk">{a.birim}</span></span>   {/* 26.10 görsel uyum: etiket+birim tek satır (flex sütununda ayrı satıra düşüyordu) */}
                <input className="girdi" type="number" min={0} step={1} inputMode="numeric" placeholder="sınırsız" value={deger(p, a.k)}
                  onChange={(e) => setTaslak((t) => ({ ...t, [p.ad]: { ...(t[p.ad] ?? {}), [a.k]: e.target.value } }))} /></label>))}
            <button className="dugme dugme-ana" type="submit" disabled={!taslak[p.ad]}>Kaydet</button>
          </form>
        </Kart>))}
    </Sayfa>
  );
}
