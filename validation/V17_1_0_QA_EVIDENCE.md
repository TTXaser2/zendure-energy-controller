# ZEC V17.1.0 – technische QA des finalen Source-Freeze

Release `V17.1.0` · `v17.1.0-20261019`. Regression auf dem extern bibliotheksverifizierten Checkpoint-14-Source-Stand: **165 Testdateien**, vier disjunkte, erschöpfende Partitionsläufe wegen begrenzter Einzelsitzungsdauer.

| Gate | Partitionen / Ergebnisse |
|---|---|
| Normale pytest-Regression | 310/636 Subtests, 358/5, 275/6, 277/71 = **1.220 Tests + 718 Subtests PASS** |
| Identische pytest-Partitionen, `PYTHONWARNINGS=error::ResourceWarning` | **1.220 + 718 PASS**, alle vier Logs vorhanden |
| Deployment-Harness | 11/11 PASS (Offline-Harness, kein Pi-Systemtest) |
| Python AST / Bash / Browser JS | 89+ Source-Python, 12 Shell-Skripte, 3 Browser-JavaScripts; keine Syntaxfehler |
| Datenblatt DOCX/PDF/Release-Metadaten | Validator PASS, zehn gerenderte PDF-Seiten visuell plausibel |
| Versionsgebundener Architektur-/History-/README-Vertrag | DOC_ARCH_HISTORY_GATE PASS; generisches README und generische Installationsanleitung jetzt versionsidentisch |
| Headless Browser-Nachweis (externe Fake-Transport-/DOM-Umgebung) | Chromium Desktop 1280 px und mobil 390 px: je 3 Live-Abrufe in 2,65 s, Wechsel `fresh -> stale` als `nicht aktuell` sichtbar, 0 JS-Pageerrors; kein Real-Pi-Benchmark |

QA-Umgebung: externes, nicht gepacktes `paho`-Testdouble plus pro-Test-Reset für historische während der Test-Collection verändernde Legacy-Mocks. Die Mockumgebung ist **nicht** Beleg einer realen MQTT-Verbindung. **Technisches Paketgate** (Manifest, Byteintegrität, final ZIP/CRC, Fresh-extract, Docker/Deployment-Tools) wird separat gegen exakt das Release-ZIP dokumentiert.

Neue Runtimefunktionalität (S3, 1-Hz-Status, Grid-Stale und beide Pflichtfixes) stammt aus dem erprobten, extern gesicherten Source-Checkpoint 10. Releasekorrekturen seitdem betreffen dokumentierte Testidentitäten, QA-Race, Version-/Installationsdokumentation und neue QA-/Manifest-Tools. Der geschützte Reglerkern wurde dabei nicht geändert.

**Produktive Feldevidenz:** NICHT ERBRACHT. V17.0.2 bleibt auf dem Pi installiert, bis das echte V17.1.0-Update durchgeführt wurde. Physische Reglerwirkung, reale 1-Hz-/Sensoraktualität, Last auf Pi 3B+ und tatsächliche Stale-Event-Recovery werden danach gesondert geprüft.
