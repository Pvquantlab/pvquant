import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { Dogrulama } from "../../api/types";
import {
  M, D, YESIL, FILIZ, ALTIN, ALTIN_KOYU, METIN, METIN_IKINCIL,
  KREM, BEYAZ, GECE_YESIL, KENAR_GUNDUZ, GOLGE_GUNDUZ, KENAR_GECE, Marka,
} from "./Vitrin";

/** /yontem — yöntem ve doğrulama alt sayfası (v2.333, envanter raporu m.5).
 *  Amaç: vitrindeki ve paneldeki her doğruluk değerinin nasıl üretildiğini
 *  denetlenebilir biçimde anlatmak — "ölçülü dürüstlük" kimliğinin kanıt
 *  derinliği. Vitrinle aynı gün-yayı dili: şafak (giriş) → gündüz (süreç ve
 *  tanımlar) → gece (kalibrasyon ve denetlenebilirlik).
 *  Dürüstlük kuralları burada da geçerli: sayı vaat edilmez, canlı değerler
 *  yalnız kamuya açık /v1/dogrulama ucundan gelir; uç kapalıysa çip çizilmez. */

const ADIMLAR = [
  ["Tahmin önceden kaydedilir",
   "Her santral için saatlik tahmin ve iyimser–kötümser aralık, gün başlamadan üretilir ve zaman damgasıyla saklanır. Kayıt üzerinde sonradan düzeltme yapılmaz."],
  ["Gerçekleşen üretim toplanır",
   "Üretim (SCADA/sayaç) verisi geldikçe saatlik seriye işlenir. Ölçüm gelmeyen saatler karneye dâhil edilmez; eksik veri sıfır sayılmaz."],
  ["Her gece otomatik karşılaştırma",
   "Kapanan günün tahmini ile gerçekleşen üretimi, tüm santrallar için aynı kuralla karşılaştırılır. Hesap kişiye ve güne göre değişmez."],
  ["Sonuç birikir, geçmiş değişmez",
   "Karne satırları yalnızca eklenir; kötü geçen gün silinmez, yeniden hesaplanmaz. Doğruluk değerleri bu birikimin penceresidir."],
] as const;

const METRIKLER = [
  ["Ortalama sapma (WMAPE)",
   "Gündüz saatlerinde |tahmin − gerçekleşen| toplanır ve toplam gerçekleşen üretime bölünür. Üretime ağırlıklıdır: düşük üretimli saatlerdeki küçük mutlak farkların yüzdeyi şişirmesine izin verilmez. Küçük değer iyidir."],
  ["Basit yöntem (referans)",
   "“Yarın = dün aynı saat” kuralı. Maliyeti sıfır olduğu için sektörde taban kabul edilir; her doğruluk değeri bu tabanla yan yana yayımlanır. Tabanı geçemeyen tahminin değeri yoktur."],
  ["Sıkı referans",
   "Ay ve saate göre iklim beklentisi ile akıllı sürekliliğin birleşimi — basit yöntemden belirgin ölçüde zor bir kıyas çıtası. Kolay rakibe karşı değil, güçlü referansa karşı ölçülürüz."],
  ["Beceri",
   "Referansa göre iyileşme oranı: (referans sapması − PVQuant sapması) / referans sapması. Sıfırın üstü, tahminin referanstan iyi olduğu anlamına gelir."],
  ["Bant kapsaması",
   "Gerçekleşen üretimin, önceden ilan edilen iyimser–kötümser aralık içinde kaldığı saatlerin oranı. Hedef %80'dir — %100 değil: her zaman tutan bant, karar için fazla geniş demektir."],
] as const;

export function Yontem() {
  const [dg, setDg] = useState<Dogrulama | null>(null);
  useEffect(() => {
    api.dogrulama().then((d) => { if (d?.durum === "acik") setDg(d); }).catch(() => {});
    const eski = document.title;
    document.title = "PVQuant — Yöntem ve doğrulama";
    return () => { document.title = eski; };
  }, []);
  const kartG = { background: "#FFFFFF", border: KENAR_GUNDUZ, borderRadius: 16,
    padding: "20px 22px", boxShadow: GOLGE_GUNDUZ } as const;
  const kartN = { background: "rgba(255,255,255,0.03)", border: KENAR_GECE,
    borderRadius: 16, padding: "20px 22px" } as const;
  return (
    <div style={{ background: BEYAZ, color: METIN, minHeight: "100vh" }}>
      <style>{`
        .vt-dugme:hover { filter: brightness(1.08); }
        .vt-dugme:active { transform: translateY(1px); }
        .vt-dugme:focus-visible, .vt-baglanti:focus-visible {
          outline: 2.5px solid ${YESIL}; outline-offset: 2.5px; }
        @media (prefers-reduced-motion: reduce) {
          .vt-dugme { transition: none !important; }
        }
        .yt-tanim { display: grid; gap: 4px 22px; padding: 16px 0;
          grid-template-columns: minmax(150px, 210px) 1fr; }
        /* dar ekranda etiket üstte: iki sütun 375px'te tek kelimelik satırlara
           düşürüyordu */
        @media (max-width: 620px) { .yt-tanim { grid-template-columns: 1fr; } }
      `}</style>

      {/* ---- üst şerit: vitrinle aynı şafak zemini ---- */}
      <div style={{ background:
        `linear-gradient(180deg, ${KREM} 0%, #FDF3DF 62%, ${BEYAZ} 100%)` }}>
        <header style={{ display: "flex", justifyContent: "space-between",
          alignItems: "center", padding: "22px 6vw", gap: 12 }}>
          <a href="/" className="vt-baglanti" style={{ display: "flex",
            alignItems: "center", gap: 10, fontWeight: 700, fontSize: 18,
            color: METIN, textDecoration: "none" }}>
            <Marka />
            PVQuant
          </a>
          <a href="/" className="vt-baglanti" style={{ fontSize: 14.5,
            fontWeight: 500, color: METIN_IKINCIL, textDecoration: "none" }}>
            ← Ana sayfa</a>
        </header>

        <section style={{ maxWidth: 760, margin: "0 auto",
          padding: "40px 6vw 54px", textAlign: "center" }}>
          <div style={{ fontFamily: M, fontSize: 12, letterSpacing: "0.14em",
            color: ALTIN_KOYU }}>AÇIK KARNE · YÖNTEM VE DOĞRULAMA</div>
          <h1 style={{ fontFamily: D, fontSize: "clamp(30px, 4.6vw, 46px)",
            lineHeight: 1.1, margin: "16px 0 0", letterSpacing: "-0.025em" }}>
            Sayıların arkasındaki <span style={{ color: YESIL }}>yöntem</span>.
          </h1>
          <p style={{ fontSize: 16.5, color: METIN_IKINCIL, maxWidth: 600,
            margin: "18px auto 0", lineHeight: 1.65 }}>
            Vitrindeki ve paneldeki her doğruluk değeri aynı gece sürecinden
            çıkar. Bu sayfa o süreci, metrik tanımlarını ve sonuçların nasıl
            denetlenebileceğini açıklar — beyan değil, tarif.
          </p>
        </section>
      </div>

      {/* ---- gündüz 1: gece sınavı süreci (gerçek bir sıra — numara hak edilmiş) ---- */}
      <section style={{ padding: "48px 6vw 8px" }}>
        <div style={{ maxWidth: 860, margin: "0 auto" }}>
          <div style={{ fontFamily: M, fontSize: 12, letterSpacing: "0.14em",
            color: YESIL, textAlign: "center" }}>GECE SINAVI</div>
          <h2 style={{ fontFamily: D, letterSpacing: "-0.018em",
            fontSize: "clamp(22px, 3vw, 30px)", textAlign: "center",
            margin: "12px 0 30px" }}>Karne nasıl oluşur</h2>
          {/* 2×2 sabit: auto-fit 240px, ara genişliklerde 3+1 bırakıp
              dördüncü adımı yalnız koyuyordu */}
          <div style={{ display: "grid", gap: 14,
            gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 320px), 1fr))" }}>
            {ADIMLAR.map(([baslik, metin], i) => (
              <div key={baslik} style={kartG}>
                <div style={{ fontFamily: M, fontSize: 11, color: ALTIN_KOYU,
                  letterSpacing: "0.08em" }}>{String(i + 1).padStart(2, "0")}</div>
                <div style={{ fontWeight: 650, fontSize: 15.5,
                  margin: "8px 0 6px" }}>{baslik}</div>
                <div style={{ fontSize: 13.5, lineHeight: 1.6,
                  color: METIN_IKINCIL }}>{metin}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ---- gündüz 2: metrik tanımları ---- */}
      <section style={{ padding: "56px 6vw 64px" }}>
        <div style={{ maxWidth: 760, margin: "0 auto" }}>
          <div style={{ fontFamily: M, fontSize: 12, letterSpacing: "0.14em",
            color: YESIL, textAlign: "center" }}>TANIMLAR</div>
          <h2 style={{ fontFamily: D, letterSpacing: "-0.018em",
            fontSize: "clamp(22px, 3vw, 30px)", textAlign: "center",
            margin: "12px 0 30px" }}>Metrikler ne ölçer</h2>
          {METRIKLER.map(([ad, tanim]) => (
            <div key={ad} className="yt-tanim" style={{ borderTop: KENAR_GUNDUZ }}>
              <div style={{ fontWeight: 650, fontSize: 14.5 }}>{ad}</div>
              <div style={{ fontSize: 14, lineHeight: 1.65,
                color: METIN_IKINCIL }}>{tanim}</div>
            </div>
          ))}
          <div style={{ borderTop: KENAR_GUNDUZ }} />
        </div>
      </section>

      {/* ---- gece: kalibrasyon + denetlenebilirlik ---- */}
      <section style={{ background:
        `linear-gradient(180deg, #081A24 0%, ${GECE_YESIL} 30%, ${GECE_YESIL} 100%)`,
        color: "#F2F7F4", padding: "64px 6vw 72px" }}>
        <div style={{ maxWidth: 760, margin: "0 auto" }}>
          <div style={{ fontFamily: M, fontSize: 12, letterSpacing: "0.14em",
            color: FILIZ, textAlign: "center" }}>DÜRÜSTLÜK KURALLARI</div>
          <h2 style={{ fontFamily: D, letterSpacing: "-0.018em", color: "#F2F7F4",
            fontSize: "clamp(22px, 3vw, 30px)", textAlign: "center",
            margin: "12px 0 30px" }}>Aralık ve yayın disiplini</h2>
          <div style={{ display: "grid", gap: 14 }}>
            <div style={kartN}>
              <div style={{ fontWeight: 650, fontSize: 15.5,
                marginBottom: 6 }}>Aralık gerçek hatayla ayarlanır</div>
              <div style={{ fontSize: 14, lineHeight: 1.65, color: "#9DB3A9" }}>
                İyimser–kötümser bandın genişliği varsayımla değil, santralın
                geçmiş sınav sonuçlarıyla kalibre edilir ve tahmin ufkuna göre
                değişir: yarın için dar, üç gün sonrası için daha geniştir.
                Kapsama hedeften saparsa bant otomatik olarak daraltılır ya da
                genişletilir.
              </div>
            </div>
            <div style={kartN}>
              <div style={{ fontWeight: 650, fontSize: 15.5,
                marginBottom: 6 }}>Yetersiz veriyle karne yayımlanmaz</div>
              <div style={{ fontSize: 14, lineHeight: 1.65, color: "#9DB3A9" }}>
                Kamuya açık karne, en az 30 günlük gece sınavı birikmeden
                yayımlanmaz; doğruluk değerleri kaç günlük pencereden
                hesaplandıysa o pencere karnenin üzerinde yazar. Ölçüm olmayan
                dönem için değer üretilmez — eksik veri tire ile gösterilir.
              </div>
            </div>
            <div style={kartN}>
              <div style={{ fontWeight: 650, fontSize: 15.5,
                marginBottom: 6 }}>Denetlenebilirlik</div>
              <div style={{ fontSize: 14, lineHeight: 1.65, color: "#9DB3A9" }}>
                Vitrindeki Açık karne elle yazılmış değildir; kimlik doğrulaması
                gerektirmeyen bir uçtan canlı okunur. Aynı sayıları herkes,
                herhangi bir anda kendisi çekebilir:
              </div>
              <div style={{ fontFamily: M, fontSize: 12.5, color: "#8FD4B4",
                background: "rgba(0,0,0,0.25)", border: KENAR_GECE,
                borderRadius: 10, padding: "10px 14px", marginTop: 12,
                overflowX: "auto", whiteSpace: "nowrap" }}>
                GET /v1/dogrulama</div>
              {dg && (
                <div style={{ fontFamily: M, fontSize: 11.5, color: "#8AA79B",
                  marginTop: 10 }}>
                  şu an: {dg.santral_etiketi} · son {dg.pencere_gun} gün ·
                  ortalama sapma %{dg.wmape_pct?.toLocaleString("tr-TR") ?? "—"}
                </div>
              )}
            </div>
          </div>
          <div style={{ display: "flex", gap: 14, justifyContent: "center",
            marginTop: 36, flexWrap: "wrap" }}>
            <a href="/#karne" className="vt-dugme vt-baglanti"
              style={{ padding: "13px 26px", borderRadius: 12, fontSize: 15,
              fontWeight: 600, textDecoration: "none", background: FILIZ,
              color: "#06231A" }}>Açık karneyi görün</a>
            <a href="/#basla" className="vt-dugme vt-baglanti"
              style={{ padding: "13px 26px", borderRadius: 12, fontSize: 15,
              fontWeight: 600, textDecoration: "none", background: "transparent",
              border: `1.5px solid ${ALTIN}`, color: "#F2D9AE" }}>
              Kendi karnenizi başlatın</a>
          </div>
        </div>
      </section>

      <footer style={{ background: GECE_YESIL, color: "#5C6F66",
        padding: "0 6vw 30px" }}>
        <div style={{ maxWidth: 760, margin: "0 auto", fontFamily: M,
          fontSize: 11, display: "flex", justifyContent: "space-between",
          flexWrap: "wrap", gap: 8, borderTop: "1px solid rgba(255,255,255,0.08)",
          paddingTop: 22 }}>
          <span>© PVQuant 2026</span>
          <a href="/" style={{ color: "#8AA79B", textDecoration: "none" }}>
            pvquant ana sayfa</a>
        </div>
      </footer>
    </div>
  );
}
