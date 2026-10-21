# ZEC V16.0.1 – Technical Notes

## Fehlerursache

Die Paketidentitätsprüfung des V16.0.0-Installers enthielt einen Python-RegEx in einem nicht quotierten Shell-Heredoc. Die mehrstufige Backslash-/Quote-Auswertung erzeugte beim realen Installerlauf syntaktisch ungültigen Python-Code. Der Preflight brach dadurch vor der Installationsklassifikation mit `mode=UNCLASSIFIED` ab.

## Korrektur

`tools/deployment_contract.py` stellt nun die ausführbare Operation `identity` bereit. Sie verwendet den bereits gemeinsamen `read_identity()`-Parser und vergleicht die gelesene Version und Build-ID fail-closed mit der erwarteten Releaseidentität. Der Installer ruft diese Operation direkt aus `package_preflight()` auf und speichert die maschinenlesbare Prüfausgabe im temporären Stage-Verzeichnis.

Damit gibt es im Installer keinen zweiten, shell-escape-abhängigen Versionsparser mehr. Die gemeinsame Identitätsoperation besitzt Positiv- und Negativtests und wird zusätzlich durch einen Integrationstest im Installertext abgesichert.

## No-Regression

Der Hotfix verändert weder den Live-Regelalgorithmus noch Konfiguration, Migration, Graph Core, Measurement, Command-Lifecycle oder Hardware-Schonung. `controller_logic.py` bleibt byteidentisch zum kanonischen V16.0.0-Original.
