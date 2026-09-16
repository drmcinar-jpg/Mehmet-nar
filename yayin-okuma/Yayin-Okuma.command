#!/bin/bash
# macOS: bu dosyaya CIFT TIKLAYIN. Terminal acilir, makaleler cekilir,
# rapor tarayicida acilir.
cd "$(dirname "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
  echo
  echo "  Python 3 bulunamadi."
  echo "  Kurmak icin Terminal'e su komutu yazip Enter'a basin:"
  echo
  echo "      xcode-select --install"
  echo
  echo "  ya da https://www.python.org/downloads/ adresinden kurun."
  echo
  read -n 1 -s -r -p "Kapatmak icin bir tusa basin..."
  exit 1
fi

python3 calistir.py "$@"
durum=$?

echo
if [ $durum -ne 0 ]; then
  echo "  Program hata ile bitti. Yukaridaki mesaja bakin."
fi
read -n 1 -s -r -p "Bu pencereyi kapatmak icin bir tusa basin..."
echo
