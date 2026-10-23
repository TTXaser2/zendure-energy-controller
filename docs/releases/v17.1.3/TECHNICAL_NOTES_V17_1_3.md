**Stand 22.10.2026:** Änderungen gegen V17.1.2; echte Realfeldabnahme erst nach Installation.

# Technische Änderungen V17.1.3

- **Geschützter Regler:** `controller_logic.py` SHA256 `8bf439456e773aa84097e54059b3da1065deac5200d9304c0dc5960a5e24b1d7`, byteidentisch.
- **Settings:** 190 operative Felder und 74 Bereichserklärungen; ausschließlich Hilfe-/Darstellungsebene, ohne neuerdings angebundene Config-Consumer. `MAX_POWER_STEP_W` beschränkt normale Basis **pro Zyklus nach Smoothing**. A400/R100 sind Overlay-Raten **pro Sekunde**; physische und Sicherheitslimits sind höherrangig.
- **Minigraph:** Die V17.1.2-Zeitsemantik bleibt erhalten: 60-Minuten-Zeitserie in Minutenfenstern, 5-/15-Minuten-Rohwerte und echte Messlücken. Neu sind die kompakte Beschriftung „Minigraph-Update 3 s · Livewert 1 s“, „Aktuellster Wert“ an der Achse und die höhenneutrale Anordnung ohne Verkleinerung des Diagramms.
- **Responsive:** Die Netzleistungskarte bewahrt die vollständigen Quellen-/Frischeangaben und die originale 103-px-Minigraph-Höhe. In der Standardansicht liegen die oberen Karten bei 1280/1769 px wieder bei 300 px; kein starres Abschneiden. In sehr schmalen Ansichten oder bei zusätzlichen Expertendetails kann die Höhe bedarfsgerecht wachsen.
- **Installer:** unterstützter Upgrade-Pfad V17.1.2 → V17.1.3; Fresh Install ausschließlich explizit; SHA256 separat nach Paketabschluss veröffentlicht.
- **Archive:** historisches Material ist versionsgetrennte Provenienz, nicht aktuelle Freigabe- oder Reglerautorität.

Verpflichtende Gates: reguläre und strenge Tests, Browser-/Mobil-/Accessibility-/Pi-Performancebudgets, syntaktische Checks, Manifest/CRC, Update- und Fresh-Install-Simulationen, Fresh-extract, Datenblatt und No-Drop.
