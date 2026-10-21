# Technische Hinweise – V12.11.3

Die Installations-Abnahme ist von der Runtime-Readiness getrennt. `/ready` selbst wird nicht abgeschwächt. Der Installer klassifiziert wiederholte `/ready`-Snapshots über `tools/evaluate_installation_readiness.py` als `READY`, `TRANSITIONAL` oder `REJECT`.

Ein `TRANSITIONAL`-Start wird erst nach mindestens 15 aufeinanderfolgenden zulässigen Snapshots und frühestens 30 Sekunden akzeptiert. Der Zustand wird ausdrücklich als Warnung protokolliert und nicht als `ready=true` ausgegeben.

Journaldiagnose bei echtem Fehlschlag wird ausschließlich ab Beginn der aktuellen Installation ausgegeben.
