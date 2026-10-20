#!/bin/bash
# zincir2 — kontrol matrisinin kaldığı yerden sürmesi (WebKit sayfa çökmesi, hücre 113), özet, teşhis A/B.
set -u; cd "$(dirname "$0")/../.."
K=analiz/fable5-once; S=analiz/fable5-sonra
adim() { echo "$(date '+%H:%M:%S') $1 çıkış $2" >> $K/zincir.log; }
while ! grep -q "BİTTİ" $K/zincir.log; do sleep 15; done
for deneme in 1 2 3; do node olc/matris.mjs --hedef fable5-sonra --cikti $S --motor chromium,firefox,webkit,edge --gorunum 390x844,1440x900 --ag yok,hizli3g,yavas4g,kablo20 --kosu 3 >> $S/matris.log 2>&1; r=$?; adim "matris sonra devam $deneme" $r; [ $r -eq 0 ] && break; done
node olc/ozet.mjs $S > $S/ozet.log 2>&1; adim "özet sonra 2" $?
node olc/ab-boya.mjs --surucu pw-chromium,pw-webkit --gorunum 1440x900,390x844 --degisken mevcut,filtresiz,camsiz,filtresiz+camsiz,video-durgun --kosu 2 --hedef fable5-once --cikti $K/ab > $K/ab.log 2>&1; adim "ab teşhis" $?
echo "$(date '+%H:%M:%S') BİTTİ2" >> $K/zincir.log
