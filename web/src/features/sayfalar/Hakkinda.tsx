import { useEffect, useState } from "react";
import { api, bellektenOku, ayniysaEskisi } from "../../api/client";
import type { Hakkinda as HakkindaT, KuralTablosu } from "../../api/types";
import { Kart, Sayfa, sayiTr, YerTutucu } from "./parcalar";

/** v2.270 (Dalga 0) — Hakkında › Veri kaynakları ve lisanslar.
 *  Gizlilik Anayasası v2.245 istisnası: kaynak adı + lisans bağlantısı YALNIZ burada (ve rapor künyesi, README).
 *  Liste sunucunun gerçek kullanımından gelir; kullanılmayan kaynağa atıf yazılmaz. */
/** 18.11 Parti 4 (aşamalı çizim): dört kart baştan yerinde — önceden üçü veri gelince araya giriyordu (iki istek × koşullu kart = üç aşamalı
 *  kuruluş; canlı hakkinda 723 ms). Gövdeler ölçülen boyda yer tutucu (510/750/600/195); veri yok/alınamadı açıkça yazılır, kart kalkmaz. */
const ALINAMADI = "Sunucudan alınamadı; örnek kipte bu liste yoktur.";   // 18.11 Parti 4 son kontrol: dört kartta aynı dürüst metin (null = örnek kip ya da hata)
export function Hakkinda() {
  // 24.10 açık tema geçiş turu: bayat-önce — bellekte son liste varsa dönüşte anında; yoldayken yer tutucu (metin yerine)
  const [h, setH] = useState<HakkindaT | null | undefined>(() => bellektenOku<HakkindaT>("/v1/hakkinda"));
  useEffect(() => { api.hakkinda().then((v) => setH((e) => (v ? ayniysaEskisi(e, v) : v))).catch(() => setH(null)); }, []);
  // v2.528 (P10, ENV-F04): uzlaştırma kuralı sürüm tablosu — API'de vardı (GET /v1/kurallar), panelde yoktu
  const [kurallar, setKurallar] = useState<KuralTablosu | null | undefined>(() => bellektenOku<KuralTablosu>("/v1/kurallar"));
  useEffect(() => { api.kurallar().then((v) => setKurallar((e) => (v ? ayniysaEskisi(e, v) : v))).catch(() => setKurallar(null)); }, []);
  const gunTr = (s: string | null) => s ? new Date(s + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "short", year: "numeric" }) : "—";
  const sayiMi = (v: number | null | undefined, nd = 2) => typeof v === "number" ? sayiTr(v, nd) : "—";
  const yonlu = (k: Record<string, number> | null) => k ? `${sayiMi(k.acik)} / ${sayiMi(k.fazla)}` : "—";   // sistem açığı / sistem fazlası (dengede ipucunda)
  const tarih = (s: string | null | undefined) => s ? new Date(s).toLocaleString("tr-TR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "—";
  const sol = { textAlign: "left" as const };
  // v2.535: kural satırı doğrulama durumu — dört değer, dört rozet; bilinmeyen değer «—»
  const durumRozeti = (d: string | undefined) => d === "dogrulandi" ? <span className="rozet rozet-ok rozet-kucuk">doğrulandı</span>
    : d === "cikarim" ? <span className="rozet rozet-notr rozet-kucuk" title="Yürürlük tarihi «yayımı takip eden fatura dönemi» ifadesinden çıkarım">çıkarım</span>
    : d === "dogrulama_gerekli" ? <span className="rozet rozet-uyari rozet-kucuk" title="Dayanağın bir parçası birincil kaynakta bulunamadı">doğrulama gerekli</span>
    : d === "belirsiz" ? <span className="rozet rozet-dikkat rozet-kucuk" title="1.1.2027 sonrası uygulama ayrıntıları henüz belirsiz (DUY m.110)">belirsiz</span> : "—";
  const bag = { color: "var(--ikincil)", textDecoration: "underline", textUnderlineOffset: 2 };
  return (
    <Sayfa baslik="Hakkında" alt="Veri kaynakları, lisanslar ve işleme notu.">
      <Kart baslik="Veri kaynakları ve lisanslar">
        {h === undefined ? <YerTutucu yukseklik={490} />
         : !h ? <p className="soluk" style={{ margin: 0 }}>{ALINAMADI}</p> : (
          <>
            {h.uyarilar.length > 0 && <ul className="not-listesi uyari" style={{ margin: "0 0 10px" }}>{h.uyarilar.map((u) => <li key={u}>{u}</li>)}</ul>}
            <div className="grafik-kaydir">
              <table className="veri">
                <thead><tr><th style={sol}>Kaynak</th><th style={sol}>Kurum</th><th style={sol}>Lisans</th><th style={sol}>Ne için</th></tr></thead>
                <tbody>
                  {h.kaynaklar.map((k) => (
                    <tr key={k.kimlik}>
                      <td style={{ ...sol, fontWeight: 600 }}><a href={k.veri_url} target="_blank" rel="noreferrer" style={bag}>{k.ad}</a></td>
                      <td style={sol}>{k.kurum}</td>
                      <td style={sol}><a href={k.lisans_url} target="_blank" rel="noreferrer" style={bag}>{k.lisans}</a>
                        {/* v2.535: lisans sayfası son ne zaman okundu — kayıt yoksa açıkça «doğrulama kaydı yok» */}
                        <div className="soluk t-kucuk" style={{ marginTop: 2 }} title={k.lisans_notu ?? undefined}>{k.lisans_dogrulama ? `lisans sayfası doğrulandı ${gunTr(k.lisans_dogrulama)}` : "lisans sayfası doğrulama kaydı yok"}</div></td>
                      <td className="soluk" style={sol}>{k.not}</td>
                    </tr>))}
                </tbody>
              </table>
            </div>
            <p className="t-ikincil" style={{ margin: "12px 0 0", lineHeight: 1.55 }}>{h.yontem}</p>
            {/* v2.569 (Faz 0 karne paketi): karne tanımı değişikliği tarihli ve açık — «geçmiş değişmez» ilkesinin tek istisnası burada yazılı */}
            <p className="soluk t-ikincil" style={{ margin: "8px 0 0", lineHeight: 1.55, maxWidth: "90ch" }}>
              Karne tanımı 10 Kasım 2026'da düzeltildi: her saat için yalnızca en erken yayımlanan tahmin sınava girer; gün içi güncellemeler ve
              program tahmini (bir gün önce 15:30 kesimi öncesi) ayrı sayılır. Geçmiş karne yeni tanımla yeniden hesaplandı; önceki değerler yedekte tutulur.
            </p>
          </>
        )}
      </Kart>
        <Kart baslik="Mevzuat ve standart dayanağı" sag={<span className="cip" title="k/l, V, B, AFL ve DSG eşiği kural tablosundan gelir; yalnız KÜPST n ve tolerans santral ayarından geçersiz kılınabilir">yalnız KÜPST n/tolerans ayardan değişir</span>}>
          {h === undefined ? <YerTutucu yukseklik={680} /> : !h || !h.mevzuat?.length ? <p className="soluk" style={{ margin: 0 }}>{!h ? ALINAMADI : "Kayıt yok."}</p> : (<>
          <div className="grafik-kaydir">
            <table className="veri">
              <thead><tr><th style={sol}>Dayanak</th><th style={sol}>Kapsam</th><th style={sol}>Yayım (Resmî Gazete tarih-sayı, karar)</th><th style={sol}>Not</th></tr></thead>
              <tbody>
                {h.mevzuat!.map((m) => (
                  <tr key={m.ad}>
                    <td style={{ ...sol, fontWeight: 600, minWidth: 180, maxWidth: 250, whiteSpace: "normal" }}>{m.ad}</td>
                    <td style={{ ...sol, minWidth: 180, maxWidth: 260, whiteSpace: "normal" }}>{m.kapsam}</td>
                    {/* v2.535: birincil yayım bilgisi — doğrulama arşivinin kaynak envanteriyle aynı */}
                    <td className="t-etiket" style={{ ...sol, whiteSpace: "normal", minWidth: 320 }}>{m.kunye ?? "—"}</td>
                    <td className="soluk" style={{ ...sol, minWidth: 240, whiteSpace: "normal" }}>{m.not}</td>
                  </tr>))}
              </tbody>
            </table>
          </div>
          <p className="soluk t-ikincil" style={{ margin: "10px 0 0" }}>
            Ürün bu çerçevenin tanımlarını uygular; madde numaraları yürürlükteki metne, yayım sütunu o metnin Resmî Gazete yayımına işaret eder (son değişiklik dâhil; 03.11.2026 doğrulama arşiviyle eş).
            Mevzuat değişirse kural tablosu (kural motoru) yeni sürümle güncellenir; k/l, V, B, AFL ve DSG eşiği ayarlardan değişmez.
            Yalnız KÜPST n ve tolerans Santralim › Santral ayarları'ndan geçersiz kılınabilir; geçersiz kılma Doğruluk sayfasında etiketlenir.
          </p>
          </>)}
        </Kart>
        <Kart baslik="Uzlaştırma kuralı sürüm tablosu" alt="Dengesizlik ve KGÜP sapma hesabında kullanılan katsayı ve parametrelerin geçerlilik dönemleri (lisanslı serbest piyasa); yeniden hesap bu tabloyla yapılır, EPİAŞ sonucu esastır"
          sag={<>
            <span className="cip">salt okunur · kaynak: kural motoru</span>
            {/* v2.535: kaç satırın dayanağı eksik — gizlenmez */}
            {kurallar?.satirlar.some((r) => r.dogrulama === "dogrulama_gerekli") && <span className="rozet rozet-uyari rozet-kucuk" title="Dayanağın bir parçası birincil kaynakta bulunamadı; ayrıntı satırın Dayanak alanında">{sayiTr(kurallar.satirlar.filter((r) => r.dogrulama === "dogrulama_gerekli").length)} satır doğrulama gerekli</span>}
          </>}>
          {kurallar === undefined ? <YerTutucu yukseklik={560} /> : !kurallar || kurallar.satirlar.length === 0 ? <p className="soluk" style={{ margin: 0 }}>{!kurallar ? ALINAMADI : "Kayıt yok."}</p> : (<>
          <div className="grafik-kaydir">
            <table className="veri dar">
              <thead><tr><th style={sol}>Geçerlilik</th><th style={sol}>Kural sürümü</th><th style={sol}>Rejim</th><th title="Dengesizlik katsayıları sistem yönüne göre (Karar 14030): sistem açığı / sistem fazlası; dengede ipucunda">k (açık / fazla)</th><th title="Sistem açığı / sistem fazlası">l (açık / fazla)</th><th title="Düşük fiyat eşiği (TL/MWh)">V</th><th title="KÜPST tolerans oranı (m) ve fiyat katsayısı (n; arıza eşiğinde n arıza)">KÜPST m / n</th><th title="DSG netleşme eşiği">DSG eşiği</th><th style={sol} title="doğrulandı: birincil kaynak belirli · çıkarım: yürürlük tarihi metinden çıkarım · doğrulama gerekli: dayanağın bir parçası bulunamadı · belirsiz: 2027 sonrası">Durum</th><th style={sol}>Dayanak</th></tr></thead>
              <tbody>
                {kurallar.satirlar.map((r) => (
                  <tr key={r.gecerlilik_bas}>
                    <td style={{ ...sol, whiteSpace: "nowrap" }}>{gunTr(r.gecerlilik_bas)} – {r.gecerlilik_bitis ? gunTr(r.gecerlilik_bitis) : "…"}</td>
                    <td style={sol}>{r.kural_surumu}</td>
                    <td style={sol}>{r.rejim}</td>
                    <td className="mono" title={r.k ? `dengede ${sayiMi(r.k.dengede)}` : undefined}>{yonlu(r.k)}</td>
                    <td className="mono" title={r.l ? `dengede ${sayiMi(r.l.dengede)}` : undefined}>{yonlu(r.l)}</td>
                    <td className="mono">{sayiMi(r.V, 0)}</td>
                    <td className="mono">{sayiMi(r.kupst.m, 2)} / {sayiMi(r.kupst.n, 2)}{r.kupst.n_ariza != null ? ` (${sayiTr(r.kupst.n_ariza, 2)})` : ""}</td>
                    <td className="mono" title={r.dsg_dayanak ?? undefined}>{sayiMi(r.dsg_esik, 2)}</td>   {/* 04.11 v2.529: 1.1.2025 öncesi eşik yok → «—», dayanak ipucunda */}
                    <td style={{ ...sol, whiteSpace: "nowrap" }}>{durumRozeti(r.dogrulama)}</td>
                    {/* v2.535: dayanak açılır metinde — satır sığar, tam metin ve eksik parça notu tıklayınca */}
                    <td className="soluk" style={{ ...sol, minWidth: 220, maxWidth: 420, whiteSpace: "normal" }}>
                      <details><summary style={{ cursor: "pointer" }}>dayanak ve durum notu</summary>
                        <div className="t-etiket" style={{ marginTop: 6, lineHeight: 1.5 }}>
                          <div><b>EDT:</b> {r.edt_dayanak}</div>
                          {r.kupst.dayanak && <div><b>KÜPST:</b> {r.kupst.dayanak}</div>}
                          {r.dsg_dayanak && <div><b>DSG:</b> {r.dsg_dayanak}</div>}
                          {r.dogrulama_notu && <div><b>Durum notu:</b> {r.dogrulama_notu}</div>}
                        </div></details></td>
                  </tr>))}
              </tbody>
            </table>
          </div>
          <p className="soluk t-ikincil" style={{ margin: "10px 0 0" }}>{kurallar.satirlar.some((r) => r.dsg_esik == null) && <>DSG eşiği «—»: 1.1.2025 öncesinde üye eşiği yoktu, sapmalar DSG içinde tamamen netleşir (DUY m.111(3)-(5) 1.1.2025'ten). </>}Durum sütunu: «doğrulandı» birincil kaynak (Resmî Gazete yayımı / Kurul kararı) belirli; «çıkarım» yürürlük tarihi «yayımı takip eden fatura dönemi» ifadesinden çıkarım; «doğrulama gerekli» dayanağın bir parçası birincil kaynakta bulunamadı (hangi parça olduğu Dayanak altında). k/l, V, B, AFL ve DSG eşiği bu tablodan gelir ve ayarlardan değişmez; yalnız KÜPST n ve tolerans santral ayarından geçersiz kılınabilir (Doğruluk sayfasında etiketlenir). Dış API: GET /v1/kurallar.</p>
          </>)}
        </Kart>
        <Kart baslik="Meteoroloji arşivi" sag={<span className="cip">tahmin başına nokta serileri</span>}>
          {h === undefined ? <YerTutucu yukseklik={180} /> : !h || Object.keys(h.arsiv).length === 0 ? <p className="soluk" style={{ margin: 0 }}>{!h ? ALINAMADI : "Arşiv boş."}</p> : (<>
          <div className="grafik-kaydir">
            <table className="veri">
              <thead><tr><th style={sol}>Kaynak</th><th style={sol} title="Arşivdeki en yeni model tahmininin başlangıç saati; indirmenin yapıldığı saat değil (o aşağıda, iş günlüğünden)">Son model tahmini</th><th>Nokta</th><th>Satır</th><th style={sol}>Kapsam</th></tr></thead>
              <tbody>
                {Object.entries(h.arsiv).map(([k, v]) => (
                  <tr key={k}><td style={sol}>{k}</td><td className="mono" style={sol}>{tarih(v.son)}</td><td className="mono">{sayiTr(v.nokta)}</td><td className="mono">{sayiTr(v.satir)}</td>
                    <td className="mono" style={sol}>{tarih(v.ilk)} → {tarih(v.son_ts)}</td></tr>))}
              </tbody>
            </table>
          </div>
          {/* v2.535: indirme işinin günlüğü — «son model tahmini» ile karıştırılmaz; kayıt yoksa açıkça söylenir */}
          {h.isler && Object.entries(h.isler).map(([j, v]) => (
            <p className="t-ikincil" key={j} style={{ margin: "10px 0 0" }}>
              <b>{v.ad}:</b> {v.son_deneme
                ? <>son deneme {tarih(v.son_deneme)} ({v.son_durum === "ok" ? "başarılı" : `hata${v.son_ayrinti ? `: ${v.son_ayrinti}` : ""}`}) · son başarılı {tarih(v.son_basarili)}</>
                : "iş günlüğünde kayıt yok"}
              {v.son_deneme && v.son_durum !== "ok" && <span className="rozet rozet-uyari rozet-kucuk" style={{ marginLeft: 6 }}>son deneme başarısız</span>}
            </p>))}
          <p className="soluk t-ikincil" style={{ margin: "10px 0 0" }}>
            Her gece, tahmin işinden bir saat önce hava tahmini verisi indirilir, santral noktaları çıkarılır ve saklanır; tahmin, kalibrasyon ve hava verisi
            tutarlılık denetimi aynı arşivden beslenir. Ham ızgara dosyaları tutulmaz.
          </p>
          </>)}
        </Kart>
    </Sayfa>
  );
}
