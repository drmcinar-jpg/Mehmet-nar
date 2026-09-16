#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Yayın Okuma
===========
Seçili dergilerde PubMed'e yeni düşen makaleleri toplar, Türkçe özetler ve
tek bir HTML raporu olarak tarayıcıda açar.

Kullanım:
    python3 calistir.py                 # son 3 ayı tazele, raporu aç
    python3 calistir.py --gun 30        # yalnızca son 30 günü çek
    python3 calistir.py --ozetsiz       # yapay zeka özeti üretme (hızlı/ücretsiz)
    python3 calistir.py --acma          # raporu oluştur ama tarayıcıda açma
    python3 calistir.py --sifirla       # önbelleği yok say, her şeyi yeniden çek

Rapordaki Bugün / Bu hafta / Bu ay / Son 3 ay sekmeleri, indirilen bu
pencerenin içinden anında süzer; sekme değiştirmek için yeniden çekmeye
gerek yoktur.
"""

import argparse
import os
import sys
import webbrowser
from datetime import date, datetime, timedelta

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)

from yayin_okuma import ayarlar as ayar_modulu          # noqa: E402
from yayin_okuma import onbellek as onbellek_modulu     # noqa: E402
from yayin_okuma import ozet as ozet_modulu             # noqa: E402
from yayin_okuma import pubmed, rapor                   # noqa: E402
from yayin_okuma.dergiler import DERGILER, KONU_FILTRESI  # noqa: E402

RAPOR_YOLU = os.path.join(KOK, "rapor", "yayin-raporu.html")


def yaz(mesaj=""):
    print(mesaj, flush=True)


def sorgu_kur(dergi):
    temel = '%s[Journal]' % dergi["issn"]
    if dergi.get("kapsam") == "konulu":
        return "(%s) AND %s" % (temel, KONU_FILTRESI)
    return temel


def pmidleri_topla(istemci, bas, bit, tarih_turu, dergi_basina_azami):
    """Her dergi icin ayri arama yapar; {pmid: dergi} ve dergi basina sayilari dondurur."""
    pmid_dergi = {}
    sayimlar = []
    uyarilar = []

    for i, dergi in enumerate(DERGILER, 1):
        etiket = "[%2d/%d] %-34s" % (i, len(DERGILER), dergi["kisa"])
        try:
            pmidler = istemci.ara(sorgu_kur(dergi), bas, bit, tarih_turu, dergi_basina_azami)
        except pubmed.PubMedHatasi as e:
            yaz("%s HATA — %s" % (etiket, e))
            uyarilar.append("%s taranamadı: %s" % (dergi["ad"], e))
            continue

        for p in pmidler:
            pmid_dergi.setdefault(p, dergi)
        sayimlar.append((dergi, len(pmidler)))
        yaz("%s %4d makale" % (etiket, len(pmidler)))

        if len(pmidler) >= dergi_basina_azami:
            uyarilar.append(
                "%s için %d makale sınırına ulaşıldı; daha eskiler atlanmış olabilir "
                "(ayarlar.json → dergi_basina_azami)." % (dergi["ad"], dergi_basina_azami))

    return pmid_dergi, sayimlar, uyarilar


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Seçili dergilerdeki yeni PubMed makalelerini listeler ve özetler.")
    ap.add_argument("--gun", type=int, default=None,
                    help="Kaç günlük yayın çekilsin (varsayılan: ayarlar.json'daki değer)")
    ap.add_argument("--ozetsiz", action="store_true",
                    help="Yapay zeka özeti üretme, abstract sonucunu kullan")
    ap.add_argument("--acma", action="store_true", help="Raporu tarayıcıda açma")
    ap.add_argument("--sifirla", action="store_true", help="Önbelleği yok say, her şeyi yeniden çek")
    ap.add_argument("--cikti", default=RAPOR_YOLU, help="Rapor dosyasının yolu")
    a = ap.parse_args(argv)

    ayar = ayar_modulu.yukle(KOK)
    gun = a.gun if a.gun is not None else int(ayar["gecmis_gun"])
    gun = max(1, min(gun, 400))
    bugun = date.today()
    bas = bugun - timedelta(days=gun)
    calistirma_damgasi = datetime.now().isoformat(timespec="seconds")
    yeni_siniri = rapor.yeni_siniri_hesapla(ayar.get("yeni_rozeti_saat", 24))

    yaz("=" * 64)
    yaz("  YAYIN OKUMA — %s" % bugun.strftime("%d.%m.%Y"))
    yaz("  %d dergi · son %d gün (%s – %s)"
        % (len(DERGILER), gun, bas.strftime("%d.%m"), bugun.strftime("%d.%m.%Y")))
    yaz("=" * 64)
    yaz()

    onbellek = {"makaleler": {}, "son_calistirma": ""} if a.sifirla \
        else onbellek_modulu.yukle(KOK)
    # Onbellek, --gun ile gecici olarak daralan pencereye gore budanmasin;
    # yoksa "--gun 7" 3 aylik arsivi silip bir sonraki tam taramayi yavaslatir.
    saklama_gunu = max(gun, int(ayar["gecmis_gun"])) + 30
    onbellek_modulu.eskileri_temizle(onbellek, saklama_gunu)
    zaten_var = set(onbellek["makaleler"])

    istemci = pubmed.Istemci(
        api_key=ayar_modulu.ncbi_anahtari(ayar),
        eposta=ayar.get("eposta", ""),
        ilerleme=yaz,
    )

    yaz("Dergiler taranıyor…")
    try:
        pmid_dergi, sayimlar, uyarilar = pmidleri_topla(
            istemci, bas, bugun, ayar.get("tarih_turu", "edat"),
            int(ayar["dergi_basina_azami"]))
    except KeyboardInterrupt:
        yaz("\nİptal edildi.")
        return 1

    if not pmid_dergi and not zaten_var:
        yaz()
        yaz("Hiç makale bulunamadı. İnternet bağlantınızı kontrol edip tekrar deneyin.")
        return 1

    yeniler = [p for p in pmid_dergi if p not in zaten_var]
    yaz()
    yaz("Toplam %d kayıt bulundu; %d tanesi yeni (%d tanesi önbellekten geldi)."
        % (len(pmid_dergi), len(yeniler), len(pmid_dergi) - len(yeniler)))

    if yeniler:
        try:
            cekilenler = istemci.getir(yeniler)
        except pubmed.PubMedHatasi as e:
            yaz("Makale ayrıntıları indirilemedi: %s" % e)
            cekilenler = []
        for m in cekilenler:
            m["ilk_gorulme"] = calistirma_damgasi
            # Dergi ISSN'i kayitta farkli surumde gelebilir; aramadaki dergiye sabitle
            dergi = pmid_dergi.get(m["pmid"])
            if dergi:
                m["dergi_issn"] = dergi["issn"]
            onbellek["makaleler"][m["pmid"]] = m

    # --- ozetleme ---
    pencere_ici = []
    for m in onbellek["makaleler"].values():
        iso = m.get("giris_tarihi") or m.get("yayin_tarihi")
        if not iso:
            continue
        try:
            if (bugun - date.fromisoformat(iso)).days <= gun:
                pencere_ici.append(m)
        except ValueError:
            continue

    yaz()
    yaz("Özetler hazırlanıyor…")
    anahtar = "" if (a.ozetsiz or not ayar.get("yapay_zeka_ozet")) \
        else ayar_modulu.anthropic_anahtari(ayar)
    if a.ozetsiz:
        yaz("  --ozetsiz verildi → abstract sonuç bölümleri kullanılıyor")
    try:
        uretilen = ozet_modulu.ozetle(
            pencere_ici, anahtar, ayar.get("model", "claude-sonnet-5"),
            int(ayar["calistirma_basina_azami_ozet"]), ilerleme=yaz)
    except KeyboardInterrupt:
        yaz("\nÖzetleme iptal edildi, mevcut özetlerle devam ediliyor.")
        uretilen = 0
    if uretilen:
        yaz("  %d yeni Türkçe özet üretildi" % uretilen)

    onbellek["son_calistirma"] = calistirma_damgasi
    onbellek_modulu.kaydet(KOK, onbellek)

    # --- rapor ---
    yol, sayi = rapor.olustur(
        pencere_ici, DERGILER, a.cikti, bugun=bugun,
        yeni_siniri=yeni_siniri, notlar=uyarilar)

    yeni_sayisi = sum(1 for m in pencere_ici if rapor.yeni_mi(m, yeni_siniri))
    yaz()
    yaz("-" * 64)
    yaz("Rapor hazır: %s" % yol)
    yaz("%d makale · %d yeni" % (sayi, yeni_sayisi))
    yaz("-" * 64)

    if not a.acma and ayar.get("raporu_otomatik_ac", True):
        webbrowser.open("file://" + os.path.abspath(yol))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        yaz("\nİptal edildi.")
        sys.exit(1)
