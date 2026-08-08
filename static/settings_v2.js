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
    app.drawerScrollY = window.scrollY || document.documentElement.scrollTop || 0;
    document.body.style.top = `-${app.drawerScrollY}px`;
    document.body.classList.add('category-drawer-open');
  }
  function unlockCategoryDrawerScroll() {
    if (!document.body.classList.contains('category-drawer-open')) return;
    document.body.classList.remove('category-drawer-open');
    document.body.style.top = '';
    window.scrollTo({top:app.drawerScrollY, left:0, behavior:'auto'});
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
      <div class="setting-copy"><div class="setting-label">${esc(pair.label)}</div>${app.mode==='expert'?`<div class="setting-key">${esc(pair.hour)} + ${esc(pair.minute)}</div>`:''}<div class="setting-help">${esc(pair.description)}</div></div>
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
      <div class="setting-copy"><div class="setting-label">${esc(s.label)}</div>${app.mode==='expert'?`<div class="setting-key">${esc(s.key)}</div>`:''}<div class="setting-help">${esc(s.description || '')}</div></div>
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
    let body = `<div class="category-panel"><div class="category-head"><div class="category-icon">${icon(c.name)}</div><div><h1>${esc(c.name)}</h1><p>${esc(c.description)}</p></div></div>`;
    if (app.model.status.startup_mode === 'FIRST_INSTALL_SETUP') body += `<div class="status-banner"><b>Erstinbetriebnahme:</b> ZEC bleibt fail-closed und sendet keine Gerätekommandos, bis alle Pflichtwerte ausdrücklich festgelegt, geprüft und gespeichert wurden.</div>`;
    else if (app.model.status.config_health !== 'valid') body += `<div class="status-banner"><b>Konfigurationsstatus:</b> ${esc(app.model.status.config_health)}. Configured bleibt reparierbar; effective nutzt den letzten gültigen Snapshot.</div>`;
    if (app.model.status.pending_restart) body += `<div class="status-banner"><b>Dienstneustart ausstehend.</b> ${app.model.status.pending_restart_keys.map(esc).join(', ')}</div>`;
    let renderedSettings = 0;
    c.sections.forEach(section => {
      const rowParts = section.settings.map(settingHtml).filter(Boolean);
      renderedSettings += rowParts.length;
      if (rowParts.length) body += `<section class="section-block"><h2>${esc(section.name)}</h2><div class="settings-grid">${rowParts.join('')}</div></section>`;
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
  function renderSearch() {
    const query = $('#settingsSearch').value.trim().toLowerCase();
    const box = $('#searchResults');
    if (!query) { box.innerHTML = '<div class="empty-state">Suchbegriff eingeben.</div>'; return; }
    const results = settings().filter(s => !s.expert || app.mode === 'expert').filter(s => `${s.label} ${s.description} ${s.key} ${s._category}`.toLowerCase().includes(query));
    box.innerHTML = `<b>${results.length} Treffer</b>${results.map(s=>`<button class="search-result" data-result="${esc(s.key)}"><span><strong>${esc(s.label)}</strong><small>${esc(s.description)}</small></span><span class="result-category">${esc(s._category)}</span></button>`).join('')}`;
    $$('[data-result]').forEach(el => el.onclick = () => {
      const setting = settingByKey(el.dataset.result);
      app.category = setting._category;
      closeSearch();
      render();
      setTimeout(() => targetForSettingKey(setting.key)?.scrollIntoView({behavior:'smooth',block:'center'}), 50);
    });
  }
  function clearValidationIssues() {
    app.validationIssues = [];
  }
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
      render();
      return;
    }
    app.compoundDraft.delete(kind);
    const hourSpec = settingByKey(pair.hour);
    const minuteSpec = settingByKey(pair.minute);
    if (same(parsed.hour, hourSpec.configured)) app.draft.delete(pair.hour); else app.draft.set(pair.hour, parsed.hour);
    if (same(parsed.minute, minuteSpec.configured)) app.draft.delete(pair.minute); else app.draft.set(pair.minute, parsed.minute);
    render();
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
        render();
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
      const firstKey = (i.keys || []).find(key => settingByKey(key));
      const code = app.mode === 'expert' && i.code ? `<span class="issue-code">${esc(i.code)}</span>` : '';
      const jump = firstKey ? `<button type="button" class="issue-jump" data-issue-key="${esc(firstKey)}">Zur Einstellung</button>` : '';
      return `<li class="${esc(i.severity || 'error')}"><div class="issue-copy"><span>${esc(i.message || 'Die Änderung ist nicht zulässig.')}</span>${code}</div>${jump}</li>`;
    }).join('')}</ul>`;
    if (diff.length) out += diff.map(d=>`<div class="diff-row"><div><b>${esc(d.label)}</b><div class="diff-values">${esc(fmt(d.old))} <span class="diff-arrow">→</span> ${esc(fmt(d.new))}</div></div><span class="meta-pill ${d.apply_class==='restart_required'?'restart':'live'}">${esc(d.apply_text)}</span></div>`).join('');
    else if (!issues.length) out += '<div class="notice info">Keine wirksame Änderung erkannt.</div>';
    if (confirmations.length) out += confirmations.map(c=>`<label class="confirmation"><input type="checkbox" data-confirm="${esc(c)}"><span>Hinweis <b>${esc(c)}</b> wurde geprüft und wird bewusst bestätigt.</span></label>`).join('');
    $('#previewBody').innerHTML = out;
    $$('[data-issue-key]').forEach(button => button.onclick = () => jumpToSetting(button.dataset.issueKey));
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
      }
    } catch (error) {
      $('#commitChanges').disabled = false;
      toast(`${action.kind === 'restart' ? 'Neustart' : 'Pointer-Reparatur'} fehlgeschlagen: ${error.message}`);
    }
  }
  async function modalPrimaryAction() {
    if (app.modalMode === 'preview') return commit();
    return runAdminAction();
  }
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
      if ($('#previewModal')?.classList.contains('open')) closePreview();
      else if ($('.settings-sidebar')?.classList.contains('open')) setCategoryDrawerOpen(false);
      else if (document.body.classList.contains('search-open')) closeSearch();
    });
  });
})();
