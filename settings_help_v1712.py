"""Reviewed, user-facing applicability and plain-language help (V17.1.2).

Only prose: no controller state, commands, defaults, or config migration.
Entries are keyed to real, operational SettingsRegistry controls. Absence of an
entry for a field that already has a reviewed applicability description is fine;
all other operational keys are explicitly covered, verified by tests.
"""
from types import MappingProxyType

WHEN = MappingProxyType({
# Zendure identity/energy; capacity never grants authority to charge/discharge.
'ZENDURE_BATTERY_CAPACITY_WH': 'Nur für Energieanzeige und Prognosen mit einer verlässlichen Kapazitätsangabe. Der Wert öffnet weder die Lade-/Entladegrenzen noch veranlasst er eine Ladung.',
'DEVICE_ID': 'Bei der Zuordnung der MQTT-Nachrichten zu der einen tatsächlich gesteuerten Zendure-Headunit. Stimmt die Kennung nicht zum Gerät, können aktuelle Messungen oder sichere Befehle fehlen.',
# Primary storage: read-only integration; source-specific keys only in that source profile.
'SECOND_BATTERY_STALE_TIMEOUT_SECONDS': 'Nur bei eingeschalteter Primärspeicher-Integration und eingehenden Daten. Nach Ablauf gelten alte Werte nicht mehr als verlässliche Grundlage für Ladeverteilung und Gegenladeschutz.',
'SECOND_BATTERY_DISPLAY_NAME': 'Nur für den angezeigten Namen, nicht für Messwerte oder Ladeentscheidungen. Ein selbst vergebener Name hat Vorrang vor dem Gerätenamen des Profils.',
'SECOND_BATTERY_SOURCE_PROFILE': 'Nur bei eingeschalteter Primärspeicher-Integration. EVCC, eigenes MQTT und direktes Modbus haben jeweils andere Anschlussfelder; die Auswahl sendet keine Primärspeicher-Steuerbefehle.',
'SECOND_BATTERY_MODBUS_TEMPLATE': 'Nur bei gewählter direkter Modbus-Anbindung. Das Geräteprofil bestimmt die tatsächlich lesbaren Register und deren Bedeutung; es führt keine Schreibbefehle aus.',
'SECOND_BATTERY_MODBUS_HOST': 'Nur bei direkter Modbus-Anbindung. Ohne erreichbare Adresse des Primärspeichers können aktuelle Leistung und Ladezustand nicht aus diesem Pfad übernommen werden.',
'SECOND_BATTERY_MODBUS_PORT': 'Nur bei direkter Modbus-Anbindung zusammen mit Host, Geräteprofil und Geräteadresse; ein falscher Port verhindert aktuelle Messungen, statt Ersatzwerte zu erfinden.',
'SECOND_BATTERY_MODBUS_UNIT_ID': 'Nur bei direkter Modbus-Anbindung und passender Geräteadresse. Diese Nummer wählt das angesprochene Gerät am Modbus-Anschluss, nicht die Zendure-Headunit.',
'SECOND_BATTERY_CAPACITY_TOPIC': 'Nur im benutzerdefinierten MQTT-Profil, wenn die optionale Kapazität von einem Topic gelesen werden soll. Ohne verlässliche Kapazität bleibt die davon abhängige Energieanzeige eingeschränkt.',
'SECOND_BATTERY_POWER_TOPIC': 'Nur im benutzerdefinierten MQTT-Profil. Leistung ist für die sichere Erkennung von Laden, Entladen und Gegenladen entscheidend; fehlende oder alte Werte dürfen das nicht bestätigen.',
'SECOND_BATTERY_SOC_TOPIC': 'Nur im benutzerdefinierten MQTT-Profil, soweit Ladezustandsdaten für die gewählte Funktion benötigt werden. Ein nicht empfangener Wert darf nicht als neuer Ladezustand gelten.',
'SECOND_BATTERY_EVCC_BASE_TOPIC': 'Nur mit dem EVCC-Standardprofil; ZEC ergänzt die vorgesehenen Untertopics für die benötigten Messgrößen. Kein Effekt bei direkter Modbus- oder eigener MQTT-Anbindung.',
'SECOND_BATTERY_CAPACITY_JSON_PATH': 'Nur wenn das Kapazitäts-Topic ein JSON-Objekt sendet. Bei direktem Zahlenwert wird dieser Feldpfad nicht gebraucht.',
'SECOND_BATTERY_CAPACITY_PAYLOAD_TYPE': 'Nur bei eigener MQTT-Kapazitätsquelle. Zahlenwert und JSON-Objekt benötigen unterschiedliche Auswertung; ein falscher Typ führt nicht zu einer erfundenen Kapazität.',
'SECOND_BATTERY_POWER_JSON_PATH': 'Nur wenn das benutzerdefinierte Leistungs-Topic ein JSON-Objekt sendet. Bei einer direkt gesendeten Zahl ist kein Feldpfad erforderlich.',
'SECOND_BATTERY_POWER_PAYLOAD_TYPE': 'Nur bei eigener MQTT-Leistungsquelle. Das Format muss zur tatsächlichen Nachricht passen, sonst fehlt eine belastbare Primärspeicher-Istleistung.',
'SECOND_BATTERY_SOC_JSON_PATH': 'Nur wenn das benutzerdefinierte Ladezustands-Topic ein JSON-Objekt sendet. Ein einzelner Zahlenwert benötigt keinen Feldpfad.',
'SECOND_BATTERY_SOC_PAYLOAD_TYPE': 'Nur bei eigener MQTT-Ladezustandsquelle. Ohne Übereinstimmung von Format und Nachricht wird kein verlässlicher Ladezustand abgeleitet.',
'SECOND_BATTERY_CAPACITY_UNIT': 'Nur bei eigener MQTT-Kapazitätsquelle. ZEC rechnet den empfangenen Wert für Energieanzeigen in eine gemeinsame Einheit um; dies ändert nicht die gemeldete Batterieleistung.',
'SECOND_BATTERY_DISCHARGE_SIGN': 'Nur bei eigener MQTT-Leistungsquelle. Hier wird festgelegt, welches Vorzeichen Laden oder Entladen bedeutet; eine falsche Zuordnung verfälscht auch die Gegenlade-Erkennung.',
'SECOND_BATTERY_POWER_UNIT': 'Nur bei eigener MQTT-Leistungsquelle. Die empfangene Leistung wird entsprechend in Watt umgerechnet; dies setzt keine reale Leistungsgrenze.',
'SECOND_BATTERY_MAX_CHARGE_POWER_W': 'Nur für die Einordnung und Begrenzung der zulässigen Primärspeicher-/Harvest-Berechnungen bei aktivem Primärspeicher. ZEC befiehlt dem Primärspeicher damit keine Ladung.',
# Measurement / graph storage, not a second controller.
'MEASUREMENT_LOG_MAX_BYTES': 'Nur bei eingeschalteter zyklischer Messdatenaufzeichnung. Größere Dateien werden später rotiert; der Wert ändert keine Netz- oder Batterieregelung.',
'MEASUREMENT_LOG_ALLOW_SD_FALLBACK': 'Nur wenn das gewählte Messdaten-Speicherziel ausfällt oder nicht nutzbar ist. Die Reserveablage erlaubt weitere Aufzeichnung unter ihren eigenen Platzgrenzen, aber keinen unbeschränkten Schreibbetrieb.',
'MEASUREMENT_LOG_FALLBACK_DIR': 'Nur bei ausdrücklich erlaubtem Ausweichen auf eine Ersatzablage. Der Pfad muss erreichbar und beschreibbar sein; sonst fallen neue Messdaten aus, nicht die Schutzgrenzen.',
'MEASUREMENT_LOG_FALLBACK_MAX_BYTES': 'Nur wenn die Ersatzablage tatsächlich genutzt wird. Die Grenze schützt deren Speicherplatz und begrenzt nicht die Leistungsregelung.',
'MEASUREMENT_LOG_FILE': 'Nur für aktivierte CSV-Messdatenaufzeichnung; Dateiname und Speicherziel bestimmen, wo neue Zeilen landen, nicht ob Zendure lädt.',
'MEASUREMENT_LOG_MODE': 'Aus unterbindet neue zyklische Measurement-V4-Dateizeilen; Standard und Erweitert schreiben unterschiedliche Diagnosedetails. Der unabhängig arbeitende Controller bleibt aktiv.',
'MEASUREMENT_DB_ENABLED': 'Nur für die separate Graphdatenbank. Ausschalten stoppt deren neue Speicherung, nicht den Echtzeitregler oder die bereits vorhandene CSV-Messdatenaufzeichnung.',
'MEASUREMENT_DB_PATH': 'Nur bei eingeschaltetem Graphdatenbankspeicher; die Datenbank benötigt einen zugänglichen Speicherort. Der Pfad ist kein Eingangssensor für die Regelung.',
'MEASUREMENT_LOG_FLUSH_EVERY_ROWS': 'Nur bei laufender CSV-Aufzeichnung: nach dieser Anzahl gesammelter Zeilen wird zum Speichermedium geschrieben. Häufigeres Schreiben kann die SD-Karte stärker belasten.',
'MEASUREMENT_LOG_FLUSH_EVERY_SECONDS': 'Nur bei laufender CSV-Aufzeichnung: spätestens nach dieser Wartezeit werden zwischengespeicherte Zeilen geschrieben. Längere Wartezeiten können beim Ausfall jüngste Aufzeichnungen kosten.',
'MEASUREMENT_LOG_MIN_FREE_DISK_MB': 'Nur beim Schreiben neuer Messdaten. Bei zu wenig freiem Speicher greift der Platzschutz; das ist kein Befehl an Zendure.',
'MEASUREMENT_LOG_DIR': 'Nur bei aktivierter CSV-Aufzeichnung und passender Wahl des Speicherziels. Ein fehlendes Verzeichnis erzeugt keine Ersatzmesswerte.',
'MEASUREMENT_LOG_MOUNTPOINT': 'Nur wenn Messdaten auf einen separaten Datenträger geschrieben werden sollen. Ohne passenden eingehängten Datenträger wird nicht stillschweigend ein beliebiger Systempfad benutzt.',
'MEASUREMENT_LOG_STORAGE_TARGET': 'Nur für neue CSV-Messdaten: bestimmt SD-Karte oder vorgesehenes externes Ziel. Ein Wechsel verschiebt keine vorhandene Historie und verändert keinen Regelzyklus.',
'GRAPH_HISTORY_LIMIT': 'Nur für den begrenzten kurzfristigen RAM-Verlauf. Mehr Einträge benötigen mehr Arbeitsspeicher; die Datenmenge ändert weder den Sensor- noch den Reglertakt.',
'SOC_DAY_GRAPH_BOOTSTRAP_CACHE_SECONDS': 'Nur beim vorbereiteten Tagesgraphen aus gespeicherten Messdaten. Größere Cachezeit spart Ladeaufwand, kann aber die anfänglich sichtbare Kurve länger unverändert lassen.',
'SOC_DAY_GRAPH_BOOTSTRAP_FROM_MEASUREMENTS': 'Nur für die anfängliche Tageskurve, wenn passende ältere Messdaten vorhanden sind. Es werden keine fehlenden Sensorwerte erfunden und keine Controllerzustände zurückgesetzt.',
'SOC_DAY_GRAPH_ENABLED': 'Nur für die separate Aufzeichnung und Darstellung des Tages-Ladezustandsverlaufs. Ausschalten beendet diese Graphfunktion, nicht die Batterie-SOC-Schutzentscheidung.',
'SOC_DAY_GRAPH_SAMPLE_SECONDS': 'Nur bei aktivierter Tagesgraph-Aufzeichnung. Bestimmt die Graph-Speicherkadenz, nicht die reale SOC-Erfassungsrate der Zendure.',
'MEASUREMENT_V4_MANIFEST_UPDATE_EVERY_ROWS': 'Nur bei aktivem Measurement-V4-Dateibetrieb. Weniger häufige Indexaktualisierung spart Schreibvorgänge; die Messdaten bleiben weiterhin eigenständig.',
'MEASUREMENT_V4_MANIFEST_UPDATE_EVERY_SECONDS': 'Nur bei aktivem Measurement-V4-Dateibetrieb. Regelt die zeitliche Aktualisierung der Dateiliste für Analyse/Inventar, nicht die Leistung des Controllers.',
# Grid and transport; sensor validity is separate from browser refresh.
'MQTT_TOPIC_DIAGNOSTIC_ENABLED': 'Nur für die zusätzliche Topic-Diagnose. Sie zeigt empfangene MQTT-Nachrichten, schaltet aber weder den MQTT-Kommandoweg noch eine zusätzliche Gerätesteuerung ein.',
'MQTT_TOPIC_DIAGNOSTIC_FILTER': 'Nur bei aktivierter Topic-Diagnose. Der Filter schränkt sichtbare Diagnoseeinträge ein, nicht die produktiv abonnierten Steuer- und Messdaten.',
'MQTT_TOPIC_DIAGNOSTIC_HISTORY_LIMIT': 'Nur bei aktivierter MQTT-Topic-Diagnose. Mehr gespeicherte Diagnoseeinträge erhöhen den Speicherbedarf; sie verändern weder Gerätetakte noch Sollwerte.',
'MQTT_TOPIC_DIAGNOSTIC_VIEW_MODE': 'Nur für die Darstellungsform der MQTT-Topic-Diagnose. Rohdatenansicht und verdichtete Ansicht ändern keine an das Gerät gesendeten Befehle.',
'MQTT_BROKER': 'Bei jeder MQTT-Verbindung zu Zendure; ohne erreichbaren Broker fehlen der sichere Gerätebefehlskanal und aktuelle MQTT-Telemetrie. Eine Änderung benötigt die vorgesehene Neuverbindung.',
'MQTT_PASSWORD': 'Nur falls der konfigurierte Broker eine Anmeldung verlangt. Dieses Kennwort ist geheim; eine Änderung betrifft die Verbindung, nicht die gewünschte Ladeleistung.',
'MQTT_PORT': 'Zusammen mit Brokeradresse und gegebenenfalls Benutzeranmeldung. Ein nicht erreichbarer Port bedeutet keine verlässliche Verbindung; er ist kein Port der Weboberfläche.',
'MQTT_USER': 'Nur wenn der MQTT-Broker eine Anmeldung verlangt. Benutzer und Passwort müssen zusammenpassen; die Einstellung wählt keine andere Zendure-Headunit.',
'GRID_POWER_PLAUSIBILITY_MAX_ABS_W': 'Nur zur Prüfung, ob ein eingehender Netzleistungswert physikalisch plausibel ist. Auffällige Extremwerte dürfen nicht als echte Import-/Exportgrundlage für AUTO verwendet werden.',
'SMA_ENERGY_METER_LOG_DIAGNOSTICS': 'Nur für den SMA-Direktempfang und dessen zusätzliche Textdiagnose bei eingeschaltetem Datei-Logging. Ein Logeintrag beweist keine neue Regelentscheidung.',
'SMA_ENERGY_METER_LOG_INTERVAL_SECONDS': 'Nur bei eingeschalteter periodischer SMA-Paketdiagnose. Kürzere Intervalle erhöhen Logvolumen, nicht die Häufigkeit der SMA-Messungen.',
'SMA_ENERGY_METER_PACKET_GAP_WARN_SECONDS': 'Nur bei der SMA-Paketdiagnose. Längere Empfangslücken werden gemeldet; die separate Frischeprüfung entscheidet unabhängig über die Verwendbarkeit der Netzleistung.',
'SMA_ENERGY_METER_GROUP': 'Nur für direkt empfangene SMA-Speedwire-Pakete. Die Multicast-Gruppe muss zum lokalen Messgerät passen; sie wird bei Shelly-HTTP als aktiver Quelle nicht benötigt.',
'SMA_ENERGY_METER_INTERFACE': 'Nur bei SMA-Direktempfang, insbesondere wenn der Host mehrere Netzwerkschnittstellen hat. Eine falsche Auswahl kann den Paketempfang verhindern.',
'SMA_ENERGY_METER_PASSIVE_ENABLED': 'Nur wenn Shelly als aktive Netzquelle gewählt ist. SMA darf dann zusätzlich zur Diagnose beobachtet werden, ohne die aktive Leistungsregelung unbemerkt auf SMA umzustellen.',
'SMA_ENERGY_METER_PORT': 'Nur für den lokalen SMA-Speedwire-Empfänger. Dieser UDP-Port ist weder der ZEC-Webport noch der MQTT-Brokerport.',
'SMA_ENERGY_METER_SERIAL': 'Nur für den SMA-Direktempfang mit gewünschtem Gerätefilter. Ohne sichere Zuordnung darf ein anderes SMA-Gerät nicht als Hausnetz-Zähler ausgegeben werden.',
'SMA_ENERGY_METER_SOCKET_MODE': 'Nur für die SMA-Speedwire-Netzwerkschnittstelle. Die gewählte Empfangsart betrifft das Teilen des Messdatenports mit anderen Diensten; sie verändert nicht den Messwert selbst.',
'SMA_ENERGY_METER_STALE_TIMEOUT_SECONDS': 'Nur für die Frischeentscheidung des direkten SMA-Empfängers. Ein abgelaufener Paketwert ist nicht mehr aktuell, auch wenn die Statusseite jede Sekunde neu zeichnet.',
'SMA_ENERGY_METER_SUSY_ID': 'Nur beim gewählten SMA-Empfangsfilter. Zusammen mit einer eventuellen Seriennummer wird das richtige physische Messgerät identifiziert.',
'SHELLY_IP': 'Nur wenn Shelly-kompatibles HTTP als aktive Netzquelle gewählt wurde. Die Adresse muss zum tatsächlichen Endpunkt am Hausanschluss passen; ein beliebiges Shelly-Gerät genügt nicht.',
'SHELLY_STALE_TIMEOUT_SECONDS': 'Nur für die Shelly-kompatible Netzquelle. Fehlt länger ein gültiger HTTP-Messwert, darf dessen alte Leistung nicht als neue AUTO-Information gelten.',
'GRID_METER_SOURCE': 'Immer dann, wenn ZEC Netzbezug oder Einspeisung für AUTO/Safety beurteilt. Die Auswahl ist exklusiv: Shelly-HTTP oder SMA-Speedwire; eine passive Diagnosequelle übernimmt nicht unbemerkt die Regelung.',
'ZENDURE_LOCAL_API_ENABLED': 'Nur für die lokale Zendure-Diagnoseseite. Einschalten allein ersetzt weder die MQTT-Anbindung noch aktiviert es eine zusätzliche Leistungssteuerung.',
'ZENDURE_LOCAL_API_ERROR_BACKOFF_SECONDS': 'Nur nach einem fehlgeschlagenen lokalen Zendure-API-Aufruf. Die Pause schützt den kleinen Host vor wiederholter Hintergrundlast und ist kein Regler-Cooldown.',
'ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS': 'Nur bei eingeschalteter lokaler Zendure-Abfrage. Der Wert begrenzt die Hintergrundabfragen, ohne die 1-s-Anzeige oder den eigentlichen Reglertakt zu versprechen.',
'ZENDURE_LOCAL_API_SOC_PRIORITY': 'Nur wenn die lokale Geräteantwort mehrere unterschiedliche SOC-Felder liefert. Die gewählte Quelle muss tatsächlich vorhanden und gültig sein; eine Priorität erfindet keinen Ladezustand.',
'ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY': 'Nur bei erlaubter lokaler Telemetrie. Bei Aktiv bleibt gültiges MQTT führend und die lokale Antwort darf nur bei entsprechendem Ausfall einspringen.',
'ZENDURE_LOCAL_API_USE_FOR_TELEMETRY': 'Nur bei gültiger lokaler Geräteverbindung. Ergänzende Werte werden auf Aktualität geprüft; diese Einstellung sendet keine zusätzlichen Leistungskommandos.',
'ZENDURE_LOCAL_IP': 'Nur für aktivierte lokale Zendure-Diagnose beziehungsweise zugelassene zusätzliche Telemetrie. Die IP muss zur Headunit gehören; das ist nicht die Broker-Adresse.',
'ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS': 'Nur für die Laufzeitbegrenzung der lokalen Hintergrundabfrage. Ein zu großer Wert kann Ressourcen länger binden, ohne den Controller nachweislich schneller zu machen.',
'ZENDURE_LOCAL_API_TIMEOUT_SECONDS': 'Nur für einzelne lokale API-Anfragen. Bei Ausbleiben einer Antwort gelten deren Werte nicht automatisch als frisch; MQTT und Control-Safety bleiben getrennt.',
# User interface, runtime logging, bounded analysis and safety.
'WEB_SERVICE_RESTART_ENABLED': 'Nur beim ausdrücklich bestätigten administrativen Dienstneustart aus der Weboberfläche. Einstellungen, die einen Neustart benötigen, wirken nicht durch die bloße Freigabe dieses Schalters.',
'ANALYSIS_EXTENDED_MAX_FILES': 'Nur für bewusst bestätigte größere Offline-Analysen. Mehr Dateien erhöhen den möglichen Rechen- und I/O-Aufwand auf dem Raspberry Pi; der Echtzeitregler bleibt getrennt.',
'ANALYSIS_EXTENDED_MAX_ROWS': 'Nur für ausdrücklich erweiterte Offline-Auswertungen. Ein höheres Limit lässt größere Datenmengen zu, ist aber keine Empfehlung, große V4-Historien ungebremst in den Arbeitsspeicher zu laden.',
'ANALYSIS_EXTENDED_MAX_TOTAL_BYTES': 'Nur für bewusst größere Analyseaufträge. Ein höheres Dateivolumen erhöht Host-/Datenträgerbelastung; der Analyseauftrag muss trotzdem die eigenen Sicherheitsgrenzen einhalten.',
'ANALYSIS_EXTENDED_WORKER_MEMORY_LIMIT_MB': 'Nur für den separaten erweiterten Analyseprozess. Mehr RAM kann zulässige Auswertungen ermöglichen, aber bei knapper Hardware die laufenden Dienste beeinträchtigen.',
'ANALYSIS_EXTENDED_WORKER_TIMEOUT_SECONDS': 'Nur für ausdrücklich erweiterte Analysejobs. Ein größeres Zeitbudget macht keine Analyse automatisch genauer und verändert die Ladeentscheidung nicht.',
'ANALYSIS_MAX_FILES': 'Nur für normale lokale Analysejobs. Die Dateigrenze verhindert übergroße Aufträge, ohne die bereits gesammelten Messdaten zu löschen.',
'ANALYSIS_MAX_ROWS': 'Nur für normale lokale Auswertungen. Begrenzte Zeilenzahl schützt CPU und Arbeitsspeicher; sie verändert weder Datenerfassung noch Regelung.',
'ANALYSIS_MAX_TOTAL_BYTES': 'Nur bei Auswahl von Dateien für eine normale Analyse. Überlange Datensätze werden abgewiesen und dürfen nicht ungeprüft den produktiven Pi blockieren.',
'ANALYSIS_WORKER_MEMORY_LIMIT_MB': 'Nur für den eigenständigen Analyseprozess. Bei Überlast wird die Analyse begrenzt, nicht der Controller absichtlich neu gestartet.',
'ANALYSIS_WORKER_TIMEOUT_SECONDS': 'Nur während eines normalen Analysejobs. Ein Ablauf beendet die Analyse nach ihrer Zeitgrenze; er schaltet weder Zendure noch den Webserver ab.',
'REPLAY_WEB_PORT': 'Nur bei separat gestartetem Analyse-/Replay-Dienst. Der Port ist nicht der ZEC-Statusseitenport und hat keinen Einfluss auf produktive Leistungsbefehle.',
'UI_DARK_MODE': 'Nur für das Farbschema der Oberfläche. Ein-/Ausschalten hat keinen Einfluss auf Netz- oder Speicherleistung und darf Warnhinweise nicht unsichtbar machen.',
'UI_MODE': 'Nur für die Menge sichtbarer Details in der Weboberfläche. Im Expertenmodus bleiben alle Standardinformationen und Warnungen erhalten; die Regelstrategie bleibt unverändert.',
'SLOW_CYCLE_WARN_MS': 'Nur für eine Laufzeitwarnung, wenn ein Rechenschritt ungewöhnlich lange dauert. Der Grenzwert beschleunigt den tatsächlichen Regler nicht.',
'FILE_LOG_BACKUP_COUNT': 'Nur bei aktivem Datei-Logging und Rotation. Ältere Textdateien belegen zusätzlichen Speicher und dokumentieren Ereignisse, nicht die tatsächliche Batteriealterung.',
'FILE_LOG_DIR': 'Nur bei eingeschaltetem Datei-Logging. Das Verzeichnis muss beschreibbar sein; ein unbrauchbarer Logpfad autorisiert keine neuen Kommandos.',
'FILE_LOG_ENABLED': 'Nur für zusätzliche persistente Textprotokolle. Ohne diese Option bleiben Laufzeit- und Gerätesteuerung getrennt; die Aufbewahrungsgrenzen sind eigene Einstellungen.',
'FILE_LOG_FILE': 'Nur für aktiviertes Datei-Logging. Der Name legt die Textprotokolldatei fest, nicht den Ort der Measurement-V4-CSV-Dateien.',
'FILE_LOG_MAX_BYTES': 'Nur bei eingeschaltetem Datei-Logging. Beim Erreichen der Größenobergrenze wird das Textlog rotiert; der Wert ersetzt keine Speicherplatzüberwachung.',
'DEBUG': 'Nur für technische Fehlersuche mit zusätzlichen Meldungen. Abschalten mindert Logvolumen und ändert weder AUTO-Berechnung noch Geräteschutz.',
'LOG_CONTROL': 'Nur für zusätzliche protokollierte Reglerentscheidungen bei aktivierter Diagnoseausgabe. Ein Debug-Text ist kein unabhängiger Beweis einer Gerätewirkung.',
'LOG_MANUAL': 'Nur bei Aktionen im manuellen Modus und eingeschaltetem relevantem Logging. Die Option startet oder beendet keinen manuellen Lade-/Entladevorgang.',
'LOG_MQTT': 'Nur für die Diagnose gesendeter MQTT-Befehle. Ein protokollierter Versand belegt nicht, dass Zendure die Leistung physisch umgesetzt hat.',
'LOG_RAW_RESPONSE': 'Nur bei entsprechender Shelly-HTTP-Diagnose. Vollständige Antworten können umfangreich oder vertraulich sein und sind kein Grund, die Datenquelle zu wechseln.',
'LOG_SOC': 'Nur für zusätzliche Empfangsprotokolle des Zendure-Ladezustands. Die SOC-Schutzgrenzen werden dadurch nicht verschoben.',
'LOG_VALUES': 'Nur für zusätzliche Netzleistungs- und Glättungsdiagnose. Die Eingangsquelle und die tatsächliche Messfrequenz bleiben unverändert.',
'MAX_CONSECUTIVE_ERRORS': 'Nur für den Schutz bei unmittelbar aufeinanderfolgenden Laufzeitfehlern. Die Schwelle ist keine normale Reaktionsverstärkung und darf echte Störungen nicht maskieren.',
'MQTT_DISCONNECTED_SAFE_STATE': 'Nur wenn die produktive MQTT-Verbindung ausfällt. Der Schutz soll eine unsichere weitere Leistungsanforderung verhindern; er prüft nicht den normalen Export-Sollwert.',
'SAFE_STATE_ON_SHELLY_ERROR': 'Nur bei entsprechendem Ausfall des aktiven Shelly-HTTP-Netzleistungswegs. Wird stattdessen SMA direkt genutzt, hat dieser seinen eigenen Frische- und Schutzvertrag.',
'SOC_STALE_TIMEOUT_SECONDS': 'Nur für die Frische des Zendure-Akku-Ladezustands. Ein veralteter Wert darf nicht als Grundlage für weiter erlaubte Entladung dienen.',
'ZENDURE_POWER_STALE_TIMEOUT_SECONDS': 'Nur für das Alter der unabhängigen Zendure-Istleistung. Ein alter Messwert bestätigt weder die Wirksamkeit eines neuen Befehls noch eine neue Ladung.',
'HEADLESS_MODE': 'Nur für die Auslieferung der Weboberflächen. Im Headless-Modus bleibt der Controller nicht automatisch abgeschaltet; für einen Eingriff in die Steuerung sind andere Einstellungen zuständig.',
'WEB_HOST': 'Nur für die Netzwerkadresse, an die der ZEC-Webserver bindet. Eine falsche Bind-Adresse kann den Webzugriff verhindern, nicht die Batteriebelastung reduzieren.',
'WEB_PORT': 'Nur für die Erreichbarkeit der Status-, Graph- und Einstellungsseiten. Ein anderer Port benötigt passende Netz-/Dienstkonfiguration und verändert keinen Regelwert.',
'ZENDURE_MQTT_AFTER_RESTART_GRACE_SECONDS': 'Nur in der begrenzten Wiederanlaufphase nach Broker- oder MQTT-Neustart. Ein kurzfristig fehlendes Telegramm darf nicht als langanhaltender Defekt fehlgedeutet werden.',
'ZENDURE_MQTT_CRITICAL_GROUP_STALE_SECONDS': 'Nur für die Diagnose kritischer Zendure-MQTT-Gruppen. Zu alte Gruppen können nicht als frischer Sensorwert gelten, auch wenn andere Topics noch eintreffen.',
})

# Two especially easy-to-misread regulation controls need a direct comparison.
FAST_CAPTURE_PLAIN = MappingProxyType({
 'HARVEST_FAST_CAPTURE_MODE': {
  'short': ('Fast Capture kann zusätzlichen Solarüberschuss schneller für die Zendure-Ladung nutzen, wenn der Primärspeicher nachweislich voll ist und praktisch nicht mehr lädt oder fast seine Ladeleistungsgrenze erreicht. ' 
            '„Aus“: keine zusätzliche Ladeanforderung, die normale Automatik bleibt erhalten. „Shadow (nur Diagnose)“: berechnet Möglichkeiten, ohne die Ladeanforderung zu ändern. „Aktiv“: darf innerhalb aller Schutzgrenzen zusätzliches Laden anfordern.'),
  'purpose': ('Die normale AUTO-Regelung bildet zuerst ihre Ladeanforderung aus Netzabweichung, Glättung und begrenzter Änderung pro Regelzyklus. ' 
              'Erst danach darf Fast Capture bei bestätigtem Restexport einen zusätzlichen positiven Ladeanteil daraufsetzen. ' 
              'Dessen Anstieg ist auf 400 Watt pro Sekunde begrenzt; bei normalem Rückgang wird er mit höchstens 100 Watt pro Sekunde abgebaut. ' 
              'Das sind Raten pro tatsächlich vergangener Sekunde, nicht jeweils 400 oder 100 Watt pro Regelzyklus. ' 
              'Bei plötzlichem Netzbezug, Messwertausfall, unerwünschtem Umladen oder anderem Schutzgrund fällt der Zusatz sofort weg. ' 
              'Eine tatsächliche Zunahme der Ladeleistung ist nicht garantiert: Geräteleistung, Ladezustand und alle Schutzvorgaben können sie begrenzen.'),
  'when': ('Nur im AUTO-Modus, bei bestätigter Netzeinspeisung und frischen Netz-, Primärspeicher- und Zendure-Messwerten. ' 
           'Der Primärspeicher muss entweder voll und praktisch ohne Ladeleistung sein oder seine bekannte Ladeleistungsgrenze fast erreichen. ' 
           'Ist diese Lage nicht sicher, bleibt die Zusatzfunktion ohne Wirkung; normale AUTO-Ladung läuft unverändert weiter.'),
 },
 'MAX_POWER_STEP_W': {
  'short': ('Begrenzt die normale Änderung des Zendure-Leistungsziels je Regelzyklus nach der Glättung. ' 
            'Ein kleiner Wert reagiert ruhiger, ein großer schneller; das ist keine zusätzliche Watt-pro-Sekunde-Grenze.'),
  'purpose': ('Dieser Wert begrenzt nach der Glättung, wie stark das normale Lade- oder Entladeziel in einem Regelzyklus verändert werden darf. ' 
              'Wenn Fast Capture ausdrücklich aktiv und zulässig ist, kann anschließend ein eigener zusätzlicher Ladeanteil entstehen. ' 
              'Dessen Anstieg ist auf 400 Watt pro Sekunde begrenzt, und er wird normalerweise mit 100 Watt pro Sekunde zurückgenommen. ' 
              'Die beiden Grenzen werden nicht einfach als feste Wattzahl pro Zyklus addiert. ' 
              'Weder eine höhere Schrittgrenze noch Fast Capture überstimmen Ladezustand, tatsächliche Geräteleistung, Schutzfunktionen oder Messdatenqualität. ' 
              'Größere Schritte sind keine generelle Empfehlung; sie können die Regelung unruhiger machen.'),
  'when': ('Bei normalen Lade- und Entladekorrekturen im AUTO-Betrieb nach der Glättung. ' 
           'Die eigene Fast-Capture-Zusatzrate wirkt nur im separat freigegebenen Aktivfall. ' 
           'Sicherheitsbedingte Abbrüche und Neutralisierung sind keine gewöhnlichen, langsam begrenzten Regeländerungen.'),
 },
})
