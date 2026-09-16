# -*- coding: utf-8 -*-
"""PubMed E-utilities istemcisi. Sadece Python standart kutuphanesini kullanir."""

import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime

TABAN = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
ARAC = "yayin-okuma"
EFETCH_PARTI = 150


class PubMedHatasi(Exception):
    pass


class Istemci:
    def __init__(self, api_key="", eposta="", ilerleme=None):
        self.api_key = api_key
        self.eposta = eposta
        # NCBI siniri: anahtarsiz 3 istek/sn, anahtarli 10 istek/sn
        self._aralik = 0.11 if api_key else 0.36
        self._son_istek = 0.0
        self._ilerleme = ilerleme or (lambda m: None)
        self._ssl = ssl.create_default_context()

    # ---------- alt seviye ----------

    def _bekle(self):
        gecen = time.monotonic() - self._son_istek
        if gecen < self._aralik:
            time.sleep(self._aralik - gecen)
        self._son_istek = time.monotonic()

    def _istek(self, uc, parametreler, deneme=4):
        ortak = {"db": "pubmed", "tool": ARAC}
        if self.eposta:
            ortak["email"] = self.eposta
        if self.api_key:
            ortak["api_key"] = self.api_key
        ortak.update(parametreler)
        veri = urllib.parse.urlencode(ortak, doseq=True).encode("utf-8")

        son_hata = None
        for i in range(deneme):
            self._bekle()
            try:
                istek = urllib.request.Request(
                    TABAN + uc,
                    data=veri,
                    headers={"User-Agent": ARAC + "/1.0"},
                )
                with urllib.request.urlopen(istek, timeout=60, context=self._ssl) as y:
                    return y.read()
            except urllib.error.HTTPError as e:
                son_hata = e
                # 429 (cok fazla istek) ve 5xx icin bekleyip tekrar dene
                if e.code not in (429, 500, 502, 503, 504):
                    raise PubMedHatasi("PubMed %s hatasi: %s" % (e.code, e.reason))
            except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as e:
                son_hata = e
            if i < deneme - 1:
                time.sleep(2 ** i)

        raise PubMedHatasi(
            "PubMed'e ulasilamadi (%s). Internet baglantinizi kontrol edin." % son_hata
        )

    # ---------- arama ----------

    def ara(self, sorgu, bas_tarih, bit_tarih, tarih_turu="edat", azami=400):
        """Sorguya uyan PMID listesini dondurur."""
        ham = self._istek("esearch.fcgi", {
            "term": sorgu,
            "retmax": str(azami),
            "retmode": "json",
            "datetype": tarih_turu,
            "mindate": bas_tarih.strftime("%Y/%m/%d"),
            "maxdate": bit_tarih.strftime("%Y/%m/%d"),
            "sort": "date",
        })
        try:
            cevap = json.loads(ham.decode("utf-8"))
        except ValueError:
            raise PubMedHatasi("PubMed beklenmeyen bir cevap dondurdu.")
        sonuc = cevap.get("esearchresult", {})
        if "ERROR" in sonuc:
            raise PubMedHatasi("PubMed sorgu hatasi: %s" % sonuc["ERROR"])
        return sonuc.get("idlist", [])

    # ---------- kayitlari cekme ----------

    def getir(self, pmidler):
        """PMID listesi icin makale kayitlarini dondurur."""
        makaleler = []
        toplam = len(pmidler)
        for i in range(0, toplam, EFETCH_PARTI):
            parti = pmidler[i:i + EFETCH_PARTI]
            self._ilerleme("    ayrıntılar indiriliyor: %d/%d" % (min(i + len(parti), toplam), toplam))
            ham = self._istek("efetch.fcgi", {
                "id": ",".join(parti),
                "retmode": "xml",
            })
            makaleler.extend(_xml_coz(ham))
        return makaleler


# ---------------------------------------------------------------- XML cozumleme

def _metin(el):
    """Ic etiketleri (<i>, <sub>, <sup>...) koruyarak duz metin cikarir."""
    if el is None:
        return ""
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def _tarih_oku(el):
    if el is None:
        return None
    y = el.findtext("Year")
    if not y:
        return None
    a = el.findtext("Month") or "1"
    g = el.findtext("Day") or "1"
    aylar = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
             "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
    try:
        ay = int(a)
    except ValueError:
        ay = aylar.get(a.strip()[:3].lower(), 1)
    try:
        return date(int(y), max(1, min(12, ay)), max(1, min(28, int(g))))
    except (ValueError, TypeError):
        try:
            return date(int(y), max(1, min(12, ay)), 1)
        except ValueError:
            return None


def _giris_tarihi(kok):
    """PubMed'e giris (entrez) tarihi."""
    for durum in ("entrez", "pubmed", "medline"):
        el = kok.find(".//PubmedData/History/PubMedPubDate[@PubStatus='%s']" % durum)
        t = _tarih_oku(el)
        if t:
            return t
    return None


def _yayin_tarihi(kok):
    t = _tarih_oku(kok.find(".//Article/Journal/JournalIssue/PubDate"))
    if t:
        return t
    ham = kok.findtext(".//Article/Journal/JournalIssue/PubDate/MedlineDate") or ""
    m = re.search(r"(19|20)\d{2}", ham)
    if m:
        try:
            return date(int(m.group(0)), 1, 1)
        except ValueError:
            pass
    return None


def _yazarlar(kok):
    isimler = []
    for y in kok.findall(".//Article/AuthorList/Author"):
        soyad = y.findtext("LastName")
        bas = y.findtext("Initials") or ""
        if soyad:
            isimler.append((soyad + " " + bas).strip())
        elif y.findtext("CollectiveName"):
            isimler.append(y.findtext("CollectiveName"))
    return isimler


def _ozet_bolumleri(kok):
    """[(baslik, metin), ...] seklinde yapilandirilmis ozet."""
    bolumler = []
    for ab in kok.findall(".//Article/Abstract/AbstractText"):
        metin = _metin(ab)
        if not metin:
            continue
        baslik = (ab.get("Label") or ab.get("NlmCategory") or "").strip()
        bolumler.append((baslik, metin))
    return bolumler


def _kimlikler(kok):
    doi = ""
    for el in kok.findall(".//Article/ELocationID"):
        if (el.get("EIdType") or "").lower() == "doi":
            doi = _metin(el)
    if not doi:
        for el in kok.findall(".//PubmedData/ArticleIdList/ArticleId"):
            if (el.get("IdType") or "").lower() == "doi":
                doi = _metin(el)
    return doi


def _xml_coz(ham):
    try:
        agac = ET.fromstring(ham)
    except ET.ParseError as e:
        raise PubMedHatasi("PubMed cevabi cozumlenemedi: %s" % e)

    makaleler = []
    for kok in agac.findall(".//PubmedArticle"):
        pmid = kok.findtext(".//MedlineCitation/PMID")
        if not pmid:
            continue

        bolumler = _ozet_bolumleri(kok)
        giris = _giris_tarihi(kok)
        yayin = _yayin_tarihi(kok)
        turler = [_metin(t) for t in kok.findall(".//Article/PublicationTypeList/PublicationType")]

        makaleler.append({
            "pmid": pmid,
            "baslik": _metin(kok.find(".//Article/ArticleTitle")),
            "dergi_issn": (kok.findtext(".//Article/Journal/ISSN") or "").strip(),
            "dergi_kisa": (kok.findtext(".//MedlineJournalInfo/MedlineTA")
                           or kok.findtext(".//Article/Journal/ISOAbbreviation") or "").strip(),
            "dergi_tam": (kok.findtext(".//Article/Journal/Title") or "").strip(),
            "yazarlar": _yazarlar(kok),
            "ozet_bolumleri": bolumler,
            "ozet_metni": " ".join(m for _, m in bolumler),
            "doi": _kimlikler(kok),
            "turler": turler,
            "anahtar_kelimeler": [_metin(k) for k in kok.findall(".//KeywordList/Keyword")][:12],
            "giris_tarihi": giris.isoformat() if giris else "",
            "yayin_tarihi": yayin.isoformat() if yayin else "",
            "cekilme_zamani": datetime.now().isoformat(timespec="seconds"),
        })
    return makaleler
