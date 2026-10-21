# ZEC V15.0.3

## Zweck
V15.0.3 integriert das technische ZEC-Datenblatt dauerhaft in den Produkt- und Releaseprozess. Der Release enthält keine Änderung der Live-Regelalgorithmen.

## Dauerhafte Datenblattintegration
- stabile Releasepfade `docs/ZEC_Technisches_Datenblatt.pdf` und `.docx`;
- aktueller Ist-Zustand statt Versionshistorie;
- verpflichtende Hardware-/Softwarevoraussetzungen und Anlagenkonstellationen;
- SMA-Speedwire und Shelly-Pro-3EM/Shelly-kompatibler HTTP-Messpfad bleiben als produktive Messpfade dokumentiert;
- kanonische Verankerung in `06_ZEC_RELEASE_AND_HANDOVER_PROCESS.md`;
- stdlib-only Datenblattvalidator für Source-/Package-/Installer-/Field-Gates;
- Fresh-extract muss beide Dokumente und ihre Releaseidentität bestätigen.

## Schutzgrenzen
- `controller_logic.py` bleibt byteidentisch zu V15.0.2.
- Native Modbus-/Primärspeicherimplementierung unverändert.
- Keine neue Runtime-Abhängigkeit.
- Measurement V4 unverändert.

## Releaseidentität
- Version: `15.0.3`
- Label: `V15.0.3`
- Build-ID: `v15.0.3-20260911`
- Upgradequelle: ausschließlich `15.0.2 / v15.0.2-20260911`
- Paket: `zendure_controller_v15_0_3.zip`
