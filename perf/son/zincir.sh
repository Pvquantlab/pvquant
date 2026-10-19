#!/bin/bash
# zincir.sh — son derleme (final2 = 160a22a) için tam doğrulama: matris, Lighthouse, ekran/piksel, etkileşim, Firefox kaydırma A/B, video, özet, kıyas.
set -u
cd "$(dirname "$0")/.."
adim() { echo "$(date '+%H:%M:%S') $1 çıkış $2" >> son/zincir.log; }
node olc/matris.mjs --hedef final2 --cikti son > son/matris.log 2>&1; adim matris $?
node olc/lh.mjs --hedef final2 --cikti son --kosu 3 > son/lh.log 2>&1; adim lighthouse $?
node olc/ekran.mjs --hedef final2 --cikti son > son/ekran.log 2>&1; adim ekran $?
node olc/piksel.mjs baseline son > son/piksel.log 2>&1; adim piksel $?
for g in 390x844 768x1024 1440x900 1920x1080; do node olc/piksel-bolum.mjs --motor webkit --gorunum $g --sonra son --hedef final2 >> son/piksel-bolum.log 2>&1; adim "piksel-bolum $g" $?; done
node olc/etkilesim.mjs --hedef final2 --cikti son > son/etkilesim.log 2>&1; adim etkilesim $?
for k in 1 2 3; do for h in sonra final2; do node olc/ab-boya.mjs --hedef $h --surucu firefox-stok --basli --gorunum 1440x900,390x844 --degisken mevcut --kosu 1 --cikti son/firefox-kaydirma/k$k >> son/ab.log 2>&1; adim "ab $h k$k" $?; done; done
node olc/video-zaman.mjs --hedef final2 --degisken yeni --kosu 2 --gorunum 1440x900 --cikti son > son/video.log 2>&1; adim video $?
node olc/ozet.mjs son > son/ozet.log 2>&1; adim ozet $?
node olc/kiyas.mjs --sonra son --hedef final2 > son/kiyas.log 2>&1; adim kiyas $?
node olc/iz/yazilim-ff2.mjs --hedef final2 > son/yazilim-ff.log 2>&1; adim yazilim-ff $?
echo "$(date '+%H:%M:%S') BİTTİ" >> son/zincir.log
