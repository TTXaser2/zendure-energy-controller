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
  function dirtyCount() { return app.draft.size + Array.from(app.secretOps.values()).filter(x => x.op !== 'keep').length; }
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
  function setCategoryDrawerOpen(open) {
    const sidebar = $('.settings-sidebar');
    const button = $('#mobileMenu');
    const backdrop = $('#categoryDrawerBackdrop');
    const active = categoryDrawerIsMobile() && !!open;
    sidebar?.classList.toggle('open', active);
    document.body.classList.toggle('category-drawer-open', active);
    button?.setAttribute('aria-expanded', String(active));
    sidebar?.setAttribute('aria-hidden', String(categoryDrawerIsMobile() ? !active : false));
    if (backdrop) backdrop.hidden = !active;
  }
  function scrollCategoryToTop() {
    requestAnimationFrame(() => {
      window.scrollTo({top:0, left:0, behavior:'auto'});
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
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
        const content = `<span class="category-link-icon">${icon(c.name)}</span><span>${esc(c.name)}</span><span class="count">${c.setting_count}</span>`;
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
  function inputHtml(s) {
    const value = currentValue(s);
    const disabled = !s.editable || (!dependencyVisible(s) && app.mode === 'expert');
    const dis = disabled ? ' disabled' : '';
    let control = '';
    if (s.value_type === 'bool') {
      control = `<label class="switch"><input type="checkbox" data-key="${esc(s.key)}" ${value === true ? 'checked' : ''}${dis}><span class="switch-track"></span><span>${value === true ? 'Ein' : 'Aus'}</span></label>`;
    } else if (s.value_type === 'enum') {
      control = `<select data-key="${esc(s.key)}"${dis}>${s.options.map(o => `<option value="${esc(o.value)}" ${same(value,o.value)?'selected':''}>${esc(o.label)}</option>`).join('')}</select>`;
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
    if ((!visible && app.mode === 'standard') || (s.expert && app.mode !== 'expert')) return '';
    const dirty = app.draft.has(s.key) || (app.secretOps.get(s.key)?.op && app.secretOps.get(s.key).op !== 'keep');
    const classes = ['setting-row', dirty?'dirty':'', s.pending_restart?'pending':'', s.issues?.some(i=>i.blocking)?'has-error':'', !visible?'hidden-by-dependency':''].filter(Boolean).join(' ');
    let range = '';
    if (s.minimum !== null || s.maximum !== null) range = `Zulässig: ${s.minimum ?? '−∞'}–${s.maximum ?? '∞'}${s.unit ? ` ${s.unit}` : ''}`;
    const metas = [
      range,
      s.default !== null ? `Default: ${String(s.default)}${s.unit ? ` ${s.unit}` : ''}` : '',
      s.configured_differs_effective ? `Wirksam: ${String(s.effective)}` : '',
      s.inherited_default ? 'geerbter Default' : '',
    ].filter(Boolean);
    return `<article class="${classes}" data-setting="${esc(s.key)}">
      <div class="setting-copy"><div class="setting-label">${esc(s.label)}</div>${app.mode==='expert'?`<div class="setting-key">${esc(s.key)}</div>`:''}<div class="setting-help">${esc(s.description || '')}</div></div>
      <div class="setting-editor">${inputHtml(s)}<div class="field-meta">${metas.map(m=>`<span class="meta-pill">${esc(m)}</span>`).join('')}<span class="meta-pill ${s.apply_class==='restart_required'?'restart':'live'}">${esc(s.apply_text || s.apply_class)}</span>${s.editable&&!s.secret_set?`<button type="button" class="reset-button" data-reset="${esc(s.key)}">Auf Default</button>`:''}</div></div>
    </article>`;
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
    if (app.model.status.config_health !== 'valid') body += `<div class="status-banner"><b>Konfigurationsstatus:</b> ${esc(app.model.status.config_health)}. Configured bleibt reparierbar; effective nutzt den letzten gültigen Snapshot.</div>`;
    if (app.model.status.pending_restart) body += `<div class="status-banner"><b>Dienstneustart ausstehend.</b> ${app.model.status.pending_restart_keys.map(esc).join(', ')}</div>`;
    c.sections.forEach(section => {
      const rows = section.settings.map(settingHtml).join('');
      if (rows) body += `<section class="section-block"><h2>${esc(section.name)}</h2><div class="settings-grid">${rows}</div></section>`;
    });
    if (c.name === 'System & Diagnose' && app.mode === 'expert' && app.model.capabilities.restart_action) {
      body += `<section class="section-block admin-actions-section"><h2>Administrative Aktionen</h2><div class="settings-grid"><article class="setting-row full admin-action-card"><div class="setting-copy"><div class="setting-label">Controller-Dienst neu starten</div><div class="setting-help">Startet ausschließlich den Zendure-Controller über den geschützten, fest hinterlegten Helper neu. Ungespeicherte Änderungen werden nicht übernommen. Anschließend werden Version, Build-ID und Ready-Status geprüft.</div></div><div class="setting-editor"><button id="adminRestartAction" class="admin-action-button" type="button">Controller-Dienst neu starten</button></div></article></div></section>`;
    }
    body += '</div>';
    content.innerHTML = body;
    bindInputs();
    const adminRestart = $('#adminRestartAction');
    if (adminRestart) adminRestart.onclick = restart;
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
      setTimeout(() => document.querySelector(`[data-setting="${CSS.escape(setting.key)}"]`)?.scrollIntoView({behavior:'smooth',block:'center'}), 50);
    });
  }
  function bindInputs() {
    $$('[data-key]').forEach(el => {
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
        render();
      };
    });
    $$('[data-reset]').forEach(button => button.onclick = () => {
      const s = settingByKey(button.dataset.reset);
      if (same(s.default, s.configured)) app.draft.delete(s.key); else app.draft.set(s.key, s.default);
      app.preview = null;
      render();
    });
    $$('[data-secret]').forEach(button => button.onclick = () => {
      app.secretOps.set(button.dataset.key, {op:button.dataset.secret});
      app.preview = null;
      render();
    });
    $$('[data-secret-value]').forEach(el => el.oninput = () => {
      app.secretOps.set(el.dataset.secretValue, {op:'replace',value:el.value});
      app.preview = null;
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
    $('#pointerRepairAction').hidden = !app.model.capabilities.last_good_pointer_repair;
    $('#restartAction').hidden = !app.model.status.pending_restart;
    renderNav();
    renderCategory();
    updateBar();
  }
  function payload() {
    const changes = {};
    app.draft.forEach((value,key) => changes[key] = {op:'set', value});
    const secrets = {};
    app.secretOps.forEach((value,key) => secrets[key] = value);
    return {base_revision:app.model.base_revision, changes, secrets};
  }
  async function preview() {
    if (app.previewInFlight || dirtyCount() === 0) return;
    app.previewInFlight = true;
    updateBar();
    try {
      app.preview = await api('/settings/preview', {method:'POST', body:JSON.stringify(payload())});
      openPreview();
    } catch (error) {
      toast(`Prüfung fehlgeschlagen: ${error.message}`);
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
  function openPreview() {
    const p = app.preview;
    let out = '';
    if (p.issues.length) out += `<ul class="issue-list">${p.issues.map(i=>`<li class="${esc(i.severity)}"><b>${esc(i.code)}</b>: ${esc(i.message)}</li>`).join('')}</ul>`;
    if (p.diff.length) out += p.diff.map(d=>`<div class="diff-row"><div><b>${esc(d.label)}</b><div class="diff-values">${esc(fmt(d.old))} <span class="diff-arrow">→</span> ${esc(fmt(d.new))}</div></div><span class="meta-pill ${d.apply_class==='restart_required'?'restart':'live'}">${esc(d.apply_text)}</span></div>`).join('');
    else out += '<div class="notice info">Keine wirksame Änderung erkannt.</div>';
    if (p.confirmations_required.length) out += p.confirmations_required.map(c=>`<label class="confirmation"><input type="checkbox" data-confirm="${esc(c)}"><span>Hinweis <b>${esc(c)}</b> wurde geprüft und wird bewusst bestätigt.</span></label>`).join('');
    $('#previewBody').innerHTML = out;
    $('#commitChanges').disabled = p.status !== 'ready' || !p.preview_id;
    lockPreviewScroll();
    $('#previewModal').classList.add('open');
    $('#previewClose')?.focus({preventScroll:true});
  }
  function closePreview() {
    $('#previewModal').classList.remove('open');
    $('#previewBody').innerHTML = '';
    app.preview = null;
    unlockPreviewScroll();
    updateBar();
  }
  async function commit() {
    try {
      const confirmations = $$('[data-confirm]:checked').map(x => x.dataset.confirm);
      const result = await api('/settings/commit', {method:'POST', body:JSON.stringify({preview_id:app.preview.preview_id, confirmations})});
      closePreview();
      app.draft.clear();
      app.secretOps.clear();
      toast(result.pending_restart ? 'Gespeichert. Dienstneustart erforderlich.' : 'Änderungen gespeichert und live übernommen.');
      await load();
    } catch (error) { toast(`Speichern fehlgeschlagen: ${error.message}`); }
  }
  function discard() { app.draft.clear(); app.secretOps.clear(); app.preview = null; render(); }
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
  async function restart() {
    if (!confirm('Dienstneustart vorbereiten? Ungespeicherte Änderungen werden nicht übernommen.')) return;
    if (!confirm('Dienst jetzt wirklich neu starten und anschließend ready=true prüfen?')) return;
    try {
      const info = await api('/restart-service', {method:'POST', body:JSON.stringify({confirmation:'RESTART_SERVICE'})});
      pollReady(info);
    } catch (error) { toast(`Neustart fehlgeschlagen: ${error.message}`); }
  }
  async function repairPointer() {
    try {
      const p = await api('/admin/last-good-pointer-repair/preview', {method:'POST',body:'{}'});
      const summary = `Slot ${p.target_slot}, Generation ${p.generation_id}\nTyped: ${p.typed_revision}\nConfig: ${p.config_hash}\nManifest: ${p.manifest_hash}`;
      if (!confirm(`Pointer-Reparatur prüfen:\n\n${summary}\n\nEs werden keine Slot- oder Config-Dateien geändert.`)) return;
      if (!confirm('Current-Pointer jetzt atomar auf den verifizierten Slot setzen?')) return;
      await api('/admin/last-good-pointer-repair/commit', {method:'POST',body:JSON.stringify({action_token:p.action_token,confirmation:'REPAIR_POINTER'})});
      toast('Last-Good-Pointer erfolgreich repariert.');
      await load();
    } catch (error) { toast(`Pointer-Reparatur fehlgeschlagen: ${error.message}`); }
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
    $('#commitChanges').onclick = commit;
    $('#mobileMenu').onclick = () => setCategoryDrawerOpen(!$('.settings-sidebar')?.classList.contains('open'));
    $('#categoryDrawerBackdrop').onclick = () => setCategoryDrawerOpen(false);
    setCategoryDrawerOpen(false);
    window.addEventListener('resize', () => setCategoryDrawerOpen(false));
    $('#restartAction').onclick = restart;
    $('#pointerRepairAction').onclick = repairPointer;
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
