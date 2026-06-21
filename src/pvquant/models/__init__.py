"""Saf matematiksel modeller.

Bu modüldeki tüm fonksiyonlar:
- Yan etkisizdir (pure functions)
- numpy/pandas Series alır ve döner (vektörize)
- Birimleri docstring'de açık şekilde belirtir
- Orijinal akademik kaynaklara atıf yapar

Modeller modüllere göre gruplanmıştır:
- `irradiance`: GHI/DHI/DNI ayrıştırma ve POA transposition (Erbs, Perez)
- `temperature`: Hücre sıcaklığı (NOCT, Faiman, SAPM thermal)
- `power`: DC güç (PVWatts, Skoplaki-Palyvos, Barhdadi-Bennis)
- `bifacial`: Bifacial katkı (basit ve view-factor)
"""
