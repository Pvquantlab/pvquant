# Tur 5 — Frontend Entegrasyonu (3 dosya, kopyala-yapıştır blokları)

Çekirdek patch (`hibrit_ui_cekirdek.patch`) uygulandıktan sonra bu üç
dokunuş yapılır. Frontend dosyaların yerel düzenlemeler içerdiği için
patch yerine ANKRAJ + BLOK veriyorum — çakışma riski sıfır.

---

## 1) frontend/kalibrasyon.py — "Hibritle iyileştir" butonu

Seçilen UX: (b) — fizik önce koşar (mevcut akış AYNEN), sonuç kartının
altında hibrit teklifi çıkar. Kullanıcı önce/sonra farkını GÖRÜR.

`_stage_done` fonksiyonunda, "Bulduklarımız" panelinin çizildiği bloğun
SONUNA şunu ekle:

```python
    # ---------- Tur 5: Hibritle iyileştir ----------
    st.divider()
    if st.session_state.get("hybrid_active"):
        hr = st.session_state.get("hybrid_report", {})
        st.success(
            f"🤖 Hibrit model devrede — holdout MAPE "
            f"%{hr.get('holdout_mape_pct', 0):.1f} "
            f"(fizik %{hr.get('physics_mape_pct', 0):.1f}, "
            f"iyileşme %{hr.get('improvement_pct', 0):.0f})"
        )
    else:
        col_h1, col_h2 = st.columns([2, 3])
        with col_h1:
            hibrit_bas = st.button("🚀 Hibritle iyileştir",
                                   key="btn_hybrid", type="secondary")
        with col_h2:
            st.caption(
                "Fizik + AI rezidüel katmanı. Sistematik sapmaları "
                "öğrenir; holdout sınavında ~%18-40 iyileşme tipik. "
                "Eğitim 30-60 sn sürer."
            )
        if hibrit_bas:
            from pvquant.pipeline.hybrid_ui import (
                run_hybrid_training, session_ozeti,
            )
            with st.spinner("Hibrit model eğitiliyor (LightGBM)..."):
                res = run_hybrid_training(
                    scada=st.session_state.scada_for_calib,     # (*)
                    historical_meteo=st.session_state.historical_meteo,  # (*)
                    plant_ctx=st.session_state.plant_context,
                    plant_name=st.session_state.get(
                        "plant_display_name", "Santral"),
                )
            if res.ok:
                st.session_state.hybrid_model = res.model
                st.session_state.hybrid_report = session_ozeti(res)
                st.session_state.hybrid_active = True
                st.rerun()
            else:
                # Sözleşme: kullanıcıya hata GÖSTERME, fizikte kal.
                # run_hybrid_training zaten logger'a yazdı.
                st.info("Hibrit bu veriyle eğitilemedi; fizik modeliyle "
                        "devam ediliyor.")
```

(*) İKİ ANKRAJ NOTU: `scada_for_calib` ve `historical_meteo` — kendi
kalibrasyon aşamanda SCADAData'yı ve meteo'yu hangi session anahtarında
tutuyorsan ONU kullan (\_stage\_calibrating içinde calibrate_from_scada'ya
geçirdiğin iki nesne). Yoksa: \_stage\_calibrating'de kalibrasyondan hemen
önce iki satır ekle:
```python
    st.session_state.scada_for_calib = scada
    st.session_state.historical_meteo = meteo
```

Yeniden kalibrasyonda bayrak sıfırlama: `_stage_calibrating`'in BAŞINA:
```python
    st.session_state.pop("hybrid_model", None)
    st.session_state.pop("hybrid_report", None)
    st.session_state.hybrid_active = False
```

---

## 2) frontend/raporlar.py — tek satır

`ctx = from_results(...)` satırından HEMEN SONRA:

```python
    from pvquant.reporting import apply_hybrid_session
    ctx = apply_hybrid_session(ctx, st.session_state)
```

Bu kadar. Hibrit aktifse: rozet "Mod C — hibrit"e döner, HOLDOUT MAPE
kutusu canlanır. Hibrit yoksa ctx'e dokunulmaz (testli).

---

## 3) frontend/tahminler.py — hibrit tahmin + belirsizlik bandı

Tahmin üretilen yerde (forecast_7day çağrısının olduğu blok), fizik
sonucu alındıktan SONRA şu dal eklenir:

```python
    # ---------- Tur 5: hibrit varsa saatlik seriyi onunla değiştir ----------
    hibrit = st.session_state.get("hybrid_model")
    if hibrit is not None and st.session_state.get("hybrid_active"):
        from pvquant.pipeline.hybrid_ui import hybrid_forecast_hourly
        h_hib = hybrid_forecast_hourly(hibrit, meteo)   # meteo: aynı MeteoData
        if h_hib is not None:
            # pipeline sonucunun saatlik çerçevesini hibritle değiştir
            fr.hourly = fr.hourly.assign(
                p_ac_kw=h_hib["p50_kw"].reindex(fr.hourly.index).values)
            for k in ("p10_kw", "p90_kw"):
                if k in h_hib.columns:
                    fr.hourly[k] = h_hib[k].reindex(fr.hourly.index).values
            fr.hourly["energy_kwh"] = fr.hourly["p_ac_kw"]
        # h_hib None ise sessizce fizik kalır (adaptör logladı)
```

Grafikte bant (mevcut çizgi grafiğin olduğu yerde, çizgiden ÖNCE):

```python
    if {"p10_kw", "p90_kw"} <= set(df_gorsel.columns):
        ax.fill_between(df_gorsel.index, df_gorsel["p10_kw"],
                        df_gorsel["p90_kw"], alpha=0.22,
                        color="#0F6E56", linewidth=0,
                        label="P10–P90 belirsizlik")
```
(Streamlit'in kendi çizgi grafiğini kullanıyorsan: `st.area_chart` yerine
üç kolonlu `st.line_chart(df[["p10_kw","p_ac_kw","p90_kw"]])` da iş görür;
matplotlib kullanıyorsan üstteki blok.)

---

## Kabul kontrolü (uçtan uca, elle)
1. REFPLANT xlsx → kalibrasyon → "Bulduklarımız" ekranında fizik sonuçları.
2. "🚀 Hibritle iyileştir" → spinner 30-60 sn → yeşil "Hibrit model
   devrede" + önce/sonra MAPE.
3. Raporlar → PDF indir → rozet "Mod C — hibrit" + HOLDOUT MAPE kutusu.
4. Tahminler → bant görünür.
5. Negatif test: hibrit patlarsa (ör. 500 saatten az temiz gündüz) mavi
   bilgi mesajı + fizik akışı bozulmadan devam.
