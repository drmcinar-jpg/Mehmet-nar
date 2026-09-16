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
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ES_ZAMANLI = 4          # varsayilan es zamanli istek sayisi
ZAMAN_ASIMI = 60        # tek bir ozet istegi icin saniye
ANTHROPIC_SURUMU = "2023-06-01"

# Desteklenen ozet saglayicilari. Yeni bir OpenAI uyumlu servis eklemek icin
# "openai-uyumlu" secip ayarlar.json'da api_ucu ve model yazmak yeterli.
SAGLAYICILAR = {
    "anthropic": {
        "ad": "Anthropic (Claude)",
        "uc": "https://api.anthropic.com/v1/messages",
        "bicim": "anthropic",
        "model": "claude-sonnet-5",
        "ortam": "ANTHROPIC_API_KEY",
        "onek": "sk-ant-",
        "adres": "https://console.anthropic.com/settings/keys",
        "model_oneki": "claude",
    },
    "deepseek": {
        "ad": "DeepSeek",
        "uc": "https://api.deepseek.com/chat/completions",
        "bicim": "openai",
        "model": "deepseek-flash",
        "ortam": "DEEPSEEK_API_KEY",
        "onek": "sk-",
        "adres": "https://platform.deepseek.com/api_keys",
        "model_oneki": "deepseek",
    },
    "openai-uyumlu": {
        "ad": "OpenAI uyumlu servis",
        "uc": "",          # ayarlar.json -> api_ucu ile verilir
        "bicim": "openai",
        "model": "",       # ayarlar.json -> model ile verilir
        "ortam": "OPENAI_API_KEY",
        "onek": "",
        "adres": "",
        "model_oneki": "",
    },
}
VARSAYILAN_SAGLAYICI = "anthropic"


def saglayici_bilgisi(ad):
    return SAGLAYICILAR.get((ad or "").strip().lower() or VARSAYILAN_SAGLAYICI,
                            SAGLAYICILAR[VARSAYILAN_SAGLAYICI])


def model_coz(saglayici_adi, model, uyari=None):
    """Ayarlardaki model bu saglayiciya ait degilse saglayicinin varsayilanina duser.

    Sagayici degistirildiginde eski model adinin kalip 404 uretmesini onler.
    """
    bilgi = saglayici_bilgisi(saglayici_adi)
    model = (model or "").strip()
    if not model:
        return bilgi["model"]

    baska = [b for a, b in SAGLAYICILAR.items()
             if a != saglayici_adi and b["model_oneki"]
             and model.lower().startswith(b["model_oneki"])]
    if baska:
        if uyari:
            uyari("  not: '%s' modeli %s sağlayıcısına ait değil, %s kullanılıyor"
                  % (model, bilgi["ad"], bilgi["model"] or "(model belirtilmemiş)"))
        return bilgi["model"]
    return model


def uc_coz(saglayici_adi, api_ucu):
    return (api_ucu or "").strip() or saglayici_bilgisi(saglayici_adi)["uc"]

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


def _sure_yaz(saniye):
    saniye = int(max(0, saniye))
    if saniye < 60:
        return "%d sn" % saniye
    if saniye < 3600:
        return "%d dk %02d sn" % (saniye // 60, saniye % 60)
    return "%d sa %02d dk" % (saniye // 3600, (saniye % 3600) // 60)


class _Ilerleme:
    """Terminalde tek satiri guncelleyen, aksi halde araliklarla yazan gosterge."""

    def __init__(self, toplam, yaz):
        self.toplam = toplam
        self.yaz = yaz
        self.baslangic = time.monotonic()
        self.bitti_mi = False
        try:
            self.canli = sys.stdout.isatty()
        except (AttributeError, ValueError):
            self.canli = False

    def guncelle(self, bitti):
        gecen = time.monotonic() - self.baslangic
        metin = "    özetlendi: %d/%d · geçen %s" % (bitti, self.toplam, _sure_yaz(gecen))
        if bitti >= 2 and bitti < self.toplam:
            kalan = gecen / bitti * (self.toplam - bitti)
            metin += " · tahmini kalan %s" % _sure_yaz(kalan)

        if self.canli:
            try:
                sys.stdout.write("\r" + metin.ljust(72))
                sys.stdout.flush()
                return
            except (OSError, ValueError):
                self.canli = False
        if bitti % 10 == 0 or bitti == self.toplam:
            self.yaz(metin)

    def bitir(self):
        if self.bitti_mi:
            return
        self.bitti_mi = True
        if self.canli:
            try:
                sys.stdout.write("\n")
                sys.stdout.flush()
            except (OSError, ValueError):
                pass


# --------------------------------------------------------------- yapay zeka

class OzetHatasi(Exception):
    pass


def _http(uc, govde, basliklar, zaman_asimi):
    istek = urllib.request.Request(uc, data=json.dumps(govde).encode("utf-8"),
                                   headers=basliklar)
    with urllib.request.urlopen(istek, timeout=zaman_asimi,
                                context=ssl.create_default_context()) as y:
        return json.loads(y.read().decode("utf-8"))


def _anthropic_cagir(uc, anahtar, model, istem, zaman_asimi):
    cevap = _http(uc, {
        "model": model,
        "max_tokens": 1000,
        "system": SISTEM,
        "messages": [{"role": "user", "content": istem}],
    }, {
        "x-api-key": anahtar,
        "anthropic-version": ANTHROPIC_SURUMU,
        "content-type": "application/json",
    }, zaman_asimi)

    return "".join(p.get("text", "") for p in cevap.get("content", [])
                   if p.get("type") == "text").strip()


def _openai_cagir(uc, anahtar, model, istem, zaman_asimi):
    """DeepSeek, OpenAI ve OpenAI uyumlu diger servisler icin."""
    cevap = _http(uc, {
        "model": model,
        "max_tokens": 1000,
        # Istem zaten JSON istiyor; bu mod cevabi garanti altina alir
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SISTEM},
            {"role": "user", "content": istem},
        ],
    }, {
        "Authorization": "Bearer " + anahtar,
        "Content-Type": "application/json",
    }, zaman_asimi)

    secenekler = cevap.get("choices") or []
    if not secenekler:
        return ""
    return (secenekler[0].get("message", {}).get("content") or "").strip()


def _api_cagir(uc, bicim, anahtar, model, istem, zaman_asimi=ZAMAN_ASIMI):
    if bicim == "anthropic":
        return _anthropic_cagir(uc, anahtar, model, istem, zaman_asimi)
    return _openai_cagir(uc, anahtar, model, istem, zaman_asimi)


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
    401: "API anahtarı geçersiz (ayarlar.json → api_anahtari)",
    403: "API anahtarının bu modele erişim izni yok",
    404: "model bulunamadı (ayarlar.json → model)",
    413: "makale özeti çok uzun",
}
_GECICI_HATALAR = {
    429: "istek sınırına takıldı",
    529: "sunucu şu an aşırı yüklü",
}


def _tek_ozet(makale, anahtar, model, uc, bicim):
    istem = SABLON.format(
        dergi=makale.get("dergi_tam") or makale.get("dergi_kisa", ""),
        baslik=makale.get("baslik", ""),
        turler=", ".join(makale.get("turler", [])) or "belirtilmemiş",
        ozet=(makale.get("ozet_metni") or "")[:9000],
    )

    son_hata = "özet üretilemedi"
    for deneme in range(3):
        try:
            return _bicimle(_json_ayikla(
                _api_cagir(uc, bicim, anahtar, model, istem)))

        except urllib.error.HTTPError as e:
            if e.code in _KALICI_HATALAR:
                # Tekrar denemek durumu degistirmez; hemen ve acikca bildir
                raise OzetHatasi("API: %s" % _KALICI_HATALAR[e.code])
            son_hata = "API: %s" % _GECICI_HATALAR.get(
                e.code, "sunucu %s hatası verdi" % e.code)

        except (urllib.error.URLError, TimeoutError, OSError):
            son_hata = "API'ye ulaşılamadı (internet bağlantısı?)"

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


def ozetle(makaleler, saglayici, azami_sayi, ilerleme=None):
    """Ozeti olmayan makaleleri (yerinde) ozetler. Uretilen ozet sayisini dondurur.

    saglayici: {"anahtar", "model", "uc", "bicim", "ad"} sozlugu.
    Anahtar bossa hepsine cikarimsal ozet uygulanir.
    """
    anahtar = saglayici.get("anahtar", "")
    model = saglayici.get("model", "")
    uc = saglayici.get("uc", "")
    bicim = saglayici.get("bicim", "anthropic")
    es_zamanli = max(1, min(int(saglayici.get("es_zamanli") or ES_ZAMANLI), 16))
    ilerleme = ilerleme or (lambda m: None)

    def _metni_var(m):
        return bool((m.get("ozet_metni") or "").strip())

    # 1) Hic ozeti olmayan makaleler
    eksik = [m for m in makaleler if not m.get("ozet")]
    # Abstract'i olmayanlara (editoryal, erratum vb.) yapay zeka ozeti gereksiz
    for m in eksik:
        if not _metni_var(m):
            m["ozet"] = _yedek(m)
    yeni = [m for m in eksik if _metni_var(m)]

    if not anahtar:
        for m in yeni:
            m["ozet"] = _yedek(m)
        if yeni:
            ilerleme("  API anahtarı yok → özetler makalenin Sonuç bölümünden çıkarıldı")
        return 0

    # 2) Daha once anahtarsiz calisildigi icin Ingilizce kalmis ozetler.
    #    Anahtar eklendikten sonra bunlar kendiliginden Turkceye cevrilsin;
    #    kullanicinin onbellegi silmesi gerekmesin.
    yukseltilecek = [m for m in makaleler
                     if (m.get("ozet") or {}).get("kaynak") == "abstract"
                     and _metni_var(m)]

    # Yeniden eskiye dogru: once en taze makaleler
    yeni.sort(key=lambda m: m.get("giris_tarihi", ""), reverse=True)
    yukseltilecek.sort(key=lambda m: m.get("giris_tarihi", ""), reverse=True)

    # Kota once yeni makalelere, artani eski Ingilizce ozetlere
    secilen = yeni[:azami_sayi]
    for m in yeni[azami_sayi:]:
        m["ozet"] = _yedek(m)
    if len(yeni) > azami_sayi:
        ilerleme("  not: %d yeni makale özet limitini aştı, onlar için abstract "
                 "sonucu kullanıldı" % (len(yeni) - azami_sayi))

    kalan_kota = azami_sayi - len(secilen)
    if kalan_kota > 0 and yukseltilecek:
        cevrilecek = yukseltilecek[:kalan_kota]
        secilen = secilen + cevrilecek
        ilerleme("  daha önce İngilizce kalmış %d özet Türkçeye çevriliyor"
                 % len(cevrilecek))
        if len(yukseltilecek) > kalan_kota:
            ilerleme("    (%d tanesi sırada; her çalıştırmada bir grup daha çevrilir."
                     % (len(yukseltilecek) - kalan_kota))
            ilerleme("     Hepsini bir seferde istiyorsanız ayarlar.json →"
                     " calistirma_basina_azami_ozet değerini yükseltin.)")

    if not secilen:
        return 0

    ilerleme("  %d makale Türkçe özetleniyor (%s · %s)…"
             % (len(secilen), saglayici.get("ad", ""), model))

    # Once tek bir deneme: anahtar/model yanlissa 150 cagri yapip 150 kez
    # basarisiz olmak yerine sebebi hemen soyleyip yedege gecelim.
    olcum = time.monotonic()
    try:
        secilen[0]["ozet"] = _tek_ozet(secilen[0], anahtar, model, uc, bicim)
    except OzetHatasi as e:
        ilerleme("")
        ilerleme("  !! Türkçe özet üretilemiyor — %s" % e)
        ilerleme("     Özetler şimdilik makalenin İngilizce sonuç bölümünden alındı.")
        ilerleme("")
        for m in secilen:
            m["ozet"] = _yedek(m)
        return 0

    tek_sure = time.monotonic() - olcum
    kalan = secilen[1:]
    if kalan:
        tahmin = tek_sure * len(kalan) / max(1, es_zamanli)
        ilerleme("  ilk özet %s sürdü → %d makale için kabaca %s"
                 % (_sure_yaz(tek_sure), len(kalan), _sure_yaz(tahmin)))
        ilerleme("  (istediğiniz an Ctrl+C ile durdurabilirsiniz; o ana kadar"
                 " üretilenler korunur)")

    basarili = 1
    hatalar = []

    def is_(m):
        try:
            return m, _tek_ozet(m, anahtar, model, uc, bicim), None
        except OzetHatasi as e:
            return m, None, str(e)

    if kalan:
        gosterge = _Ilerleme(len(secilen), ilerleme)
        havuz = ThreadPoolExecutor(max_workers=es_zamanli)
        gelecekler = [havuz.submit(is_, m) for m in kalan]
        # Makaleler sozluk oldugu icin kimlikle takip edilir
        bitmeyen = {id(m): m for m in kalan}
        bitti = 1
        try:
            # as_completed: siradaki yavas istek digerlerinin gosterimini bekletmesin
            for gelecek in as_completed(gelecekler):
                m, sonuc, hata = gelecek.result()
                bitmeyen.pop(id(m), None)
                if sonuc:
                    m["ozet"] = sonuc
                    basarili += 1
                else:
                    m["ozet"] = _yedek(m)
                    hatalar.append(hata)
                bitti += 1
                gosterge.guncelle(bitti)
        except KeyboardInterrupt:
            gosterge.bitir()
            ilerleme("")
            ilerleme("  Durduruldu. %d özet üretildi ve kaydedildi;" % basarili)
            ilerleme("  kalan %d makale bir sonraki çalıştırmada çevrilecek."
                     % len(bitmeyen))
            for g in gelecekler:
                g.cancel()
            havuz.shutdown(wait=False)
            # Yarim kalanlar ozetsiz gorunmesin; sonraki turda yukseltilirler
            for m in bitmeyen.values():
                if not m.get("ozet"):
                    m["ozet"] = _yedek(m)
            return basarili
        finally:
            gosterge.bitir()
        havuz.shutdown(wait=True)

    if hatalar:
        from collections import Counter
        sebep, _ = Counter(hatalar).most_common(1)[0]
        ilerleme("  %d makale özetlenemedi (%s), abstract sonucu kullanıldı"
                 % (len(hatalar), sebep))
    return basarili
