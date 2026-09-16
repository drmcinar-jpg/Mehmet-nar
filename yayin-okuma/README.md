# Yayın Okuma

Seçili 21 dergide **PubMed'e yeni düşen makaleleri** toplar, her birini **Türkçe
özetler** ve tek bir HTML raporu olarak tarayıcıda açar.

Sabah dosyaya çift tıklarsınız; rapor açılır. Raporun üstündeki
**Bugün · Bu hafta · Bu ay · Son 3 ay** sekmeleri anında süzer — sekme
değiştirmek için yeniden bekleme yok.

---

## Kurulum

Ek kütüphane gerekmez; yalnızca **Python 3.8+** yeterli.

macOS'ta Python 3 kurulu değilse Terminal'de:

```
xcode-select --install
```

## Çalıştırma

| İşletim sistemi | Yapılacak |
|---|---|
| macOS | **`Yayin-Okuma.command`** dosyasına çift tıklayın |
| Windows | **`Yayin-Okuma.bat`** dosyasına çift tıklayın |
| Terminal | `python3 calistir.py` |

> macOS ilk açılışta "geliştirici doğrulanamadı" derse: dosyaya **sağ tık →
> Aç → Aç**. Bir kez yapmanız yeterli.

### Komut satırı seçenekleri

```
python3 calistir.py               # son 3 ayı tazele, raporu aç
python3 calistir.py --gun 30      # sadece son 30 günü çek (daha hızlı)
python3 calistir.py --ozetsiz     # yapay zeka özeti üretme (ücretsiz/hızlı)
python3 calistir.py --acma        # raporu üret ama tarayıcıda açma
python3 calistir.py --sifirla     # önbelleği yok say, her şeyi yeniden çek
```

---

## Türkçe özetler

Her makale için üretilen özet şunları içerir:

- **Tek cümlelik ana bulgu**
- **Yöntem** (tasarım + örneklem)
- **2-4 madde hâlinde bulgular** — sayısal sonuçlarla (OR, RR, %, p, n)
- **Klinik karşılığı** — tüp bebek/kadın doğum pratiğinde ne değişir
- Konu etiketleri ve kanıt düzeyi rozeti

Bunun için bir **Anthropic API anahtarı** gerekir. `ayarlar.json` dosyasını
açıp şu satırı doldurun:

```json
"anthropic_api_key": "sk-ant-...",
```

Anahtar https://console.anthropic.com/settings/keys adresinden alınır
(kullandığın kadar öde). `ANTHROPIC_API_KEY` ortam değişkenini de okur.

**Anahtar yoksa program yine çalışır:** o zaman özet yerine makalenin kendi
sonuç bölümü (İngilizce) gösterilir — internetten başka bir ücret çıkmaz.
Human Reproduction'ın `SUMMARY ANSWER` / `WIDER IMPLICATIONS`, Lancet'in
`INTERPRETATION` gibi farklı başlıkları da tanınır.

### Maliyet kontrolü

- Üretilen her özet diske kaydedilir; **aynı makale iki kez özetlenmez.**
- `calistirma_basina_azami_ozet` (varsayılan 80) tek çalıştırmadaki özet
  sayısını sınırlar; aşanlar için abstract sonucu kullanılır.
- İlk çalıştırma 3 aylık arşivi tarar ve uzun sürer. Sonraki günlerde yalnızca
  **yeni** makaleler indirilip özetlenir — birkaç saniye.

---

## Takip edilen dergiler

**Çekirdek üreme tıbbı** — bu dergilerin *tüm* yayınları listelenir:

Human Reproduction Update · Human Reproduction · Fertility and Sterility ·
Reproductive BioMedicine Online · J. Assisted Reproduction and Genetics ·
Reproductive Biology and Endocrinology · Molecular Human Reproduction ·
Reproduction (SRF) · F&S Reports · F&S Science

**Genel jinekoloji** — AJOG · Obstetrics & Gynecology (Green Journal) ·
Ultrasound in Obstetrics & Gynecology · BJOG

**Endokrinoloji** — Endocrine Reviews · Nature Reviews Endocrinology · JCEM

**Genel tıp** — NEJM · The Lancet · BMJ · JAMA

Son üç gruptaki dergiler çok geniş olduğu için **yalnızca üreme/infertilite
konulu** yayınları alınır (infertilite, IVF/ICSI, PGT, over rezervi, PKOS,
endometriozis, tekrarlayan gebelik kaybı, fertilite koruma, POY vb. — tam
liste `yayin_okuma/dergiler.py` içindeki `KONU_FILTRESI`).

### Dergi eklemek / çıkarmak

`yayin_okuma/dergiler.py` dosyasındaki `DERGILER` listesine satır ekleyin.
Dergiler **ISSN** ile aranır (kısaltmadan daha güvenilir); ISSN'i PubMed'de
derginin herhangi bir makalesinde görebilirsiniz.

```python
{"issn": "1234-5678", "ad": "Dergi Adı", "kisa": "Derg Ad",
 "grup": "Çekirdek üreme tıbbı", "kapsam": "tam"},
```

`"kapsam": "tam"` → derginin her şeyi gelir.
`"kapsam": "konulu"` → sadece üreme konulu yayınları gelir.

---

## Rapordaki özellikler

- **Bugün / Bu hafta / Bu ay / Son 3 ay** sekmeleri (yanlarında makale sayısı)
- **YENİ** rozeti — bu çalıştırmada ilk kez görülen makaleler
- Başlık, özet, yazar, dergi ve anahtar kelimede **arama**
- Dergiye ve yayın türüne göre **süzme** (ör. yalnızca RKÇ / meta-analiz / derleme)
- **"okundu"** işareti — tarayıcıda kalıcıdır, okunanları gizleyebilirsiniz
- Her makalede **PubMed** ve **DOI (tam metin)** bağlantısı
- Özgün İngilizce abstract, açılır bölümde
- Koyu/açık tema, telefonda da düzgün görünüm, yazdırılabilir çıktı

Rapor tek bir dosyadır (`rapor/yayin-raporu.html`) — internet olmadan da
açılır, e-postayla gönderilebilir.

---

## Ayarlar (`ayarlar.json`)

İlk çalıştırmada kendiliğinden oluşur.

| Anahtar | Ne işe yarar |
|---|---|
| `gecmis_gun` | Kaç günlük yayın çekilsin (varsayılan 92 = 3 ay) |
| `dergi_basina_azami` | Bir dergiden çekilecek azami makale (varsayılan 400) |
| `yapay_zeka_ozet` | Türkçe özet üretilsin mi |
| `anthropic_api_key` | Türkçe özet için API anahtarı |
| `model` | Kullanılacak model (varsayılan `claude-sonnet-5`) |
| `calistirma_basina_azami_ozet` | Tek çalıştırmadaki azami özet sayısı |
| `ncbi_api_key` | İsteğe bağlı; PubMed hızını 3→10 istek/sn çıkarır ([ücretsiz](https://account.ncbi.nlm.nih.gov/settings/)) |
| `eposta` | NCBI'ın önerdiği iletişim adresi (isteğe bağlı) |
| `tarih_turu` | `edat` = PubMed'e giriş tarihi (önerilen), `pdat` = yayın tarihi |
| `raporu_otomatik_ac` | Bitince tarayıcı açılsın mı |

`ayarlar.json` API anahtarınızı içerdiği için **git'e gönderilmez**
(`.gitignore`'da). Örnek dosya: `ayarlar.ornek.json`.

---

## Her sabah kendiliğinden çalışsın (macOS)

Terminal'de `crontab -e` yazıp şu satırı ekleyin (her gün 07:30):

```
30 7 * * * cd ~/Desktop/projeler/yayın\ okuma && /usr/bin/python3 calistir.py --acma
```

Böylece siz dosyaya tıkladığınızda rapor çoktan hazır olur.

---

## Dosya düzeni

```
yayin-okuma/
├── Yayin-Okuma.command      ← macOS'ta çift tıklayın
├── Yayin-Okuma.bat          ← Windows'ta çift tıklayın
├── calistir.py              ← ana program
├── ayarlar.json             ← ayarlarınız (ilk çalıştırmada oluşur)
├── yayin_okuma/
│   ├── dergiler.py          ← dergi listesi ve konu filtresi
│   ├── pubmed.py            ← PubMed E-utilities istemcisi
│   ├── ozet.py              ← Türkçe özetleme
│   ├── rapor.py             ← HTML rapor üretimi
│   ├── onbellek.py          ← indirilenleri saklar
│   └── ayarlar.py
├── veri/makaleler.json      ← önbellek (otomatik)
└── rapor/yayin-raporu.html  ← rapor (otomatik)
```

## Sorun giderme

**"PubMed'e ulaşılamadı"** — İnternet bağlantısı yok ya da NCBI geçici olarak
yanıt vermiyor. Program 4 kez tekrar dener; biraz sonra yine deneyin.

**Bir dergide 0 makale** — O dergi o dönemde gerçekten yayın yapmamış olabilir
(örn. Endocrine Reviews yılda az sayı çıkarır). Sürekli 0 ise ISSN'i kontrol edin.

**"… sınırına ulaşıldı" uyarısı** — Raporun üstünde çıkar; `dergi_basina_azami`
değerini artırın.

**Özetler İngilizce geliyor** — `ayarlar.json` içinde `anthropic_api_key` boş
demektir; doldurun ve `--sifirla` olmadan tekrar çalıştırın (eski özetler
korunur, yenileri Türkçe üretilir).
