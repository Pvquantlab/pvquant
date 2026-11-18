"""v2.265 — Dalga 5.17: değişim damgası — 'panelde bir şey değişti mi?' sorusuna tek ucuz yanıt.

Kaynak DB (süreç içi bellek değil: API çok kopyalı olabilir, worker ayrı süreçtir). Beş + dört zaman damgası okunur (26.10: piyasa, iş kaydı, meteo, santral özü);
ETag = sha256(bunlar)[:16]. İstemci 60 s (görünür) / 5 dk (arka plan) yoklar, yalnız ETag değişince veri çeker.
Telemetri şeridindeki 'tazelendi' iddiası ANCAK bu yoklama gerçekten çalışırken yazılır (dürüstlük ilkesi).
"""
from __future__ import annotations

import hashlib
import json
import threading
import time


def etag_uret(damga: dict) -> str:
    return 'W/"' + hashlib.sha256(json.dumps(damga, sort_keys=True, default=str).encode()).hexdigest()[:16] + '"'


def hesapla(tenant_id, plant_id) -> dict:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text(
            "SELECT (SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p) AS son_scada,"
            " (SELECT max(run_at) FROM forecast_runs r WHERE plant_id=:p AND EXISTS (SELECT 1 FROM forecast_values v WHERE v.run_id=r.id)) AS son_kosu,"
            " (SELECT max(created_at) FROM alerts WHERE plant_id=:p) AS son_alarm,"
            " (SELECT count(*) FROM alerts WHERE plant_id=:p AND acked_by IS NULL AND created_at >= now() - interval '7 days') AS acik_alarm,"
            " (SELECT max(date) FROM skill_daily WHERE plant_id=:p) AS son_skill,"
            " (SELECT max(created_at) FROM calibrations WHERE plant_id=:p) AS son_kalibrasyon,"
            # 16.11 gezinme hizi (piyasa/finans): dosya yuklemeleri de damgada - sunucu yanit onbellegi (yanit_onbellegi) bu damgayla
            # anahtarli; EPIAS bildirimi / saatlik detay / sayac dosyasi / KGUP surumu yuklenince mutabakat-finans yanitlari tazelenir
            " (SELECT max(olusturma) FROM uzlastirma_bildirimi WHERE plant_id=:p) AS son_mutabakat_yukleme,"
            " (SELECT max(olusturma) FROM uzlastirma_saatlik WHERE plant_id=:p) AS son_saatlik_yukleme,"
            " (SELECT max(olusturma) FROM sayac_yukleme WHERE plant_id=:p) AS son_sayac_yukleme,"
            " (SELECT max(olusturma) FROM kgup_surum WHERE plant_id=:p) AS son_kgup_surum"),
            {"p": plant_id}).mappings().first()
    d = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dict(r).items()}
    d["acik_alarm"] = int(d.get("acik_alarm") or 0)
    d.update(_ortak_damga(tenant_id, plant_id))
    return d


def _ortak_damga(tenant_id, plant_id) -> dict:
    """26.10 eşzamanlama — damga artık şunları da kapsar (müşteri paneli bunlar değişince de tazelenir):
    son_piyasa: PTF/SMF güncellemesi (piyasa_fiyat.guncelleme; gece_piyasa işi), son_is: kiracının ya da küresel son iş kaydı
    (jobs_log.started; gece işlemleri kartı), son_meteo: santral noktasına en yakın meteo arşivi koşusu (gece_meteo işi),
    santral_ozu: santral parametreleri satırının özeti (kapasite, konum, params_json; Santral ayarları kaydedilince değişir).
    Küresel tablolar sistem bağlamından okunur (RLS dışı, kiracı süzgeci sorguda)."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        d = _kiraci_damga(s, tenant_id)
        d["santral_ozu"] = s.execute(text("SELECT md5(CAST(row_to_json(p) AS text)) FROM plants p WHERE p.id = CAST(:p AS uuid) AND p.tenant_id = CAST(:t AS uuid)"),
                                     {"t": str(tenant_id), "p": str(plant_id)}).scalar()
        d["son_meteo"] = _son_meteo(s, str(plant_id))
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in d.items()}


def _kiraci_damga(s, tenant_id) -> dict:
    """Kiraciya ait, santraldan bagimsiz damga parcalari (sistem baglami): son_piyasa (PTF/SMF guncellemesi), son_is (kiracinin ya da
    kuresel son is kaydi). 18.11 DSG/portfoy hiz turu: santral damgasi ve portfoy damgasi ortak kullanir."""
    from sqlalchemy import text
    r = s.execute(text(
        "SELECT (SELECT max(guncelleme) FROM piyasa_fiyat) AS son_piyasa,"
        " (SELECT max(started) FROM jobs_log WHERE tenant_id = CAST(:t AS uuid) OR tenant_id IS NULL) AS son_is"),
        {"t": str(tenant_id)}).mappings().first()
    return dict(r)


def kiraci_hesapla(tenant_id) -> dict:
    """18.11 gezinme (Parti B #3) — KIRACI damgasi: yanit_onbellegi.getir_kiraci kiracinin TUM santrallerini kapsayan uclari (/v1/portfoy,
    portfoy/tahmin, portfoy/dsg, portfoy/kupst, portfoy/finansal-etki — canlida sarmalsizdi: finansal-etki 18–23 s, dsg 1,7 s) bununla
    anahtarlar. Kapsam: arsivlenmemis santrallerin olcumu/kosusu/yuklemeleri (scada, forecast_runs, kgup_surum, uzlastirma, sayac), acik alarm
    ozu (/v1/portfoy acik alarm sayar: 7 gun, okunmamis), santral satirlarinin ozeti (arsivleme/ayar degisince) ve kiraci parcalari (piyasa, is).
    Kiraci baglaminda (RLS) ve ayrica santral suzgeciyle (alerts yalniz kiracinin arsivlenmemis santrallari)."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami, tenant_baglami
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text(
            "WITH u AS (SELECT id AS plant_id FROM plants WHERE NOT archived)"
            " SELECT (SELECT max(ts_utc) FROM scada_hourly h WHERE h.plant_id IN (SELECT plant_id FROM u)) AS son_scada,"
            " (SELECT max(run_at) FROM forecast_runs r WHERE r.plant_id IN (SELECT plant_id FROM u) AND EXISTS (SELECT 1 FROM forecast_values v WHERE v.run_id = r.id)) AS son_kosu,"
            " (SELECT max(olusturma) FROM kgup_surum k WHERE k.plant_id IN (SELECT plant_id FROM u)) AS son_kgup_surum,"
            " (SELECT max(olusturma) FROM uzlastirma_bildirimi m WHERE m.plant_id IN (SELECT plant_id FROM u)) AS son_mutabakat_yukleme,"
            " (SELECT max(olusturma) FROM sayac_yukleme y WHERE y.plant_id IN (SELECT plant_id FROM u)) AS son_sayac_yukleme,"
            " (SELECT count(*) || ':' || COALESCE(CAST(max(created_at) AS text), '') FROM alerts a WHERE a.plant_id IN (SELECT plant_id FROM u) AND a.created_at >= now() - interval '7 days' AND a.acked_by IS NULL) AS alarm_ozu,"
            " (SELECT md5(string_agg(md5(CAST(row_to_json(p) AS text)), ',' ORDER BY p.id)) FROM plants p) AS santral_ozu")).mappings().first()
        d = dict(r)
    with sistem_baglami() as s:
        d.update(_kiraci_damga(s, tenant_id))
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in d.items()}


def portfoy_hesapla(tenant_id, portfoy_id) -> dict:
    """18.11 DSG/portfoy hiz turu — PORTFOY damgasi: yanit onbellegi (yanit_onbellegi.getir_portfoy) portfoy uclarini bununla anahtarlar.
    Kapsam: uyelerin olcumu/kosusu/yuklemeleri (scada, forecast_runs, kgup_surum, uzlastirma, sayac), portfoy/uyelik/sozlesme kayitlarinin
    guncellemesi, gece isinin portfoy sonucu (portfoy_sonuc.hesap_zamani), uye santral satirlarinin ozeti ve kiraci parcalari (piyasa, is).
    Uyelik gecmisi (gecerli_bit dolmus uyeler dahil) kapsamda: donem gorunumleri gecmis uyelikle hesaplanir. Kiraci baglaminda (RLS)."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami, tenant_baglami
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text(
            "WITH u AS (SELECT DISTINCT plant_id FROM portfoy_uyelik WHERE portfoy_id = CAST(:pf AS uuid))"
            " SELECT (SELECT max(ts_utc) FROM scada_hourly h WHERE h.plant_id IN (SELECT plant_id FROM u)) AS son_scada,"
            " (SELECT max(run_at) FROM forecast_runs r WHERE r.plant_id IN (SELECT plant_id FROM u) AND EXISTS (SELECT 1 FROM forecast_values v WHERE v.run_id = r.id)) AS son_kosu,"
            " (SELECT max(olusturma) FROM kgup_surum k WHERE k.plant_id IN (SELECT plant_id FROM u)) AS son_kgup_surum,"
            " (SELECT max(olusturma) FROM uzlastirma_bildirimi m WHERE m.plant_id IN (SELECT plant_id FROM u)) AS son_mutabakat_yukleme,"
            " (SELECT max(olusturma) FROM sayac_yukleme y WHERE y.plant_id IN (SELECT plant_id FROM u)) AS son_sayac_yukleme,"
            " (SELECT max(GREATEST(created_at, updated_at)) FROM portfoy WHERE id = CAST(:pf AS uuid)) AS portfoy_guncelleme,"
            " (SELECT max(GREATEST(created_at, updated_at)) FROM portfoy_uyelik WHERE portfoy_id = CAST(:pf AS uuid)) AS uyelik_guncelleme,"
            " (SELECT max(GREATEST(created_at, updated_at)) FROM ticari_sozlesme WHERE portfoy_id = CAST(:pf AS uuid)) AS sozlesme_guncelleme,"
            " (SELECT max(hesap_zamani) FROM portfoy_sonuc WHERE portfoy_id = CAST(:pf AS uuid)) AS son_portfoy_sonuc,"
            " (SELECT md5(string_agg(md5(CAST(row_to_json(p) AS text)), ',' ORDER BY p.id)) FROM plants p WHERE p.id IN (SELECT plant_id FROM u)) AS santral_ozu"),
            {"pf": str(portfoy_id)}).mappings().first()
        d = dict(r)
    with sistem_baglami() as s:
        d.update(_kiraci_damga(s, tenant_id))
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in d.items()}


_METEO_SN = 30.0    # 17.11 inceleme: surec ici hatirlama iscilerarasi etag farki yaratir (4 isci); pencere 30 s <= istemci yoklamasi 60 s
_METEO: dict[str, tuple[float, object]] = {}
_METEO_KILIT = threading.Lock()


def _son_meteo(s, plant_id: str):
    """Santral noktasına en yakın meteo arşivi koşusu — 17.11 Genel bakış hız turu: iki düzeltme.
    (1) `abs(m.lat - p.lat) < 0.05` yüklemi meteo_arsiv_nokta_ts (lat, lon, ts_utc) dizinini kullanamıyordu (1,45 M satır, sıralı
        tarama) → BETWEEN aralık yüklemi (ÖLÇÜLDÜ canlı EXPLAIN: 152 → 97 ms; nokta 52 bin satır).
    (2) Arşiv yalnız gece işiyle değişir; 30 s süreç içi hatırlama ile damga çoğu yoklamada 97 ms yerine ~0 ms öder. İşçiler arası
        etag farkı en çok 30 s sürer (istemci 60 s'de bir yoklar: en çok bir fazladan tazeleme); tahmin koşusu zaten ayrıca damgada."""
    simdi = time.monotonic()
    with _METEO_KILIT:
        v = _METEO.get(plant_id)
        if v and simdi - v[0] < _METEO_SN:
            return v[1]
    from sqlalchemy import text
    deger = s.execute(text(
        "SELECT max(m.kosu_zamani) FROM meteo_arsiv m, plants p WHERE p.id = CAST(:p AS uuid)"
        "  AND m.lat BETWEEN p.lat - 0.05 AND p.lat + 0.05 AND m.lon BETWEEN p.lon - 0.05 AND p.lon + 0.05"), {"p": plant_id}).scalar()
    with _METEO_KILIT:
        _METEO[plant_id] = (simdi, deger)
    return deger
