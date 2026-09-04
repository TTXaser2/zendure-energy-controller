# Nächster Entwicklungsblock nach WP2

WP2 hat Teile des ursprünglich separat gedachten Command-/Run-Instrumentierungsblocks bereits mit erledigt. Der nächste sinnvolle Block sollte daher nicht künstlich an der alten Nummerierung festhalten.

Empfehlung:

## WP3 – Graph Query Service & Catalog Foundation

- zentraler, V3-nativer Historical Query Service;
- Series Catalog mit Unit, Scale, temporal type, entity scope, Aggregationssemantik und i18n-Key;
- automatische High-Res/1-min-Auswahl anhand Zeitraum/Viewport;
- Overview-/Inspector-Grundabfragen einschließlich sparse Intervals/Command Events/Config/Topology/Coverage;
- bestehende Status-History-Endpunkte nur dort auf den gemeinsamen Layer umstellen, wo dies technische Schuld vermeidet;
- Query-/Footprint-/Cache-Benchmarks;
- noch keine fertige neue Graph-UI und kein produktiver V3-Cutover.

Der produktive Offline-Rebuild/Cutover kann danach auf einen bereits getesteten Query-Layer aufsetzen und bleibt wegen der einzigen Installation bewusst einfach und downtime-tolerant.
