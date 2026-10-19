#!/bin/sh
# Son derleme (a1fb5b8) — yalnız Firefox kod yolu değişti: Firefox ölçümleri + tüm ekran görüntüleri + Lighthouse yeniden
cd "$(dirname "$0")/.."
echo "== matris firefox $(date)"; node olc/matris.mjs --hedef sonra --cikti after --motor firefox >> after/matris.log 2>&1
echo "== ekran $(date)"; node olc/ekran.mjs --hedef sonra --cikti after
echo "== etkileşim firefox $(date)"; node olc/etkilesim.mjs --hedef sonra --cikti after --motor firefox
echo "== lighthouse $(date)"; node olc/lh.mjs --hedef sonra --cikti after
echo "== boya firefox $(date)"; node olc/ab-boya.mjs --hedef sonra --cikti after/ab --surucu firefox-stok --gorunum 1440x900,390x844 --kosu 3 --basli --degisken mevcut
echo "== video-zaman $(date)"; node olc/video-zaman.mjs --hedef sonra --cikti analiz/ara-sonra2 --kosu 1 --degisken yeni,filtresiz
echo "== yükleme firefox $(date)"; node olc/ab-yukleme.mjs --hedef sonra --cikti after/ab --ag yavas4g,hizli3g,kablo20 --motor firefox
echo "ZINCIR-BITTI $(date)"
