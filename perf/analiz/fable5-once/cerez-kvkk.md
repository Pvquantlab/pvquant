# Çerez / yerel depolama envanteri (vitrin «/» ve «/yontem») — 20.10, kaynak taraması (çalışma zamanı doğrulaması: tarayıcı sınaması bölümünde)

**Çerez: yok.** `web/src` içinde `document.cookie` hiç geçmiyor; canlı `/` ve `/v1/dogrulama` yanıtlarında `Set-Cookie` yok
(curl -D, 20.10). Oturum belirteci çerezde değil `localStorage`'da taşınıyor (`pvq_token`, yalnız giriş yapan kullanıcıda).

**Üçüncü taraf köken: yok.** `web/src` ve `index.html`'de pvquant.com dışında hiçbir ağ kökeni yok (yalnız SIL OFL lisans adresi bir
font yorumunda). Fontlar (Fontsource) kendi sunucudan; analitik/izleme betiği yok; Google Fonts/CDN yok.

**Yerel depolama anahtarları (localStorage; kullanıcı tanımlayıcı değil, cihazda kalır, sunucuya gitmez):**

| Anahtar | Ne | Kim yazar | Ömür |
|---|---|---|---|
| `pvq_token` | oturum belirteci (yalnız giriş sonrası) | api/client.ts, App.tsx | çıkışa dek |
| `pvq_plant` | seçili santral kimliği (panel) | panel | kullanıcı değiştirene dek |
| `pvq_tema` | açık/koyu tema tercihi (panel) | shell/Kabuk.tsx | kullanıcı değiştirene dek |
| `pvq_yavas_hat` | poster 2 sn'den yavaş indiyse «video indirme» kararı (vitrin) | heroHazir.ts | süreli (dosya içinde) |
| `pvq_keskin_yazilim` | Firefox'ta WebGL tuvalinin yazılımla birleştirmede sökülme kararı | keskinGL.ts | 7 gün |
| sessionStorage `pvq_parca_yenile` | parça yükleme hatasında bir kez yenileme kilidi | main.tsx | sekme |

Vitrine giren anonim ziyaretçide yazılan tek kalıcı anahtarlar: `pvq_yavas_hat` (yalnız yavaş hatta) ve `pvq_keskin_yazilim`
(yalnız Firefox + yazılım birleştirme). İkisi de kişisel veri değil, teknik tercih; KVKK/çerez bildirimi gerektiren bir izleme yok.

**Çalışma zamanı doğrulaması (olc/cerez-sina.mjs, 20.10; dört motor, 390×844, «/» ve «/yontem», 8 sn + sayfa sonuna kaydırma):**
çerez 0/0/0/0 (Chromium, Firefox, WebKit, Edge); «/»te localStorage yalnız `pvq_yavas_hat` (poster hız kararı), «/yontem»de hiç;
sessionStorage boş; istenen köken yalnız sitenin kendisi (`analiz/fable5-once/cerez-sina.txt`).
