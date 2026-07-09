"""
PVQuant Santralim - Statik Demo Verisi (Faz 2 Adim 2)

Backend'e baglanana kadar (Adim 4-5) Santralim ekrani bu veriyi kullanir.
Prototipteki degerlerle birebir ayni.
"""

# Santral bilgisi
SANTRAL = {
    "id": "konya-ges",
    "adi": "Konya GES",
    "kapasite_mw": 2.5,
    "konum": "Konya, Turkiye",
    "devreye_alma": "2023",
}

# Kalibrasyon durumu
KALIBRASYON = {
    "durum": "kalibre",
    "sapma_pct": 0.00,
    "son_kalibrasyon": "6 Tem",
}

# Bugunun ozeti
BUGUN = {
    "tahmini_uretim_kwh": 13870,
    "yarin_beklenen_kwh": 12560,
    "bu_hafta_toplam_mwh": 89.7,
    "yarin_hava": "parcali bulutlu",
    "yarin_dusus_pct": 9,
    "cuma_dusus_pct": 18,
}

# 3 gunluk hava
HAVA = [
    {"gun": "Bugun",    "icon": "gunes",   "sicaklik": 31, "ghi_kwh_m2": 7.1},
    {"gun": "Persembe", "icon": "bulutlu", "sicaklik": 29, "ghi_kwh_m2": 6.4},
    {"gun": "Cuma",     "icon": "bulut",   "sicaklik": 26, "ghi_kwh_m2": 4.9},
]

# Saatlik uretim (bugun)
SAATLIK_GERCEK = [
    (0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0),
    (6, 50), (7, 180), (8, 420), (9, 780), (10, 1180),
    (11, 1520), (12, 1780), (13, 1920), (14, 1850),
]
SAATLIK_TAHMIN = [
    (14, 1850), (15, 1620), (16, 1280), (17, 850),
    (18, 380), (19, 100), (20, 0), (21, 0), (22, 0), (23, 0),
]

SIMDI_SAAT = 14

# 7 gunluk mini bar (MWh)
GUNLUK_TAHMIN = [
    {"gun": "Car", "mwh": 13.87, "bugun": True},
    {"gun": "Per", "mwh": 12.56, "bugun": False},
    {"gun": "Cum", "mwh": 11.38, "bugun": False},
    {"gun": "Cmt", "mwh": 12.41, "bugun": False},
    {"gun": "Paz", "mwh": 9.82,  "bugun": False},
    {"gun": "Pzt", "mwh": 14.40, "bugun": False},
    {"gun": "Sal", "mwh": 15.23, "bugun": False},
]

# Veri sagligi
VERI_SAGLIGI = {
    "son_scada_yukleme": "6 Tem 2026",
    "islenen_saat": 15538,
    "temizlenen_anomali": 67,
}