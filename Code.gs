/**
 * Mehmet Nar - Kayıt Formu (Google Apps Script)
 *
 * Bu dosya web uygulamasının SUNUCU tarafıdır.
 * Veriler, bu script'in bağlı olduğu Google E-Tablo'daki "Kayitlar" sekmesine yazılır.
 *
 * ÖNEMLİ: "Kaydet" sorunu genelde fetch() + "Sadece ben" erişiminden olur.
 * Burada google.script.run kullanıldığı için o sorun yaşanmaz.
 */

// Verilerin yazılacağı sekme adı
const SHEET_NAME = 'Kayitlar';

// Sütun başlıkları (formdaki alanlarla aynı sırada olmalı)
const HEADERS = ['Tarih', 'Ad Soyad', 'Telefon', 'Ürün', 'Adet', 'Tutar (TL)', 'Açıklama'];

/**
 * Web uygulaması açıldığında çalışır ve formu (index.html) gösterir.
 */
function doGet() {
  return HtmlService.createHtmlOutputFromFile('index')
    .setTitle('Mehmet Nar - Kayıt Formu')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/**
 * Verilerin yazılacağı sayfayı döndürür; yoksa oluşturur ve başlıkları ekler.
 */
function getSheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  if (!ss) {
    throw new Error(
      'Bu script bir Google E-Tablo\'ya bağlı değil. ' +
      'Script\'i bir E-Tablo\'dan açın (Uzantılar > Apps Script) ya da ' +
      'aşağıdaki SPREADSHEET_ID yöntemini kullanın.'
    );
  }
  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
  }
  // Başlık satırı yoksa ekle
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(HEADERS);
    sheet.getRange(1, 1, 1, HEADERS.length).setFontWeight('bold');
    sheet.setFrozenRows(1);
  }
  return sheet;
}

/**
 * Formdan gelen veriyi E-Tablo'ya kaydeder.
 * HTML tarafında: google.script.run.kaydet(data)
 *
 * @param {Object} data - { ad, telefon, urun, adet, tutar, aciklama }
 * @return {Object} { ok: true } veya hata fırlatır
 */
function kaydet(data) {
  try {
    if (!data || !data.ad) {
      throw new Error('Ad Soyad alanı boş olamaz.');
    }
    const sheet = getSheet_();
    const satir = [
      new Date(),                 // Tarih (otomatik)
      String(data.ad || '').trim(),
      String(data.telefon || '').trim(),
      String(data.urun || '').trim(),
      data.adet ? Number(data.adet) : '',
      data.tutar ? Number(data.tutar) : '',
      String(data.aciklama || '').trim()
    ];
    sheet.appendRow(satir);
    return { ok: true, mesaj: 'Kayıt başarıyla eklendi.' };
  } catch (err) {
    // Hatayı HTML tarafındaki withFailureHandler yakalasın diye yeniden fırlat
    throw new Error('Kaydedilemedi: ' + err.message);
  }
}

/**
 * (İsteğe bağlı) Bağlantıyı test etmek için kullanılabilir.
 */
function testKaydet() {
  return kaydet({
    ad: 'Test Kullanıcı',
    telefon: '0555 000 0000',
    urun: 'Nar',
    adet: 10,
    tutar: 250,
    aciklama: 'Deneme kaydı'
  });
}
