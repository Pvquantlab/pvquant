# UYGULAMA — TL bölümü kartları («panel kesiti», tasarım C)

Bu klasördeki dosyalar depoya **birebir** uygulanır. Depoda değişiklik bu oturumda yapılmadı;
her şey geçici bir git worktree'sinde uygulanıp doğrulandı (aşağıda §4).

> **Adlar henüz çalışma adıdır** (isim kümesi A: Teslim programı · Sapma maliyeti · Şablonlu dışa
> verim · Alarm kütüphanesi · Gün içi aralık). İsim seçimi en sona bırakıldı. Seçilince yalnız
> `TurkiyePiyasasi.tsx` içindeki `KARTLAR[].ad` alanları değişir; başka hiçbir dosya ad taşımaz.

## 1. En kısa yol: yama

Depo kökünde (`main`, v2.392 üzerinde temiz uygulandığı doğrulandı):

```bash
git apply kart-tasarim/kod/degisiklik.patch
cd web && npm test && npx oxlint && npm run build
```

## 2. Dosya dosya (yama yerine elle)

| Bu klasörde | Depoda hedef | İşlem |
|---|---|---|
| `KartCizimleri.tsx` | `web/src/features/vitrin/KartCizimleri.tsx` | **yeni** — beş satır içi SVG çizim bileşeni (`CizimProgram`, `CizimSapma`, `CizimAktarim`, `CizimAlarm`, `CizimAralik`) |
| `TurkiyePiyasasi.tsx` | `web/src/features/vitrin/TurkiyePiyasasi.tsx` | **değiştir** — kart verisi (`KARTLAR`) ve `.vt-kesit` işaretlemesi; bölüm başı, maket penceresi, `id="para"` ve bölüm notu aynen |
| `vitrin-ek.css` | `web/src/features/vitrin/vitrin.css` | **sonuna ekle** — CİLA katmanı; her seçici `.vt` ile başlar (yapi.test bu kuralı tarar) |
| `TextliCizimler.tsx` | `web/src/features/vitrin/TextliCizimler.tsx` | **değiştir** — artık kullanılmayan `VinyetTl`, `VinyetTicaretGenis`, `VinyetTicaretDar` çıkarıldı; `PncEkranAna/İkinci` (maket) aynen |
| — | `web/src/features/vitrin/varlik/vinyet-{program,toplayici,operator-genis,operator-dar}.svg` | **sil** — yalnız eski kartlar kullanıyordu |
| `yapi.test.ek.ts` | `web/test/vitrin/yapi.test.ts` | **sonuna ekle** — yeni pin testi (§3) |

## 3. Testler

**Mevcut testler kırılmıyor** (değişmeden geçiyor):
- `yapi.test.ts` › «Türkiye piyasası: elle yazılmış TL ve kurulu güç dipnotu yok» — `id="para"` ve
  bölüm notu cümlesi korunur; «25,4 bin TL / 4,5 MW» yok.
- `yapi.test.ts` › «vitrin.css'teki her seçici .vt ile başlar» — `vitrin-ek.css`'in tüm seçicileri
  `.vt-kesit…` ya da `.vt [data-canlan]…`.
- `yapi.test.ts` › «satır içi stil yok» — yeni bileşenlerde `style={` yok.
- `yapi.test.ts` › iş ızgarası pini «Ticaret masası» yalnız `IsIzgarasi.tsx`'te aranır; TL kartlarından
  kalkması onu etkilemez.
- `gizlilik.test.ts` — vitrin klasörünün her dosyasını tarar; `KartCizimleri.tsx` dahil yasaklı
  terim yok (metinlerde yöntem/kaynak adı geçmez; «DSG», «API», «webhook» serbest).

**Eklenen pin** (`yapi.test.ek.ts`): TL bölümü tek `.vt-kesit` yüzeyi ve tam beş kart taşır; eski
vinyet ve «tek tık» geri dönmez; **amber (#C27803) yalnız `CizimSapma` (gerçekleşen eğrisi) ve
`CizimAlarm` (gelen ölçüm) içinde**; kart çizimlerinde şeftali (#FFB4A2) ve eylem rengi (#B11F47) yok.
Böylece veri renk sözleşmesi testle korunur.

## 4. Doğrulama (geçici worktree, 2026-10-05)

- `node --test "test/**/*.test.ts"` → **24/24 geçti** (23 mevcut + 1 yeni).
- `npx oxlint` → vitrin klasöründe uyarı yok; tüm depoda uyarı sayısı öncesi/sonrası aynı (16 = 16,
  hepsi `features/sayfalar`'da, önceden var).
- `npm run build` → başarılı (tek uyarı önceden var olan 500 kB parça uyarısı).
- Gerçek sayfa (`vite`, `?vitrin#para`) 1440 / 900 / 390 px: beş hücre, beş SVG, yinelenen `id` yok,
  konsol hatası yok, yatay taşma yok. Ekran görüntüleri: `onizleme/ekran/final-vitrin-{1440,900,390}.jpg`.
- Maket penceresiyle birlikte görünüm (4. aşamadaki «iki panel» riski): pencere şeftali sahnede
  eğik/üst üste duruyor, kesit düz beyaz yüzey — ekran görüntüsünde karışmıyor.

## 5. Notlar ve açık uçlar

- **Maket penceresi dokunulmadı** (kapsam dışı). İçindeki başlık ve `aria-label` hâlâ «Sapmanın TL
  kartı» diyor; K2'nin son adı farklı olursa pencere başlığı ile kart adı ayrışır → ayrı işte ele alınmalı.
- **Kullanılmayan eski CSS** (`.vt-vin-kart`, `.vt-masalar`, `.vt-v-genis`, `.vt-v-dar`, `.vt-sss-yer .vt-vin`)
  `vitrin.css`'te kaldı; yamaya bilerek alınmadı (kapsam: yalnız beş kart). İsterseniz ayrı bir temizlik
  commit'iyle silinebilir; hiçbir bileşen kullanmıyor.
- Kart sırası korunuyor (K1–K3 üst sıra, K4–K5 geniş alt sıra); kartlar eylemsiz (R21), kalkmaz.
- Giriş animasyonu `.vt-izgara` kartlarıyla aynı kademe; `prefers-reduced-motion`'da kapalı;
  `forced-colors`'da hücre kenarı geri gelir.
- Sürüm/commit mesajı deponun düzenine göre (ör. «v2.393 — TL bölümü kartları: panel kesiti»).

## 6. Yeniden üretmek

Adlar, metinler ya da çizimler değişirse elle düzenlemeyin; kaynaktan üretin:

```bash
# adlar: kart-tasarim/onizleme/_uret/uret.mjs → KARTLAR[].ad
# metin seçimi: kart-tasarim/onizleme/_uret/aciklamalar.mjs → SECIM
node kart-tasarim/onizleme/_uret/kod-uret.mjs   # önizlemeler + kod/KartCizimleri.tsx + kod/TurkiyePiyasasi.tsx
```

`kod-uret.mjs`, `TurkiyePiyasasi.tsx`'in bölüm başını ve maket penceresini depodaki güncel dosyadan
okur; yalnız kart verisini ve kart işaretlemesini değiştirir. Yeniden ürettikten sonra yamayı da
yenilemek için §2'deki adımları bir worktree'de uygulayıp `git diff --cached > kod/degisiklik.patch`.
