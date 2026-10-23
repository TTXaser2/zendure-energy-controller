**Build-QA-Stand 22.10.2026:** Der Code- und Dokumentationsstand besitzt eigene V17.1.3-Regression; das finale Paket wird getrennt verifiziert.

# ZEC V17.1.3 – Releaseüberblick

**Releaseidentität:** `V17.1.3 / 17.1.3 / v17.1.3-20261022`. **Dokumentenstatus:** Release-Freeze-Vorbereitung; der finale technische Status steht im separat verifizierten Releasebericht. V17.1.3 ist auf dem Pi noch nicht feldabgenommen.

V17.1.3 ist ein korrigierender Releasepfad auf dem unveränderten V17.1.2-Regler. Produktzweck: erneute sprachliche und fachliche Härtung der 190 operativen Settings-Hilfen, 74 Bereichserklärungen und dynamischen Metahinweise; kompakte Statusseite mit unverändertem 103-px-Minigraphen; Dokumentations-, Installer- und UML-Atlas-Integration. Die bereits vorhandene V17.1.2-Zeitsemantik der 5-/15-/60-Minuten-Kurven und deren Datenlücken bleibt erhalten.

**Nicht im Scope:** Controller-Strategie, Fast-Capture-Rate, Zendure-Command, Safety, Hardwareschonung und andere neue Regelmodule. Vorherige natürliche Feldlücken bleiben offen.

**Installation:** `README_INSTALLATION_V17_1_3.md`, wobei nur das Installer-ZIP auf den Pi übertragen wird und die finale SHA256 direkt im externen Installationsbefehl steht, nach technischem Paketfreeze. Der reguläre Installer führt vollen Preflight vor Mutation aus. Kein realer Clean-Fresh-Reset des Produktiv-Pi.


**Dokumentation:** Der neue quellgeprüfte UML-Regleratlas ist als DOT/SVG/PNG unter `docs/architecture/uml/` integriert, einschließlich `SOURCE_REVIEW_V17_1_3.md`, Traceability und `DOC_UML_RELEASE_GATE`. Der geschützte Reglerkern ist unverändert.
