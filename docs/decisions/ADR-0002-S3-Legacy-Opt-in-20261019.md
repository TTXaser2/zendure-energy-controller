# ADR-0002 – S3-Saisonpolicy ausschließlich mit explizitem Opt-in

**Entscheid 19.10.2026**, aus `ZEC_S3_PRODUKTIONSSPEZIFIKATION_V17_0_2_FINAL_20261019.md`; dokumentiert, kein historisch behauptetes Original des V17.0.2-Releases.

**Problem:** V17.0.2 speichert `HARVEST_SEASON_MODE=sma_priority` als Default, ohne den Wert in der Runtime anzuwenden. Eine unmittelbare Aktivierung beim Update änderte den Regler ohne Zustimmung.

**Beschluss:** `HARVEST_SEASON_POLICY_ENABLED=false` für Alt- und Neuinstallationen. Erst bestätigtes Settings-Preview/Commit aktiviert `parallel|sma_priority|calendar` für strategische High-SOC-Share-Allokation; Export Capture und sämtliche Safety-/Command-Grenzen bleiben höher priorisiert. Tagesprofilgrenzen bleiben deterministisch, lokale Zeit, strict T0<T1<T2<T3, inklusive linke/exklusive rechte Grenze; gültige Kalendergrenzen wiederkehrend und inklusiv.

**Abgelehnte Alternative:** saisonale Default-Wirksamkeit durch reine Verwendung des alten persistierten Modes. **Grund:** stiller und nicht regressionsneutraler Verhaltenswechsel.

**Implementierung:** `controller_logic.py`, `settings_registry.py`, `settings_validation.py`; Tests `tests/test_s3_and_status_live_dev.py`, `tests/test_v17_nextrelease_s3_diagnostics.py`. Kein Ertragsversprechen ohne physischen Feldnachweis.
