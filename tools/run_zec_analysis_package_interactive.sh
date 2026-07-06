#!/usr/bin/env bash
set -u

cd /opt/zendure-controller || exit 1

echo "Starte ZEC-Diagnosepaket..."
echo

if [[ -x ./tools/create_zec_analysis_package.sh ]]; then
  ./tools/create_zec_analysis_package.sh "$@"
else
  bash ./tools/create_zec_analysis_package.sh "$@"
fi

status=$?
echo
if [[ $status -eq 0 ]]; then
  echo "ZEC-Diagnosepaket fertig. Bitte den ausgegebenen ZIP-Pfad in /home/pi/Downloads verwenden."
else
  echo "ZEC-Diagnosepaket mit Fehlercode $status beendet."
fi
echo
read -r -p "Enter drücken zum Schließen..."
exit "$status"
