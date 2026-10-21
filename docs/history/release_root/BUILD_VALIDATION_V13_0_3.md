# ZEC V13.0.3 – Build Validation

**Build-ID:** `v13.0.3-20260814`  
**Quellbasis:** V13.0.2 / `v13.0.2-20260812`  
**Basis-ZIP SHA256:** `f7f35b73f8f66e36ba469685c67f95982168d8f7f81b82e7f6083800c15bc9a4`

## Implementierter Scope

- technische vs. nutzerrelevante Migrationsschritte getrennt;
- technische V13.0.1-Display-Metadata-Kompatibilität bleibt roh diagnostizierbar, wird aber nicht als Benutzer-Migration/Bestätigung dargestellt;
- No-op-Bestätigungen serverseitig unterdrückt;
- kontextbezogene Preview-Titel und No-op-Texte;
- No-op mit genau einer Navigation und ohne Commitbutton;
- technische Details nur im Expertenmodus;
- Parent zählt nur nutzerrelevante Migrationen;
- echte Warn-/Commitpfade bleiben erhalten;
- Legacy-Rohimport-Warnung mit verständlichem Benutzertext.

## Tests im Arbeitsbaum

- `pytest`: **808 passed, 681 subtests passed**.
- `unittest` mit `PYTHONWARNINGS=error::ResourceWarning`: **808 tests, OK**.
- gezielte Config-Route-/V13.0.3-UX-Suite: **13 passed**.
- Python AST: **169/169 PASS**.
- Python `compileall`/Bytecode-Compile: **169/169 PASS**.
- JavaScript `node --check`: **2/2 PASS**.
- Shell `bash -n`: **9/9 PASS**.
- JSON parse: **6/6 PASS**.

## No-Regression

Die spezifikationsgeschützten Regler-, Command-, Measurement-, SQLite-/Backfill- und Last-Good-/Recovery-Dateien wurden gegen die verifizierte V13.0.2-Basis SHA256-weise geprüft und sind byteidentisch. Details: `V13_0_3_TARGETED_PROTECTED_DIFF.md`.

## Source-Manifest und Paket-Gate

`V13_0_3_SOURCE_MANIFEST.sha256` wurde nach Abschluss der Releaseartefakte mit **407 Einträgen** final erzeugt und im Arbeitsbaum vollständig verifiziert. Das finale ZIP muss anschließend frisch entpackt werden; Test-, Syntax-, Manifest- und Differentialgates werden aus genau diesem Paket erneut geprüft. Das Ergebnis dieser letzten Paketprüfung steht in der externen `V13_0_3_FINAL_VALIDATION.md`.
