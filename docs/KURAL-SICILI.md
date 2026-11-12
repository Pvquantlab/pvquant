# Mevzuat kural sicili (Faz 4 F4-F, v2.600)

Tarih: 12 Kasım 2026. Kod: `src/pvquant/ext/turkiye/kural_sicili.py` (saf, tek kaynak), `kurallar.py` (motor; sicilden okur),
`services/kural_sicili_service.py` (anlık görüntü). Göç: `alembic/versions/v2600_kural_sicili_anlik.py`. Testler:
`tests/test_kural_sicili_v2600.py`, `tests/ext/test_ext_turkiye_kurallar.py` (54 vektör), `tests/test_kurallar_gecis.py` (gün gün tablo bekçisi).

## İlke

Kural değerleri (EDT k/l, V, B, AFL, KÜPST m/n/taban, DSG eşiği, KGÜP kesimi, TPYS takvimi, senaryo fiyatı) ve yürürlük tarihleri
tek bir sürümlü sicilde yaşar. Motor sicilden okur; ekran, rapor ve dış API sicilin ürettiği aynı etiketi basar. **DB'de düzenlenebilir
kural tablosu yoktur:** geri test ve CI deterministiktir; değişiklik koddan, mühürle, testle gelir. Kural **değerleri** bu pakette
değişmedi; 54 vektör ve gün gün tablo bekçisi birebirliği doğrular.

## Kayıt yapısı (`KuralKaydi`)

| Alan | Anlam |
|---|---|
| `kural_id` | `afl`, `edt.rejim`, `edt.V`, `edt.B`, `edt.toplama`, `kupst`, `kupst.taban`, `kupst.net_sapma`, `dsg.esik`, `kgup.kesim`, `kgup.takvim`, `piyasa.senaryo`, `2027`, `dgp.15dk` |
| `surum` | sürüm etiketi (`kural_surumu` parçaları buradan: `edt-2026-V100-edta_ayrik`, `kupst-14907`, `afl-2026-04-04`…) |
| `yururluk_bas` / `yururluk_bit` | yarı açık aralık; `yururluk_bit` NULL = süresiz; `BASLANGIC` 2000-01-01 kapsam başı |
| `deger` | sayı, sözlük (k/l, m/n) ya da None (belirsiz) |
| `kunye_ad`, `madde`, `yayim_rg` | kunye.py anahtarı, madde atfı, RG tarih-sayı |
| `dogrulama` | `dogrulandi` · `cikarim` · `yorum` · `varsayim` · `belirsiz` · `dogrulanamadi` — YAPISAL (metinden türetilmez) |
| `gerekce` | motorun bastığı dayanak metni (v2.535 metinleriyle birebir) |
| `segmentler`, `kosul`, `rejim`, `degisiklik` | KÜPST segment grubu; `portfoy` / `luy_istisna`; rejim; değiştirdiği sürüm |

Sicil 71 kayıt: AFL zinciri 37, EDT 8, KÜPST 16, DSG 4, KGÜP 3, piyasa 1, 2027/15 dk 2.

## Sürüm dizgileri (bulgu M5)

- `Kural.surum` = `edt+kupst` — **biçimi değişmedi**: sonuç kayıtlarındaki `kural_surumu` geçmişle karşılaştırılabilir kalır.
- `Kural.surum_tam` = `edt+kupst+afl<değer>+dsg<yüzde>` — AFL ya da DSG eşiği değişince ayırt eder; `parametre_cercevesi` `surum_tam`
  sütunu taşır; sonuç meta'ları `kural_surumu_tam` alır.
- `kural_sicili_sha` (sicil JSON'unun SHA-256 ilk 16 hex'i) — hangi kural kümesiyle hesaplandı; FEM, portföy finans/DSG ve bağımsız
  doğrulama meta'larında.

## Anlık görüntü

`kural_sicili_anlik` (yalnız ekleme, sha16 benzersiz): gece işi `gece_kural_sicili` (03:08 TSİ) ve worker açılış koşusu `anlik_kaydet` çağırır (API açılışına DB bağımlılığı eklenmedi);
sha yeni değilse satır eklenmez. `GET /v1/kurallar/sicil` sicili ve son anlık görüntüleri döndürür.

## Gelecek yürürlük ve belirsizler

| Kayıt | Durum | Not |
|---|---|---|
| `2027-belirsiz` | belirsiz | RG 21.1.2025-32789 Md.13 (tek EDT_f, 15 dk «ç» bazlı KÜPST); 2026 rejimi sürer, sonuç «belirsiz» etiketli |
| `dsg-5-2027-varsayim` | varsayim | yıllık düşürme kararı en geç 1.12.2026; %5 varsayıldı |
| `dgp-15dk-belirsiz` | belirsiz | 15 dk DGP fiilî başlangıcı ilan edilmedi; arşiv saatlik (ZAMAN-SOZLESMESI) |
| `kupst-2025-iletim-belirsiz`, `kupst-dagitim-portfoy-belirsiz` | dogrulanamadi / belirsiz | katsayı doğrulanamadı → hesap «hesaplanamaz» |
| `edt-2025`, `kupst-7524`, AFL 2015/2017 | dogrulanamadi | karar numarası/dönem bulunamadı; değer ikincil kaynaktan |

## API ve arayüz

- `GET /v1/kurallar`: `satirlar` (tablo) + v2.600 `sicil` özeti (sürüm, sha16, kayıt sayısı, doğrulama dağılımı, bugün yürürlükte,
  gelecek) + `bugun` (kural özeti: k/l, V, B, AFL, KÜPST, DSG, takvim).
- `GET /v1/kurallar/sicil`: sicilin tamamı + anlık görüntü listesi.
- Arayüz sabitleri API'den: Portföy KÜPST kartı (`kural.m`/`n`/`yururluk`), Olay kaydı arıza sayacı (`n`/`n_ariza`), Doğruluk hesap yöntemi
  metni (`dz.kural.k/l`); KÜPST yürürlük tarihi `kural.yururluk` (sicilden). Arka uç alanları: `kupst.uevcbler[].kural {m, n, surum, taban, yururluk}` (m/n None → ekranda «—»; yürürlük kapsam başı sentineliyse None),
  `ariza_sayaci {n, n_ariza, ariza_esigi, kural_surumu, karar}` (n_ariza yoksa ekran ve açıklama sayı basmaz: «bu segmentte arıza sayısı katsayıyı değiştirmez»), kural özeti `kural_surumu_tam`, `kural_sicili_sha`, `kgup_kesim`, `kgup_takvim`.
- Sonuç meta'ları: FEM `meta.kural_sicili_sha` + `kural_sicili_surumu` + `kural_surumu_tam`; portföy finans/DSG `meta`; bağımsız doğrulama `meta()`.
- `kgup.TAKVIM` ve `piyasa_service.SENARYO_PTF/SMF/AD` sicil kayıtlarından (`kgup.takvim`, `piyasa.senaryo`) okunur; `kurallar.BELIRSIZ_2027_GEREKCE` sicilden.

## Yapılmayan

- `DAYANAK_KUNYELERI` literal blokları tekilleştirilmedi: `tests/test_kunye_bekcisi.py` blokları **literal** bekliyor (grep'lenebilir RG
  atıfları); bekçi korunduğu için sicilin künye adları (`kunye_ad`) kunye.py'ye bağlandı, bloklara dokunulmadı.
- Tarife eskalasyon baz yılı: kodda böyle bir sabit yok (eskalasyon tarife nesnesinde parametrik); sicile alınacak değer bulunmadı.
