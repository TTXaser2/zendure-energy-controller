# Technische Änderungen V17.1.2

- **Geschützter Regler:** `controller_logic.py` SHA256 `8bf439456e773aa84097e54059b3da1065deac5200d9304c0dc5960a5e24b1d7`, byteidentisch.
- **Settings:** 190 operative Felder und 74 Bereichserklärungen; ausschließlich Hilfe-/Darstellungsebene, ohne neuerdings angebundene Config-Consumer. `MAX_POWER_STEP_W` beschränkt normale Basis **pro Zyklus nach Smoothing**. A400/R100 sind Overlay-Raten **pro Sekunde**; physische und Sicherheitslimits sind höherrangig.
- **Graph:** 60-Minuten-Zeitserie in Minutenfenstern; read-only Provenienz, echte Rohsamples und begrenzte historische Daten; ohne neue Abtastrate, ohne erfundene Werte. 5/15 bleiben Einzelmessungen.
- **Responsive:** Netzleistungs-Statuskarte wächst mit ihrem Anbieter-/Frischefooter, statt dessen vertikal abzuschneiden.
- **Installer:** unterstützter Upgrade-Pfad V17.1.1 → V17.1.2; Fresh Install ausschließlich explizit; SHA256 separat nach Paketabschluss veröffentlicht.
- **Archive:** historisches Material ist versionsgetrennte Provenienz, nicht aktuelle Freigabe- oder Reglerautorität.

Verpflichtende Gates: reguläre und strenge Tests, Browser-/Mobil-/Accessibility-/Pi-Performancebudgets, syntaktische Checks, Manifest/CRC, Update- und Fresh-Install-Simulationen, Fresh-extract, Datenblatt und No-Drop.
