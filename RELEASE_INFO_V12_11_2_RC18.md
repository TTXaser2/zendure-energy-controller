# Release Info – Zendure Energy Controller V12.11.2-RC18

## Zweck

RC18 entkoppelt die read-only lokale Zendure-API vollständig vom Regelzyklus und korrigiert den rein diagnostischen Measurement-V4-Vertrag der Zielwert-Power-Cap-Stufe.

## Intended Delta

- genau ein `ZendureLocalApiWorker`-Daemonthread;
- genau eine Worker-Session und ein immutable Latest-Snapshot;
- monotone Poll-/Backoff-/Freshness-Zeitführung;
- Configgeneration und IP-Wechsel-Guard;
- Snapshotübernahme ausschließlich im Controller-Hauptthread;
- acht additive zyklische V4-Felder;
- Status-/Runtime-Events für Worker, Versuche, Fehler und Backoff;
- numerische `target_limited_w`-/Limiter-Flags.

## Sicherheitsabgrenzung

Keine Änderung an Reglerformeln, Modi, Harvest, Cross-Charge, Command-Safety, Resync, Neutralisierung, Flash-Schutz, Offgrid, Configwerten, Storage-Retention oder Excel.

## Measurement

```text
Standard: 246 Felder
Extended: 249 Felder
RC17 Standardheader bleibt 238 / 192ccc890c2e1d80
```

## Produktivstatus

Build- und Regressionstestvalidiert. Produktivvalidierung nach Installation ausstehend.
