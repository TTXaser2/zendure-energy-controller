# V18.0.1 – technische Korrekturen (ENTWURF)

Der Recovery-Fix hebt SAFE_STATE im Nacht-Battery-Care-Floor-Zweig ausschließlich bei intern frischem SOC, frischem Netz und bestätigtem neutralem Befehls- und Istleistungspfad zu HOLD auf. Physische 0-W-Neutralisierung bleibt verbindlich; keine erneute Entladung unter R.

Das neue deduplizierte Reserve-Journal trennt `physical_effect_confirmed=false` und tatsächlich beobachtete Neutralisierung. Die Settings-UI prüft API-Struktur und bietet begrenzte Retry-/Reloadmöglichkeiten. Neue Primärspeicher-Grenze ist reine Darstellung, keine Ladegrenze.

Werkzeug `tools/zec_battery_care_7d_readonly.py` ist stand-alone/read-only, testet reale SQLite-Nutzspalten und nutzt V4-Valid/Fresh-Fallback.
