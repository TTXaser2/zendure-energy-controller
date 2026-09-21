# ZEC V16.2.1 – Technical Notes

## Gemeinsamer Speicherstatuskarten-Vertrag

Zendure und Primärspeicher verwenden in der Standardansicht dieselbe fachliche Reihenfolge: SOC, signierte Istleistung, Zustand, relevante SOC-Grenze, verbleibender SOC-Abstand und richtungsabhängiger Leistungsbalken. Gleichartige Informationen erhalten damit dieselben Bezeichnungen und Positionen.

Die Istleistung bleibt als große signierte Zahl rechts oben sichtbar. Eine zusätzliche ausgeschriebene Richtungsangabe wird dort bewusst nicht verwendet. Der Leistungsbalken verstärkt die Richtung visuell:

- Laden: grün, Füllrichtung links → rechts;
- Entladen: orange/amber, Füllrichtung rechts → links.

Der Balkentext verwendet konkrete Leistung und Maximalleistung (z. B. `400 W / 2,30 kW max`) statt einer weiteren Prozentangabe.

## Restenergie-Semantik

Die Standardkarte zeigt keine auf den freigegebenen SOC-Korridor normalisierte Prozentzahl mehr. Stattdessen gilt:

- Entladen: `Noch entladbar = aktueller SOC - Entladegrenze`;
- Laden: `Noch ladbar = Ladegrenze - aktueller SOC`.

Der Prozentwert ist damit ein unmittelbar verständlicher Abstand in SOC-Prozentpunkten. Ist eine belastbare Kapazität verfügbar, wird zusätzlich die entsprechende Restenergie in kWh angezeigt. Für Primärspeicher-Kapazität hat ein realer/source-seitiger Wert Vorrang vor dem optionalen manuellen Fallback. Fehlt die Kapazität, bleibt die Prozentpunkt-Angabe sichtbar und nur die kWh-Angabe entfällt.

Beim SMA Sunny Island bleibt die frische und gültige read-only Capability `current_discharge_floor_soc` die untere Entladegrenze. Der intern/API-/Measurement-seitig vorhandene normalisierte usable SOC bleibt für Diagnose und den späteren Block B erhalten, wird aber nicht mehr als konkurrierender Prozentwert in der Standardkarte dargestellt.

## Primärspeicher-Expertendetails

Harmonisierung und Harvest-Rechnung bleiben fachlich erhalten, werden jedoch nicht mehr als permanente Standardkartenzeilen gerendert. Im Expertenkontext der Primärspeicherkarte bleiben diese Details zusammen mit Quellenstatus und normalisiertem usable SOC zugänglich. Dies ist eine lokale Entlastung der Karte und **keine** vollständige Umsetzung des offenen `ZEC-BL-UI-STATUS-EXPERT-001`.

## Primärspeicher-Maximalleistung

`SECOND_BATTERY_MAX_DISCHARGE_POWER_W` ist analog zur maximalen Ladeleistung der optionale manuelle Maximalwert für die Entlade-Skala. Der Wert besitzt ausschließlich Status-/Diagnosewirkung. Die spätere automatische Ermittlung technischer Gerätemetadaten bleibt unter `ZEC-BL-PRIMARY-METADATA-001` separat spezifikationsbedürftig.

## No-Regression

`controller_logic.py` bleibt byteidentisch zu V16.2.0 mit SHA256 `d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`. V16.2.1 verändert weder Regelstrategie noch Command-/Safety-/Recoverysemantik.
