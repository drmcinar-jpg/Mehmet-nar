# -*- coding: utf-8 -*-
"""Takip edilen dergi listesi.

Her dergi PubMed'de ISSN ile aranir. ISSN, dergi kisaltmasindan daha
guvenilirdir (ornegin "Reproduction" gibi genel adlar yanlis eslesebilir).
Tum ISSN'ler PubMed uzerinde dogrulanmistir.

kapsam:
  "tam"    -> derginin o donemdeki butun yayinlari listelenir
  "konulu" -> genel dergi; sadece ureme/infertilite konulu yayinlar listelenir
"""

DERGILER = [
    # --- 1. Cekirdek ureme tibbi dergileri (her sey gelsin) ---
    {"issn": "1355-4786", "ad": "Human Reproduction Update",            "kisa": "Hum Reprod Update",   "grup": "Çekirdek üreme tıbbı", "kapsam": "tam"},
    {"issn": "0268-1161", "ad": "Human Reproduction",                   "kisa": "Hum Reprod",          "grup": "Çekirdek üreme tıbbı", "kapsam": "tam"},
    {"issn": "0015-0282", "ad": "Fertility and Sterility",              "kisa": "Fertil Steril",       "grup": "Çekirdek üreme tıbbı", "kapsam": "tam"},
    {"issn": "1472-6483", "ad": "Reproductive BioMedicine Online",      "kisa": "Reprod Biomed Online","grup": "Çekirdek üreme tıbbı", "kapsam": "tam"},
    {"issn": "1058-0468", "ad": "J. Assisted Reproduction and Genetics","kisa": "J Assist Reprod Genet","grup": "Çekirdek üreme tıbbı","kapsam": "tam"},
    {"issn": "1477-7827", "ad": "Reproductive Biology and Endocrinology","kisa": "Reprod Biol Endocrinol","grup": "Çekirdek üreme tıbbı","kapsam": "tam"},
    {"issn": "1360-9947", "ad": "Molecular Human Reproduction",         "kisa": "Mol Hum Reprod",      "grup": "Çekirdek üreme tıbbı", "kapsam": "tam"},
    {"issn": "1470-1626", "ad": "Reproduction (SRF)",                   "kisa": "Reproduction",        "grup": "Çekirdek üreme tıbbı", "kapsam": "tam"},
    {"issn": "2666-3341", "ad": "F&S Reports",                          "kisa": "F S Rep",             "grup": "Çekirdek üreme tıbbı", "kapsam": "tam"},
    {"issn": "2666-335X", "ad": "F&S Science",                          "kisa": "F S Sci",             "grup": "Çekirdek üreme tıbbı", "kapsam": "tam"},

    # --- 2. Ust duzey genel jinekoloji (sadece ureme konulu) ---
    {"issn": "0002-9378", "ad": "Am. J. Obstetrics & Gynecology",       "kisa": "Am J Obstet Gynecol", "grup": "Genel jinekoloji",     "kapsam": "konulu"},
    {"issn": "0029-7844", "ad": "Obstetrics & Gynecology (Green J.)",   "kisa": "Obstet Gynecol",      "grup": "Genel jinekoloji",     "kapsam": "konulu"},
    {"issn": "0960-7692", "ad": "Ultrasound in Obstetrics & Gynecology","kisa": "Ultrasound Obstet Gynecol","grup": "Genel jinekoloji", "kapsam": "konulu"},
    {"issn": "1470-0328", "ad": "BJOG",                                 "kisa": "BJOG",                "grup": "Genel jinekoloji",     "kapsam": "konulu"},

    # --- 3. Endokrinoloji (PKOS, over rezervi, POY) ---
    {"issn": "0163-769X", "ad": "Endocrine Reviews",                    "kisa": "Endocr Rev",          "grup": "Endokrinoloji",        "kapsam": "konulu"},
    {"issn": "1759-5029", "ad": "Nature Reviews Endocrinology",         "kisa": "Nat Rev Endocrinol",  "grup": "Endokrinoloji",        "kapsam": "konulu"},
    {"issn": "0021-972X", "ad": "J. Clinical Endocrinology & Metabolism","kisa": "J Clin Endocrinol Metab","grup": "Endokrinoloji",     "kapsam": "konulu"},

    # --- 4. Genel tip dev dergileri (sadece ureme konulu) ---
    {"issn": "0028-4793", "ad": "New England Journal of Medicine",      "kisa": "N Engl J Med",        "grup": "Genel tıp",            "kapsam": "konulu"},
    {"issn": "0140-6736", "ad": "The Lancet",                           "kisa": "Lancet",              "grup": "Genel tıp",            "kapsam": "konulu"},
    {"issn": "0959-8138", "ad": "BMJ",                                  "kisa": "BMJ",                 "grup": "Genel tıp",            "kapsam": "konulu"},
    {"issn": "0098-7484", "ad": "JAMA",                                 "kisa": "JAMA",                "grup": "Genel tıp",            "kapsam": "konulu"},
]

# "konulu" dergilerde bu konu filtresi uygulanir.
KONU_FILTRESI = (
    '('
    'infertil*[tiab] OR subfertil*[tiab] OR fertility[tiab] OR '
    '"in vitro fertilization"[tiab] OR "in vitro fertilisation"[tiab] OR '
    'IVF[tiab] OR ICSI[tiab] OR "assisted reproduct*"[tiab] OR '
    'embryo*[tiab] OR blastocyst*[tiab] OR oocyte*[tiab] OR '
    'sperm*[tiab] OR semen[tiab] OR azoospermi*[tiab] OR '
    '"ovarian reserve"[tiab] OR "ovarian stimulation"[tiab] OR '
    '"ovarian hyperstimulation"[tiab] OR gonadotropin*[tiab] OR '
    '"anti-mullerian"[tiab] OR "antimullerian"[tiab] OR AMH[tiab] OR '
    '"polycystic ovary"[tiab] OR PCOS[tiab] OR endometriosis[tiab] OR '
    'adenomyosis[tiab] OR endometrium[tiab] OR endometrial[tiab] OR '
    '"preimplantation genetic"[tiab] OR PGT[tiab] OR aneuploid*[tiab] OR '
    '"recurrent pregnancy loss"[tiab] OR "recurrent miscarriage"[tiab] OR '
    'miscarriage[tiab] OR "implantation failure"[tiab] OR '
    '"fertility preservation"[tiab] OR "oocyte cryopreservation"[tiab] OR '
    '"egg freezing"[tiab] OR "uterine transplant*"[tiab] OR '
    '"premature ovarian"[tiab] OR "primary ovarian insufficiency"[tiab] OR '
    'menopause[tiab] OR amenorrh*[tiab] OR "intrauterine insemination"[tiab] OR '
    'hydrosalpinx[tiab] OR myoma[tiab] OR fibroid*[tiab] OR '
    '"Infertility"[MeSH] OR "Reproductive Techniques, Assisted"[MeSH] OR '
    '"Fertilization in Vitro"[MeSH] OR "Polycystic Ovary Syndrome"[MeSH] OR '
    '"Endometriosis"[MeSH] OR "Ovarian Reserve"[MeSH] OR '
    '"Fertility Preservation"[MeSH] OR "Abortion, Habitual"[MeSH]'
    ')'
)
