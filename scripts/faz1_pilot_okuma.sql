-- v2.577 (Faz 1 F1-F1) — CANLI PİLOT İÇİN SALT OKUNUR TOPLU SAYIMLAR. Müşteri kimliği, e-posta, ad yazdırmaz; yalnız santral kimliği ve sayılar.
-- Koşum (sunucuda, salt okunur):  docker compose exec -T db psql -U pvquant -d pvquant -At -F' | ' -f /opt/pvquant/scripts/faz1_pilot_okuma.sql
-- Çıktı Faz 1 kanıt klasörüne (kanit/F1-F1_canli_sayim.txt) yapıştırılır; motor (gece_bagimsiz_dogrulama) dağıtımdan sonra 30 günlük sonucu kendisi üretir.
\echo '== santral başına tahmin koşusu (son 90 gün): sayı, ilk/son, etiket dağılımı'
SELECT plant_id, count(*) AS kosu, min(run_at)::date AS ilk, max(run_at)::date AS son,
       count(*) FILTER (WHERE COALESCE(etiket, meteo_ozet_json->>'etiket') = 'gun_ici') AS gun_ici,
       count(*) FILTER (WHERE model = 'backtest' OR meteo_source IN ('open-meteo-arsiv', 'sentetik_tohum')) AS geriye_bakisli
FROM forecast_runs WHERE run_at >= now() - interval '90 days' GROUP BY 1 ORDER BY 2 DESC;
\echo '== santral başına geçerli ölçüm saati (son 90 gün) ve bayrak dağılımı'
SELECT plant_id, count(*) FILTER (WHERE flag = 'valid') AS valid, count(*) FILTER (WHERE flag <> 'valid') AS bayrakli,
       min(ts_utc)::date AS ilk, max(ts_utc)::date AS son, count(*) FILTER (WHERE kapsama_dk IS NOT NULL) AS kapsamali
FROM scada_hourly WHERE ts_utc >= now() - interval '90 days' GROUP BY 1 ORDER BY 2 DESC;
\echo '== bayrak dağılımı (son 90 gün, tüm santraller)'
SELECT flag, count(*) FROM scada_hourly WHERE ts_utc >= now() - interval '90 days' GROUP BY 1 ORDER BY 2 DESC;
\echo '== olay kaydı (son 90 gün): tür başına sayı ve saat'
SELECT plant_id, tur, count(*) AS olay, round(sum(EXTRACT(EPOCH FROM (COALESCE(bitis, now()) - baslangic)) / 3600)::numeric, 1) AS saat
FROM olay WHERE durum <> 'iptal' AND baslangic >= now() - interval '90 days' GROUP BY 1, 2 ORDER BY 1, 2;
\echo '== karne satırları (son 30 gün) kova başına'
SELECT horizon_bucket, count(*) FROM skill_daily WHERE date >= current_date - 30 GROUP BY 1 ORDER BY 1;
\echo '== bağımsız doğrulama kayıtları (dağıtımdan sonra dolar)'
SELECT plant_id, kural, donem_bas, donem_bit, hesap_zamani, metrik_json->>'n_saat' AS n_saat, metrik_json->>'wmape' AS wmape FROM dogrulama_sonuc ORDER BY hesap_zamani DESC LIMIT 20;
\echo '== santral saat dilimi ve kapasite (kimlik yok)'
SELECT id AS plant_id, tz, capacity_kwp, ac_limit_kw, archived FROM plants ORDER BY capacity_kwp DESC;
