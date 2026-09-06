# CLAUDE.md — PVQuant Faz 2: Streamlit UI *(tarihî belge — v2.194 notu)*

> **Güncellik notu (v2.194):** Streamlit fazı v2.160'ta kapandı (frontend/ silindi);
> UI artık `web/` (React + Vite + ECharts; tasarım tokenları `web/src/index.css` — v2.196 "Rapor Odası" dili, kaynak mockup `docs/design/redesign-2026/varyant-d-rapor-odasi.html`,
> ısı haritası paleti v2.188'den beri Mürekkep–Bakır). Bu belgeden **bağlayıcı kalanlar:**
> GİZLİLİK ANAYASASI (aşağıda) ve veri kuralları (gerçek SCADA asla commit'e girmez,
> commit disiplini). Streamlit'e ve Plotly'ye özgü satırlar tarihîdir.

Bu repo, PV santraller için saatlik üretim tahmini yapan PVQuant ürününün kodudur (tahmin ufku bugün 15 gündür). Backend (fizik modeli + kalibrasyon) tamamlanmıştır; bu fazın işi, onaylanmış tasarım prototipini Streamlit uygulaması olarak inşa edip backend'e bağlamaktı.

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
- **Lisans atfı istisnası (5 Eyl 2026, kullanıcı kararı):** Kullanılan meteoroloji/ışınım verilerinin lisansları (CC BY 4.0 vb.) atıf şart koşar; bu yükümlülük yöntem gizliliğini delmez, kaynağın ADINI söyler. Atıf yalnız üç yerde ve tek biçimde bulunur: (1) panelde "Hakkında › Veri kaynakları ve lisanslar" paneli, (2) PDF/Excel raporun künye (son) sayfası, (3) README "Veri kaynakları" bölümü. Çalışma ekranları, grafik dip notları, tooltip ve hata mesajları "profesyonel meteoroloji verisi" demeye devam eder; kaynak adı orada geçmez. Atıf metni lisansın üç şartını taşır: kaynak adı + lisans adı ve bağlantısı + "veri PVQuant tarafından işlenmiştir" notu; ör. "Meteoroloji verisi: ECMWF (Open Data, CC BY 4.0), Deutscher Wetterdienst (CC BY 4.0), NOAA/NCEP (kamu malı), Copernicus CAMS ve PVGIS/JRC (CC BY 4.0). Veriler PVQuant tarafından işlenmiştir; kaynaklar bu ürünü desteklemez." Kaynak listesi gerçek kullanımı yansıtır (geçiş bitene kadar Open-Meteo, CC BY 4.0). Yasaklı-terim grep'i bu üç yeri hariç tutar; başka yerde kaynak adı çıkarsa ihlaldir. **Uygulama (v2.269, 6 Eyl 2026):** üç yerin dosyaları — (1) `web/src/features/sayfalar/Hakkinda.tsx` ← `GET /v1/hakkinda` ← `services/kaynak_service.py` (liste gerçek kullanımdan: meteo ayarı, meteo_arsiv, calibrations.quality_json.meteo_kaynak, piyasa_fiyat); (2) PDF `reporting/pdf.py::_kunye_satiri` + HTML `reporting/html/build_s16.py` REFERANS; (3) README «Veri kaynakları». Geçiş tamamlandı: Open-Meteo varsayılan olarak KAPALI (`PVQUANT_METEO_KAYNAK=acik`), kullanılırsa Hakkında'da uyumluluk uyarısı görünür.
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
