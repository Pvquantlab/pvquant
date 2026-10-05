# AI-slop rubriği (LLM yargıç; ekran görüntüsünden) — 16 madde

Çıktı biçimi: her madde `{no, geçti/kaldı, kanıt (bölge/koordinat), önerilen fix}`.
⚙ = deterministik teste çevrilebilir (çevrildiyse yargıç atlar, test bekçidir).
**Zorunlu talimat:** «hepsi geçti» cevabı şüphelidir — her turda, geçse bile
**en zayıf 3 maddeyi** sırala (onay yanlılığını kırar).

## Hiyerarşi
1. Göz kısma testi: sayfada İLK görülen öğe, okuyanın en kritik sorusuna cevap veren öğe mi?
   Her şey eş ağırlıklıysa KALDI.
2. ⚙ Başlık merdiveni: sayfa > bölüm > kart başlığı arasında ≥1.25× boyut ya da belirgin
   ağırlık farkı var mı?
3. KPI'da değer, etiketinden görsel olarak baskın mı? (UPPERCASE gri etiket + hafif büyük
   değer = tipik slop.)
4. Sayfada >1 dolu/primary düğme görünüyorsa KALDI.

## Yoğunluk ve kart
5. ⚙ Kart-içinde-kart: 2+ seviye çerçeve/gölgeli kutu = KALDI.
6. Üst yarıda 5+ eş boyutlu KPI kartı dizisi, önem farkı yoksa = slop imzası.
7. Fold üstü gerçek veri alanı / krom (dolgu, başlık, boş gövde) < %50 = KALDI.
8. Boş durum «No data» tek satırı mı, yönlendiren tasarım mı?

## Boşluk ritmi
9. ⚙ Grup içi boşluk < gruplar arası mı? Her şey eşit 16 px ise KALDI.
10. ⚙ Görünen padding/gap tek ölçekten mi (4/8/12/16/24/32/48)?
11. Sol kenarlar ve sütun baseline'ları tek hatta mı? Grafik kenarı metinle hizasızsa KALDI.
12. ⚙ Kenar nefesi ≥16 px; 320 px'te kesilme/taşma yok.

## Grafik
13. Tür–soru uyumu: zaman serisi pastada mı; süs gauge/donut var mı; 3 kategoriye
    lejant+yüzde+tooltip üçü birden mi binmiş?
14. ⚙ Seri renkleri jetondan ve anlamlı mı (mavi=tahmin, amber=YALNIZ gerçekleşen)?
    6+ rastgele canlı renk ya da anlamsız yeşil/kırmızı = KALDI.
15. Eksen/lejant hijyeni: binişen etiket, ≤9 px eksen yazısı, formatlanmamış değer
    (0.0000123), birimsiz eksen = KALDI.
16. KPI'da bağlam (Δ, sparkline, önceki dönem) var mı? Çıplak sayı duvarı = slop.

## Kayıtlı istisnalar (yargıç bunları KALDI saymaz)

- Madde 4, vitrin: nav'daki sabit CTA + hero CTA aynı anda görünür — bilinçli pazarlama
  kalıbı (v2.399 turu kararı).
- Madde 12: satır içi bağlar (p/li/td/dd) WCAG 2.5.8 istisnası; `::before inset:0` taşıyan
  eleman «kartın tamamı tıklanabilir» hilesidir, kendi kutusu ölçülmez (tarama.mjs bilir).

## İlk tam tur: v2.399 (06.10.2026) — bulgular ornekler/sayfa-iyi-kotu.md'de
