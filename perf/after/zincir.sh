#!/bin/sh
# «sonra» ölçüm zinciri — baseline ile aynı betikler ve parametreler, sırayla (CPU yarışı olmasın)
cd "$(dirname "$0")/.."
echo "== matris $(date)"; node olc/matris.mjs --hedef sonra --cikti after > after/matris.log 2>&1
echo "== ekran $(date)"; node olc/ekran.mjs --hedef sonra --cikti after
echo "== etkileşim $(date)"; node olc/etkilesim.mjs --hedef sonra --cikti after
echo "== lighthouse $(date)"; node olc/lh.mjs --hedef sonra --cikti after
echo "== envanter $(date)"; node olc/envanter.mjs --hedef once --cikti baseline; node olc/envanter.mjs --hedef sonra --cikti after
echo "== boya $(date)"; node olc/ab-boya.mjs --hedef sonra --cikti after/ab --surucu firefox-stok,chrome --gorunum 1440x900,390x844 --kosu 3 --basli --degisken mevcut
node olc/ab-boya.mjs --hedef sonra --cikti after/ab --surucu pw-webkit --gorunum 1440x900 --kosu 3 --basli --degisken mevcut
echo "== yükleme $(date)"; node olc/ab-yukleme.mjs --hedef sonra --cikti after/ab --ag yavas4g,hizli3g,kablo20
echo "== gürültü tabanı $(date)"; node olc/ekran.mjs --hedef once --cikti analiz/gurultu
echo "ZINCIR-BITTI $(date)"
