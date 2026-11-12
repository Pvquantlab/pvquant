"""SCADA yukleme servisi: mevcut ingestion ciktisi -> kalici tablolar."""
from __future__ import annotations
import json
import pandas as pd
from sqlalchemy import text
from pvquant.db import tenant_baglami
from pvquant.services import kalite_sozlugu as _ks   # v2.598 (F4-C): flag süzgeci tek sözlükten
from pvquant.io.ingestion.pipeline import ingest_file

_KOLONLAR = {"power_kw":"power_kw","energy_kwh":"energy_kwh",
             "poa_global":"poa_wm2","t_air":"t_air",
             "t_module":"t_module","wind_speed":"wind_ms"}


def yukle_ve_kaydet(tenant_id, plant_id, dosya_yolu, *, capacity_kwp,
                    latitude, longitude, source_timezone,
                    file_format=None, mapping=None,
                    hazir_sonuc=None) -> dict:
    """hazir_sonuc verilirse ingest_file ATLANIR; Faz 1'de uretilip
    kullanicinin onayladigi sonuc aynen kalicilastirilir. None ise
    eski atomik davranis (yukle+kaydet) aynen gecerli."""
    res = hazir_sonuc if hazir_sonuc is not None else ingest_file(
        str(dosya_yolu), capacity_kwp=capacity_kwp,
        latitude=latitude, longitude=longitude,
        source_timezone=source_timezone,
        file_format=file_format, mapping=mapping)
    clean = res.data if hasattr(res, "data") else res.to_clean_frame()
    df = clean.set_index("timestamp") if "timestamp" in clean.columns else clean
    with tenant_baglami(tenant_id) as s:
        batch_id = s.execute(text(
            "INSERT INTO ingestion_batches(tenant_id,plant_id,filename,"
            " format_json,mapping_json,transform_json,quality_json) "
            "VALUES (:t,:p,:f,:fmt,:map,:tr,:q) RETURNING id"),
            {"t": tenant_id, "p": plant_id, "f": str(dosya_yolu),
             "fmt": _kaynakli(_j(res, "file_format")), "map": _j(res, "mapping"),
             "tr": _j(res, "transform"), "q": _j(res, "report")}).scalar()
        satirlar = []
        _tr = res.transform if hasattr(res, "transform") else None
        _aralik = getattr(_tr, "source_timestep_minutes", None)   # v2.598: kaynak adımı künyeye
        _damga = getattr(_tr, "kaynak_damga_tipi", None) or "aralik_basi"   # v2.599 (F4-D): kaynağın damga konvansiyonu (çıktı daima aralık başı)
        for ts, row in df.iterrows():
            kayit = {"t": tenant_id, "p": plant_id, "ts": ts,
                     "flag": row.get("flag", "valid"), "b": batch_id,
                     "aralik": (int(_aralik) if _aralik else None), "damga": _damga}
            for src, hedef in _KOLONLAR.items():
                v = row.get(src)
                kayit[hedef] = None if pd.isna(v) else float(v)
            k = row.get("kapsama_dk")   # v2.573 (Faz 1 F1-B): saat başına ölçüm kapsaması; yoksa NULL = bilinmiyor
            kayit["kapsama_dk"] = None if k is None or pd.isna(k) else int(round(float(k)))
            satirlar.append(kayit)
        # v2.598 (Faz 4 F4-C): SCADA dosyası birincil kaynaktır (EPİAŞ/canlı satırının üstüne yazar) ama hijyenin koyduğu 'kisinti'
        # bayrağı ve kirpma işareti yeni 'valid' satırla silinmez (bir sonraki hijyen koşusu yeniden değerlendirir); künye sütunları
        # kaynak/alinma_zamani/aralik_dk dolar.
        s.execute(text(
            "INSERT INTO scada_hourly(tenant_id,plant_id,ts_utc,power_kw,"
            " energy_kwh,poa_wm2,t_air,t_module,wind_ms,flag,batch_id,kapsama_dk,kaynak,alinma_zamani,aralik_dk,kaynak_damga_tipi) "
            "VALUES (:t,:p,:ts,:power_kw,:energy_kwh,:poa_wm2,:t_air,"
            " :t_module,:wind_ms,:flag,:b,:kapsama_dk,'scada_dosya',now(),:aralik,:damga) "
            "ON CONFLICT (plant_id, ts_utc) DO UPDATE SET "
            " power_kw=EXCLUDED.power_kw, energy_kwh=EXCLUDED.energy_kwh,"
            " poa_wm2=EXCLUDED.poa_wm2, t_air=EXCLUDED.t_air,"
            " t_module=EXCLUDED.t_module, wind_ms=EXCLUDED.wind_ms,"
            " flag=(CASE WHEN scada_hourly.flag='kisinti' AND EXCLUDED.flag='valid' THEN 'kisinti' ELSE EXCLUDED.flag END),"
            " batch_id=EXCLUDED.batch_id, kapsama_dk=EXCLUDED.kapsama_dk,"
            " kaynak='scada_dosya', alinma_zamani=now(), aralik_dk=EXCLUDED.aralik_dk, kaynak_damga_tipi=EXCLUDED.kaynak_damga_tipi"), satirlar)
    return {"batch_id": str(batch_id), "n_satir": len(satirlar)}


def _kaynakli(fmt):
    """Faz 0 (10.11.2026): dosya yüklemesi format_json'a açık kaynak etiketi yazar; önceden yalnız yokluğundan (COALESCE) çıkarılıyordu.
    v2.598 (F4-C, bulgu M7): `_j` JSON METNİ döndürür; eski `dict(fmt)` metinde ValueError, None'da sözlük (psycopg adapte edemez) veriyordu —
    yükleme kaydı 500 düşüyordu. Girdi metin/sözlük/None olabilir; çıktı her zaman JSON metni."""
    if isinstance(fmt, str):
        try:
            d = json.loads(fmt)
        except ValueError:
            d = {}
    else:
        d = dict(fmt or {})
    if not isinstance(d, dict):
        d = {}
    d.setdefault("kaynak", "scada_dosya")
    return json.dumps(d, default=str, ensure_ascii=False)


def _j(res, alan):
    o = getattr(res, alan, None)
    if o is None: return None
    d = o.to_dict() if hasattr(o, "to_dict") else (
        o.model_dump() if hasattr(o, "model_dump") else None)
    return json.dumps(d, default=str, ensure_ascii=False) if d else None


def scada_oku(tenant_id, plant_id, *, gunluk_dahil: bool = False) -> pd.DataFrame:
    """Kalibrasyonun kullanacagi temiz okuma: valid satirlar, UTC index.
    v2.367: gunluk_dahil=True aylik/enerji toplamlari icindir — 'gunluk_ozet'
    bayrakli satirlar (gunluk ozet dosyalari) da okunur; kalibrasyon ve saatlik
    isler varsayilanda onlari GORMEZ."""
    kosul = ("flag IN ('valid','gunluk_ozet')" if gunluk_dahil
             else f"{_ks.sql_kosulu('tazelik')}")
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(
            "SELECT ts_utc, power_kw, energy_kwh, poa_wm2, t_air,"
            " t_module, wind_ms, kirpma FROM scada_hourly "
            "WHERE plant_id=:p AND " + kosul + " ORDER BY ts_utc"),
            s.connection(), params={"p": plant_id},
            index_col="ts_utc", parse_dates=["ts_utc"])
    return df


def aylik_ozet(df: pd.DataFrame, tz: str | None = None) -> pd.DataFrame:
    """Issue #1 (v2.68): valid saatlik SCADA'dan aylik uretim ozeti.
    Saf fonksiyon — DB'siz test edilir. Girdi: scada_oku ciktisi (UTC index).
    tz verilirse ay siniri o saat diliminin takvimiyle cizilir (durust ay:
    31 Mart 21:00 UTC, Istanbul'da 1 Nisan'dir). tz=None -> UTC takvimi.
    Cikti kolonlari: ay (YYYY-MM), uretim_mwh, saat, kapsam_pct.
    kWh kaynagi: energy_kwh; bos satirda power_kw (saatlik seri: kW x 1h = kWh).
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["ay", "uretim_mwh", "saat", "kapsam_pct"])
    kwh = df["energy_kwh"].fillna(df["power_kw"])
    idx = df.index.tz_convert(tz) if tz else df.index
    g = kwh.groupby(idx.tz_localize(None).to_period("M"))
    out = pd.DataFrame({
        "uretim_mwh": (g.sum() / 1000.0).round(2),
        "saat": g.count().astype(int),
    })
    ay_saat = out.index.to_timestamp().days_in_month * 24
    out["kapsam_pct"] = (out["saat"] / ay_saat * 100).round(1)
    # v2.316: gozlenen ILK->SON ay arasindaki IC bosluklar satir olarak dogar —
    # verisi olmayan takvim ayi eksenden sessizce dusuyordu (canlida Mayis 2026:
    # 13 aylik aralik 12 cubukla ciziliyordu). uretim_mwh NaN kalir (API katmani
    # _kw ile null basar: durust yokluk, 0 uydurulmaz), saat 0, kapsam 0.
    # BASTAKI aylar uretilmez: 3 aylik verisi olan santral 9 bos yuva gormesin.
    out = out.reindex(pd.period_range(out.index.min(), out.index.max(), freq="M"))
    out["saat"] = out["saat"].fillna(0).astype(int)
    out["kapsam_pct"] = out["kapsam_pct"].fillna(0.0)
    out.insert(0, "ay", out.index.astype(str))
    return out.reset_index(drop=True)


def aylik_uretim(tenant_id, plant_id) -> pd.DataFrame:
    """Ince DB sarmalayici: scada_oku -> aylik_ozet, santralin tz'siyle (v2.68)."""
    with tenant_baglami(tenant_id) as s:
        tz = s.execute(text("SELECT tz FROM plants WHERE id=:p"),
                       {"p": plant_id}).scalar()
    return aylik_ozet(scada_oku(tenant_id, plant_id, gunluk_dahil=True), tz=tz)   # v2.367


def veri_ozeti(tenant_id, plant_id) -> dict:
    """Hafif varlık kontrolü: tüm satırları ÇEKMEDEN sayım + son damga.
    (scada_oku 15 bin satırı yükler; boş-durum kontrolü için israftır.)"""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text(
            f"SELECT count(*) FILTER (WHERE {_ks.sql_kosulu('tazelik')}) AS valid_saat,"
            " max(ts_utc) AS son_ts FROM scada_hourly WHERE plant_id=:p"),
            {"p": plant_id}).first()
    return {"valid_saat": int(r.valid_saat or 0), "son_ts": r.son_ts}


# ---------------- v2.298: "Veriniz sizindir" — dışa aktarma ve silme ----------------
DISA_KOLONLAR = ("ts_utc", "power_kw", "energy_kwh", "poa_wm2", "t_air", "t_module", "wind_ms", "flag", "kirpma")


def scada_disa_csv(tenant_id, plant_id, baslangic=None, bitis=None) -> str:
    """Müşterinin YÜKLEDİĞİ ham serinin tamamı, yorumsuz CSV (UTC damga; bayrak ve kırpma işaretiyle).
    Giriş ekranındaki söz burada ödenir: dışa aktarım her role açıktır, filtre yalnız tarihtir."""
    from io import StringIO
    from sqlalchemy import text
    import pandas as pd
    from pvquant.db import tenant_baglami
    kosul = "plant_id=:p"
    par: dict = {"p": plant_id}
    if baslangic:
        kosul += " AND ts_utc >= :b"; par["b"] = baslangic
    if bitis:
        kosul += " AND ts_utc < CAST(:e AS timestamptz) + INTERVAL '1 day'"; par["e"] = bitis   # bitiş günü dâhil
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(f"SELECT {', '.join(DISA_KOLONLAR)} FROM scada_hourly WHERE {kosul} ORDER BY ts_utc"),
                         s.connection(), params=par)
    buf = StringIO()
    df.to_csv(buf, index=False, date_format="%Y-%m-%dT%H:%M:%SZ")
    return buf.getvalue()


def scada_sil(tenant_id, plant_id, baslangic: str, bitis: str) -> int:
    """Ham SCADA satırlarını tarih aralığında siler (bitiş günü dâhil); silinen satır sayısını döner.
    Karne arşivi (skill_daily) BİLEREK korunur: geçmiş sonuç değiştirilmez, yenisi eklenir — silme
    ham veriyi kaldırır, geçmiş sınav sonuçlarını yeniden yazmaz. Kalibrasyon bir sonraki koşuda
    kalan veriyle yeniden öğrenir."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    if not baslangic or not bitis:
        raise ValueError("silme için başlangıç ve bitiş günü zorunlu")
    with tenant_baglami(tenant_id) as s:
        n = s.execute(text(
            "DELETE FROM scada_hourly WHERE plant_id=:p AND ts_utc >= :b "
            "AND ts_utc < CAST(:e AS timestamptz) + INTERVAL '1 day'"),
            {"p": plant_id, "b": baslangic, "e": bitis}).rowcount
    return int(n)
