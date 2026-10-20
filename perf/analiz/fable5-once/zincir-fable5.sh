#!/bin/bash
# zincir-fable5.sh — 20.10 Fable 5 turu: başlangıç ölçümünün kalanı + «sonra» derlemesi ve ikinci kontrol. Sıralı (işlemci paylaşılmaz).
set -u
cd "$(dirname "$0")/../.."     # perf/
K=analiz/fable5-once; S=analiz/fable5-sonra; mkdir -p "$S"
adim() { echo "$(date '+%H:%M:%S') $1 çıkış $2" >> $K/zincir.log; }
while pgrep -f "^node olc/etkilesim" > /dev/null; do sleep 15; done; adim "etkilesim bekleme" 0
mv $K/lighthouse/lh-fable5-once.jsonl $K/lighthouse/lh-fable5-once-KIRLI.jsonl 2>/dev/null
node olc/lh.mjs --hedef fable5-once --cikti $K --kosu 3 > $K/lh-temiz.log 2>&1; adim "lighthouse temiz" $?
node olc/iz/yazilim-ff2.mjs --hedef fable5-once > $K/yazilim-ff.txt 2>&1; adim "firefox yazılım webgl 1440" $?
node olc/iz/yazilim-ff2.mjs --hedef fable5-once --gorunum 390x844 >> $K/yazilim-ff.txt 2>&1; adim "firefox yazılım webgl 390" $?
node olc/cerez-sina.mjs --hedef fable5-once > $K/cerez-sina.txt 2>&1; adim "çerez sınaması" $?
node olc/lh.mjs --hedef canli --cikti $K --kosu 2 > $K/lh-canli.log 2>&1; adim "lighthouse canlı" $?
# «sonra»: çalışma ağacının HEAD'i (Caddy sabitleme + bağımlılık temizliği; dist bayt bayt aynı olmalı)
bash replika/derle.sh fable5-sonra HEAD > $S/derle.log 2>&1; adim "derle sonra" $?
( cd .replika/fable5-once/dist && find . -type f | sort | xargs sha256sum ) > $S/once-sha.txt
( cd .replika/fable5-sonra/dist && find . -type f | sort | xargs sha256sum ) > $S/sonra-sha.txt
diff $S/once-sha.txt $S/sonra-sha.txt > $S/dist-fark.txt; adim "dist kıyas (0 = bayt bayt aynı)" $?
bash replika/baslat.sh fable5-sonra 28 > $S/baslat.log 2>&1; adim "baslat sonra" $?
node olc/matris.mjs --hedef fable5-sonra --cikti $S --motor chromium,firefox,webkit,edge --gorunum 390x844,1440x900 --ag yok,hizli3g,yavas4g,kablo20 --kosu 3 > $S/matris.log 2>&1; adim "matris sonra (390/1440, 4 hat)" $?
node olc/lh.mjs --hedef fable5-sonra --cikti $S --kosu 3 > $S/lh.log 2>&1; adim "lighthouse sonra" $?
node olc/ozet.mjs $K > $K/ozet.log 2>&1; adim "özet once" $?
node olc/ozet.mjs $S > $S/ozet.log 2>&1; adim "özet sonra" $?
echo "$(date '+%H:%M:%S') BİTTİ" >> $K/zincir.log
