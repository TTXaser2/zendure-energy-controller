# ZEC V16.2.3

## Zweck

V16.2.3 ist ein enger Deployment-/Preflight-Hotfix auf Basis von V16.2.2. Der reale V16.2.2-Preflight auf der produktiven V16.2.0-Basis blieb mutationsfrei und brach vor Dienststopp/Produktivänderung ab, weil der Installer Freitextmarker erwartete, die nicht dem tatsächlichen Format der ausgelieferten grünen Build-Evidenz entsprachen.

## Hotfixumfang

- Build-Evidenz besitzt einen kanonischen maschinenlesbaren Vertrag `ZEC_BUILD_EVIDENCE_V1`;
- `tools/deployment_contract.py verify-build-evidence` ist die gemeinsame Verifier-Autorität;
- der Installer delegiert an diesen Verifier und parst keine fragilen Marker aus human-readable Testdateien mehr;
- Releaseidentität, PASS-Status, Testdateianzahl, vollständige Regression und `ResourceWarning=error` werden fail-closed geprüft;
- Volltest- und ResourceWarning-Zählungen müssen konsistent sein;
- der finale Fresh-Extract muss den Build-Evidence-Teil des echten Installer-Preflights auf dem ausgelieferten Paket bestehen.

## Schutzgrenze

Keine Änderung an UI, Regelstrategie, Command-, Safety-, Recovery- oder Speicherlogik gegenüber V16.2.2. `controller_logic.py` bleibt byteidentisch mit SHA256 `d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`.

## Releaseidentität

- Version: `16.2.3`
- Label: `V16.2.3`
- Build-ID: `v16.2.3-20260921`
- unterstützte reale Updatequelle: `16.2.0 / v16.2.0-20260920`

## Feldstatus

V16.2.2 erhält wegen des realen mutationsfreien Preflight-Fails keinen Real-Field-PASS. V16.2.0 bleibt bis zur erfolgreichen V16.2.3-Update-Feldabnahme die letzte real bestätigte Basis.

## Technischer Status

**TECHNICAL BUILD PASS**. Reale V16.2.3-Update-Feldabnahme bleibt bis zum Pi-Lauf `PENDING`.
