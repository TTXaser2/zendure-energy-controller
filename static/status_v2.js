(() => {
  'use strict';
  const bootstrap = window.ZEC_BOOTSTRAP || {};
  const $ = (s, root=document) => root.querySelector(s);
  const $$ = (s, root=document) => Array.from(root.querySelectorAll(s));
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

  function text(path, value) {
    $$(`[data-zec="${path}"]`).forEach(el => {
      el.textContent = value === null || value === undefined || value === '' ? '—' : String(value);
    });
  }
  function setHidden(path, hidden) {
    $$(`[data-zec="${path}"]`).forEach(el => { el.hidden = !!hidden; });
  }
  function number(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }
  function fmtPower(value) {
    const n = number(value);
    if (n === null) return '—';
    const sign = n > 0 ? '+' : n < 0 ? '−' : '';
    const a = Math.abs(n);
    if (a >= 1_000_000_000) return `${sign}${(a / 1_000_000_000).toLocaleString('de-DE',{maximumFractionDigits:2})} GW`;
    if (a >= 1_000_000) return `${sign}${(a / 1_000_000).toLocaleString('de-DE',{maximumFractionDigits:2})} MW`;
    if (a >= 1000) return `${sign}${(a / 1000).toLocaleString('de-DE',{minimumFractionDigits:a < 10000 ? 2 : 1,maximumFractionDigits:a < 10000 ? 2 : 1})} kW`;
    return `${sign}${Math.round(a).toLocaleString('de-DE')} W`;
  }
  function fmtSoc(value) {
    const n = number(value);
    return n === null ? '—' : `${Math.round(n)} %`;
  }
  function setDot(footer, tone) {
    const dot = $('.zec-status-dot', footer);
    if (dot) dot.className = `zec-status-dot ${tone || 'unknown'}`;
  }
  function setRing(key, soc, tone='ok') {
    const ring = $(`[data-ring="${key}"]`);
    if (!ring) return;
    const n = number(soc);
    ring.style.setProperty('--soc', n === null ? 0 : Math.max(0, Math.min(100, n)));
    ring.classList.toggle('is-unknown', n === null);
    ring.classList.toggle('is-warn', tone === 'warn');
    ring.classList.toggle('is-bad', tone === 'bad');
    const value = $('.zec-soc-ring-inner strong', ring);
    if (value) value.textContent = fmtSoc(soc);
  }

  function updateSystemMenu(system) {
    if (!system) return;
    const button = $('#systemStatusButton');
    if (button) {
      button.className = `zec-system-pill ${system.kind || 'ok'}`;
      text('system.label', system.label || 'Systemstatus');
    }
    const list = $('#systemWarningList');
    if (list) {
      const warnings = Array.isArray(system.warnings) ? system.warnings : [];
      list.innerHTML = (warnings.length ? warnings : ['Keine aktiven Warnungen oder Fehler.'])
        .map(item => `<li>${escapeHtml(item)}</li>`).join('');
    }
    const banner = $('#criticalBanner');
    if (banner) banner.hidden = system.kind !== 'bad';
    text('system.critical_text', system.critical_text || 'Regelung ist eingeschränkt.');
  }
  function escapeHtml(v) {
    const d = document.createElement('div'); d.textContent = String(v ?? ''); return d.innerHTML;
  }

  function applyStatus(p) {
    if (!p) return;
    updateSystemMenu(p.system);
    text('server_time', p.server_time);

    text('grid.value', p.grid?.value);
    text('grid.status', p.grid?.status);
    text('grid.source', p.grid?.source);
    text('grid.freshness_text', p.grid?.freshness_text);
    const gv = $('.zec-grid-value');
    if (gv) {
      gv.classList.toggle('is-import', p.grid?.tone === 'warn');
      gv.classList.toggle('is-import-high', p.grid?.tone === 'bad');
      gv.classList.toggle('is-unknown', p.grid?.tone === 'unknown');
    }
    const gf = $('[data-card="grid"] .zec-card-footer'); if (gf) setDot(gf, p.grid?.tone);

    text('mode.mode', p.mode?.mode);
    text('mode.text', p.mode?.text);
    text('mode.target', p.mode?.target);
    text('mode.reason', p.mode?.reason);
    text('mode.projection', p.mode?.projection || '');
    text('mode.last_change', p.mode?.last_change);
    text('mode.status_text', p.mode?.status_text);
    const mf = $('[data-card="mode"] .zec-card-footer'); if (mf) setDot(mf, p.mode?.tone);

    text('zendure.actual', p.zendure?.actual);
    text('zendure.state', p.zendure?.units?.[0]?.state_text);
    text('zendure.remaining_text', p.zendure?.remaining_text);
    text('zendure.max_soc_text', p.zendure?.max_soc_text);
    text('zendure.system_soc_text', p.zendure?.system_soc_text);
    text('zendure.source', p.zendure?.source);
    const units = Array.isArray(p.zendure?.units) ? p.zendure.units : [];
    if (units.length <= 1) setRing('zendure', units[0]?.soc ?? p.zendure?.soc, units[0]?.tone || p.zendure?.tone);
    else {
      setRing('zendure_unit_1', units[0]?.soc, units[0]?.tone);
      setRing('zendure_unit_2', units[1]?.soc, units[1]?.tone);
      text('zendure_unit_1.caption', units[0]?.state_text);
      text('zendure_unit_2.caption', units[1]?.state_text);
      units.slice(0,2).forEach((unit, index) => text(`zendure.units.${index}.detail`, unit.detail));
    }
    const zw = $('[data-zec="zendure.command_warning"]');
    if (zw) { zw.textContent = p.zendure?.command_warning || ''; zw.hidden = !p.zendure?.command_warning; }
    const zf = $('[data-card="zendure"] .zec-card-footer'); if (zf) setDot(zf, p.zendure?.tone);

    setRing('primary', p.primary?.soc, p.primary?.tone);
    text('primary.actual', p.primary?.actual);
    text('primary.status', p.primary?.status);
    text('primary.line', p.primary?.line);
    text('primary.source', p.primary?.source);
    text('primary.freshness_text', p.primary?.freshness_text);
    const pf = $('[data-card="primary"] .zec-card-footer'); if (pf) setDot(pf, p.primary?.tone);

    text('source.name', p.source?.name);
    text('source.device_line', p.source?.device_line);
    text('source.age_text', p.source?.age_text);
    text('source.packets_text', p.source?.packets_text);
    text('source.auto_text', p.source?.auto_text);
    text('source.rejected_text', p.source?.rejected_text);
    text('source.rejected_count_text', p.source?.rejected_count_text);
    setHidden('source.rejected_text', !p.source?.rejected_text);
    setHidden('source.rejected_count_text', !p.source?.rejected_count_text);
    const sf = $('[data-card="source"] .zec-card-footer'); if (sf) setDot(sf, p.source?.tone);

    ['status','target','db','db_name'].forEach(k => text(`logging.${k}`, p.logging?.[k]));
    ['mqtt','api','effect','resync','loop_text','measurement_logging_text'].forEach(k => text(`diag.${k}`, p.diag?.[k]));
  }

  class PollChannel {
    constructor(url, intervalMs, handler, timeoutMs=2500) {
      this.url=url; this.intervalMs=intervalMs; this.handler=handler; this.timeoutMs=timeoutMs;
      this.timer=null; this.inFlight=false; this.controller=null;
    }
    async run() {
      if (document.visibilityState === 'hidden' || this.inFlight) return;
      this.inFlight=true; this.controller=new AbortController();
      const timeout=setTimeout(()=>this.controller.abort(),this.timeoutMs);
      try {
        const r=await fetch(this.url,{cache:'no-store',signal:this.controller.signal});
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        await this.handler(await r.json());
      } catch (_) {
        // Existing values intentionally remain visible.  Never replace data by zero.
      } finally {
        clearTimeout(timeout); this.controller=null; this.inFlight=false;
      }
    }
    start(jitter=0) {
      setTimeout(()=>{ this.run(); this.timer=setInterval(()=>this.run(),this.intervalMs); },jitter);
    }
  }

  class CanvasChart {
    constructor(canvas, tooltip) {
      this.canvas=canvas; this.tooltip=tooltip; this.hoverX=null; this.payload=null; this.kind='';
      this.resizeObserver=new ResizeObserver(()=>this.draw()); this.resizeObserver.observe(canvas);
      canvas.addEventListener('mousemove',e=>this.onMove(e));
      canvas.addEventListener('mouseleave',()=>{this.hoverX=null; this.tooltip.hidden=true; this.draw();});
      canvas.addEventListener('touchstart',e=>{if(e.touches[0])this.onMove(e.touches[0]);},{passive:true});
    }
    prepare() {
      const rect=this.canvas.getBoundingClientRect(); const dpr=window.devicePixelRatio||1;
      const w=Math.max(10,Math.floor(rect.width)); const h=Math.max(10,Math.floor(rect.height));
      if(this.canvas.width!==Math.floor(w*dpr)||this.canvas.height!==Math.floor(h*dpr)){
        this.canvas.width=Math.floor(w*dpr); this.canvas.height=Math.floor(h*dpr);
      }
      const ctx=this.canvas.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,w,h);
      return {ctx,w,h};
    }
    onMove(e) {
      if(!this.payload)return; const rect=this.canvas.getBoundingClientRect();
      this.hoverX=Math.max(0,Math.min(rect.width,e.clientX-rect.left)); this.draw();
    }
    showTooltip(html,x,y) {
      this.tooltip.innerHTML=html; this.tooltip.hidden=false;
      const wrap=this.canvas.parentElement.getBoundingClientRect(); const tip=this.tooltip.getBoundingClientRect();
      let left=x+12, top=y-tip.height-10;
      if(left+tip.width>wrap.width-4)left=x-tip.width-12;
      if(top<2)top=y+12;
      this.tooltip.style.left=`${Math.max(2,left)}px`; this.tooltip.style.top=`${Math.max(2,top)}px`;
    }
  }

  class MiniGridChart extends CanvasChart {
    setData(payload){this.payload=payload||{points:[]};this.kind='mini';this.draw();}
    draw(){
      const {ctx,w,h}=this.prepare(); const pts=this.payload?.points||[]; const values=pts.map(p=>number(p.value)).filter(v=>v!==null);
      if(values.length<2){ctx.fillStyle=css('--zec-muted');ctx.font='11px sans-serif';ctx.fillText('keine Verlaufshistorie verfügbar',8,h/2);return;}
      let lo=Math.min(...values,0),hi=Math.max(...values,0);if(Math.abs(hi-lo)<1)hi=lo+1;
      const pad={l:36,r:8,t:10,b:20}; const pw=w-pad.l-pad.r,ph=h-pad.t-pad.b;
      const x=i=>pad.l+(i/Math.max(1,pts.length-1))*pw; const y=v=>pad.t+(1-(v-lo)/(hi-lo))*ph;
      ctx.strokeStyle=css('--zec-card-border');ctx.lineWidth=1;
      [0,.5,1].forEach(f=>{ctx.beginPath();ctx.moveTo(pad.l,pad.t+f*ph);ctx.lineTo(w-pad.r,pad.t+f*ph);ctx.stroke();});
      if(lo<0&&hi>0){ctx.strokeStyle=css('--zec-subtle');ctx.setLineDash([3,3]);ctx.beginPath();ctx.moveTo(pad.l,y(0));ctx.lineTo(w-pad.r,y(0));ctx.stroke();ctx.setLineDash([]);}
      ctx.strokeStyle=css('--zec-green');ctx.lineWidth=2;ctx.beginPath();
      pts.forEach((p,i)=>{const v=number(p.value);if(v===null)return;const px=x(i),py=y(v);if(i===0)ctx.moveTo(px,py);else ctx.lineTo(px,py);});ctx.stroke();
      ctx.fillStyle=css('--zec-muted');ctx.font='9px sans-serif';ctx.fillText(fmtPower(hi),0,12);ctx.fillText(fmtPower(lo),0,h-18);ctx.fillText('letzte 48 Punkte',pad.l,h-4);ctx.textAlign='right';ctx.fillText(`aktuell ${fmtPower(values.at(-1))}`,w-pad.r,h-4);ctx.textAlign='left';
      if(this.hoverX!==null){const idx=Math.max(0,Math.min(pts.length-1,Math.round((this.hoverX-pad.l)/pw*(pts.length-1))));const p=pts[idx];const v=number(p.value);if(v!==null){const px=x(idx),py=y(v);ctx.strokeStyle=css('--zec-blue');ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(px,pad.t);ctx.lineTo(px,h-pad.b);ctx.stroke();ctx.fillStyle=css('--zec-blue');ctx.beginPath();ctx.arc(px,py,3.5,0,Math.PI*2);ctx.fill();this.showTooltip(`<strong>${escapeHtml(p.time||'')}</strong><div class="zec-chart-tooltip-row"><span>Netzleistung</span><b>${escapeHtml(fmtPower(v))}</b></div><div class="zec-chart-tooltip-row"><span>Status</span><b>${escapeHtml(p.status||'—')}</b></div>`,px,py);}}
    }
  }

  class SocDayChart extends CanvasChart {
    setData(payload){this.payload=payload||{points:[]};this.kind='soc';this.drawLegend();this.draw();}
    series(){
      const p=this.payload||{}; const colors=[css('--zec-green'),css('--zec-blue'),'#ef5f75'];
      const defs=[];
      const count=Number(p.zendure_unit_count||1);
      if(count>1){defs.push({key:'zendure_unit_1_soc',label:p.unit_labels?.[0]||'Zendure 1',color:colors[0]});defs.push({key:'zendure_unit_2_soc',label:p.unit_labels?.[1]||'Zendure 2',color:colors[1]});}
      else defs.push({key:'zendure_soc',label:'Zendure',color:colors[0]});
      defs.push({key:'primary_soc',label:'Primärspeicher',color:colors[2]});
      return defs;
    }
    drawLegend(){const legend=$('#storageSocLegend');if(!legend)return;legend.innerHTML=this.series().map(s=>`<span class="zec-legend-item"><i class="zec-legend-line" style="background:${s.color}"></i>${escapeHtml(s.label)}</span>`).join('');}
    draw(){
      const {ctx,w,h}=this.prepare(); const p=this.payload||{}; const points=p.points||[]; const pad={l:42,r:12,t:10,b:28};const pw=w-pad.l-pad.r,ph=h-pad.t-pad.b;
      const x=m=>pad.l+(Number(m)/1440)*pw; const y=v=>pad.t+(1-Number(v)/100)*ph;
      ctx.fillStyle=css('--zec-card-bg');ctx.fillRect(0,0,w,h);
      const nw=p.night_window||{}; const toMin=t=>{const m=String(t||'').match(/^(\d+):(\d+)/);return m?Number(m[1])*60+Number(m[2]):null;};const ns=toMin(nw.start),ne=toMin(nw.end);
      if(ns!==null&&ne!==null){ctx.fillStyle=css('--zec-blue-soft'); if(ns>ne){ctx.fillRect(x(0),pad.t,x(ne)-x(0),ph);ctx.fillRect(x(ns),pad.t,x(1440)-x(ns),ph);}else ctx.fillRect(x(ns),pad.t,x(ne)-x(ns),ph);}
      ctx.strokeStyle=css('--zec-card-border');ctx.lineWidth=1;ctx.fillStyle=css('--zec-muted');ctx.font='10px sans-serif';
      for(let v=0;v<=100;v+=20){const py=y(v);ctx.beginPath();ctx.moveTo(pad.l,py);ctx.lineTo(w-pad.r,py);ctx.stroke();ctx.textAlign='right';ctx.fillText(`${v} %`,pad.l-7,py+3);}
      [0,360,720,1080,1440].forEach(m=>{const px=x(m);ctx.beginPath();ctx.moveTo(px,pad.t);ctx.lineTo(px,h-pad.b);ctx.stroke();ctx.textAlign=m===0?'left':m===1440?'right':'center';ctx.fillText(`${String(Math.floor(m/60)).padStart(2,'0')}:00`,px,h-8);});ctx.textAlign='left';
      const thresholds=p.thresholds||{}; [['min_soc','Min-SOC'],['max_soc','Max-SOC'],['reserve_soc','Reserve']].forEach(([key,label])=>{const v=number(thresholds[key]);if(v===null)return;ctx.strokeStyle=key==='reserve_soc'?css('--zec-amber'):css('--zec-subtle');ctx.setLineDash([5,4]);ctx.beginPath();ctx.moveTo(pad.l,y(v));ctx.lineTo(w-pad.r,y(v));ctx.stroke();ctx.setLineDash([]);});
      const series=this.series();
      series.forEach(s=>{ctx.strokeStyle=s.color;ctx.lineWidth=2;ctx.beginPath();let started=false;points.forEach(pt=>{const v=number(pt[s.key]);if(v===null){started=false;return;}const px=x(pt.minute),py=y(v);if(!started){ctx.moveTo(px,py);started=true;}else ctx.lineTo(px,py);});ctx.stroke();});
      if(p.is_today){const now=new Date();const minute=now.getHours()*60+now.getMinutes();ctx.strokeStyle=css('--zec-blue');ctx.setLineDash([2,4]);ctx.beginPath();ctx.moveTo(x(minute),pad.t);ctx.lineTo(x(minute),h-pad.b);ctx.stroke();ctx.setLineDash([]);}
      if(this.hoverX!==null&&points.length){const minute=Math.max(0,Math.min(1440,Math.round((this.hoverX-pad.l)/pw*1440)));let nearest=points[0],dist=Infinity;points.forEach(pt=>{const d=Math.abs(Number(pt.minute)-minute);if(d<dist){dist=d;nearest=pt;}});const px=x(nearest.minute);ctx.strokeStyle=css('--zec-blue');ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(px,pad.t);ctx.lineTo(px,h-pad.b);ctx.stroke();series.forEach(s=>{const v=number(nearest[s.key]);if(v===null)return;ctx.fillStyle=s.color;ctx.beginPath();ctx.arc(px,y(v),3.5,0,Math.PI*2);ctx.fill();});const rows=series.map(s=>`<div class="zec-chart-tooltip-row"><span>${escapeHtml(s.label)}</span><b>${escapeHtml(fmtSoc(nearest[s.key]))}</b></div>`).join('');this.showTooltip(`<strong>${escapeHtml(p.date||'')} ${escapeHtml(nearest.time||'')}</strong>${rows}<div class="zec-chart-tooltip-row"><span>Zendure-Leistung</span><b>${escapeHtml(fmtPower(nearest.zendure_power_w))}</b></div><div class="zec-chart-tooltip-row"><span>Primärspeicher</span><b>${escapeHtml(fmtPower(nearest.primary_power_w))}</b></div><div class="zec-chart-tooltip-row"><span>Modus</span><b>${escapeHtml(nearest.mode||'—')}</b></div><div class="zec-chart-tooltip-row"><span>Grund</span><b>${escapeHtml(nearest.reason||'—')}</b></div>`,px,pad.t+ph*.55);}
    }
  }

  const miniChart = new MiniGridChart($('#gridMiniChart'), $('#gridMiniTooltip'));
  const socChart = new SocDayChart($('#storageSocChart'), $('#storageSocTooltip'));

  function setupInfoPopovers(){
    const pop=$('#zecInfoPopover'), title=$('#zecInfoTitle'), body=$('#zecInfoText');let current=null;
    const close=()=>{pop.hidden=true;current=null;};
    const open=(button)=>{current=button;title.textContent=button.dataset.infoTitle||'Information';body.textContent=button.dataset.infoText||'';pop.hidden=false;const r=button.getBoundingClientRect();const pr=pop.getBoundingClientRect();let left=r.right-pr.width;let top=r.bottom+8;if(left<12)left=12;if(left+pr.width>innerWidth-12)left=innerWidth-pr.width-12;if(top+pr.height>innerHeight-12)top=r.top-pr.height-8;pop.style.left=`${Math.max(12,left)}px`;pop.style.top=`${Math.max(12,top)}px`;};
    $$('.zec-info-button').forEach(btn=>{btn.addEventListener('mouseenter',()=>open(btn));btn.addEventListener('focus',()=>open(btn));btn.addEventListener('click',e=>{e.stopPropagation();current===btn&&!pop.hidden?close():open(btn);});btn.addEventListener('mouseleave',e=>{if(!pop.matches(':hover'))close();});});
    pop.addEventListener('mouseleave',close);document.addEventListener('click',e=>{if(!e.target.closest('.zec-info-button')&&!e.target.closest('#zecInfoPopover'))close();});window.addEventListener('resize',close);window.addEventListener('scroll',close,true);
  }
  function setupMenus(){
    const pairs=[['#systemStatusButton','#systemStatusMenu'],['#expertMenuButton','#expertMenu']];
    pairs.forEach(([bs,ms])=>{const b=$(bs),m=$(ms);if(!b||!m)return;b.addEventListener('click',e=>{e.stopPropagation();const next=!m.hidden;pairs.forEach(([ob,om])=>{const x=$(om),y=$(ob);if(x)x.hidden=true;if(y)y.setAttribute('aria-expanded','false');});m.hidden=!next;b.setAttribute('aria-expanded',String(next));});});
    document.addEventListener('click',()=>pairs.forEach(([b,m])=>{const menu=$(m),btn=$(b);if(menu)menu.hidden=true;if(btn)btn.setAttribute('aria-expanded','false');}));
    $$('.analysis-service-link').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();location.href=`//${location.hostname}:${a.dataset.replayPort}`;}));
  }
  function startClock(){const el=$('#localClock');const update=()=>{if(el)el.textContent=new Date().toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit',second:'2-digit'});};update();setInterval(update,1000);}

  let statusSequence=0;
  const statusPoll=new PollChannel('/status-view-data',3000,p=>{const seq=number(p.snapshot_epoch_ms)||Date.now();if(seq<statusSequence)return;statusSequence=seq;applyStatus(p);},2500);
  const miniPoll=new PollChannel('/grid-mini-data',10000,p=>miniChart.setData(p),2500);

  let selectedDate=new Date(); let dayInFlight=false; let dayController=null;
  const dateString=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  const dayLabel=d=>d.toLocaleDateString('de-DE',{weekday:'short',day:'2-digit',month:'2-digit',year:'numeric'});
  async function refreshSocDay(){
    if(document.visibilityState==='hidden'||dayInFlight)return;dayInFlight=true;dayController=new AbortController();const timeout=setTimeout(()=>dayController.abort(),5000);
    const status=$('#storageSocStatus');const ds=dateString(selectedDate);$('#socDayLabel').textContent=dayLabel(selectedDate);$('#dayNext').disabled=ds>=dateString(new Date());
    try{const r=await fetch(`/storage-soc-day-data?date=${encodeURIComponent(ds)}`,{cache:'no-store',signal:dayController.signal});if(!r.ok)throw new Error(`HTTP ${r.status}`);const p=await r.json();socChart.setData(p);status.textContent=p.is_today?`Stand: ${p.last_point_at||'—'} · aktualisiert alle 60 s · Quelle: ${p.source||'—'} · Cache ${p.cache_status||'—'}`:`${p.complete===false?'Daten unvollständig':'Vollständiger Tag'}: ${p.date} · Quelle: ${p.source||'—'} · Cache ${p.cache_status||'—'}`;}catch(e){status.textContent='SOC-Tageskurve wird noch vorbereitet oder ist vorübergehend nicht verfügbar.';}finally{clearTimeout(timeout);dayController=null;dayInFlight=false;}
  }

  $('#dayPrev').addEventListener('click',()=>{selectedDate.setDate(selectedDate.getDate()-1);refreshSocDay();});
  $('#dayNext').addEventListener('click',()=>{const n=new Date(selectedDate);n.setDate(n.getDate()+1);if(dateString(n)<=dateString(new Date())){selectedDate=n;refreshSocDay();}});
  $('#dayToday').addEventListener('click',()=>{selectedDate=new Date();refreshSocDay();});

  setupInfoPopovers(); setupMenus(); startClock(); applyStatus(bootstrap);
  statusPoll.start(Math.floor(Math.random()*700)); miniPoll.start(Math.floor(Math.random()*1000)); refreshSocDay();
  setInterval(()=>{if(dateString(selectedDate)===dateString(new Date()))refreshSocDay();},60000);
  document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'){statusPoll.run();miniPoll.run();refreshSocDay();}});
})();
