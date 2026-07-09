# CLAUDE.md — PVQuant Faz 2: Streamlit UI

Bu repo, PV santraller için 7 günlük saatlik üretim tahmini yapan PVQuant ürününün kodudur. Backend (fizik modeli + kalibrasyon) tamamlanmıştır; bu fazın işi, onaylanmış tasarım prototipini Streamlit uygulaması olarak inşa edip backend'e bağlamaktır.

## Kaynaklar

- `docs/design/PVQuant_Prototip_Final.html` — Onaylanmış görsel prototip (tek dosya, 5 ekran). Ekran yerleşimleri, renkler, bileşen tasarımları ve metinler birebir buradan alınır. Bu dosya ÇALIŞTIRILMAZ; Streamlit'te yeniden inşa için görsel şablondur. İçindeki tüm sayılar örnek veridir; gerçek uygulamada backend'den gelir.
- `docs/design/PVQuant_UI_Tasarim_Brief_v2.md` — Tasarım sisteminin bağlayıcı belgesi. Prototiple çelişki olursa brief kazanır. Özellikle §1 (Gizlilik Anayasası) ve §7 (Streamlit devir notları) her kararda uygulanır.

## Backend arayüzü — DOKUNMA, SADECE ÇAĞIR

UI şu fonksiyonları çağırır: `calibrate_from_scada` · `forecast_7day` · `OpenMeteoClient` · `load_csv`.
Backend modüllerinde değişiklik yapma; imza uymuyorsa önce sor. Bu adlar yalnızca kodda yaşar — UI'da görünen hiçbir metinde geçmez (aşağıya bak).

## GİZLİLİK ANAYASASI (ihlali kabul edilmez)

Yöntem ticari sırdır. Kullanıcıya görünen HİÇBİR metinde (ekran yazıları, tooltip, hata mesajı, buton, log görünümü, indirilen rapor içeriği) şunlar geçemez:

> Erbs · Perez · Faiman · Barhdadi · ModelSelector · calibrate() · predict() · eta_bos · bifacial · BG= · η= · Open-Meteo · "literatür katsayıları"

- Meteo kaynağı UI'da yalnızca "profesyonel meteoroloji verisi" olarak anılır.
- Şeffaflık yalnızca müşterinin kendi sonuçlarına uygulanır: önce/sonra sapması, bulunan parametreler ("Panel yönü (azimuth): 180° → 159°"), veri kalitesi raporu. Bunlar özgürce ve gururla gösterilir.
- Her PR öncesi UI string'lerinde yukarıdaki yasaklı listeyi tara (basit grep yeterli; mümkünse CI'a ekle).

## Tasarım Token'ları (global CSS ile uygula)

- **Font:** Inter (arayüz; başlıklar 600-700, -0.02em) · IBM Plex Mono (TÜM sayılar, tarihler, damgalar, API adresleri) · mikro-etiketler: 11.5px, BÜYÜK HARF, +0.08em, `#3D4854`
- **Renk:** birincil `#1F5288` (hover `#173F6E`) · sol menü/koyu zemin `#0E1D30` · metin `#0F1B28` / ikincil `#3D4854` / üçüncül `#6B7684` · kenarlık `#E2E6EA` · zemin `#F7F8F9`, kartlar beyaz · başarı `#1E9E6A` · uyarı `#C9502E` (yalnızca GERÇEK uyarılar; hava kaynaklı üretim düşüşü nötr gridir)
- **Amber `#E8940A`:** YALNIZCA grafiklerde "gerçekleşen üretim" veri rengi. Buton, rozet, vurgu olarak asla.
- **Yüzey:** gölge yok — 1px `#E2E6EA` kenarlık; köşe: kart 8px / buton 6px; 8px grid; emoji yasak (ikonlar 1.5px stroke SVG).
- **Grafik (Plotly):** amber dolu çizgi = gerçekleşen, `#2D6FB5` kesikli = tahmin; her grafikte lejant; soluk ızgara; mono eksen; "şimdi" için ince dikey çizgi; sapma histogramında sıfır çizgisi yeşil-kalın.
- Kontrast: hiçbir metin zemini üzerinde 4.5:1 altına düşmez.

## Ekranlar (çok sayfalı Streamlit)

Santralim · Veri Yükleme · Kalibrasyon · Tahminler · Raporlar
Ayrıntılı tanımlar brief §5'te. Sıra: önce iskelet + global CSS, sonra ekranlar prototipteki haliyle tek tek. **Her ekran bitiminde kullanıcıya göster, onay al, sonra ilerle.**

## MVP Sadeleştirmeleri (serbest)

- ⌘K komut paleti ertelenebilir.
- Önce/sonra ibresi statik olabilir (animasyonsuz iki değer + SVG ibre).
- Tablo: styled dataframe yeterli (mono, sağa hizalı, sıralanabilir).
- Grafiklerdeki 30g seçeneği görsel olarak durur, "Yakında" der.

## Çalışma Kuralları

- Türkçe UI metinleri; terim sözlüğü brief §6 (MAPE → "Ortalama tahmin hatası (MAPE)", bias → "Sapma", azimuth → "Panel yönü (azimuth)" vb.).
- Hata mesajları yol gösterir, suçlamaz; az veri engellemez, yönlendirir ("3 aydan kısa veri → hızlı tahmin öner").
- Gerçek SCADA verisi asla repo'ya commit edilmez; testler sentetik veriyle çalışır.
- Küçük, ekran-başına commit'ler; commit mesajları Türkçe veya İngilizce tutarlı tek dilde.
