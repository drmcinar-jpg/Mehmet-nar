# -*- coding: utf-8 -*-
"""Tek dosyalik, internet gerektirmeyen HTML rapor uretir."""

import html
import json
import os
from datetime import date, datetime, timedelta

DONEMLER = [
    {"anahtar": "bugun",  "ad": "Bugün",     "gun": 0},
    {"anahtar": "hafta",  "ad": "Bu hafta",  "gun": 7},
    {"anahtar": "ay",     "ad": "Bu ay",     "gun": 30},
    {"anahtar": "uc_ay",  "ad": "Son 3 ay",  "gun": 92},
]


def _gun_farki(iso_tarih, bugun):
    if not iso_tarih:
        return 9999
    try:
        return (bugun - date.fromisoformat(iso_tarih)).days
    except ValueError:
        return 9999


def _grup_siralari(dergiler):
    """Gruplar dergiler.py'deki sirayla gorunsun (once cekirdek ureme dergileri)."""
    sira = {}
    for d in dergiler:
        sira.setdefault(d.get("grup", "Diğer"), len(sira))
    sira.setdefault("Diğer", len(sira))
    return sira


def _kart_verisi(makaleler, dergi_haritasi, bugun, yeni_siniri, grup_siralari):
    veri = []
    for m in makaleler:
        issn = m.get("dergi_issn", "")
        dergi = dergi_haritasi.get(issn) or dergi_haritasi.get(m.get("dergi_kisa", "")) or {}
        oz = m.get("ozet") or {}
        turler = m.get("turler") or []

        onemli = [t for t in turler if t in (
            "Randomized Controlled Trial", "Meta-Analysis", "Systematic Review",
            "Review", "Clinical Trial", "Guideline", "Practice Guideline",
            "Multicenter Study", "Observational Study", "Editorial", "Comment",
            "Letter", "Case Reports", "Retracted Publication",
            "Retraction of Publication", "Published Erratum",
        )]

        yazarlar = m.get("yazarlar") or []
        if len(yazarlar) > 3:
            yazar_metni = ", ".join(yazarlar[:3]) + " ve ark."
        else:
            yazar_metni = ", ".join(yazarlar)

        veri.append({
            "pmid": m.get("pmid", ""),
            "baslik": m.get("baslik", "(başlıksız)"),
            "dergi": dergi.get("ad") or m.get("dergi_tam") or m.get("dergi_kisa", ""),
            "dergi_kisa": dergi.get("kisa") or m.get("dergi_kisa", ""),
            "grup": dergi.get("grup", "Diğer"),
            "grup_sira": grup_siralari.get(dergi.get("grup", "Diğer"), 99),
            "yazarlar": yazar_metni,
            "tarih": m.get("giris_tarihi") or m.get("yayin_tarihi") or "",
            "yayin_tarihi": m.get("yayin_tarihi", ""),
            "gun": _gun_farki(m.get("giris_tarihi") or m.get("yayin_tarihi"), bugun),
            "doi": m.get("doi", ""),
            "turler": onemli[:3],
            "yeni": yeni_mi(m, yeni_siniri),
            "ozet": {
                "kaynak": oz.get("kaynak", ""),
                "tek_cumle": oz.get("tek_cumle", ""),
                "bulgular": oz.get("bulgular", []),
                "klinik_anlam": oz.get("klinik_anlam", ""),
                "yontem": oz.get("yontem", ""),
                "guven": oz.get("guven", ""),
                "etiketler": oz.get("etiketler", []),
                "abstract_sonuc": oz.get("abstract_sonuc", ""),
            },
            "abstract": m.get("ozet_bolumleri") or [],
            "anahtar_kelimeler": (m.get("anahtar_kelimeler") or [])[:8],
        })

    # Once grup (cekirdek dergiler basta), grup icinde en yeniden eskiye
    veri.sort(key=lambda k: (k["grup_sira"], k["gun"], k["dergi"], k["baslik"]))
    return veri


def yeni_mi(makale, yeni_siniri):
    """Makale ilk kez bu pencerede mi gorulduu (YENI rozeti).

    Calistirma kimligi yerine zaman damgasi kullanilir; boylece ayni gun
    (ornegin sabah cron + sonra elle tiklama) ikinci kez calistirilinca
    rozetler kaybolmaz.
    """
    damga = makale.get("ilk_gorulme") or ""
    if not damga or yeni_siniri is None:
        return False
    try:
        return datetime.fromisoformat(damga) >= yeni_siniri
    except ValueError:
        return False


def yeni_siniri_hesapla(saat):
    return datetime.now() - timedelta(hours=max(0, float(saat or 0)))


def olustur(makaleler, dergiler, cikti_yolu, bugun=None, yeni_siniri=None, notlar=None):
    bugun = bugun or date.today()
    dergi_haritasi = {}
    for d in dergiler:
        dergi_haritasi[d["issn"]] = d
        dergi_haritasi[d["kisa"]] = d

    veri = _kart_verisi(makaleler, dergi_haritasi, bugun, yeni_siniri,
                        _grup_siralari(dergiler))

    gomulu = json.dumps({
        "makaleler": veri,
        "donemler": DONEMLER,
        "uretim": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "notlar": notlar or [],
    }, ensure_ascii=False)
    # <script> icinde guvenli olmasi icin
    gomulu = gomulu.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

    sayfa = SABLON.replace("__VERI__", gomulu).replace(
        "__TARIH__", html.escape(bugun.strftime("%d.%m.%Y")))

    klasor = os.path.dirname(os.path.abspath(cikti_yolu))
    if klasor:
        os.makedirs(klasor, exist_ok=True)
    with open(cikti_yolu, "w", encoding="utf-8") as f:
        f.write(sayfa)
    return cikti_yolu, len(veri)


SABLON = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Yayın Okuma — __TARIH__</title>
<style>
  :root{
    --arka:#f4f6f8; --kart:#ffffff; --metin:#111827; --soluk:#6b7280;
    --cizgi:#e5e7eb; --vurgu:#0f766e; --vurgu-acik:#ccfbf1; --vurgu-metin:#134e4a;
    --yeni:#b91c1c; --yeni-acik:#fee2e2; --golge:0 1px 3px rgba(0,0,0,.07);
  }
  @media (prefers-color-scheme: dark){
    :root:not([data-tema="acik"]){
      --arka:#0f1115; --kart:#181b22; --metin:#e5e7eb; --soluk:#9ca3af;
      --cizgi:#2a2f3a; --vurgu:#5eead4; --vurgu-acik:#0d3b36; --vurgu-metin:#99f6e4;
      --yeni:#fca5a5; --yeni-acik:#3f1d1d; --golge:0 1px 3px rgba(0,0,0,.4);
    }
  }
  :root[data-tema="koyu"]{
    --arka:#0f1115; --kart:#181b22; --metin:#e5e7eb; --soluk:#9ca3af;
    --cizgi:#2a2f3a; --vurgu:#5eead4; --vurgu-acik:#0d3b36; --vurgu-metin:#99f6e4;
    --yeni:#fca5a5; --yeni-acik:#3f1d1d; --golge:0 1px 3px rgba(0,0,0,.4);
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--arka);color:var(--metin);
    font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;}
  header{position:sticky;top:0;z-index:10;background:var(--kart);
    border-bottom:1px solid var(--cizgi);box-shadow:var(--golge);}
  .sarmal{max-width:1000px;margin:0 auto;padding:0 16px;}
  .ust{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;padding:14px 0 10px;}
  h1{font-size:19px;margin:0;letter-spacing:-.2px}
  .ust .bilgi{color:var(--soluk);font-size:13px}
  .ust .sag{margin-left:auto;display:flex;gap:8px;align-items:center}
  .sekmeler{display:flex;gap:6px;overflow-x:auto;padding-bottom:10px}
  .sekme{border:1px solid var(--cizgi);background:transparent;color:var(--metin);
    padding:7px 14px;border-radius:999px;cursor:pointer;font-size:14px;white-space:nowrap;
    font-family:inherit;}
  .sekme:hover{border-color:var(--vurgu)}
  .sekme[aria-selected="true"]{background:var(--vurgu);border-color:var(--vurgu);color:var(--arka);font-weight:600}
  .sekme .sayi{opacity:.75;font-size:12px;margin-left:5px}
  .araclar{display:flex;gap:8px;flex-wrap:wrap;padding:0 0 12px}
  input[type="search"],select{font:inherit;padding:8px 11px;border:1px solid var(--cizgi);
    border-radius:8px;background:var(--kart);color:var(--metin);}
  input[type="search"]{flex:1;min-width:190px}
  .kucuk{font-size:13px;color:var(--soluk)}
  .dugme{border:1px solid var(--cizgi);background:var(--kart);color:var(--metin);
    border-radius:8px;padding:7px 11px;cursor:pointer;font:inherit;font-size:13px}
  .dugme:hover{border-color:var(--vurgu)}
  main{max-width:1000px;margin:0 auto;padding:16px}
  .grup-basligi{font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;
    color:var(--soluk);margin:22px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--cizgi)}
  .grup-basligi:first-child{margin-top:0}
  article{background:var(--kart);border:1px solid var(--cizgi);border-radius:12px;
    padding:16px 18px;margin-bottom:12px;box-shadow:var(--golge)}
  article.okundu{opacity:.55}
  .ust-satir{display:flex;gap:10px;align-items:flex-start}
  .ust-satir .govde{flex:1;min-width:0}
  h2{font-size:16.5px;line-height:1.45;margin:0 0 6px;font-weight:650}
  h2 a{color:inherit;text-decoration:none}
  h2 a:hover{text-decoration:underline;text-decoration-color:var(--vurgu)}
  .kunye{font-size:12.5px;color:var(--soluk);margin-bottom:10px}
  .kunye b{color:var(--metin);font-weight:600}
  .rozetler{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
  .rozet{font-size:11px;font-weight:600;padding:2.5px 8px;border-radius:999px;
    border:1px solid var(--cizgi);color:var(--soluk);white-space:nowrap}
  .rozet.yeni{background:var(--yeni-acik);color:var(--yeni);border-color:transparent}
  .rozet.guven-yuksek{background:var(--vurgu-acik);color:var(--vurgu-metin);border-color:transparent}
  .ozet{border-left:3px solid var(--vurgu);padding-left:13px;margin:10px 0 12px}
  .tek-cumle{font-weight:600;margin:0 0 8px}
  .ozet ul{margin:0 0 8px;padding-left:19px}
  .ozet li{margin-bottom:4px}
  .klinik{background:var(--vurgu-acik);color:var(--vurgu-metin);border-radius:8px;
    padding:9px 12px;font-size:14px;margin-top:8px}
  .klinik b{font-weight:700}
  .yontem{font-size:13px;color:var(--soluk);margin:0 0 8px;font-style:italic}
  details{margin-top:10px;border-top:1px dashed var(--cizgi);padding-top:9px}
  summary{cursor:pointer;font-size:13px;color:var(--soluk);font-weight:600;user-select:none}
  summary:hover{color:var(--vurgu)}
  .abs-bolum{margin:9px 0}
  .abs-bolum h4{margin:0 0 2px;font-size:12px;text-transform:uppercase;
    letter-spacing:.4px;color:var(--soluk)}
  .abs-bolum p{margin:0;font-size:14px}
  .alt{display:flex;gap:14px;flex-wrap:wrap;margin-top:11px;font-size:13px;align-items:center}
  .alt a{color:var(--vurgu);text-decoration:none;font-weight:600}
  .alt a:hover{text-decoration:underline}
  .okundu-kutu{margin-left:auto;font-size:12.5px;color:var(--soluk);
    display:flex;gap:5px;align-items:center;cursor:pointer;user-select:none}
  .bos{text-align:center;color:var(--soluk);padding:60px 20px}
  .bos .buyuk{font-size:17px;color:var(--metin);margin-bottom:6px}
  .not{background:var(--kart);border:1px solid var(--cizgi);border-left:3px solid var(--yeni);
    border-radius:8px;padding:10px 14px;margin-bottom:14px;font-size:13px;color:var(--soluk)}
  @media print{
    header{position:static;box-shadow:none}
    .sekmeler,.araclar,.okundu-kutu,.ust .sag{display:none}
    article{break-inside:avoid;box-shadow:none}
    details{display:none}
  }
  @media (max-width:640px){
    .sarmal,main{padding-left:16px;padding-right:16px}
    h1{font-size:17px}
  }
</style>
</head>
<body>
<header>
  <div class="sarmal">
    <div class="ust">
      <h1>Yayın Okuma</h1>
      <span class="bilgi" id="ustBilgi"></span>
      <span class="sag">
        <button class="dugme" id="temaDugmesi" type="button">Koyu / Açık</button>
      </span>
    </div>
    <div class="sekmeler" id="sekmeler" role="tablist"></div>
    <div class="araclar">
      <input type="search" id="arama" placeholder="Başlık, özet, yazar, dergi veya anahtar kelimede ara…">
      <select id="dergiSecimi"><option value="">Tüm dergiler</option></select>
      <select id="turSecimi">
        <option value="">Tüm yayın türleri</option>
        <option value="__kanit">Yalnızca RKÇ / meta-analiz / derleme</option>
        <option value="Randomized Controlled Trial">Randomize kontrollü çalışma</option>
        <option value="Meta-Analysis">Meta-analiz</option>
        <option value="Systematic Review">Sistematik derleme</option>
        <option value="Review">Derleme</option>
        <option value="Guideline">Kılavuz</option>
      </select>
      <button class="dugme" id="okunanGizle" type="button">Okunanları gizle</button>
    </div>
  </div>
</header>

<main id="liste"></main>

<script id="veri" type="application/json">__VERI__</script>
<script>
(function(){
  "use strict";
  var VERI = JSON.parse(document.getElementById("veri").textContent);
  var MAKALELER = VERI.makaleler;
  var DONEMLER = VERI.donemler;

  var liste = document.getElementById("liste");
  var sekmeler = document.getElementById("sekmeler");
  var arama = document.getElementById("arama");
  var dergiSecimi = document.getElementById("dergiSecimi");
  var turSecimi = document.getElementById("turSecimi");
  var okunanGizleDugmesi = document.getElementById("okunanGizle");

  var aktifDonem = DONEMLER[0].anahtar;
  var okunanlarGizli = false;

  // --- yerel hafiza (okundu isaretleri, tema) -------------------------------
  function oku(anahtar, varsayilan){
    try{ var d = localStorage.getItem(anahtar); return d === null ? varsayilan : JSON.parse(d); }
    catch(e){ return varsayilan; }
  }
  function yaz(anahtar, deger){
    try{ localStorage.setItem(anahtar, JSON.stringify(deger)); }catch(e){}
  }
  var okunanlar = oku("yayinOkuma.okunanlar", {}) || {};

  // --- tema ----------------------------------------------------------------
  var tema = oku("yayinOkuma.tema", "");
  if(tema){ document.documentElement.setAttribute("data-tema", tema); }
  document.getElementById("temaDugmesi").addEventListener("click", function(){
    var simdi = document.documentElement.getAttribute("data-tema");
    var koyuMu = simdi ? simdi === "koyu"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
    var yeni = koyuMu ? "acik" : "koyu";
    document.documentElement.setAttribute("data-tema", yeni);
    yaz("yayinOkuma.tema", yeni);
  });

  // --- yardimcilar ---------------------------------------------------------
  function kacar(s){
    return String(s == null ? "" : s)
      .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
      .replace(/"/g,"&quot;");
  }
  function tarihYaz(iso){
    if(!iso) return "";
    var p = iso.split("-");
    return p.length === 3 ? p[2]+"."+p[1]+"."+p[0] : iso;
  }
  function gunEtiketi(g){
    if(g === 0) return "bugün";
    if(g === 1) return "dün";
    if(g < 7) return g + " gün önce";
    if(g < 30) return Math.round(g/7) + " hafta önce";
    return Math.round(g/30) + " ay önce";
  }
  var KANIT = ["Randomized Controlled Trial","Meta-Analysis","Systematic Review",
               "Review","Guideline","Practice Guideline"];

  function aranabilir(m){
    if(m.__ara) return m.__ara;
    var o = m.ozet;
    m.__ara = [m.baslik, m.dergi, m.yazarlar, o.tek_cumle, o.klinik_anlam, o.yontem,
               (o.bulgular||[]).join(" "), (o.etiketler||[]).join(" "),
               o.abstract_sonuc, (m.anahtar_kelimeler||[]).join(" "),
               (m.abstract||[]).map(function(b){return b[1];}).join(" ")]
              .join(" ").toLocaleLowerCase("tr");
    return m.__ara;
  }

  // --- suzme ---------------------------------------------------------------
  function donemSiniri(anahtar){
    for(var i=0;i<DONEMLER.length;i++){ if(DONEMLER[i].anahtar === anahtar) return DONEMLER[i].gun; }
    return 92;
  }
  function donemdekiler(anahtar){
    var sinir = donemSiniri(anahtar);
    return MAKALELER.filter(function(m){ return m.gun <= sinir; });
  }
  function suzulmus(){
    var q = arama.value.trim().toLocaleLowerCase("tr");
    var dergi = dergiSecimi.value;
    var tur = turSecimi.value;
    return donemdekiler(aktifDonem).filter(function(m){
      if(dergi && m.dergi !== dergi) return false;
      if(tur === "__kanit"){
        if(!m.turler.some(function(t){ return KANIT.indexOf(t) !== -1; })) return false;
      } else if(tur && m.turler.indexOf(tur) === -1) return false;
      if(okunanlarGizli && okunanlar[m.pmid]) return false;
      if(q && aranabilir(m).indexOf(q) === -1) return false;
      return true;
    });
  }

  // --- cizim ---------------------------------------------------------------
  function ozetHtml(m){
    var o = m.ozet, p = [];
    if(o.kaynak === "yapay-zeka"){
      if(o.tek_cumle) p.push('<p class="tek-cumle">'+kacar(o.tek_cumle)+'</p>');
      if(o.yontem) p.push('<p class="yontem">'+kacar(o.yontem)+'</p>');
      if(o.bulgular && o.bulgular.length){
        p.push('<ul>'+o.bulgular.map(function(b){return '<li>'+kacar(b)+'</li>';}).join('')+'</ul>');
      }
      if(o.klinik_anlam){
        p.push('<div class="klinik"><b>Klinik karşılığı:</b> '+kacar(o.klinik_anlam)+'</div>');
      }
    } else if(o.abstract_sonuc){
      p.push('<p class="yontem">Makalenin kendi sonuç bölümünden:</p>');
      p.push('<p class="tek-cumle">'+kacar(o.abstract_sonuc)+'</p>');
    } else {
      p.push('<p class="yontem">Bu kayıt için özet (abstract) yayımlanmamış.</p>');
    }
    return p.length ? '<div class="ozet">'+p.join('')+'</div>' : '';
  }

  function rozetlerHtml(m){
    var r = [];
    if(m.yeni) r.push('<span class="rozet yeni">YENİ</span>');
    m.turler.forEach(function(t){ r.push('<span class="rozet">'+kacar(t)+'</span>'); });
    (m.ozet.etiketler||[]).forEach(function(e){ r.push('<span class="rozet">'+kacar(e)+'</span>'); });
    if(m.ozet.guven === "yuksek") r.push('<span class="rozet guven-yuksek">güçlü kanıt</span>');
    return r.length ? '<div class="rozetler">'+r.join('')+'</div>' : '';
  }

  function abstractHtml(m){
    if(!m.abstract || !m.abstract.length) return '';
    var govde = m.abstract.map(function(b){
      var baslik = b[0] ? '<h4>'+kacar(b[0])+'</h4>' : '';
      return '<div class="abs-bolum">'+baslik+'<p>'+kacar(b[1])+'</p></div>';
    }).join('');
    return '<details><summary>Özgün abstract (İngilizce)</summary>'+govde+'</details>';
  }

  function kartHtml(m){
    var pubmed = "https://pubmed.ncbi.nlm.nih.gov/"+encodeURIComponent(m.pmid)+"/";
    var baglantilar = ['<a href="'+pubmed+'" target="_blank" rel="noopener">PubMed</a>'];
    if(m.doi){
      baglantilar.push('<a href="https://doi.org/'+encodeURIComponent(m.doi)+
                       '" target="_blank" rel="noopener">Tam metin (DOI)</a>');
    }
    var kunye = '<b>'+kacar(m.dergi)+'</b>';
    if(m.yazarlar) kunye += ' · '+kacar(m.yazarlar);
    kunye += ' · '+tarihYaz(m.tarih)+' ('+gunEtiketi(m.gun)+')';

    return '<article id="m'+kacar(m.pmid)+'"'+(okunanlar[m.pmid]?' class="okundu"':'')+'>'
      + '<h2><a href="'+pubmed+'" target="_blank" rel="noopener">'+kacar(m.baslik)+'</a></h2>'
      + '<div class="kunye">'+kunye+'</div>'
      + rozetlerHtml(m)
      + ozetHtml(m)
      + abstractHtml(m)
      + '<div class="alt">'+baglantilar.join('')
      + '<label class="okundu-kutu"><input type="checkbox" data-pmid="'+kacar(m.pmid)+'"'
      + (okunanlar[m.pmid]?' checked':'')+'> okundu</label></div>'
      + '</article>';
  }

  function ciz(){
    var kayitlar = suzulmus();
    if(!kayitlar.length){
      var sinir = donemSiniri(aktifDonem);
      liste.innerHTML = '<div class="bos"><div class="buyuk">Bu seçimde makale yok.</div>'
        + (sinir === 0
            ? 'Bugün henüz yeni kayıt düşmemiş olabilir — “Bu hafta” sekmesine bakın.'
            : 'Arama ya da filtreleri gevşetmeyi deneyin.')
        + '</div>';
      return;
    }
    var parcalar = [];
    (VERI.notlar||[]).forEach(function(n){
      parcalar.push('<div class="not">'+kacar(n)+'</div>');
    });
    var suankiGrup = null;
    kayitlar.forEach(function(m){
      if(m.grup !== suankiGrup){
        suankiGrup = m.grup;
        parcalar.push('<div class="grup-basligi">'+kacar(suankiGrup)+'</div>');
      }
      parcalar.push(kartHtml(m));
    });
    liste.innerHTML = parcalar.join('');
  }

  function sekmeleriCiz(){
    sekmeler.innerHTML = DONEMLER.map(function(d){
      var n = donemdekiler(d.anahtar).length;
      return '<button class="sekme" role="tab" type="button" data-donem="'+d.anahtar+'"'
        + ' aria-selected="'+(d.anahtar === aktifDonem)+'">'+kacar(d.ad)
        + '<span class="sayi">'+n+'</span></button>';
    }).join('');
  }

  // --- olaylar -------------------------------------------------------------
  sekmeler.addEventListener("click", function(e){
    var d = e.target.closest("[data-donem]");
    if(!d) return;
    aktifDonem = d.getAttribute("data-donem");
    sekmeleriCiz(); ciz();
    window.scrollTo({top:0, behavior:"smooth"});
  });

  liste.addEventListener("change", function(e){
    var kutu = e.target;
    if(!kutu.matches("input[data-pmid]")) return;
    var pmid = kutu.getAttribute("data-pmid");
    if(kutu.checked){ okunanlar[pmid] = 1; } else { delete okunanlar[pmid]; }
    yaz("yayinOkuma.okunanlar", okunanlar);
    var kart = kutu.closest("article");
    if(kart) kart.classList.toggle("okundu", kutu.checked);
    if(okunanlarGizli && kutu.checked) ciz();
  });

  var zamanlayici;
  arama.addEventListener("input", function(){
    clearTimeout(zamanlayici); zamanlayici = setTimeout(ciz, 140);
  });
  dergiSecimi.addEventListener("change", ciz);
  turSecimi.addEventListener("change", ciz);
  okunanGizleDugmesi.addEventListener("click", function(){
    okunanlarGizli = !okunanlarGizli;
    okunanGizleDugmesi.textContent = okunanlarGizli ? "Okunanları göster" : "Okunanları gizle";
    ciz();
  });

  // --- ilk yukleme ---------------------------------------------------------
  (function hazirla(){
    var dergiler = {};
    MAKALELER.forEach(function(m){ dergiler[m.dergi] = (dergiler[m.dergi]||0)+1; });
    Object.keys(dergiler).sort(function(a,b){ return a.localeCompare(b,"tr"); })
      .forEach(function(ad){
        var o = document.createElement("option");
        o.value = ad; o.textContent = ad+" ("+dergiler[ad]+")";
        dergiSecimi.appendChild(o);
      });

    var yeniSayisi = MAKALELER.filter(function(m){ return m.yeni; }).length;
    document.getElementById("ustBilgi").textContent =
      VERI.uretim + " · " + MAKALELER.length + " makale"
      + (yeniSayisi ? " · " + yeniSayisi + " yeni" : "");

    // Bugun bos ise dogrudan "Bu hafta" ile ac
    if(!donemdekiler(aktifDonem).length){
      for(var i=1;i<DONEMLER.length;i++){
        if(donemdekiler(DONEMLER[i].anahtar).length){ aktifDonem = DONEMLER[i].anahtar; break; }
      }
    }
    sekmeleriCiz(); ciz();
  })();
})();
</script>
</body>
</html>
"""
