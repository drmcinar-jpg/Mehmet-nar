# -*- coding: utf-8 -*-
"""Makale ozetleme.

Iki yol vardir:
  1) Yapay zeka ozeti  - Anthropic API anahtari varsa, Turkce yapilandirilmis ozet.
  2) Cikarimsal ozet   - anahtar yoksa/hata olursa, makalenin kendi Sonuc bolumunden.

Uretilen ozetler onbellege yazilir; ayni makale ikinci kez ozetlenmez.
"""

import json
import re
import ssl
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

API_UCU = "https://api.anthropic.com/v1/messages"
API_SURUMU = "2023-06-01"
ES_ZAMANLI = 4

SISTEM = (
    "Sen üreme tıbbı (IVF, infertilite, kadın doğum, üreme endokrinolojisi) alanında "
    "çalışan bir hekime literatür özeti hazırlayan uzman bir asistansın. Okuyucun konunun "
    "uzmanı bir tüp bebek hekimi; terimleri sadeleştirme, İngilizce teknik terimleri "
    "parantez içinde koru. Abartma, makalede olmayan bir şey ekleme, kesinlik derecesini "
    "makalenin kendi ifadesine sadık kalarak aktar. Yalnızca geçerli JSON döndür."
)

SABLON = """Aşağıdaki makaleyi Türkçe özetle.

Dergi: {dergi}
Başlık: {baslik}
Yayın türü: {turler}
Özet (abstract):
{ozet}

Şu şemada JSON döndür (başka hiçbir şey yazma):
{{
  "tek_cumle": "Makalenin ana bulgusu, tek cümle, en fazla 30 kelime.",
  "bulgular": ["En önemli 2-4 bulgu. Her biri tek cümle. Sayısal sonuçları (OR, RR, %, p, n) varsa yaz."],
  "klinik_anlam": "Bir tüp bebek/kadın doğum pratiğinde bu ne değiştirir? Tek-iki cümle. Pratik karşılığı yoksa 'Şimdilik doğrudan klinik karşılığı yok.' yaz.",
  "yontem": "Çalışma tasarımı ve örneklem, tek cümle (örn: 'Retrospektif kohort, 1.240 ICSI siklusu'). Belirsizse boş bırak.",
  "guven": "yuksek | orta | dusuk  — kanıt düzeyine göre (meta-analiz/RKÇ yüksek; küçük gözlemsel/hayvan/in vitro düşük).",
  "etiketler": ["En fazla 4 kısa konu etiketi, örn: PKOS, over rezervi, PGT-A, endometriozis"]
}}"""


# --------------------------------------------------------------- cikarimsal

# Onceligi yuksek sonuc basliklari. ESHRE dergileri (Hum Reprod, Hum Reprod Update)
# "CONCLUSION" yerine "SUMMARY ANSWER" ve "WIDER IMPLICATIONS OF THE FINDINGS"
# kullanir; Lancet/BMJ ise "INTERPRETATION" der.
_SONUC_BASLIKLARI = (
    "CONCLUS", "INTERPRET", "SUMMARY ANSWER", "WIDER IMPLICATION", "SONUC", "SONUÇ",
)
# Yukaridakiler yoksa bakilacak ikincil basliklar
_YEDEK_BASLIKLAR = ("SUMMARY", "DISCUSSION", "WHAT THIS", "KEY POINT")


def _cumlelere_bol(metin):
    return [c.strip() for c in re.split(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9])", metin) if c.strip()]


def _basliga_gore(bolumler, basliklar):
    """Basliklardan birine uyan TUM bolumleri sirasiyla toplar."""
    secilen = [m for b, m in bolumler
               if any(a in (b or "").upper() for a in basliklar)]
    return " ".join(secilen).strip()


def cikarimsal_ozet(makale, azami=480):
    """API anahtari olmadan calisan yedek ozet: makalenin kendi sonuc bolumu."""
    bolumler = makale.get("ozet_bolumleri") or []

    for basliklar in (_SONUC_BASLIKLARI, _YEDEK_BASLIKLAR):
        metin = _basliga_gore(bolumler, basliklar)
        if metin:
            return _kirp(metin, azami)

    tam = makale.get("ozet_metni") or ""
    if not tam:
        return ""
    cumleler = _cumlelere_bol(tam)
    # Yapilandirilmamis ozetlerde sonuc genelde son cumlelerdedir
    secim = " ".join(cumleler[-3:]) if len(cumleler) > 3 else tam
    return _kirp(secim, azami)


def _kirp(metin, azami):
    metin = re.sub(r"\s+", " ", metin).strip()
    if len(metin) <= azami:
        return metin
    kesik = metin[:azami]
    nokta = kesik.rfind(". ")
    return (kesik[:nokta + 1] if nokta > azami * 0.5 else kesik.rstrip() + "…")


# --------------------------------------------------------------- yapay zeka

class OzetHatasi(Exception):
    pass


def _api_cagir(anahtar, model, istem, zaman_asimi=90):
    govde = json.dumps({
        "model": model,
        "max_tokens": 1000,
        "system": SISTEM,
        "messages": [{"role": "user", "content": istem}],
    }).encode("utf-8")

    istek = urllib.request.Request(API_UCU, data=govde, headers={
        "x-api-key": anahtar,
        "anthropic-version": API_SURUMU,
        "content-type": "application/json",
    })
    with urllib.request.urlopen(istek, timeout=zaman_asimi,
                                context=ssl.create_default_context()) as y:
        cevap = json.loads(y.read().decode("utf-8"))

    parcalar = [p.get("text", "") for p in cevap.get("content", []) if p.get("type") == "text"]
    return "".join(parcalar).strip()


def _json_ayikla(metin):
    metin = re.sub(r"^```(?:json)?|```$", "", metin.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(metin)
    except ValueError:
        pass
    bas, son = metin.find("{"), metin.rfind("}")
    if bas != -1 and son > bas:
        return json.loads(metin[bas:son + 1])
    raise OzetHatasi("Model geçerli JSON döndürmedi.")


# Tekrar denemenin ise yaramayacagi hatalar: sebebini kullaniciya soyle
_KALICI_HATALAR = {
    400: "istek reddedildi (model adı yanlış olabilir — ayarlar.json → model)",
    401: "API anahtarı geçersiz (ayarlar.json → anthropic_api_key)",
    403: "API anahtarının bu modele erişim izni yok",
    404: "model bulunamadı (ayarlar.json → model)",
    413: "makale özeti çok uzun",
}
_GECICI_HATALAR = {
    429: "istek sınırına takıldı",
    529: "sunucu şu an aşırı yüklü",
}


def _tek_ozet(makale, anahtar, model):
    istem = SABLON.format(
        dergi=makale.get("dergi_tam") or makale.get("dergi_kisa", ""),
        baslik=makale.get("baslik", ""),
        turler=", ".join(makale.get("turler", [])) or "belirtilmemiş",
        ozet=(makale.get("ozet_metni") or "")[:9000],
    )

    son_hata = "özet üretilemedi"
    for deneme in range(3):
        try:
            return _bicimle(_json_ayikla(_api_cagir(anahtar, model, istem)))

        except urllib.error.HTTPError as e:
            if e.code in _KALICI_HATALAR:
                # Tekrar denemek durumu degistirmez; hemen ve acikca bildir
                raise OzetHatasi("Anthropic API: %s" % _KALICI_HATALAR[e.code])
            son_hata = "Anthropic API: %s" % _GECICI_HATALAR.get(
                e.code, "sunucu %s hatası verdi" % e.code)

        except (urllib.error.URLError, TimeoutError, OSError):
            son_hata = "Anthropic API'ye ulaşılamadı (internet bağlantısı?)"

        except OzetHatasi:
            son_hata = "model geçerli JSON döndürmedi"

        if deneme < 2:
            time.sleep(3 * (deneme + 1))

    raise OzetHatasi(son_hata)


def _bicimle(veri):
    bulgular = veri.get("bulgular") or []
    if isinstance(bulgular, str):
        bulgular = [bulgular]
    etiketler = veri.get("etiketler") or []
    if isinstance(etiketler, str):
        etiketler = [etiketler]

    return {
        "kaynak": "yapay-zeka",
        "tek_cumle": str(veri.get("tek_cumle", "")).strip(),
        "bulgular": [str(b).strip() for b in bulgular if str(b).strip()][:4],
        "klinik_anlam": str(veri.get("klinik_anlam", "")).strip(),
        "yontem": str(veri.get("yontem", "")).strip(),
        "guven": str(veri.get("guven", "")).strip().lower(),
        "etiketler": [str(e).strip() for e in etiketler if str(e).strip()][:4],
    }


def _yedek(makale):
    return {
        "kaynak": "abstract",
        "tek_cumle": "",
        "bulgular": [],
        "klinik_anlam": "",
        "yontem": "",
        "guven": "",
        "etiketler": [],
        "abstract_sonuc": cikarimsal_ozet(makale),
    }


def ozetle(makaleler, anahtar, model, azami_sayi, ilerleme=None):
    """Ozeti olmayan makaleleri (yerinde) ozetler. Uretilen ozet sayisini dondurur."""
    ilerleme = ilerleme or (lambda m: None)
    eksik = [m for m in makaleler if not m.get("ozet")]

    if not eksik:
        return 0

    # Abstract'i olmayanlara (editoryal, erratum vb.) yapay zeka ozeti gereksiz
    ozetlenebilir = [m for m in eksik if (m.get("ozet_metni") or "").strip()]
    ozetlenebilir_kimlikler = {id(m) for m in ozetlenebilir}
    for m in eksik:
        if id(m) not in ozetlenebilir_kimlikler:
            m["ozet"] = _yedek(m)

    if not anahtar or not ozetlenebilir:
        for m in ozetlenebilir:
            m["ozet"] = _yedek(m)
        if ozetlenebilir and not anahtar:
            ilerleme("  API anahtarı yok → özetler makalenin Sonuç bölümünden çıkarıldı")
        return 0

    # Yeniden eskiye dogru sirala, limiti asanlara cikarimsal ozet ver
    ozetlenebilir.sort(key=lambda m: m.get("giris_tarihi", ""), reverse=True)
    secilen = ozetlenebilir[:azami_sayi]
    for m in ozetlenebilir[azami_sayi:]:
        m["ozet"] = _yedek(m)
    if len(ozetlenebilir) > azami_sayi:
        ilerleme("  not: %d makale özet limitini aştı, onlar için abstract sonucu kullanıldı"
                 % (len(ozetlenebilir) - azami_sayi))

    ilerleme("  %d makale Türkçe özetleniyor (%s)…" % (len(secilen), model))

    # Once tek bir deneme: anahtar/model yanlissa 80 cagri yapip 80 kez
    # basarisiz olmak yerine sebebi hemen soyleyip yedege gecelim.
    try:
        secilen[0]["ozet"] = _tek_ozet(secilen[0], anahtar, model)
    except OzetHatasi as e:
        ilerleme("")
        ilerleme("  !! Türkçe özet üretilemiyor — %s" % e)
        ilerleme("     Özetler şimdilik makalenin İngilizce sonuç bölümünden alındı.")
        ilerleme("")
        for m in secilen:
            m["ozet"] = _yedek(m)
        return 0

    basarili = 1
    hatalar = []
    kalan = secilen[1:]

    def is_(m):
        try:
            return m, _tek_ozet(m, anahtar, model), None
        except OzetHatasi as e:
            return m, None, str(e)

    if kalan:
        with ThreadPoolExecutor(max_workers=ES_ZAMANLI) as havuz:
            for i, (m, sonuc, hata) in enumerate(havuz.map(is_, kalan), 2):
                if sonuc:
                    m["ozet"] = sonuc
                    basarili += 1
                else:
                    m["ozet"] = _yedek(m)
                    hatalar.append(hata)
                if i % 10 == 0 or i == len(secilen):
                    ilerleme("    özetlendi: %d/%d" % (i, len(secilen)))

    if hatalar:
        from collections import Counter
        sebep, _ = Counter(hatalar).most_common(1)[0]
        ilerleme("  %d makale özetlenemedi (%s), abstract sonucu kullanıldı"
                 % (len(hatalar), sebep))
    return basarili
