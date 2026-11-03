# V18.0.1 – Korrekturrelease (technischer Releasekandidat)

Stand: 02.11.2026. Quelle: unveränderte installierte V18.0.0 / v18.0.0-20261027.

Scope: Night-/Care-Reserve SAFE_STATE-Recovery; Settings-Model-API-Validierung und Retry; TT.MM.-Saison-UI bei unverändertem MM-DD-Backend; rein angezeigte Primärspeicher-SOC-Obergrenze; Shield-Status und vorhandener Info-Dialog; Reserve-Journal mit unabhängiger gemessener Wirkung; Nachtreserve-Label; separater 7D-Analyzer mit V4-Fallback und begrenzter zeitbezogener Dateiauswahl.

PV-Care-Arbitration unverändert, weil bisherige Differentialtests keinen bestätigten PV-Defekt belegen. Kein neuer Hardware- oder Netzladetest.

**Releasegrenze:** Der technische Installer-ZIP gilt erst nach dem gesonderten finalen Fresh-Extract-/Manifest-/QA-/Library-Gate als freigegeben. Aktuell vorhandener Sourcekandidat und Produktiv-Pi sind unterschiedliche Autoritäten; N/E-Feldwirkung bleibt offen.

## CP14 Quell-/Backlog-/As-built-Reconciliation

Kanonische Projektquellen 00–07 auf den aktuellen 02.11.-CP02-Nachanalysestand aktualisiert, ohne eine historische ID oder einen Open-Point zu löschen. Das reale Release-Snapshot `docs/ZEC_Master_Backlog.md` ist byteidentisch zur releaseeigenen Master-Quelle `05`. Die sechs Pflicht-UX-Fixes plus SAFE_STATE-Korrektur sind source-seitig vollständig; die Feldwirksamkeit ist separat. Produktiv V18.0.0 bleibt unverändert.
