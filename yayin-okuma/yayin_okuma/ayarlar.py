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

    "saglayici": "anthropic",
    "_saglayici_not": (
        "Turkce ozeti hangi servis uretsin: 'anthropic' (Claude), 'deepseek' "
        "ya da 'openai-uyumlu' (bu durumda api_ucu ve model'i siz yazarsiniz)."
    ),
    "api_anahtari": "",
    "_api_anahtari_not": (
        "Secilen saglayicinin API anahtari. Bos birakilirsa saglayicinin ortam "
        "degiskenine bakilir (ANTHROPIC_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY); "
        "o da yoksa ozetler makalenin kendi Sonuc bolumunden cikarilir "
        "(internet/ucret gerekmez)."
    ),
    "model": "",
    "_model_not": "Bos birakilirsa saglayicinin varsayilani kullanilir.",
    "api_ucu": "",
    "_api_ucu_not": (
        "Bos birakilirsa saglayicinin varsayilan adresi kullanilir. "
        "'openai-uyumlu' icin ornek: https://api.groq.com/openai/v1/chat/completions"
    ),
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

    # Eski surumden gecis: anthropic_api_key -> api_anahtari
    eski = (kullanici.get("anthropic_api_key") or "").strip()
    if eski and not (ayar.get("api_anahtari") or "").strip():
        ayar["api_anahtari"] = eski
        ayar["saglayici"] = ayar.get("saglayici") or "anthropic"
    ayar.pop("anthropic_api_key", None)
    ayar.pop("_anthropic_not", None)

    # Program guncellenince eklenen anahtarlari dosyaya da yaz
    if set(ayar) != set(kullanici):
        kaydet(kok, ayar)
    return ayar


def kaydet(kok, ayar):
    with open(_yol(kok), "w", encoding="utf-8") as f:
        json.dump(ayar, f, ensure_ascii=False, indent=2)


def ozet_anahtari(ayar, ortam_degiskeni="ANTHROPIC_API_KEY"):
    """Ayarlardaki anahtar; yoksa saglayicinin ortam degiskeni."""
    return (ayar.get("api_anahtari")
            or os.environ.get(ortam_degiskeni) or "").strip()


def ncbi_anahtari(ayar):
    return (ayar.get("ncbi_api_key") or os.environ.get("NCBI_API_KEY") or "").strip()
