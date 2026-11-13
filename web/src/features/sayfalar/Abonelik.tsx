import { useState, type ReactNode } from "react";
import { api, ornekKip, rolum } from "../../api/client";
import { useAbonelik } from "../../lib/abonelik";
import type { AbonelikTalep } from "../../api/types";
import { HizmetDurumu as Rozet, Kart, Katla, KotaRozet, YerTutucu, sayiTr } from "./parcalar";

/** v2.609 (Faz 6 F6-D) — MÜŞTERİ ABONELİĞİ: Ayarlar › «Aboneliğiniz» kartı (plan, durum, dâhil özellikler, sınırlar ve kullanım, yenileme) +
 *  «Teklif ya da yükseltme talebi» (doğrudan satın alma yok; talep platforma düşer) + kapalı özellik için sayfa notu (`ModulNotu`). Değerler tek uçtan
 *  (/v1/abonelik); hükümler ve sözcükler uçtan, arayüz hesaplamaz. Uyarı kipinde hiçbir sayfa kısıtlanmaz; not yalnız bilgilendirir. */
const ROZET_DURUM: Record<string, string> = { pilot: "veri_bekleniyor", aktif: "saglikli", sona_eriyor: "dikkat", yenileme_bekliyor: "dikkat", askida: "kritik", sona_erdi: "kritik", feshedildi: "uygulanmiyor" };
const KOTA_SIRA = ["santral", "kullanici", "portfoy", "ac_mw", "aylik_dis_api", "aylik_rapor", "aylik_isleme_saat"];
const gunTr = (iso: string | null) => iso ? new Date(iso + "T00:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" }) : null;

/** Kapalı özellik notu: modül plana dâhil değilse kısa bilgi + talep yönlendirmesi; dâhilse hiç çizilmez. Sayfa çalışmaya devam eder (uyarı kipi). */
export function ModulNotu({ kod }: { kod: string }) {
  const a = useAbonelik();
  const m = a?.moduller?.[kod];
  if (!a || !m || m.dahil) return null;
  return (
    <p className="form-not" style={{ margin: "0 0 12px" }}>
      <b>{m.ad}</b> {a.plan.baslik} planına dâhil değil{a.zorlama === "zorla" ? "; bu sayfa kısıtlı" : "; sayfa bilgi amaçlı çalışmaya devam ediyor"}.{" "}
      {rolum() === "viewer" ? <span>Planınız Ayarlar › Aboneliğiniz'de; talebi kuruluşunuzun editör ya da yönetici yetkili kullanıcısı gönderir.</span>
        : <a href="#kurulus">Teklif ya da yükseltme talebi için Ayarlar › Aboneliğiniz.</a>}
    </p>);
}

function Satir({ ad, children, not: n }: { ad: string; children: ReactNode; not?: string | null }) {
  return <div><dt>{ad}</dt><dd>{children}{n && <span className="kunye-not">{n}</span>}</dd></div>;
}

export function AboneliginizKarti() {
  const a = useAbonelik();
  const hata = a === null && !ornekKip;   // null: örnek kipte «yok», gerçek kipte «alınamadı» (lib hatayı önbelleklemez; sonraki ziyaret yeniden dener)
  const [talep, setTalep] = useState<AbonelikTalep>({ tur: "plan", hedef: "", mesaj: "" });
  const [sonuc, setSonuc] = useState<string | null>(null); const [talepHata, setTalepHata] = useState<string | null>(null); const [gonderiliyor, setGonderiliyor] = useState(false);
  const yazabilir = rolum() !== "viewer";
  if (a === undefined) return <Kart baslik="Aboneliğiniz"><YerTutucu yukseklik={120} /></Kart>;
  if (a === null) return <Kart baslik="Aboneliğiniz"><p className="soluk" style={{ margin: 0 }}>{hata ? "Abonelik bilgisi alınamadı. Bağlantınızı kontrol edip yeniden deneyin." : "Abonelik bilgisi bu kipte yok."}</p></Kart>;
  const dahil = Object.entries(a.moduller).filter(([, m]) => m.dahil);
  const disinda = Object.entries(a.moduller).filter(([, m]) => !m.dahil && m.durum === "mevcut");
  const yenileme = a.durum === "pilot" ? a.tarihler.pilot_bitis : a.tarihler.bitis;
  const gonder = async () => {
    setSonuc(null); setTalepHata(null); setGonderiliyor(true);
    try { await api.abonelikTalep({ tur: talep.tur, hedef: talep.hedef || null, mesaj: talep.mesaj || null }); setSonuc("Talebiniz alındı; ekibimiz kayıtlı e-posta adresinizden size ulaşacak."); setTalep({ tur: "plan", hedef: "", mesaj: "" }); }
    catch (e) { setTalepHata(String((e as Error).message ?? e)); } finally { setGonderiliyor(false); }
  };
  return (
    <Kart baslik="Aboneliğiniz" alt="Planınız, dâhil özellikler, sınırlar ve kullanım. Sınırlar uyarı kipindedir: aşımda hiçbir özellik kapanmaz, yalnız bilgi verilir."
      sag={<span className="dugme-sira"><Rozet durum={ROZET_DURUM[a.durum] ?? "dogrulanamadi"} etiket={a.durum_etiketi} />
        {a.sozlesme_istisnasi && <span className="cip" title="plan değerlerinin bir bölümü sözleşmenize göre ayarlanmış (* işaretli sınırlar)">sözleşmeye özel şartlar</span>}</span>}>
      <div className="ızgara-cift">
        <div><div className="etiket-ust">Plan ve süre</div>
        <dl className="kunye">
          <Satir ad="Plan">{a.plan.baslik}</Satir>
          <Satir ad="Durum" not={a.tarihler.kalan_gun != null ? (a.tarihler.kalan_gun >= 0 ? `${sayiTr(a.tarihler.kalan_gun)} gün kaldı` : `${sayiTr(-a.tarihler.kalan_gun)} gün önce doldu`) : null}>{a.durum_etiketi}</Satir>
          <Satir ad={a.durum === "pilot" ? "Pilot bitişi" : "Yenileme tarihi"} not={!yenileme ? "süresiz; yenileme tarihi sözleşmenizle belirlenir" : null}>{gunTr(yenileme) ?? "—"}</Satir>
          <Satir ad="Başlangıç">{gunTr(a.tarihler.baslangic) ?? "—"}</Satir>
        </dl></div>
        <div><div className="etiket-ust">Sınırlar ve kullanım</div>
        <dl className="kunye">
          {KOTA_SIRA.map((k) => { const d = a.kotalar[k]; return d ? <Satir key={k} ad={d.ad} not={d.not_ ?? null}><KotaRozet k={d} /></Satir> : null; })}
        </dl></div>
      </div>
      <div className="etiket-ust" style={{ marginTop: 12 }}>Dâhil özellikler</div>
      <div className="dugme-sira" style={{ flexWrap: "wrap", gap: 6 }}>
        {dahil.map(([kod, m]) => <span key={kod} className="cip" title={m.sinir ? "sınırlı kapsam" : undefined}>{m.ad}{m.durum !== "mevcut" ? <span className="soluk"> · {m.durum_etiketi}</span> : null}</span>)}
      </div>
      {disinda.length > 0 && <p className="soluk" style={{ fontSize: 13, margin: "10px 0 0" }}>Planınıza dâhil olmayan özellikler: {disinda.map(([, m]) => m.ad).join(", ")}.</p>}
      {a.uyarilar.length > 0 && <ul className="not-listesi uyari" style={{ marginTop: 10 }}>{a.uyarilar.map((u) => <li key={u}>{u}</li>)}</ul>}
      <p className="soluk" style={{ fontSize: 13, margin: "10px 0 0" }}>Fiyatlar ve sözleşme şartları teklifle belirlenir; panelden doğrudan satın alma yoktur. Ödeme ve faturalama panel dışında yürütülür.</p>
      {yazabilir && (
        <Katla ozet="Teklif ya da yükseltme talebi" not="plan, özellik ya da Sanayi GES için; ekibimiz kayıtlı e-postanızdan döner">
          <div className="form-izgara">
            <label className="girdi-etiket">Talep türü
              <select className="girdi" value={talep.tur} onChange={(e) => setTalep({ ...talep, tur: e.target.value as AbonelikTalep["tur"], hedef: "" })}>
                <option value="plan">Plan değişikliği</option><option value="modul">Ek özellik</option><option value="sanayi_ges">Sanayi GES (öz tüketim)</option><option value="diger">Diğer</option>
              </select></label>
            <label className="girdi-etiket">{talep.tur === "plan" ? "İstenen plan" : talep.tur === "modul" ? "İstenen özellik" : "Konu"} (isteğe bağlı)
              {talep.tur === "plan"
                ? <select className="girdi" value={talep.hedef ?? ""} onChange={(e) => setTalep({ ...talep, hedef: e.target.value })}><option value="">seçiniz</option>{["pilot", "standart", "kurumsal"].filter((p) => p !== a.plan.ad).map((p) => <option key={p} value={p}>{p === "pilot" ? "Pilot" : p === "standart" ? "Standart" : "Kurumsal"}</option>)}</select>
                : talep.tur === "modul"
                  ? <select className="girdi" value={talep.hedef ?? ""} onChange={(e) => setTalep({ ...talep, hedef: e.target.value })}><option value="">seçiniz</option>{Object.entries(a.moduller).filter(([, m]) => !m.dahil).map(([kod, m]) => <option key={kod} value={kod}>{m.ad}</option>)}</select>
                  : <input className="girdi" maxLength={64} value={talep.hedef ?? ""} onChange={(e) => setTalep({ ...talep, hedef: e.target.value })} />}</label>
            <label className="girdi-etiket form-tam">Mesaj (isteğe bağlı)<textarea className="girdi" rows={2} maxLength={500} value={talep.mesaj ?? ""} onChange={(e) => setTalep({ ...talep, mesaj: e.target.value })} /></label>
            <div className="form-tam dugme-sira">
              <button className="dugme dugme-ana" disabled={gonderiliyor} onClick={() => void gonder()}>Talep gönder</button>
              {sonuc && <span className="ayar-durum ok">{sonuc}</span>}{talepHata && <span className="ayar-durum hata">{talepHata}</span>}
            </div>
          </div>
        </Katla>)}
    </Kart>
  );
}
