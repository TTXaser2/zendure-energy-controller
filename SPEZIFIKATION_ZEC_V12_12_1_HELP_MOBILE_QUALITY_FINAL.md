# Spezifikation – ZEC V12.12.1 Help & Mobile Quality Fix

**Status:** umgesetzt / Release-Abnahme  
**Basis:** V12.12.0 (`v12.12.0-20260809`)  
**Ziel:** V12.12.1 (`v12.12.1-20260810`)

## 1. Scope

V12.12.1 korrigiert ausschließlich die Help-/Settings-/Status-Darstellung und die dazugehörige Dokumentation. Live-Regelalgorithmus, Command-Lifecycle, Cross-Charge und Measurement V4 bleiben unverändert.

## 2. Verbindliche Anforderungen

1. Alle 62 RICH-Settings erhalten konkrete Wirksamkeitsbedingungen sowie konkrete Risiko-/Sicherheitsinformationen; generische Kern-Fallbacks gelten nicht als ausreichende RICH-Hilfe.
2. Benutzertexte verwenden verständliche deutsche Terminologie. Unvermeidbare Fachbegriffe werden im Kontext erklärt. Das Handbuch erhält ein Glossar.
3. Jedes neue Setting-/Kategorie-/Abschnitts-Help-Modal beginnt bei Scrollposition 0. Das gilt auch für `Warum?` und Expert-Gate-Navigation.
4. Default-/Profil-Semantik wird strukturiert in Einordnung und Aktion dargestellt, nicht als ungetrennter konkatinierter Satz.
5. Settings-Suche priorisiert Titel, exaktes Synonym und Config-Key vor allgemeinen Hilfetext-/Formeltreffern.
6. Compound-Validation für Nachtstart/-ende bleibt auf dem logischen HH:MM-Feld; interne Hour-/Minute-Keys erscheinen nicht als separate Benutzeraktion.
7. Das Status-Info-Panel `Controller & Schnittstellen` ist intern scrollbar; internes Scrollen darf es nicht schließen, externer Desktop-Seitenscroll darf weiterhin schließen.
8. Mobil wird `Controller & Schnittstellen` als viewportnahes Panel mit explizitem Schließen und eigenem Scrollkontext dargestellt.
9. Mobil ist `.settings-main` der vertikale Scroll-Owner; globale Navigation, Settings-Kontextleiste und Change-Bar bleiben bei tiefem Inhalts-Scroll erreichbar.

## 3. Terminologie

In normalen Benutzertexten bevorzugt:

- Aktualität / Datenalter statt unkommentiertem Freshness;
- Freigabebedingung statt unkommentiertem Eligibility;
- Änderungsrisiko statt Registry-Risikoklasse;
- serverseitige Validierungsregel statt Serververtrag;
- vollständige 0-W-Zustandsneutralisierung mit Erklärung statt Full-State-Neutralisierung;
- sicherer Ausgangswert, optional mit internem Fachbegriff Sentinel in Klammern.

Technische Config-Keys, Enumwerte und Expertenverträge dürfen unverändert bleiben.

## 4. Testvertrag

Pflicht:

- vollständiger bestehender Testbestand plus V12.12.1-Regressionen;
- `ResourceWarning=error`;
- Browser-Smokes für Desktop und Mobile einschließlich Deep-Scroll;
- internes Scrollen des Statuspanels;
- Search-Ranking `Totzone`/`Deadband`;
- Help-Scroll-Reset;
- logische Compound-Validation;
- DOCX/PDF vollständig rendern und visuell prüfen;
- Byteidentität der geschützten Dateien.

Automatisiertes WebKit ist nur als PASS zu melden, wenn die Engine tatsächlich verfügbar und ausgeführt wurde. Andernfalls ist die Limitierung transparent als Feldabnahmepunkt auszuweisen.
