# Mehmet Nar — Kayıt Formu (Google Apps Script)

Basit bir web formu. Girilen veriler bağlı olduğu Google E-Tablo'daki **Kayitlar**
sekmesine kaydedilir.

## Neden eski "Kaydet" çalışmıyordu?

En sık iki neden:
1. **Yeniden dağıtılmadı (redeploy).** Apps Script, kodu değiştirince `/exec`
   linkini otomatik güncellemez. Yeni sürüm dağıtmadan eski (bozuk) kod çalışır.
2. **fetch() + "Sadece ben" erişimi.** Bu durumda Google isteği sessizce login
   sayfasına yönlendirir; kaydet'e basınca **hiçbir şey olmaz, hata da vermez.**

Bu sürüm `google.script.run` kullandığı için "Sadece ben" erişimiyle de sorunsuz
çalışır.

## Kurulum

1. https://sheets.google.com adresinde yeni bir **Google E-Tablo** oluştur.
2. E-Tabloda **Uzantılar → Apps Script** menüsüne tıkla.
3. Açılan editörde:
   - Soldaki **Code.gs** dosyasının içeriğini sil, bu repodaki `Code.gs`
     dosyasının içeriğini yapıştır.
   - **+** ile yeni dosya ekle → **HTML** seç → adını `index` koy (uzantı yazma).
     İçine bu repodaki `index.html` dosyasının içeriğini yapıştır.
   - Kaydet (💾 / Ctrl+S).

## Dağıtım (Deploy) — bu adım şart

1. Sağ üstte **Dağıt → Yeni dağıtım**.
2. Tür: **Web uygulaması**.
3. Ayarlar:
   - **Şu kişi olarak çalıştır:** Ben (kendi hesabın)
   - **Erişim:** istersen "Sadece ben", istersen "Herkes" — ikisi de çalışır.
4. **Dağıt** → izinleri onayla → çıkan `/exec` linkini aç.

## Kodu değiştirdikten sonra (ÖNEMLİ)

Her kod değişikliğinden sonra **mutlaka yeni sürüm dağıt:**

**Dağıt → Dağıtımları yönet → ✏️ (düzenle) → Sürüm: "Yeni sürüm" → Dağıt**

Aksi halde değişiklikler `/exec` linkine yansımaz.

## Test

Editörde fonksiyon listesinden `testKaydet` seçip **Çalıştır** dersen,
E-Tablo'ya bir deneme satırı eklenir. Satır geldiyse bağlantı doğru demektir.

## Alanları değiştirmek

- Sütunları değiştirmek için `Code.gs` içindeki `HEADERS` dizisini ve `kaydet`
  fonksiyonundaki `satir` dizisini güncelle.
- Form alanları için `index.html` içindeki `<input>`leri ve `data` nesnesini
  güncelle. (Her iki tarafın aynı alan adlarını kullanmasına dikkat et.)
