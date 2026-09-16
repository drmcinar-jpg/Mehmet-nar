# -*- coding: utf-8 -*-
"""ayarlar.json dosyasini okur; yoksa varsayilanlarla olusturur."""

import json
import os

VARSAYILAN = {
    "_aciklama": "Yayin Okuma ayarlari. Degistirdikten sonra programi yeniden calistirin.",

    "eposta": "",
    "ncbi_api_key": "",
    "_ncbi_not": (
        "NCBI API anahtari sart degil ama hizi 3 istek/sn'den 10 istek/sn'ye cikarir. "
        "Ucretsiz: https://account.ncbi.nlm.nih.gov/settings/ -> API Key Management"
    ),

    "gecmis_gun": 92,
    "_gecmis_gun_not": "Kac gunluk yayin cekilsin (son 3 ay icin 92). Rapordaki sekmeler bu pencereden suzulur.",

    "dergi_basina_azami": 400,
    "_dergi_basina_azami_not": "Bir dergiden tek seferde cekilecek azami makale sayisi.",

    "yapay_zeka_ozet": True,
    "anthropic_api_key": "",
    "_anthropic_not": (
        "Turkce ozet icin Anthropic API anahtari. Bos birakilirsa ANTHROPIC_API_KEY "
        "ortam degiskenine bakilir; o da yoksa ozetler makalenin kendi Sonuc bolumunden "
        "cikarilir (internet/ucret gerekmez)."
    ),
    "model": "claude-sonnet-5",
    "calistirma_basina_azami_ozet": 80,
    "_ozet_limit_not": "Beklenmedik maliyeti onlemek icin tek calistirmada uretilecek azami yapay zeka ozeti. Ozetler onbellege alinir, ayni makale iki kez ozetlenmez.",

    "tarih_turu": "edat",
    "_tarih_turu_not": "edat = PubMed'e giris tarihi (yeni cikanlari takip icin dogrusu). pdat = yayin tarihi.",

    "yeni_rozeti_saat": 24,
    "_yeni_rozeti_not": "Son kac saat icinde ilk kez gorulen makaleler YENI rozeti alsin.",

    "raporu_otomatik_ac": True,
}


def _yol(kok):
    return os.path.join(kok, "ayarlar.json")


def yukle(kok):
    """Ayarlari okur. Dosya yoksa varsayilanlarla olusturur.
    Yeni surumde eklenen anahtarlar mevcut dosyaya sessizce tamamlanir."""
    yol = _yol(kok)
    if not os.path.exists(yol):
        kaydet(kok, VARSAYILAN)
        return dict(VARSAYILAN)

    with open(yol, "r", encoding="utf-8") as f:
        kullanici = json.load(f)

    ayar = dict(VARSAYILAN)
    ayar.update(kullanici)

    # Program guncellenince eklenen anahtarlari dosyaya da yaz
    if set(ayar) != set(kullanici):
        kaydet(kok, ayar)
    return ayar


def kaydet(kok, ayar):
    with open(_yol(kok), "w", encoding="utf-8") as f:
        json.dump(ayar, f, ensure_ascii=False, indent=2)


def anthropic_anahtari(ayar):
    return (ayar.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY") or "").strip()


def ncbi_anahtari(ayar):
    return (ayar.get("ncbi_api_key") or os.environ.get("NCBI_API_KEY") or "").strip()
