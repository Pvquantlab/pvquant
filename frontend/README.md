# PVQuant Frontend - Streamlit UI (Faz 2)

Bu klasor, PVQuant kullanici arayuzunun Streamlit tabanli implementasyonunu icerir.
Backend'e (src/pvquant/) yalnizca cagirarak bagli calisir; backend degistirilmez.

## Kaynak belgeler

- docs/design/CLAUDE.md - Faz 2 kod tarafi sozlesmesi
- docs/design/PVQuant_UI_Tasarim_Brief_v2.md - Gorsel/UX anayasasi
- docs/design/PVQuant_Prototip_Final.html - Onaylanmis gorsel prototip

## Calistirmak

    cd ~/Desktop/pvquant
    source .venv/bin/activate
    streamlit run frontend/Ana.py

Ana.py Faz 2 Adim 1'de olusacak.

## Cagrilacak backend fonksiyonlari

CLAUDE.md sozlesmesine gore UI yalnizca su 4 arayuzu cagirir:

- calibrate_from_scada
- forecast_7day
- OpenMeteoClient
- load_csv

## Gizlilik denetimi

Her PR/commit oncesi UI metinlerinde yasak kelime taramasi yapilir.
Detay: docs/design/CLAUDE.md - Gizlilik Anayasasi bolumu.
