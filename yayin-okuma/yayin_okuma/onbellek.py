# -*- coding: utf-8 -*-
"""Cekilen makaleleri ve uretilen ozetleri diskte saklar.

Boylece her sabah sadece YENI makaleler indirilir ve daha once uretilmis
ozetler tekrar uretilmez (hem hizli hem ucuz).
"""

import json
import os
import tempfile
from datetime import date

DOSYA = "makaleler.json"


def _yol(kok):
    return os.path.join(kok, "veri", DOSYA)


def yukle(kok):
    yol = _yol(kok)
    if not os.path.exists(yol):
        return {"makaleler": {}, "son_calistirma": ""}
    try:
        with open(yol, "r", encoding="utf-8") as f:
            veri = json.load(f)
    except (ValueError, OSError):
        # Bozuk onbellek programi durdurmasin; sifirdan baslar
        return {"makaleler": {}, "son_calistirma": ""}
    veri.setdefault("makaleler", {})
    veri.setdefault("son_calistirma", "")
    return veri


def kaydet(kok, veri):
    yol = _yol(kok)
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    # Yarim yazilmis dosya kalmasin diye once gecici dosyaya yaz
    gecici = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=os.path.dirname(yol), delete=False, suffix=".tmp")
    try:
        json.dump(veri, gecici, ensure_ascii=False)
        gecici.close()
        os.replace(gecici.name, yol)
    except BaseException:
        gecici.close()
        if os.path.exists(gecici.name):
            os.remove(gecici.name)
        raise


def eskileri_temizle(veri, gun_siniri):
    """Pencerenin disinda kalan eski kayitlari siler."""
    bugun = date.today()
    kalanlar = {}
    for pmid, m in veri["makaleler"].items():
        iso = m.get("giris_tarihi") or m.get("yayin_tarihi")
        if not iso:
            continue
        try:
            fark = (bugun - date.fromisoformat(iso)).days
        except ValueError:
            continue
        if fark <= gun_siniri:
            kalanlar[pmid] = m
    silinen = len(veri["makaleler"]) - len(kalanlar)
    veri["makaleler"] = kalanlar
    return silinen
