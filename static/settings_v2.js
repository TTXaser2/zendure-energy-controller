(() => {
  'use strict';

  function storageGet(key, fallback) {
    try { return window.localStorage.getItem(key) ?? fallback; } catch (_) { return fallback; }
  }
  function storageSet(key, value) {
    try { window.localStorage.setItem(key, value); } catch (_) {}
  }

  const app = {
    model: null,
    mode: storageGet('zecSettingsMode', 'standard'),
    category: null,
    draft: new Map(),
    secretOps: new Map(),
    preview: null,
    previewInFlight: false,
    statusInFlight: false,
    previewScrollY: 0,
    drawerScrollY: 0,
    compoundDraft: new Map(),
    validationIssues: [],
    modalMode: 'preview',
    adminAction: null,
    configImportInspection: null,
    helpTrigger: null,
    helpReturnFocus: null,
    pendingHelpTarget: null,
    helpScrollY: 0,
  };
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => Array.from(root.querySelectorAll(s));

  const CATEGORY_PATHS = {
    'Betriebsart & manuelle Steuerung': '<path d="M4 7h10M18 7h2M10 17h10M4 17h2"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="17" r="2"/>',
    'Leistungsgrenzen & SOC-Schutz': '<path d="M12 3 4.5 6v5.5c0 4.5 3 7.4 7.5 9.5 4.5-2.1 7.5-5 7.5-9.5V6Z"/><path d="M8 13h8M12 9v8"/>',
    'Nachtbetrieb': '<path d="M19 15.5A8 8 0 0 1 8.5 5a7 7 0 1 0 10.5 10.5Z"/>',
    'AUTO-Regelung': '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 2v3M22 12h-3M12 22v-3M2 12h3"/>',
    'Primärspeicher & SMA': '<rect x="3" y="6" width="17" height="12" rx="2"/><path d="M20 10h2v4h-2M7 10h6M10 7v6"/>',
    'Harvest / Restüberschuss': '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.9 4.9 7 7M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1"/>',
    'Cross-Charge-Schutz': '<path d="M4 8h13l-3-3M20 16H7l3 3"/>',
    'Kommandowirkung & Resync': '<path d="M4.5 9A8 8 0 0 1 18 5.5M18 2v4h-4M19.5 15A8 8 0 0 1 6 18.5M6 22v-4h4"/>',
    'Zendure-Geräte': '<rect x="4" y="3" width="16" height="18" rx="3"/><path d="M8 7h8M8 17h8M10 11h4"/>',
    'Schnittstellen & Datenquellen': '<circle cx="6" cy="12" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="18" cy="18" r="2"/><path d="m8 11 8-4M8 13l8 4"/>',
    'Messdaten & Speicherung': '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
    'System & Diagnose': '<path d="M4 18h16M6 15V9M10 15V5M14 15v-3M18 15V7"/>',
  };

  function icon(name) {
    const body = CATEGORY_PATHS[name] || CATEGORY_PATHS['System & Diagnose'];
    return `<svg class="settings-category-svg" viewBox="0 0 24 24" aria-hidden="true">${body}</svg>`;
  }
  function esc(v) {
    return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  function same(a, b) { return JSON.stringify(a) === JSON.stringify(b); }

  const NIGHT_COMPOUNDS = {
    start: {hour:'NIGHT_START_HOUR', minute:'NIGHT_START_MINUTE', label:'Startzeit des Nachtmodus', description:'Beginn des festen Nachtfensters im Format HH:MM.'},
    end: {hour:'NIGHT_END_HOUR', minute:'NIGHT_END_MINUTE', label:'Endzeit des Nachtmodus', description:'Ende des festen Nachtfensters im Format HH:MM.'},
  };
  const NIGHT_KEYS = new Set(Object.values(NIGHT_COMPOUNDS).flatMap(x => [x.hour, x.minute]));
  function nightCompoundForKey(key) {
    return Object.entries(NIGHT_COMPOUNDS).find(([, pair]) => pair.hour === key || pair.minute === key)?.[0] || null;
  }
  function formatTime(hour, minute) {
    return `${String(Number(hour)).padStart(2,'0')}:${String(Number(minute)).padStart(2,'0')}`;
  }
  function parseTime(value) {
    const match = /^(\d{2}):(\d{2})$/.exec(String(value || '').trim());
    if (!match) return null;
    const hour = Number(match[1]);
    const minute = Number(match[2]);
    if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return null;
    return {hour, minute, text:`${match[1]}:${match[2]}`};
  }
  function csrf() { return $('meta[name="zec-csrf"]')?.content || app.model?.csrf_token || ''; }
  async function api(url, opt = {}) {
    const headers = Object.assign({'Accept':'application/json'}, opt.headers || {});
    if (opt.method && opt.method !== 'GET') {
      headers['Content-Type'] = 'application/json';
      headers['X-CSRF-Token'] = csrf();
    }
    const response = await fetch(url, Object.assign({cache:'no-store', credentials:'same-origin'}, opt, {headers}));
    let data = {};
    try { data = await response.json(); }
    catch (_) { data = {message: await response.text()}; }
    if (!response.ok) {
      const error = new Error(data.detail || data.error || data.message || `HTTP ${response.status}`);
      error.status = response.status;
      error.data = data;
      throw error;
    }
    return data;
  }
  function settings() {
    return app.model.categories.flatMap(c => c.sections.flatMap(section => section.settings.map(x => Object.assign({_category:c.name, _section:section.name}, x))));
  }
  function settingByKey(key) { return settings().find(s => s.key === key); }
  function relationLabel(relation) {
    return ({REQUIRES:'benötigt',ENABLES:'aktiviert',GATES:'gesteuert durch',LIMITS:'begrenzt durch',OVERRIDES:'übersteuert',OVERRIDDEN_BY:'übersteuert durch',PAIRED_WITH:'gehört zusammen mit',SOURCE_FOR:'Quelle/Bezugswert',DIAGNOSTIC_ONLY:'nur Diagnose',RESTART_COUPLED:'Neustart gekoppelt'})[relation] || relation || 'verknüpft mit';
  }
  function helpButton(kind, id, label) {
    const attr = kind === 'setting' ? `data-help-setting="${esc(id)}"` : (kind === 'category' ? `data-help-category="${esc(id)}"` : `data-help-section="${esc(id)}"`);
    return `<button type="button" class="help-info-button" ${attr} aria-label="Hilfe zu ${esc(label)}" title="Erklärung anzeigen">i</button>`;
  }
  function currentByKey(key) {
    const spec = settingByKey(key);
    return spec ? currentValue(spec) : undefined;
  }
  function guidanceForSetting(s) {
    const messages = [];
    if (!dependencyVisible(s)) {
      const rule = s.dependency_rule || {};
      const driver = settingByKey(rule.key);
      const driverLabel = driver?.label || rule.key || 'übergeordnete Einstellung';
      let text = `Derzeit ohne Wirkung: ${driverLabel} erfüllt die Aktivierungsbedingung nicht.`;
      if (s.key.startsWith('MANUAL_FIXED_') || s.key.startsWith('MANUAL_') && s.key.endsWith('_AFTER_TARGET')) text = 'Gespeichert, aber derzeit inaktiv: Der zugehörige feste manuelle Modus ist nicht ausgewählt.';
      else if (s.key.startsWith('NIGHT_')) text = 'Gespeichert, aber derzeit inaktiv: Nachtbetrieb ist ausgeschaltet.';
      else if (s.key.startsWith('ZENDURE_LOCAL_API_') && s.key !== 'ZENDURE_LOCAL_API_ENABLED') text = 'Derzeit ohne Wirkung: Die lokale Zendure-API ist ausgeschaltet.';
      else if (s.key.startsWith('MEASUREMENT_') && currentByKey('MEASUREMENT_LOG_MODE') === 'off') text = 'Derzeit ohne Wirkung: Measurement-Logging ist ausgeschaltet.';
      messages.push({kind:'inactive', text});
    }
    const overridePairs = {
      HARVEST_PRIMARY_CHARGE_FLOOR_RATIO:'HARVEST_PRIMARY_CHARGE_FLOOR_W',
      HARVEST_PRIMARY_CHARGE_RESTART_RATIO:'HARVEST_PRIMARY_CHARGE_RESTART_W',
      HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_RATIO:'HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W',
    };
    const override = overridePairs[s.key];
    if (override && Number(currentByKey(override) || 0) > 0) messages.push({kind:'override', text:`Derzeit übersteuert: ${settingByKey(override)?.label || override} ist positiv gesetzt; dieser Ratio-Wert ist für die effektive Schwelle nicht wirksam.`});
    const reverse = Object.entries(overridePairs).find(([,w]) => w === s.key)?.[0];
    if (reverse && Number(currentValue(s) || 0) > 0) messages.push({kind:'effective', text:`Absolute W-Quelle aktiv: ${settingByKey(reverse)?.label || reverse} wird für diese Schwelle übersteuert.`});
    if (s.key.startsWith('SECOND_BATTERY_') && currentByKey('SECOND_BATTERY_SOURCE_PROFILE') === 'evcc_standard' && ['SECOND_BATTERY_POWER_TOPIC','SECOND_BATTERY_SOC_TOPIC','SECOND_BATTERY_CAPACITY_TOPIC'].includes(s.key)) messages.push({kind:'inactive',text:'Für Profil EVCC Standard nicht verwendet; die Topics werden aus dem EVCC-Basis-Topic abgeleitet.'});
    if (s.key === 'SECOND_BATTERY_EVCC_BASE_TOPIC' && currentByKey('SECOND_BATTERY_SOURCE_PROFILE') === 'custom') messages.push({kind:'inactive',text:'Für das benutzerdefinierte Profil nicht verwendet.'});
    return messages;
  }
  function guidanceHtml(s) {
    const messages = guidanceForSetting(s);
    if (!messages.length) return '';
    return `<div class="setting-guidance">${messages.map(m=>`<div class="guidance-line ${esc(m.kind)}"><span class="guidance-icon" aria-hidden="true">${m.kind==='override'?'↳':m.kind==='effective'?'✓':'i'}</span><span>${esc(m.text)}</span></div>`).join('')}</div>`;
  }
  function categoryGuidance(categoryName) {
    const n = (key) => Number(currentByKey(key));
    const notices = [];
    if (categoryName === 'AUTO-Regelung') {
      if (n('DEADBAND_W') < 20 && n('CONTROL_GAIN') > .5 && n('MAX_POWER_STEP_W') > 300) notices.push({kind:'warning',text:'Aggressive Kombination: sehr kleine Totzone, hoher Gain und großer Leistungsschritt können die Regelung unnötig nervös machen.'});
      if (n('MOVING_AVERAGE_SAMPLES') > 30) notices.push({kind:'warning',text:'Großes Mittelwertfenster: Die Regelung reagiert deutlich träger auf reale Laständerungen.'});
      if (n('INTERVAL_SECONDS') <= 1 && n('MOVING_AVERAGE_SAMPLES') <= 2 && n('SMOOTHING_FACTOR') >= .8) notices.push({kind:'warning',text:'Sehr schnelle Stellkonfiguration: kurzes Intervall, kleines Mittelwertfenster und geringe Glättung erhöhen die Reaktionsaktivität.'});
      if (n('MIN_COMMAND_CHANGE_W') > n('MAX_POWER_STEP_W')) notices.push({kind:'warning',text:'Mindest-Commandänderung ist größer als der maximale Leistungsschritt; einzelne Schritte können häufig unterdrückt werden.'});
      if (n('MIN_COMMAND_CHANGE_W') > 2*n('DEADBAND_W')) notices.push({kind:'info',text:'Die Command-Auflösung ist mehr als doppelt so groß wie die Totzone; Feinkorrekturen können verzögert publiziert werden.'});
    }
    if (categoryName === 'Harvest / Restüberschuss') {
      const interval = n('INTERVAL_SECONDS');
      ['HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_SECONDS','REST_SURPLUS_ENTRY_CONFIRM_SECONDS'].forEach(key=>{
        if (n(key) < 2*interval) notices.push({kind:'warning',text:`${settingByKey(key)?.label || key}: Bestätigungszeit liegt unter zwei Regelintervallen; kurze Ereignisse können früh qualifizieren.`});
        if (n(key) > 180) notices.push({kind:'warning',text:`${settingByKey(key)?.label || key}: Bestätigungszeit über 180 s kann kurze nutzbare Harvestfenster verpassen.`});
      });
      if (n('MIN_COMMAND_CHANGE_W') > n('REST_SURPLUS_MIN_EXPORT_W')) notices.push({kind:'warning',text:'Command-Auflösung ist größer als die Restüberschuss-Entry-Schwelle; kleine Harvest-Korrekturen können unterdrückt werden.'});
      if (n('REST_SURPLUS_MIN_EXPORT_W') < n('DEADBAND_W')) notices.push({kind:'info',text:'Restüberschuss-Entry liegt unter der normalen AUTO-Totzone. Das ist als Harvest-Speziallage zulässig; die Entry-Schwelle ist kein Restexportziel.'});
      if (n('MAX_POWER_STEP_W') < n('REST_SURPLUS_MIN_EXPORT_W')) notices.push({kind:'warning',text:'Der maximale Leistungsschritt liegt unter der Harvest-Entry-Schwelle; Restüberschuss kann bewusst langsamer aufgenommen werden.'});
      if (n('SMOOTHING_FACTOR') < .10 || interval >= 10) notices.push({kind:'warning',text:'Harvest-Reaktion ist durch starke Glättung oder langes Regelintervall deutlich träge.'});
    }
    if (categoryName === 'Cross-Charge-Schutz' && n('SECOND_BATTERY_STALE_TIMEOUT_SECONDS') < 5) notices.push({kind:'warning',text:'Sehr kurze Zweitbatterie-Aktualität: kurze MQTT-Pausen können den Schutz unnötig früh blockieren.'});
    if (categoryName === 'Kommandowirkung & Resync' && n('COMMAND_RESYNC_COOLDOWN_SECONDS') === 0) notices.push({kind:'warning',text:'Resync-Wartezeit ist 0 s. Dadurch können Wiederherstellungs-Publishes sehr häufig wiederholt werden.'});
    if (categoryName === 'Nachtbetrieb' && currentByKey('NIGHT_DISCHARGE_ENABLED') === true) {
      if (n('NIGHT_DISCHARGE_POWER_W') <= 0) notices.push({kind:'warning',text:'Nachtbetrieb ist aktiviert, aber die feste Nachtleistung ist 0 W. Die serverseitige Prüfung wird diese Kombination blockieren.'});
      if (n('NIGHT_DISCHARGE_POWER_W') > n('MAX_DISCHARGE_POWER_W')) notices.push({kind:'warning',text:'Die feste Nachtleistung liegt über der globalen maximalen Entladeleistung und wird beim Preview blockiert.'});
      const reserve = currentByKey('NIGHT_DISCHARGE_STOP_SOC_PERCENT');
      if (reserve !== null && reserve !== '' && Number(reserve) < n('MIN_SOC_PERCENT')) notices.push({kind:'warning',text:'Der Nacht-Reserve-SOC liegt unter dem globalen Mindest-SOC und wird beim Preview blockiert.'});
      if (reserve !== null && reserve !== '' && Number(reserve) > n('MAX_SOC_PERCENT')) notices.push({kind:'warning',text:'Der Nacht-Reserve-SOC liegt über MAX_SOC; die feste Nachtentladung kann dadurch sehr früh oder gar nicht starten.'});
    }
    if (categoryName === 'Schnittstellen & Datenquellen' && currentByKey('ZENDURE_LOCAL_API_ENABLED') === true) {
      const interval = n('INTERVAL_SECONDS');
      if (n('ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS') >= .75*interval) notices.push({kind:'warning',text:'Local-API-Control-Timeout erreicht mindestens 75 % des Regelintervalls; bei Nutzung im relevanten Pfad steigt das Laufzeitrisiko.'});
      if (n('ZENDURE_LOCAL_API_TIMEOUT_SECONDS') >= interval) notices.push({kind:'warning',text:'Der volle Local-API-Timeout ist mindestens so lang wie das Regelintervall. Der Zugriff läuft asynchron, kann aber Snapshot-Aktualisierung verzögern.'});
    }
    return notices;
  }
  function categoryGuidanceHtml(categoryName) {
    const notices = categoryGuidance(categoryName);
    if (!notices.length) return '';
    return `<div class="guided-notices" aria-label="Geführte Hinweise">${notices.map(n=>`<div class="notice ${esc(n.kind)} guided-notice"><b>${n.kind==='warning'?'Hinweis zur Kombination':'Einordnung'}:</b> ${esc(n.text)}</div>`).join('')}</div>`;
  }
  function currentValue(s) { return app.draft.has(s.key) ? app.draft.get(s.key) : s.configured; }
  function dirtyCount() {
    let count = Array.from(app.draft.keys()).filter(key => !NIGHT_KEYS.has(key)).length;
    if (compoundDirty('start')) count += 1;
    if (compoundDirty('end')) count += 1;
    count += Array.from(app.secretOps.values()).filter(x => x.op !== 'keep').length;
    return count;
  }
  function groups() {
    const order = ['A. Betrieb','B. Regelung & Speicherstrategie','C. Geräte & Schnittstellen','D. Daten, System & Diagnose'];
    const grouped = new Map(order.map(g => [g, []]));
    app.model.categories.forEach(c => {
      if (!grouped.has(c.group)) grouped.set(c.group, []);
      grouped.get(c.group).push(c);
    });
    return new Map(Array.from(grouped.entries()).filter(([, cats]) => cats.length));
  }
  function categoryDrawerIsMobile() {
    return window.matchMedia('(max-width: 820px)').matches;
  }
  function lockCategoryDrawerScroll() {
    if (document.body.classList.contains('category-drawer-open')) return;
    const main = $('.settings-main');
    app.drawerScrollY = categoryDrawerIsMobile() ? (main?.scrollTop || 0) : (window.scrollY || document.documentElement.scrollTop || 0);
    document.body.classList.add('category-drawer-open');
  }
  function unlockCategoryDrawerScroll() {
    if (!document.body.classList.contains('category-drawer-open')) return;
    document.body.classList.remove('category-drawer-open');
    if (categoryDrawerIsMobile()) { const main = $('.settings-main'); if (main) main.scrollTop = app.drawerScrollY || 0; }
    else window.scrollTo({top:app.drawerScrollY, left:0, behavior:'auto'});
  }
  function setCategoryDrawerOpen(open) {
    const sidebar = $('.settings-sidebar');
    const button = $('#mobileMenu');
    const backdrop = $('#categoryDrawerBackdrop');
    const active = categoryDrawerIsMobile() && !!open;
    sidebar?.classList.toggle('open', active);
    if (active) lockCategoryDrawerScroll(); else unlockCategoryDrawerScroll();
    button?.setAttribute('aria-expanded', String(active));
    sidebar?.setAttribute('aria-hidden', String(categoryDrawerIsMobile() ? !active : false));
    if (backdrop) backdrop.hidden = !active;
  }
  function scrollCategoryToTop() {
    requestAnimationFrame(() => {
      const main = $('.settings-main');
      if (main) main.scrollTop = 0;
      if (categoryDrawerIsMobile()) {
        window.scrollTo({top:0, left:0, behavior:'auto'});
        document.documentElement.scrollTop = 0;
        document.body.scrollTop = 0;
      }
    });
  }
  function selectCategory(name) {
    app.category = name;
    setCategoryDrawerOpen(false);
    $('#mobileCategories')?.removeAttribute('open');
    render();
    scrollCategoryToTop();
  }
  function renderNav() {
    const nav = $('#settingsNav');
    const mobile = $('#mobileCategoryList');
    nav.innerHTML = '';
    mobile.innerHTML = '';
    groups().forEach((cats, group) => {
      nav.insertAdjacentHTML('beforeend', `<div class="nav-group">${esc(group)}</div>`);
      mobile.insertAdjacentHTML('beforeend', `<div class="mobile-category-group"><strong>${esc(group)}</strong></div>`);
      cats.forEach(c => {
        const count = categoryVisibleCount(c);
        const content = `<span class="category-link-icon">${icon(c.name)}</span><span>${esc(c.name)}</span><span class="count">${count}</span>`;
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `category-link${app.category === c.name ? ' active' : ''}`;
        button.innerHTML = content;
        button.onclick = () => selectCategory(c.name);
        nav.appendChild(button);
        const mobileButton = button.cloneNode(true);
        mobileButton.onclick = () => selectCategory(c.name);
        mobile.appendChild(mobileButton);
      });
    });
  }
  function dependencyVisible(s) {
    const rule = s.dependency_rule;
    if (!rule) return true;
    const dep = settingByKey(rule.key);
    if (!dep) return true;
    const value = currentValue(dep);
    if (Object.prototype.hasOwnProperty.call(rule, 'equals')) return same(value, rule.equals);
    if (Object.prototype.hasOwnProperty.call(rule, 'not_equals')) return !same(value, rule.not_equals);
    return true;
  }
  function settingVisibleInMode(s) {
    const firstInstallRequired = app.model?.status?.startup_mode === 'FIRST_INSTALL_SETUP' && s.required_first_install;
    if (firstInstallRequired) return true;
    if (s.expert && app.mode !== 'expert') return false;
    if (!dependencyVisible(s) && app.mode === 'standard') return false;
    return true;
  }
  function categoryVisibleCount(category) {
    let count = 0;
    category.sections.forEach(section => section.settings.forEach(s => {
      if (!settingVisibleInMode(s)) return;
      if (s.key === NIGHT_COMPOUNDS.start.minute || s.key === NIGHT_COMPOUNDS.end.minute) return;
      count += 1;
    }));
    return count;
  }
  function expertHiddenCount(category) {
    const firstInstall = app.model?.status?.startup_mode === 'FIRST_INSTALL_SETUP';
    return category.sections.reduce((total, section) => total + section.settings.filter(s => s.expert && !(firstInstall && s.required_first_install)).length, 0);
  }
  function nightText(kind) {
    const pair = NIGHT_COMPOUNDS[kind];
    if (app.compoundDraft.has(kind)) return app.compoundDraft.get(kind);
    return formatTime(currentValue(settingByKey(pair.hour)), currentValue(settingByKey(pair.minute)));
  }
  function compoundDirty(kind) {
    const pair = NIGHT_COMPOUNDS[kind];
    if (app.compoundDraft.has(kind)) {
      const configured = formatTime(settingByKey(pair.hour).configured, settingByKey(pair.minute).configured);
      return app.compoundDraft.get(kind) !== configured;
    }
    return app.draft.has(pair.hour) || app.draft.has(pair.minute);
  }
  function issueForKeys(keys) {
    const all = [];
    keys.forEach(key => {
      const spec = settingByKey(key);
      (spec?.issues || []).forEach(issue => all.push(issue));
    });
    app.validationIssues.forEach(issue => {
      if ((issue.keys || []).some(key => keys.includes(key))) all.push(issue);
    });
    return all;
  }
  function issueHtml(issues) {
    const visible = issues.filter(issue => issue.blocking || issue.severity === 'warning');
    if (!visible.length) return '';
    return `<div class="field-issues">${visible.map(issue=>`<div class="field-issue ${esc(issue.severity || 'error')}">${esc(issue.message || 'Die Eingabe ist nicht zulässig.')}</div>`).join('')}</div>`;
  }
  function clearValidationIssuesForKeys(keys) {
    app.validationIssues = app.validationIssues.filter(issue => !(issue.keys || []).some(key => keys.includes(key)));
  }
  function addValidationIssue(issue) {
    app.validationIssues.push(issue);
  }
  function validateSingleSetting(spec, value, rawValue = null) {
    const issues = [];
    const fail = (code, message) => issues.push({code, severity:'error', blocking:true, keys:[spec.key], message});
    if (['int','optional_int','float'].includes(spec.value_type) && value !== null) {
      if (typeof value !== 'number' || !Number.isFinite(value)) fail('NUMBER_INVALID', `${spec.label}: Bitte eine gültige Zahl eingeben.`);
      else {
        if (spec.minimum !== null && value < spec.minimum) fail('VALUE_BELOW_MIN', `${spec.label}: Der Wert muss mindestens ${spec.minimum}${spec.unit?` ${spec.unit}`:''} betragen.`);
        if (spec.maximum !== null && value > spec.maximum) fail('VALUE_ABOVE_MAX', `${spec.label}: Der Wert darf höchstens ${spec.maximum}${spec.unit?` ${spec.unit}`:''} betragen.`);
      }
    }
    if (spec.value_type === 'enum' && !spec.options.some(option => same(option.value, value))) fail('ENUM_INVALID', `${spec.label}: Der gewählte Wert ist nicht zulässig.`);
    if (spec.codec_id === 'optional_int_zero_none') {
      const raw = String(rawValue ?? value ?? '').trim();
      if (raw && !/^[+-]?\d+$/.test(raw)) fail('NUMBER_INVALID', `${spec.label}: Bitte eine ganze Zahl oder einen leeren Wert eingeben.`);
    }
    if ((spec.key === 'SMA_ENERGY_METER_SERIAL' || spec.key === 'SMA_ENERGY_METER_SUSY_ID')) {
      const raw = String(rawValue ?? value ?? '').trim();
      if (raw && !/^\d+$/.test(raw)) fail('NUMBER_INVALID', `${spec.label}: Bitte nur Ziffern eingeben oder das Feld leer lassen.`);
    }
    return issues;
  }
  function nightCompoundHtml(kind) {
    const pair = NIGHT_COMPOUNDS[kind];
    const hourSpec = settingByKey(pair.hour);
    const minuteSpec = settingByKey(pair.minute);
    if (!hourSpec || !minuteSpec || !settingVisibleInMode(hourSpec)) return '';
    const dependencyOk = dependencyVisible(hourSpec);
    const disabled = !hourSpec.editable || (!dependencyOk && app.mode === 'expert');
    const issues = issueForKeys([pair.hour, pair.minute]);
    const classes = ['setting-row', compoundDirty(kind)?'dirty':'', issues.some(i=>i.blocking)?'has-error':'', !dependencyOk?'hidden-by-dependency':''].filter(Boolean).join(' ');
    const defaultText = formatTime(hourSpec.default, minuteSpec.default);
    return `<article class="${classes}" data-compound="night-${kind}" data-setting="${esc(pair.hour)}">
      <div class="setting-copy"><div class="setting-title-line"><div class="setting-label">${esc(pair.label)}</div>${helpButton('setting', pair.hour, pair.label)}</div>${app.mode==='expert'?`<div class="setting-key">${esc(pair.hour)} + ${esc(pair.minute)}</div>`:''}<div class="setting-help">${esc(hourSpec.help?.short || pair.description)}</div>${guidanceHtml(hourSpec)}</div>
      <div class="setting-editor"><div class="setting-control"><input class="night-time-input" type="text" inputmode="numeric" autocomplete="off" maxlength="5" placeholder="HH:MM" data-night-time="${kind}" value="${esc(nightText(kind))}"${disabled?' disabled':''} aria-invalid="${issues.some(i=>i.blocking)?'true':'false'}"></div>${issueHtml(issues)}<div class="field-meta"><span class="meta-pill">Zulässig: 00:00–23:59</span><span class="meta-pill">Ausgangswert dieses Releases: ${esc(defaultText)}</span><span class="meta-pill ${hourSpec.apply_class==='restart_required'?'restart':'live'}">${esc(hourSpec.apply_text || hourSpec.apply_class)}</span></div></div>
    </article>`;
  }
  function inputHtml(s) {
    const value = currentValue(s);
    const disabled = !s.editable || (!dependencyVisible(s) && app.mode === 'expert');
    const dis = disabled ? ' disabled' : '';
    let control = '';
    if (s.value_type === 'bool') {
      control = `<label class="switch"><input type="checkbox" data-key="${esc(s.key)}" ${value === true ? 'checked' : ''}${dis}><span class="switch-track"></span><span>${value === true ? 'Ein' : 'Aus'}</span></label>`;
    } else if (s.value_type === 'enum') {
      const placeholder = s.required_first_install && (value === null || value === undefined || value === '') ? '<option value="" selected disabled>Bitte auswählen …</option>' : '';
      control = `<select data-key="${esc(s.key)}"${dis}>${placeholder}${s.options.map(o => `<option value="${esc(o.value)}" ${same(value,o.value)?'selected':''}>${esc(o.label)}</option>`).join('')}</select>`;
    } else if (s.value_type === 'secret') {
      const op = app.secretOps.get(s.key) || {op:'keep'};
      control = `<div class="secret-actions"><button type="button" data-secret="keep" data-key="${esc(s.key)}" class="${op.op==='keep'?'active':''}">Behalten</button><button type="button" data-secret="replace" data-key="${esc(s.key)}" class="${op.op==='replace'?'active':''}">Ersetzen</button><button type="button" data-secret="clear" data-key="${esc(s.key)}" class="${op.op==='clear'?'active':''}">Löschen</button></div>${op.op==='replace'?`<input class="secret-input" type="password" autocomplete="new-password" data-secret-value="${esc(s.key)}" placeholder="Neues Secret" value="${esc(op.value||'')}">`:`<div class="setting-help">Secret ist ${s.secret_set?'gesetzt':'nicht gesetzt'}; der Wert wird niemals angezeigt.</div>`}`;
    } else {
      const type = ['int','optional_int','float'].includes(s.value_type) ? 'number' : 'text';
      const step = s.value_type === 'float' ? 'any' : '1';
      control = `<input type="${type}" data-key="${esc(s.key)}" value="${esc(value ?? '')}" ${type==='number'?`step="${step}" `:''}${s.minimum!==null?`min="${s.minimum}" `:''}${s.maximum!==null?`max="${s.maximum}" `:''}${dis}>`;
    }
    return `<div class="setting-control">${control}${s.unit?`<span class="unit">${esc(s.unit)}</span>`:''}</div>`;
  }
  function settingHtml(s) {
    const visible = dependencyVisible(s);
    if (!settingVisibleInMode(s)) return '';
    if (NIGHT_KEYS.has(s.key)) {
      if (s.key === NIGHT_COMPOUNDS.start.hour) return nightCompoundHtml('start');
      if (s.key === NIGHT_COMPOUNDS.end.hour) return nightCompoundHtml('end');
      return '';
    }
    const issues = issueForKeys([s.key]);
    const dirty = app.draft.has(s.key) || (app.secretOps.get(s.key)?.op && app.secretOps.get(s.key).op !== 'keep');
    const classes = ['setting-row', dirty?'dirty':'', s.pending_restart?'pending':'', issues.some(i=>i.blocking)?'has-error':'', !visible?'hidden-by-dependency':''].filter(Boolean).join(' ');
    let range = '';
    if (s.minimum !== null || s.maximum !== null) range = `Zulässig: ${s.minimum ?? '−∞'}–${s.maximum ?? '∞'}${s.unit ? ` ${s.unit}` : ''}`;
    const metas = [
      range,
      s.default_ui?.meta || '',
      (app.model?.status?.startup_mode === 'FIRST_INSTALL_SETUP' && s.required_first_install) ? 'Erstinbetriebnahme: erforderlich' : '',
      s.configured_differs_effective ? `Wirksam: ${String(s.effective)}` : '',
      s.inherited_default ? 'geerbter Ausgangswert' : '',
    ].filter(Boolean);
    const resetAction = s.editable && !s.secret_set && s.default_ui?.action ? `<button type="button" class="reset-button" data-reset="${esc(s.key)}">${esc(s.default_ui.action)}</button>` : '';
    return `<article class="${classes}" data-setting="${esc(s.key)}">
      <div class="setting-copy"><div class="setting-title-line"><div class="setting-label">${esc(s.label)}</div>${helpButton('setting', s.key, s.label)}</div>${app.mode==='expert'?`<div class="setting-key">${esc(s.key)}</div>`:''}<div class="setting-help">${esc(s.help?.short || s.description || '')}</div>${guidanceHtml(s)}</div>
      <div class="setting-editor">${inputHtml(s)}${issueHtml(issues)}<div class="field-meta">${metas.map(m=>`<span class="meta-pill">${esc(m)}</span>`).join('')}<span class="meta-pill ${s.apply_class==='restart_required'?'restart':'live'}">${esc(s.apply_text || s.apply_class)}</span>${resetAction}</div></div>
    </article>`;
  }
  function emptyStateHtml(category) {
    const expertCount = expertHiddenCount(category);
    if (app.mode === 'standard' && expertCount > 0) {
      return `<section class="empty-state category-empty-state"><strong>Keine Einstellungen im Standardmodus</strong><p>Die Parameter dieser Kategorie sind technische Schutz- und Diagnoseeinstellungen und werden nur im Expertenmodus angezeigt. Die Schutzfunktionen selbst bleiben auch im Standardmodus aktiv.</p><div class="empty-state-count">${expertCount} Experteneinstellung${expertCount===1?'':'en'} ausgeblendet</div><button id="showExpertMode" class="admin-action-button" type="button">Expertenmodus anzeigen</button></section>`;
    }
    const total = category.sections.reduce((n, section) => n + section.settings.length, 0);
    return `<section class="empty-state category-empty-state"><strong>Derzeit keine sichtbaren Einstellungen</strong><p>${total ? 'Die Einstellungen dieser Kategorie sind aufgrund der aktuellen Konfiguration oder Abhängigkeiten momentan nicht editierbar.' : 'Für diese Kategorie sind keine editierbaren Parameter registriert.'}</p></section>`;
  }
  function renderCategory() {
    const content = $('#settingsContent');
    content.classList.remove('loading');
    const c = app.model.categories.find(x => x.name === app.category) || app.model.categories[0];
    if (!c) {
      content.innerHTML = '<div class="empty-state">Keine Einstellungen.</div>';
      return;
    }
    let body = `<div class="category-panel"><div class="category-head"><div class="category-icon">${icon(c.name)}</div><div class="category-head-copy"><div class="category-title-line"><h1>${esc(c.name)}</h1>${helpButton('category', c.name, c.name)}</div><p>${esc(c.description)}</p></div></div>`;
    if (app.model.status.startup_mode === 'FIRST_INSTALL_SETUP') body += `<div class="status-banner"><b>Erstinbetriebnahme:</b> ZEC bleibt fail-closed und sendet keine Gerätekommandos, bis alle Pflichtwerte ausdrücklich festgelegt, geprüft und gespeichert wurden.</div>`;
    else if (app.model.status.config_health !== 'valid') body += `<div class="status-banner"><b>Konfigurationsstatus:</b> ${esc(app.model.status.config_health)}. Configured bleibt reparierbar; effective nutzt den letzten gültigen Snapshot.</div>`;
    if (app.model.status.pending_restart) body += `<div class="status-banner"><b>Dienstneustart ausstehend.</b> ${app.model.status.pending_restart_keys.map(esc).join(', ')}</div>`;
    body += categoryGuidanceHtml(c.name);
    let renderedSettings = 0;
    c.sections.forEach(section => {
      const rowParts = section.settings.map(settingHtml).filter(Boolean);
      renderedSettings += rowParts.length;
      if (rowParts.length) body += `<section class="section-block"><div class="section-title-line"><h2>${esc(section.name)}</h2>${section.help ? helpButton('section', `${c.name}|||${section.name}`, section.name) : ''}</div><div class="settings-grid">${rowParts.join('')}</div></section>`;
    });
    const showAdmin = c.name === 'System & Diagnose' && app.mode === 'expert';
    if (renderedSettings === 0 && !showAdmin) body += emptyStateHtml(c);
    if (showAdmin) {
      const restartDisabled = !app.model.capabilities.restart_action;
      const pointerEnabled = !!app.model.capabilities.last_good_pointer_repair;
      body += `<section class="section-block admin-actions-section"><h2>Administrative Aktionen</h2><div class="settings-grid">`;
      body += `<article class="setting-row full admin-action-card"><div class="setting-copy"><div class="setting-label">Controller-Dienst neu starten</div><div class="setting-help">Startet ausschließlich den Zendure-Controller über den geschützten, fest hinterlegten Helper neu. Ungespeicherte Änderungen werden nicht übernommen. Anschließend werden Version, Build-ID und Ready-Status geprüft.</div></div><div class="setting-editor"><button id="adminRestartAction" class="admin-action-button" type="button"${restartDisabled?' disabled':''}>Controller-Dienst neu starten</button></div></article>`;
      body += `<article class="setting-row full admin-action-card"><div class="setting-copy"><div class="setting-label">Last-Good-Konfigurationsspeicher</div><div class="setting-help">Repariert ausschließlich den internen Verweis auf einen zuvor vollständig validierten Last-Good-Konfigurationsslot. Es werden keine normalen Einstellungen geladen, geändert oder auf Default gesetzt. Die serverseitige Prüfung bestimmt den Zielslot fail-closed; das Frontend trifft keine Slotwahl.</div><div class="admin-action-status">Status: ${pointerEnabled?'Reparatur erforderlich':'kein Reparaturbedarf erkannt'}</div></div><div class="setting-editor"><button id="adminPointerRepairAction" class="admin-action-button" type="button"${pointerEnabled?'':' disabled'}>Last-Good-Pointer reparieren</button></div></article>`;
      body += `</div></section>`;
    }
    body += '</div>';
    content.innerHTML = body;
    bindInputs();
    bindHelpButtons();
    const showExpert = $('#showExpertMode');
    if (showExpert) showExpert.onclick = () => { app.mode='expert'; storageSet('zecSettingsMode', app.mode); render(); };
    const adminRestart = $('#adminRestartAction');
    if (adminRestart && !adminRestart.disabled) adminRestart.onclick = restart;
    const adminPointer = $('#adminPointerRepairAction');
    if (adminPointer && !adminPointer.disabled) adminPointer.onclick = repairPointer;
  }
  function openSearch() {
    document.body.classList.add('search-open');
    $('#searchDrawer').setAttribute('aria-hidden','false');
    setTimeout(() => $('#settingsSearch').focus(), 30);
  }
  function closeSearch() {
    document.body.classList.remove('search-open');
    $('#searchDrawer').setAttribute('aria-hidden','true');
  }
  function searchVisibleInMode(s) {
    const firstInstallRequired = app.model?.status?.startup_mode === 'FIRST_INSTALL_SETUP' && s.required_first_install;
    return firstInstallRequired || !s.expert || app.mode === 'expert';
  }
  function searchHaystack(s) {
    const help = s.help || {};
    const deps = (help.dependencies || []).map(dep => `${dep.relation || ''} ${dep.key || ''} ${settingByKey(dep.key)?.label || ''}`).join(' ');
    const optionText = (help.option_help || []).map(o => `${o.value || ''} ${o.text || ''}`).join(' ');
    return [s.label,s.key,s._category,s._section,s.description,help.short,help.extended,help.when,help.formula,help.override,help.risk,(help.search_terms||[]).join(' '),deps,optionText].filter(Boolean).join(' ').toLowerCase();
  }
  function normalizedSearchText(value) { return String(value || '').trim().toLowerCase(); }
  function searchMatch(s, query) {
    const q = normalizedSearchText(query);
    if (!q) return null;
    const label = normalizedSearchText(s.label);
    const key = normalizedSearchText(s.key);
    const category = normalizedSearchText(s._category);
    const section = normalizedSearchText(s._section);
    const terms = (s.help?.search_terms || []).map(term => normalizedSearchText(term)).filter(Boolean);
    const exactTerm = terms.find(term => term === q);
    const termContains = terms.find(term => term.includes(q));
    const short = normalizedSearchText(s.help?.short);
    const extended = normalizedSearchText(s.help?.extended);
    const when = normalizedSearchText(s.help?.when);
    const formula = normalizedSearchText(s.help?.formula);
    const override = normalizedSearchText(s.help?.override);
    const risk = normalizedSearchText(s.help?.risk);
    const deps = (s.help?.dependencies || []).map(dep => `${dep.relation || ''} ${dep.key || ''} ${settingByKey(dep.key)?.label || ''}`.toLowerCase()).join(' ');
    const options = (s.help?.option_help || []).map(o => `${o.value || ''} ${o.text || ''}`.toLowerCase()).join(' ');
    if (label === q) return {score:0, reason:null};
    if (label.startsWith(q)) return {score:5, reason:null};
    if (label.includes(q)) return {score:10, reason:null};
    if (exactTerm) return {score:15, reason:`Synonym: ${exactTerm}`};
    if (key === q) return {score:20, reason:'Config-Key'};
    if (key.includes(q)) return {score:25, reason:'Config-Key'};
    if (termContains) return {score:30, reason:`Suchbegriff: ${termContains}`};
    if (section.includes(q)) return {score:40, reason:'Abschnitt'};
    if (category.includes(q)) return {score:45, reason:'Kategorie'};
    if (short.includes(q)) return {score:60, reason:'Kurz-Hilfe'};
    if (when.includes(q)) return {score:65, reason:'Wirkbedingungen'};
    if (override.includes(q)) return {score:68, reason:'Vorrang / Überschreibung'};
    if (formula.includes(q)) return {score:70, reason:'Formel'};
    if (deps.includes(q)) return {score:72, reason:'Abhängigkeit'};
    if (options.includes(q)) return {score:74, reason:'Option'};
    if (risk.includes(q)) return {score:76, reason:'Sicherheitshinweis'};
    if (extended.includes(q) || searchHaystack(s).includes(q)) return {score:80, reason:'Hilfetext'};
    return null;
  }
  function renderSearch() {
    const query = $('#settingsSearch').value.trim().toLowerCase();
    const box = $('#searchResults');
    if (!query) { box.innerHTML = '<div class="empty-state">Suchbegriff eingeben.</div>'; return; }
    const results = settings().filter(searchVisibleInMode).map(s => ({s, match:searchMatch(s, query)})).filter(x => x.match).sort((a,b) => a.match.score - b.match.score || String(a.s.label).localeCompare(String(b.s.label),'de')).map(x => Object.assign({_searchMatch:x.match}, x.s));
    box.innerHTML = `<b>${results.length} Treffer</b>${results.map(s=>{
      const reason = s._searchMatch?.reason || null;
      const snippet = s.help?.short || s.description || '';
      return `<button class="search-result" data-result="${esc(s.key)}"><span><strong>${esc(s.label)}</strong><small>${esc(snippet)}</small>${reason?`<em class="search-reason">gefunden über: ${esc(reason)}</em>`:''}</span><span class="result-category">${esc(s._category)}<br>${esc(s._section)}</span></button>`;
    }).join('')}`;
    $$('[data-result]').forEach(el => el.onclick = () => {
      const setting = settingByKey(el.dataset.result);
      app.category = setting._category;
      closeSearch();
      render();
      setTimeout(() => {
        const target = targetForSettingKey(setting.key);
        target?.scrollIntoView({behavior:'smooth',block:'center'});
        target?.classList.add('guided-target');
        setTimeout(()=>target?.classList.remove('guided-target'), 1800);
      }, 50);
    });
  }
  function helpSection(title, content, extraClass = '') {
    if (!content) return '';
    return `<section class="help-section ${esc(extraClass)}"><h3>${esc(title)}</h3>${content}</section>`;
  }
  function helpText(text) { return text ? `<p>${esc(text)}</p>` : ''; }
  function helpHandbook(ref) {
    const links = [];
    if (ref?.url) links.push(`<a class="handbook-link" href="${esc(ref.url)}" target="_blank" rel="noopener">Im Handbuch: ${esc(ref.section_title)} · Seite ${esc(ref.page)}</a>`);
    const glossary = app.model?.glossary;
    if (glossary?.url) links.push(`<a class="handbook-link" href="${esc(glossary.url)}" target="_blank" rel="noopener">Begriffe & Abkürzungen · Seite ${esc(glossary.page)}</a>`);
    return links.length ? `<div class="help-handbook-links">${links.join('')}</div>` : '';
  }
  function defaultHelpHtml(s) {
    const meta = String(s.default_ui?.meta || '').trim();
    const action = String(s.default_ui?.action || '').trim();
    const rows = [];
    rows.push(`<div><b>Einordnung</b><span>${esc(meta || 'Kein allgemeines Reset-Ziel verfügbar.')}</span></div>`);
    if (action) rows.push(`<div><b>Verfügbare Aktion</b><span>${esc(action)}</span></div>`);
    else rows.push('<div><b>Reset</b><span>Für diese Einstellung gibt es bewusst kein allgemeines Reset-Ziel.</span></div>');
    return `<div class="help-kv-list">${rows.join('')}</div>`;
  }
  function dependencyHelpHtml(s) {
    const deps = s.help?.dependencies || [];
    if (!deps.length) return '';
    const intro = s.help?.dependency_help ? `<p>${esc(s.help.dependency_help)}</p>` : '';
    const items = deps.map(dep => {
      const target = settingByKey(dep.key);
      const label = target?.label || dep.key;
      const tech = app.mode === 'expert' ? `<span class="dep-key">${esc(dep.key)}</span>` : '';
      if (!target) return `<div class="dependency-row static"><span>${esc(relationLabel(dep.relation))}</span><b>${esc(label)}</b>${tech}</div>`;
      return `<button type="button" class="dependency-row" data-help-dependency="${esc(dep.key)}"><span>${esc(relationLabel(dep.relation))}</span><b>${esc(label)}</b>${tech}</button>`;
    }).join('');
    return `${intro}<div class="dependency-list">${items}</div>`;
  }
  function optionHelpHtml(s) {
    const options = s.help?.option_help || [];
    if (!options.length) return '';
    return `<div class="help-kv-list">${options.map(o=>`<div><b>${esc(o.value)}</b><span>${esc(o.text)}</span></div>`).join('')}</div>`;
  }
  function effectHelpHtml(s) {
    const h = s.help || {};
    const rows = [];
    if (h.effect_increase) rows.push(['Wert erhöhen', h.effect_increase]);
    if (h.effect_decrease) rows.push(['Wert verringern', h.effect_decrease]);
    if (h.effect_enable) rows.push(['Einschalten', h.effect_enable]);
    if (h.effect_disable) rows.push(['Ausschalten', h.effect_disable]);
    if (!rows.length) return '';
    return `<div class="help-kv-list">${rows.map(([k,v])=>`<div><b>${esc(k)}</b><span>${esc(v)}</span></div>`).join('')}</div>`;
  }
  function validationHelpHtml(s) {
    const rows = [];
    if (s.minimum !== null || s.maximum !== null) rows.push(`<div><b>Wertebereich</b><span>${esc(s.minimum ?? '−∞')} bis ${esc(s.maximum ?? '∞')}${s.unit?` ${esc(s.unit)}`:''}</span></div>`);
    if (s.options?.length) rows.push(`<div><b>Zulässige Werte</b><span>${s.options.map(o=>esc(o.label)).join(' · ')}</span></div>`);
    if (s.validation_text) rows.push(`<div><b>Serverseitige Validierungsregel</b><span>${esc(s.validation_text)}</span></div>`);
    return rows.length ? `<div class="help-kv-list">${rows.join('')}</div>` : '';
  }
  function exampleHelpHtml(example) {
    if (!example) return '';
    return `<div class="help-example"><b>${esc(example.title)}</b>${(example.inputs||[]).length?`<ul>${example.inputs.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:''}<div class="help-formula">${esc(example.calculation)}</div><div class="help-example-result">${esc(example.result)}</div><p>${esc(example.interpretation)}</p></div>`;
  }
  function technicalHelpHtml(s) {
    if (app.mode !== 'expert') return '';
    const refs = s.help?.evidence_refs || [];
    const validators = s.validator_ids || [];
    const rows = [
      ['Config-Key', s.key], ['Typ / Codec', `${s.value_type} / ${s.codec_id}`],
      ['Art der Wirksamkeit', s.apply_class], ['Änderungsrisiko', s.risk || 'nicht klassifiziert'],
      ['Validatoren', validators.length ? validators.join(', ') : 'keine setting-spezifische ID'],
      ['Vertragsquellen', refs.length ? refs.join(' · ') : 'SettingsRegistry'],
    ];
    return `<div class="technical-contract">${rows.map(([k,v])=>`<div><span>${esc(k)}</span><code>${esc(v)}</code></div>`).join('')}</div>`;
  }
  function settingHelpBody(s) {
    const h = s.help || {};
    const dynamicWhen = guidanceForSetting(s).map(x=>x.text).join(' ');
    const when = dynamicWhen || h.when || (s.dependency_rule ? 'Die Einstellung wirkt nur, wenn die zugehörige Aktivierungs- oder Quellbedingung erfüllt ist.' : 'Die Einstellung wirkt gemäß der unten angegebenen Wirksamkeitsart und den fachlichen Schutzbedingungen.');
    const body = [
      `<div class="help-context"><span>${esc(s._category)}</span><span>›</span><span>${esc(s._section)}</span>${h.level==='rich'?'<span class="help-level rich">RICH</span>':'<span class="help-level">BASE</span>'}</div>`,
      helpSection('Kurz erklärt', helpText(h.short || s.description)),
      helpSection('Wann wirkt die Einstellung?', helpText(when)),
      helpSection('Wirkung bei Änderung', effectHelpHtml(s)),
      helpSection('Abhängigkeiten & Vorrangregeln', `${dependencyHelpHtml(s)}${h.override?`<div class="help-callout override"><b>Vorrang / Überschreibung</b><span>${esc(h.override)}</span></div>`:''}`),
      helpSection('Grenzen / Validierung', validationHelpHtml(s)),
      helpSection('Risiko / Sicherheitswirkung', helpText(h.risk)),
      helpSection('Beispiel / Rechnung', `${h.formula?`<div class="help-formula">${esc(h.formula)}</div>`:''}${exampleHelpHtml(h.example)}`),
      helpSection('Optionen', optionHelpHtml(s)),
      helpSection('Default-/Profil-Semantik', defaultHelpHtml(s)),
      helpSection('Wirksamkeit nach Speichern', helpText(s.apply_text || s.apply_class)),
      helpSection('Handbuch', helpHandbook(h.handbook)),
      helpSection('Technischer Vertrag', technicalHelpHtml(s), 'technical'),
    ].filter(Boolean).join('');
    return body;
  }
  function lockHelpScroll() {
    if (document.body.classList.contains('preview-open') || document.body.classList.contains('help-open')) return;
    app.helpScrollY = window.scrollY || document.documentElement.scrollTop || 0;
    document.body.style.top = `-${app.helpScrollY}px`;
    document.body.classList.add('help-open');
  }
  function unlockHelpScroll() {
    if (!document.body.classList.contains('help-open')) return;
    document.body.classList.remove('help-open');
    document.body.style.top = '';
    window.scrollTo({top:app.helpScrollY,left:0,behavior:'auto'});
  }
  function openHelpModal(title, bodyHtml, trigger = null) {
    app.helpReturnFocus = trigger || document.activeElement;
    $('#helpTitle').textContent = title;
    const helpBody = $('#helpBody');
    helpBody.innerHTML = bodyHtml;
    helpBody.scrollTop = 0;
    lockHelpScroll();
    $('#helpModal').classList.add('open');
    bindHelpModalActions();
    requestAnimationFrame(() => { helpBody.scrollTop = 0; });
    $('#helpClose')?.focus({preventScroll:true});
  }
  function closeHelpModal() {
    if (!$('#helpModal')?.classList.contains('open')) return;
    $('#helpModal').classList.remove('open');
    $('#helpBody').innerHTML = '';
    app.pendingHelpTarget = null;
    unlockHelpScroll();
    const target = app.helpReturnFocus;
    app.helpReturnFocus = null;
    if (target?.isConnected) target.focus({preventScroll:true});
  }
  function openSettingHelp(key, trigger = null) {
    const s = settingByKey(key);
    if (!s) return;
    openHelpModal(s.label, settingHelpBody(s), trigger);
  }
  function openCategoryHelp(name, trigger = null) {
    const c = app.model.categories.find(x=>x.name===name);
    if (!c) return;
    const sections = c.sections.filter(sec=>sec.help).map(sec=>`<button type="button" class="help-related" data-help-section="${esc(c.name)}|||${esc(sec.name)}">${esc(sec.name)}</button>`).join('');
    const body = `<div class="help-context"><span>Kategorie</span><span>›</span><span>${esc(c.group)}</span></div>${helpSection('Zielbild', helpText(c.help || c.description))}${sections?helpSection('Abschnitte',`<div class="help-related-list">${sections}</div>`):''}${helpSection('Handbuch', helpHandbook(c.handbook))}`;
    openHelpModal(c.name, body, trigger);
  }
  function openSectionHelp(encoded, trigger = null) {
    const [categoryName, sectionName] = String(encoded||'').split('|||');
    const c = app.model.categories.find(x=>x.name===categoryName);
    const section = c?.sections.find(x=>x.name===sectionName);
    if (!c || !section) return;
    const related = section.settings.filter(searchVisibleInMode).map(s=>`<button type="button" class="help-related" data-help-setting="${esc(s.key)}">${esc(s.label)}</button>`).join('');
    const body = `<div class="help-context"><span>${esc(c.name)}</span><span>›</span><span>Abschnitt</span></div>${helpSection('Zusammenhang', helpText(section.help))}${related?helpSection('Einstellungen in diesem Abschnitt',`<div class="help-related-list">${related}</div>`):''}${helpSection('Handbuch', helpHandbook(section.handbook))}`;
    openHelpModal(section.name, body, trigger);
  }
  function showExpertHelpGate(key) {
    const target = settingByKey(key);
    if (!target) return;
    app.pendingHelpTarget = key;
    const helpBody = $('#helpBody');
    helpBody.innerHTML = `<div class="notice info"><b>${esc(target.label)}</b> ist nur im Expertenmodus sichtbar. Der Ansichtsmodus wird nicht automatisch geändert.</div><div class="help-gate-actions"><button type="button" class="admin-action-button" data-help-show-expert="${esc(key)}">Im Expertenmodus anzeigen</button></div>`;
    helpBody.scrollTop = 0;
    bindHelpModalActions();
    requestAnimationFrame(() => { helpBody.scrollTop = 0; });
  }
  function navigateHelpDependency(key) {
    const target = settingByKey(key);
    if (!target) return;
    if (target.expert && app.mode !== 'expert' && !(app.model?.status?.startup_mode === 'FIRST_INSTALL_SETUP' && target.required_first_install)) {
      showExpertHelpGate(key);
      return;
    }
    closeHelpModal();
    app.category = target._category;
    render();
    setTimeout(()=>{
      const el = targetForSettingKey(key);
      el?.scrollIntoView({behavior:'smooth',block:'center'});
      el?.classList.add('guided-target');
      setTimeout(()=>el?.classList.remove('guided-target'),1800);
      el?.querySelector('input,select,button')?.focus({preventScroll:true});
    },60);
  }
  function bindHelpModalActions() {
    $$('[data-help-dependency]', $('#helpBody')).forEach(el=>el.onclick=()=>navigateHelpDependency(el.dataset.helpDependency));
    $$('[data-help-setting]', $('#helpBody')).forEach(el=>el.onclick=()=>openSettingHelp(el.dataset.helpSetting, el));
    $$('[data-help-section]', $('#helpBody')).forEach(el=>el.onclick=()=>openSectionHelp(el.dataset.helpSection, el));
    $$('[data-help-show-expert]', $('#helpBody')).forEach(el=>el.onclick=()=>{
      const key=el.dataset.helpShowExpert;
      closeHelpModal();
      app.mode='expert'; storageSet('zecSettingsMode', app.mode);
      const target=settingByKey(key); app.category=target?._category || app.category; render();
      setTimeout(()=>targetForSettingKey(key)?.scrollIntoView({behavior:'smooth',block:'center'}),60);
    });
  }
  function bindHelpButtons() {
    $$('[data-help-setting]').forEach(el=>{ if (!el.closest('#helpBody')) el.onclick=event=>{event.stopPropagation();openSettingHelp(el.dataset.helpSetting,el);}; });
    $$('[data-help-category]').forEach(el=>el.onclick=event=>{event.stopPropagation();openCategoryHelp(el.dataset.helpCategory,el);});
    $$('[data-help-section]').forEach(el=>{ if (!el.closest('#helpBody')) el.onclick=event=>{event.stopPropagation();openSectionHelp(el.dataset.helpSection,el);}; });
  }
  function trapHelpFocus(event) {
    if (event.key !== 'Tab' || !$('#helpModal')?.classList.contains('open')) return;
    const focusables = $$('button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])', $('#helpModal')).filter(el=>!el.disabled && el.offsetParent!==null);
    if (!focusables.length) return;
    const first=focusables[0], last=focusables[focusables.length-1];
    if (event.shiftKey && document.activeElement===first) {event.preventDefault();last.focus();}
    else if (!event.shiftKey && document.activeElement===last) {event.preventDefault();first.focus();}
  }

  function clearValidationIssues() {
    app.validationIssues = [];
  }
  function scheduleRenderAfterInput() { requestAnimationFrame(() => render()); }
  function setNightCompound(kind, raw) {
    const pair = NIGHT_COMPOUNDS[kind];
    const parsed = parseTime(raw);
    app.preview = null;
    clearValidationIssuesForKeys([pair.hour, pair.minute]);
    if (!parsed) {
      app.compoundDraft.set(kind, String(raw));
      app.draft.delete(pair.hour);
      app.draft.delete(pair.minute);
      addValidationIssue({code:'TIME_FORMAT_INVALID',severity:'error',blocking:true,keys:[pair.hour,pair.minute],message:`${NIGHT_COMPOUNDS[kind].label}: Bitte eine gültige Uhrzeit im Format HH:MM zwischen 00:00 und 23:59 eingeben.`});
      scheduleRenderAfterInput();
      return;
    }
    app.compoundDraft.delete(kind);
    const hourSpec = settingByKey(pair.hour);
    const minuteSpec = settingByKey(pair.minute);
    if (same(parsed.hour, hourSpec.configured)) app.draft.delete(pair.hour); else app.draft.set(pair.hour, parsed.hour);
    if (same(parsed.minute, minuteSpec.configured)) app.draft.delete(pair.minute); else app.draft.set(pair.minute, parsed.minute);
    scheduleRenderAfterInput();
  }
  function bindInputs() {
    $$('[data-night-time]').forEach(el => {
      el.onchange = () => setNightCompound(el.dataset.nightTime, el.value);
    });
    $$('[data-key]:not([data-night-time])').forEach(el => {
      el.onchange = () => {
        const s = settingByKey(el.dataset.key);
        let value;
        if (s.value_type === 'bool') value = el.checked;
        else if (s.value_type === 'int') value = el.value === '' ? '' : Number(el.value);
        else if (s.value_type === 'optional_int') value = el.value === '' ? null : Number(el.value);
        else if (s.value_type === 'float') value = el.value === '' ? '' : Number(el.value);
        else value = el.value;
        if (same(value, s.configured)) app.draft.delete(s.key); else app.draft.set(s.key, value);
        app.preview = null;
        clearValidationIssuesForKeys([s.key]);
        validateSingleSetting(s, value, el.value).forEach(addValidationIssue);
        scheduleRenderAfterInput();
      };
    });
    $$('[data-reset]').forEach(button => button.onclick = () => {
      const s = settingByKey(button.dataset.reset);
      if (!s?.default_ui?.action || !(Object.prototype.hasOwnProperty.call(s.default_ui, 'value'))) return;
      const resetValue = s.default_ui.value;
      if (same(resetValue, s.configured)) app.draft.delete(s.key); else app.draft.set(s.key, resetValue);
      app.preview = null;
      clearValidationIssuesForKeys([s.key]);
      render();
    });
    $$('[data-secret]').forEach(button => button.onclick = () => {
      app.secretOps.set(button.dataset.key, {op:button.dataset.secret});
      app.preview = null;
      clearValidationIssues();
      render();
    });
    $$('[data-secret-value]').forEach(el => el.oninput = () => {
      app.secretOps.set(el.dataset.secretValue, {op:'replace',value:el.value});
      app.preview = null;
      clearValidationIssues();
      updateBar();
    });
  }
  function updateBar() {
    const count = dirtyCount();
    $('#dirtyCount').classList.toggle('active', count > 0);
    $('#dirtyText').textContent = count === 0 ? 'Keine ungespeicherten Änderungen' : `${count} ungespeicherte Änderung${count===1?'':'en'}`;
    $('#reviewChanges').disabled = count === 0 || app.previewInFlight;
    $('#discardChanges').disabled = count === 0;
  }
  function render() {
    if (!app.model) return;
    document.body.classList.toggle('expert-mode', app.mode === 'expert');
    $$('[data-mode]').forEach(b => b.classList.toggle('active', b.dataset.mode === app.mode));
    const health = app.model.status.config_health;
    const ready = app.model.ready_status?.ready === true;
    $('#healthDot').className = `health-dot ${health}`;
    $('#healthText').textContent = health === 'valid' ? (app.model.status.pending_restart?'Gespeichert · Neustart ausstehend':'Konfiguration gültig') : `Konfiguration ${health}`;
    $('#headerVersion').textContent = app.model.controller_version;
    $('#headerSource').textContent = `Config: ${app.model.status.effective_source || 'unbekannt'}`;
    $('#headerReady').innerHTML = `<span class="health-dot ${ready?'valid':'invalid_runtime'}"></span> Ready: ${ready?'ja':'nein'}`;
    $('#restartAction').hidden = !app.model.status.pending_restart;
    renderNav();
    renderCategory();
    updateBar();
  }
  function payload() {
    const changes = {};
    app.draft.forEach((value,key) => { if (!NIGHT_KEYS.has(key)) changes[key] = {op:'set', value}; });
    Object.values(NIGHT_COMPOUNDS).forEach(pair => {
      if (!app.draft.has(pair.hour) && !app.draft.has(pair.minute)) return;
      changes[pair.hour] = {op:'set', value:currentValue(settingByKey(pair.hour))};
      changes[pair.minute] = {op:'set', value:currentValue(settingByKey(pair.minute))};
    });
    const secrets = {};
    app.secretOps.forEach((value,key) => secrets[key] = value);
    return {base_revision:app.model.base_revision, changes, secrets};
  }
  function validateClientDraft() {
    const issues = [];
    Object.entries(NIGHT_COMPOUNDS).forEach(([kind, pair]) => {
      if (!app.compoundDraft.has(kind)) return;
      const raw = app.compoundDraft.get(kind);
      if (!parseTime(raw)) issues.push({
        code:'TIME_FORMAT_INVALID', severity:'error', blocking:true, keys:[pair.hour,pair.minute],
        message:`${pair.label}: Bitte eine gültige Uhrzeit im Format HH:MM zwischen 00:00 und 23:59 eingeben.`
      });
    });
    app.draft.forEach((value,key) => {
      if (NIGHT_KEYS.has(key)) return;
      const spec = settingByKey(key);
      if (!spec) return;
      validateSingleSetting(spec, value, value).forEach(issue => issues.push(issue));
    });
    return issues;
  }
  function friendlyPreviewError(error) {
    if (error.status === 409) return 'Konfiguration wurde zwischenzeitlich geändert. Aktuellen Stand neu laden und Änderungen erneut prüfen.';
    if (error.status === 403) return 'Die Änderungsprüfung wurde aus Sicherheitsgründen abgewiesen. Seite neu laden und erneut versuchen.';
    if (error.status >= 500 || error.status === 422) return 'Die Änderungsprüfung konnte wegen eines internen Fehlers nicht ausgeführt werden.';
    return 'Die Änderungsprüfung konnte nicht ausgeführt werden.';
  }
  async function preview() {
    if (app.previewInFlight || dirtyCount() === 0) return;
    const clientIssues = validateClientDraft();
    if (clientIssues.length) {
      app.preview = {status:'blocked', preview_id:null, issues:clientIssues, diff:[], confirmations_required:[]};
      app.validationIssues = clientIssues;
      renderCategory();
      openPreview();
      return;
    }
    app.previewInFlight = true;
    updateBar();
    try {
      app.preview = await api('/settings/preview', {method:'POST', body:JSON.stringify(payload())});
      app.validationIssues = app.preview.issues || [];
      renderCategory();
      openPreview();
    } catch (error) {
      if (error.status === 422 && error.data?.status === 'blocked' && Array.isArray(error.data.issues)) {
        app.preview = error.data;
        app.validationIssues = error.data.issues;
        renderCategory();
        openPreview();
      } else {
        toast(friendlyPreviewError(error));
      }
    } finally {
      app.previewInFlight = false;
      updateBar();
    }
  }
  function fmt(v) {
    if (v && typeof v === 'object' && 'secret_set' in v) return v.secret_set ? '•••••• (gesetzt)' : 'nicht gesetzt';
    if (v === null || v === undefined || v === '') return 'leer';
    return String(v);
  }
  function lockPreviewScroll() {
    if (document.body.classList.contains('preview-open')) return;
    app.previewScrollY = window.scrollY || document.documentElement.scrollTop || 0;
    document.body.style.top = `-${app.previewScrollY}px`;
    document.body.classList.add('preview-open');
  }
  function unlockPreviewScroll() {
    if (!document.body.classList.contains('preview-open')) return;
    document.body.classList.remove('preview-open');
    document.body.style.top = '';
    window.scrollTo({top:app.previewScrollY, left:0, behavior:'auto'});
  }
  function normalizedPreviewDiff(diff) {
    const source = Array.isArray(diff) ? diff : [];
    const nightChanged = source.some(item => NIGHT_KEYS.has(item.key));
    const out = source.filter(item => !NIGHT_KEYS.has(item.key));
    if (nightChanged) {
      const start = NIGHT_COMPOUNDS.start;
      const end = NIGHT_COMPOUNDS.end;
      const relevant = source.filter(item => NIGHT_KEYS.has(item.key));
      out.unshift({
        key:'__night_window__',
        label:'Nachtfenster',
        old:`${formatTime(settingByKey(start.hour).configured, settingByKey(start.minute).configured)} → ${formatTime(settingByKey(end.hour).configured, settingByKey(end.minute).configured)}`,
        new:`${formatTime(currentValue(settingByKey(start.hour)), currentValue(settingByKey(start.minute)))} → ${formatTime(currentValue(settingByKey(end.hour)), currentValue(settingByKey(end.minute)))}`,
        apply_class:relevant.some(item => item.apply_class === 'restart_required') ? 'restart_required' : (relevant[0]?.apply_class || 'live_next_cycle'),
        apply_text:relevant.find(item => item.apply_text)?.apply_text || 'wird nach dem Speichern wirksam',
      });
    }
    return out;
  }
  function targetForSettingKey(key) {
    const kind = nightCompoundForKey(key);
    if (kind) return document.querySelector(`[data-compound="night-${kind}"]`);
    return document.querySelector(`[data-setting="${CSS.escape(key)}"]`);
  }
  function logicalIssueTargets(keys) {
    const out = [];
    const seen = new Set();
    (keys || []).forEach(key => {
      const kind = nightCompoundForKey(key);
      if (kind) {
        const id = `night:${kind}`;
        if (!seen.has(id)) { seen.add(id); out.push({id, key:NIGHT_COMPOUNDS[kind].hour, label:NIGHT_COMPOUNDS[kind].label, kind}); }
        return;
      }
      if (!seen.has(key)) { seen.add(key); out.push({id:key, key, label:settingByKey(key)?.label || key, kind:null}); }
    });
    return out;
  }
  function openIssueHelp(targetId, trigger = null) {
    if (String(targetId).startsWith('night:')) {
      const kind = String(targetId).split(':')[1];
      const pair = NIGHT_COMPOUNDS[kind];
      const representative = settingByKey(pair?.hour);
      if (representative) openHelpModal(pair.label, settingHelpBody(representative), trigger);
      return;
    }
    openSettingHelp(targetId, trigger);
  }
  function jumpToSetting(key) {
    const setting = settingByKey(key);
    if (!setting) return;
    $('#previewModal').classList.remove('open');
    $('#previewBody').innerHTML = '';
    app.preview = null;
    unlockPreviewScroll();
    app.category = setting._category;
    setCategoryDrawerOpen(false);
    render();
    setTimeout(() => {
      const target = targetForSettingKey(key);
      target?.scrollIntoView({behavior:'smooth', block:'center'});
      target?.querySelector('input,select,button')?.focus({preventScroll:true});
    }, 50);
  }
  function openPreview() {
    const p = app.preview || {};
    const issues = Array.isArray(p.issues) ? p.issues : [];
    const diff = normalizedPreviewDiff(p.diff);
    const confirmations = Array.isArray(p.confirmations_required) ? p.confirmations_required : [];
    $('#previewTitle').textContent = p.status === 'blocked' ? 'Änderungen können noch nicht gespeichert werden' : 'Änderungen prüfen';
    let out = '';
    if (issues.length) out += `<ul class="issue-list">${issues.map(i=>{
      const keys = (i.keys || []).filter(key => settingByKey(key));
      const targets = logicalIssueTargets(keys);
      const firstTarget = targets[0];
      const code = app.mode === 'expert' && i.code ? `<span class="issue-code">${esc(i.code)}</span>` : '';
      const source = i.params?.effective_source ? `<div class="issue-source">Wirksame Quelle: <code>${esc(i.params.effective_source)}</code>. Die Hilfe erläutert, welcher Wert in dieser Konstellation Vorrang hat.</div>` : '';
      const links = targets.length ? `<div class="issue-actions">${targets.map((target,index)=>`<button type="button" class="issue-jump" data-issue-key="${esc(target.key)}">${index===0?'Zur Einstellung':esc(target.label)}</button>`).join('')}<button type="button" class="issue-jump issue-why" data-issue-help="${esc(firstTarget.id)}">Warum?</button></div>` : '';
      return `<li class="${esc(i.severity || 'error')}"><div class="issue-copy"><span>${esc(i.message || 'Die Änderung ist nicht zulässig.')}</span>${source}${code}</div>${links}</li>`;
    }).join('')}</ul>`;
    if (diff.length) out += diff.map(d=>`<div class="diff-row"><div><b>${esc(d.label)}</b><div class="diff-values">${esc(fmt(d.old))} <span class="diff-arrow">→</span> ${esc(fmt(d.new))}</div></div><span class="meta-pill ${d.apply_class==='restart_required'?'restart':'live'}">${esc(d.apply_text)}</span></div>`).join('');
    else if (!issues.length) out += '<div class="notice info">Keine wirksame Änderung erkannt.</div>';
    if (confirmations.length) out += confirmations.map(c=>`<label class="confirmation"><input type="checkbox" data-confirm="${esc(c)}"><span>Hinweis <b>${esc(c)}</b> wurde geprüft und wird bewusst bestätigt.</span></label>`).join('');
    $('#previewBody').innerHTML = out;
    $$('[data-issue-key]').forEach(button => button.onclick = () => jumpToSetting(button.dataset.issueKey));
    $$('[data-issue-help]').forEach(button => button.onclick = () => openIssueHelp(button.dataset.issueHelp, button));
    $('#commitChanges').disabled = p.status !== 'ready' || !p.preview_id;
    $('#commitChanges').textContent = p.status === 'ready' && p.preview_id ? 'Speichern' : 'Speichern nicht möglich';
    $('#previewBack').textContent = 'Zurück';
    app.modalMode = 'preview';
    lockPreviewScroll();
    $('#previewModal').classList.add('open');
    $('#previewClose')?.focus({preventScroll:true});
  }
  function closePreview() {
    $('#previewModal').classList.remove('open');
    $('#previewBody').innerHTML = '';
    app.preview = null;
    app.modalMode = 'preview';
    app.adminAction = null;
    unlockPreviewScroll();
    updateBar();
  }
  async function commit() {
    try {
      const confirmations = $$('[data-confirm]:checked').map(x => x.dataset.confirm);
      const result = await api('/settings/commit', {method:'POST', body:JSON.stringify({preview_id:app.preview.preview_id, confirmations})});
      closePreview();
      app.draft.clear();
      app.compoundDraft.clear();
      app.secretOps.clear();
      clearValidationIssues();
      toast(result.pending_restart ? 'Gespeichert. Dienstneustart erforderlich.' : 'Änderungen gespeichert und live übernommen.');
      await load();
    } catch (error) { toast(`Speichern fehlgeschlagen: ${error.message}`); }
  }
  function discard() { app.draft.clear(); app.compoundDraft.clear(); app.secretOps.clear(); app.preview = null; clearValidationIssues(); render(); }
  function toast(text, ms = 5000) {
    const el = $('#settingsToast');
    el.textContent = text;
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), ms);
  }
  async function pollReady(info) {
    const deadline = Date.now() + 90000;
    toast('Neustart läuft; Ready-Status wird geprüft …', 90000);
    while (Date.now() < deadline) {
      await new Promise(resolve => setTimeout(resolve, 1500));
      try {
        const ready = await api(info.ready_url || '/ready');
        if (ready.ready === true && ready.version === info.expected_version && ready.build_id === info.expected_build_id) {
          toast('Dienstneustart erfolgreich: erwartete Version ist ready.', 7000);
          await load();
          return;
        }
      } catch (_) { /* transient connection loss is expected */ }
    }
    toast('Neustart ausgelöst, aber ready=true wurde innerhalb von 90 Sekunden nicht bestätigt.', 10000);
  }
  function openAdminModal({title, bodyHtml, primaryLabel, mode, action}) {
    app.modalMode = mode;
    app.adminAction = action || null;
    $('#previewTitle').textContent = title;
    $('#previewBody').innerHTML = bodyHtml;
    $('#previewBack').textContent = 'Abbrechen';
    $('#commitChanges').textContent = primaryLabel;
    $('#commitChanges').disabled = false;
    lockPreviewScroll();
    $('#previewModal').classList.add('open');
    $('#previewClose')?.focus({preventScroll:true});
  }
  function restart() {
    const count = dirtyCount();
    const unsaved = count > 0 ? `<div class="notice warning"><b>${count} ungespeicherte Änderung${count===1?'':'en'}.</b> Diese Änderungen werden durch den Neustart nicht übernommen und bleiben nur im aktuellen Browserentwurf erhalten.</div>` : '<div class="notice info">Es liegen keine ungespeicherten Änderungen vor.</div>';
    openAdminModal({
      title:'Controller-Dienst neu starten',
      mode:'restart',
      primaryLabel:'Controller neu starten',
      bodyHtml:`${unsaved}<div class="admin-confirm-grid"><div><span>Aktion</span><b>Nur Zendure-Controller neu starten</b></div><div><span>Anschließende Prüfung</span><b>Version · Build-ID · Ready-Status</b></div></div><p class="admin-confirm-copy">Der geschützte Restart-Helper startet ausschließlich den Controller-Dienst. MQTT, EVCC und andere Systemdienste werden durch diese Aktion nicht neu gestartet.</p>`,
      action:{kind:'restart'}
    });
  }
  async function repairPointer() {
    try {
      const p = await api('/admin/last-good-pointer-repair/preview', {method:'POST',body:'{}'});
      openAdminModal({
        title:'Last-Good-Pointer reparieren',
        mode:'pointer',
        primaryLabel:'Pointer reparieren',
        bodyHtml:`<div class="notice info">Die serverseitige Prüfung hat genau einen zulässigen Zielslot bestimmt. Es werden keine normalen Einstellungen und keine Slotinhalte geändert.</div><div class="admin-confirm-grid"><div><span>Zielslot</span><b>${esc(p.target_slot)}</b></div><div><span>Generation</span><b>${esc(p.generation_id)}</b></div><div><span>Typed Revision</span><b class="mono">${esc(p.typed_revision)}</b></div><div><span>Config-Hash</span><b class="mono">${esc(p.config_hash)}</b></div><div><span>Manifest-Hash</span><b class="mono">${esc(p.manifest_hash)}</b></div></div><p class="admin-confirm-copy">Beim Commit wird ausschließlich der <code>current</code>-Pointer atomar auf diesen unmittelbar zuvor validierten Slot gesetzt.</p>`,
        action:{kind:'pointer', preview:p}
      });
    } catch (error) { toast(`Pointer-Vorprüfung konnte nicht ausgeführt werden: ${error.message}`); }
  }
  async function runAdminAction() {
    const action = app.adminAction;
    if (!action) return;
    $('#commitChanges').disabled = true;
    try {
      if (action.kind === 'restart') {
        const info = await api('/restart-service', {method:'POST', body:JSON.stringify({confirmation:'RESTART_SERVICE'})});
        closePreview();
        pollReady(info);
        return;
      }
      if (action.kind === 'pointer') {
        const p = action.preview;
        await api('/admin/last-good-pointer-repair/commit', {method:'POST',body:JSON.stringify({action_token:p.action_token,confirmation:'REPAIR_POINTER'})});
        closePreview();
        toast('Last-Good-Pointer erfolgreich repariert.');
        await load();
        return;
      }
      if (action.kind === 'custom' && typeof action.run === 'function') {
        await action.run();
        closePreview();
        return;
      }
    } catch (error) {
      $('#commitChanges').disabled = false;
      toast(`${action.errorLabel || (action.kind === 'restart' ? 'Neustart' : 'Pointer-Reparatur')} fehlgeschlagen: ${error.message}`);
    }
  }
  async function modalPrimaryAction() {
    if (app.modalMode === 'preview') return commit();
    return runAdminAction();
  }
  function requestZecConfirmation({title, bodyHtml, primaryLabel, action, errorLabel}) {
    closeConfigStates();
    openAdminModal({title, bodyHtml, primaryLabel, mode:'custom', action:{kind:'custom', run:action, errorLabel}});
  }
  function closeConfigStates() {
    const modal=$('#configStatesModal');if(!modal?.classList.contains('open'))return;
    modal.classList.remove('open');$('#configStatesBody').innerHTML='';unlockPreviewScroll();
  }
  async function downloadConfigArtifact(url, body, fallbackName) {
    const response=await fetch(url,{method:'POST',cache:'no-store',credentials:'same-origin',headers:{'Accept':'application/vnd.zec.config+json','Content-Type':'application/json','X-CSRF-Token':csrf()},body:JSON.stringify(body||{})});
    if(!response.ok){let message=`HTTP ${response.status}`;try{const data=await response.json();message=data.error||data.detail||message;}catch(_){}throw new Error(message);}
    const blob=await response.blob();const cd=response.headers.get('content-disposition')||'';const match=/filename="?([^";]+)"?/i.exec(cd);const name=match?.[1]||fallbackName;
    const href=URL.createObjectURL(blob);const a=document.createElement('a');a.href=href;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(href),1000);
  }
  async function inspectConfigFile(file, legacy) {
    const url=`/config-import/inspect${legacy?`?legacy=1&expert=${app.mode==='expert'?'1':'0'}`:''}`;
    const response=await fetch(url,{method:'POST',cache:'no-store',credentials:'same-origin',headers:{'Accept':'application/json','Content-Type':'application/octet-stream','X-CSRF-Token':csrf()},body:file});
    let data={};try{data=await response.json();}catch(_){}
    if(!response.ok){const err=new Error(data.error||data.detail||`HTTP ${response.status}`);err.status=response.status;err.data=data;throw err;}return data;
  }
  async function loadConfigStatePreview(state) {
    if(dirtyCount()>0){toast('Vor dem Laden eines Konfigurationsstands bitte den aktuellen Browserentwurf speichern oder verwerfen.');return;}
    try{
      const result=await api(`/config-states/${encodeURIComponent(state.state_id)}/preview`,{method:'POST',body:JSON.stringify({state_revision:state.state_revision,base_revision:app.model.base_revision,expert:app.mode==='expert',secrets:{}})});
      app.preview=result;app.validationIssues=result.issues||[];closeConfigStates();openPreview();
    }catch(error){toast(`Konfigurationsstand konnte nicht geprüft werden: ${error.message}`);}
  }
  async function renderConfigStates() {
    const body=$('#configStatesBody');body.innerHTML='<div class="empty-state">Konfigurationsstände werden geladen …</div>';
    try{
      const result=await api('/config-states');const states=result.items||[];const expert=app.mode==='expert';
      const scopeOptions=expert?'<option value="full_managed">Alle verwalteten Einstellungen</option><option value="portable_profile">Teilbares Regelprofil</option><option value="categories">Ausgewählte Kategorien (Experte)</option><option value="keys">Ausgewählte Keys (Experte)</option>':'<option value="full_managed">Alle verwalteten Einstellungen</option><option value="portable_profile">Teilbares Regelprofil</option>';
      const list=states.length?states.map(st=>`<div class="config-state-item ${st.status==='corrupt'?'corrupt':''}" data-state-id="${esc(st.state_id)}"><div><b>${esc(st.name||'Konfigurationsstand')}</b><div>${esc(st.description||'')}</div><div class="config-state-meta">${esc(st.created_at||'—')} · ${esc(st.source_app_version||'—')} · ${esc(st.scope_mode||'—')} · ${esc(st.scope_key_count??'—')} Keys</div></div><div class="config-state-item-actions">${st.status==='valid'?`<button type="button" data-state-load="${esc(st.state_id)}">Prüfen & laden</button><button type="button" data-state-export="${esc(st.state_id)}">Export</button><button type="button" data-state-rename="${esc(st.state_id)}">Umbenennen</button><button type="button" data-state-delete="${esc(st.state_id)}">Löschen</button>`:'<span class="config-state-warning">Beschädigt – Laden gesperrt</span>'}</div></div>`).join(''):'<div class="empty-state">Noch keine benannten Konfigurationsstände vorhanden.</div>';
      body.innerHTML=`
        <section class="config-state-section"><div class="config-state-warning"><b>Getrennter Benutzerstand:</b> Ein benannter Stand ist kein Last-Good-Recoveryslot und wird beim Laden nie sofort aktiv. Laden/Import führen immer über Migration, Servervalidierung, Diff, Bestätigung und revisionsgebundenen Commit.</div></section>
        <section class="config-state-section"><h3>Benannten Stand anlegen</h3><div class="config-state-grid"><label>Name<input id="stateName" maxlength="80" placeholder="z. B. Sommer optimiert"></label><label>Scope<select id="stateScope">${scopeOptions}</select></label><label class="full">Beschreibung<textarea id="stateDescription" maxlength="500" rows="2"></textarea></label>${expert?'<label class="full" id="stateScopeDetails" hidden>Auswahl (Komma-getrennte Kategorien oder Config-Keys)<input id="stateScopeSelection" autocomplete="off"></label>':''}</div><div class="config-state-actions"><button id="createState" type="button">Aktuellen Stand speichern</button></div></section>
        <section class="config-state-section"><h3>Gespeicherte Stände</h3><div class="config-state-list">${list}</div></section>
        <section class="config-state-section"><h3>Export</h3><p class="config-state-warning">Vollständige Exporte dienen Backup/Migration. Teilbare Regelprofile enthalten ausschließlich als portabel klassifizierte Regelparameter. Der SHA-256-Prüfwert des ZEC-CONFIG-BUNDLE bestätigt Integrität, nicht Urheber oder vertrauenswürdige Herkunft.</p><div class="config-state-actions"><button id="exportFull" type="button">Vollständigen Export erstellen</button><button id="exportProfile" type="button">Teilbares Regelprofil exportieren</button>${expert?'<button id="exportWithSecrets" type="button">Vollständiger Export inkl. Secrets (Experte)</button>':''}</div></section>
        <section class="config-state-section"><h3>Import</h3><input id="configImportFile" type="file" accept=".json,.zec-config.json,application/json"><div class="config-import-options">${expert?'<label><input id="legacyConfigImport" type="checkbox"> Legacy config.json (ohne Bundle-Integrität)</label>':''}<label id="skipUnknownImportWrap" hidden><input id="skipUnknownImport" type="checkbox"> Unbekannte Quellschlüssel ausdrücklich überspringen</label><label id="importSecretOperationWrap" hidden>Secrets<select id="importSecretOperation"><option value="keep">Vorhandene Secrets behalten</option><option value="replace">Im Bundle enthaltene Secrets übernehmen</option><option value="clear">Betroffene Secrets ausdrücklich löschen</option></select></label></div><div id="configImportInfo" class="config-state-warning">Import lädt nie direkt: zuerst Integritäts-/Kompatibilitätsprüfung, Migration, vollständige Servervalidierung und Diff.</div><div class="config-state-actions"><button id="inspectConfigImport" type="button">Datei prüfen</button></div></section>`;
      const byId=id=>states.find(x=>x.state_id===id);
      $$('[data-state-load]',body).forEach(btn=>btn.onclick=()=>loadConfigStatePreview(byId(btn.dataset.stateLoad)));
      $$('[data-state-export]',body).forEach(btn=>btn.onclick=async()=>{const st=byId(btn.dataset.stateExport);try{await downloadConfigArtifact(`/config-states/${encodeURIComponent(st.state_id)}/export`,{state_revision:st.state_revision},`zec-config-state-${st.state_id}.zec-config.json`);}catch(e){toast(`Export fehlgeschlagen: ${e.message}`);}});
      $$('[data-state-rename]',body).forEach(btn=>btn.onclick=()=>{const st=byId(btn.dataset.stateRename);requestZecConfirmation({title:'Konfigurationsstand umbenennen',primaryLabel:'Umbenennen',errorLabel:'Umbenennen',bodyHtml:`<label class="admin-confirm-copy">Neuer Name<input id="stateRenameValue" maxlength="80" value="${esc(st.name||'')}"></label>`,action:async()=>{const name=String($('#stateRenameValue')?.value||'').trim();await api(`/config-states/${encodeURIComponent(st.state_id)}`,{method:'PATCH',body:JSON.stringify({state_revision:st.state_revision,name})});toast('Konfigurationsstand umbenannt.');}});});
      $$('[data-state-delete]',body).forEach(btn=>btn.onclick=()=>{const st=byId(btn.dataset.stateDelete);requestZecConfirmation({title:'Konfigurationsstand löschen',primaryLabel:'Endgültig löschen',errorLabel:'Löschen',bodyHtml:`<div class="notice warning"><b>${esc(st.name||st.state_id)}</b> wird gelöscht. Die aktive Konfiguration und Last-Good werden dadurch nicht verändert.</div>`,action:async()=>{await api(`/config-states/${encodeURIComponent(st.state_id)}`,{method:'DELETE',body:JSON.stringify({state_revision:st.state_revision})});toast('Konfigurationsstand gelöscht.');}});});
      $('#stateScope')?.addEventListener('change',()=>{const details=$('#stateScopeDetails');if(details)details.hidden=!['categories','keys'].includes($('#stateScope').value);});
      $('#createState').onclick=async()=>{try{const mode=$('#stateScope').value;const selection=String($('#stateScopeSelection')?.value||'').split(',').map(x=>x.trim()).filter(Boolean);const payload={name:$('#stateName').value,description:$('#stateDescription').value,scope_mode:mode};if(mode==='categories')payload.categories=selection;if(mode==='keys')payload.keys=selection;await api('/config-states/create',{method:'POST',body:JSON.stringify(payload)});toast('Konfigurationsstand gespeichert.');await renderConfigStates();}catch(e){toast(`Stand konnte nicht gespeichert werden: ${e.message}`);}};
      $('#exportFull').onclick=async()=>{try{await downloadConfigArtifact('/config-export',{scope_mode:'full_managed',name:'ZEC Konfiguration'},'zec-config-export.zec-config.json');}catch(e){toast(`Export fehlgeschlagen: ${e.message}`);}};
      $('#exportProfile').onclick=async()=>{try{await downloadConfigArtifact('/config-profile-export',{name:'ZEC Regelprofil'},'zec-regelprofil.zec-config.json');}catch(e){toast(`Profil-Export fehlgeschlagen: ${e.message}`);}};
      if(expert)$('#exportWithSecrets').onclick=()=>requestZecConfirmation({title:'Export inklusive Secrets',primaryLabel:'Secret-Export erstellen',errorLabel:'Secret-Export',bodyHtml:'<div class="notice warning"><b>Dieser Export enthält Secret-Klartext.</b> Die Datei darf nur geschützt gespeichert und gezielt weitergegeben werden.</div>',action:async()=>{await downloadConfigArtifact('/config-export',{scope_mode:'full_managed',name:'ZEC Konfiguration inkl. Secrets',include_secrets:true,expert:true,confirm_secret_export:true},'zec-config-export-mit-secrets.zec-config.json');toast('Secret-Export erstellt.');}});
      $('#configImportFile')?.addEventListener('change',()=>{app.configImportInspection=null;const button=$('#inspectConfigImport');if(button)button.textContent='Datei prüfen';});
      $('#inspectConfigImport').onclick=async()=>{
        if(dirtyCount()>0){toast('Vor einem Import bitte den aktuellen Browserentwurf speichern oder verwerfen.');return;}
        const file=$('#configImportFile').files?.[0];if(!file){toast('Bitte zuerst eine Importdatei auswählen.');return;}
        try{
          if(!app.configImportInspection){
            const inspected=await inspectConfigFile(file,expert&&$('#legacyConfigImport')?.checked);
            app.configImportInspection=inspected;
            const unknown=inspected.unknown_source_keys||[];const secretAvailable=inspected.secrets?.available||[];
            $('#configImportInfo').textContent=`Quelle ${inspected.source?.app_version||'—'} · ${inspected.scope?.keys?.length||0} Scope-Keys · ${inspected.migration_steps?.length||0} Migrationen${unknown.length?` · ${unknown.length} unbekannte Keys`:''}${inspected.legacy_raw?' · Legacy ohne Bundle-Integrität':''}. Entscheidungen prüfen und anschließend Preview erstellen.`;
            const unknownWrap=$('#skipUnknownImportWrap');if(unknownWrap)unknownWrap.hidden=!(expert&&unknown.length);
            const secretWrap=$('#importSecretOperationWrap');if(secretWrap)secretWrap.hidden=!(expert&&secretAvailable.length);
            if(unknown.length&&!expert){toast('Import enthält unbekannte Schlüssel. Überspringen ist nur im Expertenmodus möglich.');return;}
            $('#inspectConfigImport').textContent='Preview erstellen';
            return;
          }
          const inspected=app.configImportInspection;const unknown=inspected.unknown_source_keys||[];const secretAvailable=inspected.secrets?.available||[];
          const skipUnknown=Boolean(expert&&unknown.length&&$('#skipUnknownImport')?.checked);
          if(unknown.length&&!skipUnknown){toast('Die unbekannten Quellschlüssel müssen im Expertenmodus ausdrücklich zum Überspringen bestätigt werden.');return;}
          const secrets={};
          if(expert&&secretAvailable.length){const op=$('#importSecretOperation')?.value||'keep';secretAvailable.forEach(key=>secrets[key]={op});}
          const preview=await api(`/config-import/${encodeURIComponent(inspected.import_token)}/preview`,{method:'POST',body:JSON.stringify({base_revision:app.model.base_revision,expert,skip_unknown:skipUnknown,secrets})});
          app.configImportInspection=null;app.preview=preview;app.validationIssues=preview.issues||[];closeConfigStates();openPreview();
        }catch(e){toast(`Importprüfung fehlgeschlagen: ${e.message}`);}
      }
    }catch(error){body.innerHTML=`<div class="notice error">Konfigurationsstände konnten nicht geladen werden: ${esc(error.message)}</div>`;}
  }
  function openConfigStates(){if(dirtyCount()>0){toast('Konfigurationsstände können erst geladen/importiert werden, wenn der aktuelle Browserentwurf gespeichert oder verworfen wurde.');return;}lockPreviewScroll();$('#configStatesModal').classList.add('open');renderConfigStates();$('#configStatesClose')?.focus({preventScroll:true});}

  function setTopbarSystem(system, serverTime) {
    if (!system) return;
    const kind = system.kind || 'unknown';
    const button = $('#systemStatusButton');
    if (button) {
      button.className = `zec-system-pill ${kind}`;
      const label = $('[data-zec="system.label"]');
      if (label) label.textContent = system.label || 'Systemstatus';
    }
    const dot = $('#globalStatusNavDot');
    if (dot) {
      dot.className = `zec-nav-live-dot ${kind}`;
      dot.setAttribute('aria-label', `Aktueller Systemstatus: ${kind}`);
    }
    const list = $('#systemWarningList');
    if (list) {
      const warnings = Array.isArray(system.warnings) ? system.warnings : [];
      list.innerHTML = (warnings.length ? warnings : ['Keine aktiven Warnungen oder Fehler.']).map(x=>`<li>${esc(x)}</li>`).join('');
    }
    if (serverTime) {
      $$('[data-zec="server_time"]').forEach(el => el.textContent = serverTime);
    }
  }
  async function refreshGlobalStatus() {
    if (document.visibilityState === 'hidden' || app.statusInFlight) return;
    app.statusInFlight = true;
    try {
      const payload = await api('/status-view-data');
      setTopbarSystem(payload.system, payload.server_time);
    } catch (_) { /* retain last known status */ }
    finally { app.statusInFlight = false; }
  }
  function bindSharedTopbar() {
    const statusButton = $('#systemStatusButton');
    const statusMenu = $('#systemStatusMenu');
    if (statusButton && statusMenu) {
      statusButton.onclick = event => {
        event.stopPropagation();
        const hidden = statusMenu.hidden;
        statusMenu.hidden = !hidden;
        statusButton.setAttribute('aria-expanded', String(hidden));
      };
      document.addEventListener('click', event => {
        if (!statusMenu.hidden && !event.target.closest('.zec-system-menu-wrap')) {
          statusMenu.hidden = true;
          statusButton.setAttribute('aria-expanded','false');
        }
      });
    }
    $$('.analysis-service-link').forEach(link => link.onclick = event => {
      event.preventDefault();
      const port = Number(link.dataset.replayPort || 8090);
      window.location.href = `${window.location.protocol}//${window.location.hostname}:${port}/`;
    });
    const clock = $('#localClock');
    if (clock) setInterval(() => { clock.textContent = new Date().toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit',second:'2-digit'}); }, 1000);
  }
  async function load() {
    try {
      app.model = await api('/settings/model');
      app.category = app.category && app.model.categories.some(c=>c.name===app.category) ? app.category : app.model.categories[0]?.name;
      $('#sidebarVersion').textContent = `Controller: ${app.model.controller_version}`;
      render();
    } catch (error) {
      $('#settingsContent').innerHTML = `<div class="notice error">Settings-Modell konnte nicht geladen werden: ${esc(error.message)}</div>`;
    }
  }

  window.addEventListener('DOMContentLoaded', () => {
    bindSharedTopbar();
    setTopbarSystem(window.ZEC_SETTINGS_BOOTSTRAP?.system, window.ZEC_SETTINGS_BOOTSTRAP?.server_time);
    $$('[data-mode]').forEach(button => button.onclick = () => {
      app.mode = button.dataset.mode;
      storageSet('zecSettingsMode', app.mode);
      render();
      renderSearch();
    });
    $('#openConfigStates').onclick = openConfigStates;
    $('#configStatesClose').onclick = closeConfigStates;
    $('#configStatesDone').onclick = closeConfigStates;
    $('#configStatesModal').onclick = event => { if (event.target === $('#configStatesModal')) closeConfigStates(); };
    $('#openSearch').onclick = openSearch;
    $('#closeSearch').onclick = closeSearch;
    $('#drawerBackdrop').onclick = closeSearch;
    $('#settingsSearch').oninput = renderSearch;
    $('#searchClear').onclick = () => { $('#settingsSearch').value=''; renderSearch(); };
    $('#reviewChanges').onclick = preview;
    $('#discardChanges').onclick = discard;
    $('#previewClose').onclick = closePreview;
    $('#previewBack').onclick = closePreview;
    $('#previewModal').onclick = event => { if (event.target === $('#previewModal')) closePreview(); };
    $('#helpClose').onclick = closeHelpModal;
    $('#helpDone').onclick = closeHelpModal;
    $('#helpModal').onclick = event => { if (event.target === $('#helpModal')) closeHelpModal(); };
    $('#helpModal').addEventListener('keydown', trapHelpFocus);
    $('#commitChanges').onclick = modalPrimaryAction;
    $('#mobileMenu').onclick = () => setCategoryDrawerOpen(!$('.settings-sidebar')?.classList.contains('open'));
    $('#categoryDrawerBackdrop').onclick = () => setCategoryDrawerOpen(false);
    setCategoryDrawerOpen(false);
    window.addEventListener('resize', () => setCategoryDrawerOpen(false));
    $('#restartAction').onclick = restart;
    load();
    refreshGlobalStatus();
    setInterval(refreshGlobalStatus, 3000);
    document.addEventListener('visibilitychange', () => { if (document.visibilityState !== 'hidden') refreshGlobalStatus(); });
    document.addEventListener('keydown', event => {
      if (event.key !== 'Escape') return;
      if ($('#helpModal')?.classList.contains('open')) closeHelpModal();
      else if ($('#configStatesModal')?.classList.contains('open')) closeConfigStates();
      else if ($('#previewModal')?.classList.contains('open')) closePreview();
      else if ($('.settings-sidebar')?.classList.contains('open')) setCategoryDrawerOpen(false);
      else if (document.body.classList.contains('search-open')) closeSearch();
    });
  });
})();
