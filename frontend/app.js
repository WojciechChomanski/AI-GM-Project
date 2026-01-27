/* =========================================================================
   The Breath & The Veil — Minimal Frontend (Turn-Based v1.1 — Debugged)
   ========================================================================= */
const API_BASE_URL = ""; // Relative fetches
const STORAGE = {
  chars: 'btv.characters',
  maps: 'btv.maps',
  activeChar: 'btv.activeCharacterId',
  activeMap: 'btv.activeMapId',
  combat: mapId => `btv.combat.${mapId||'none'}`
};
const $ = sel => document.querySelector(sel);
/* ------------------------- State & Persistence -------------------------- */
const state = {
  characters: load('btv.characters', []),
  maps: load('btv.maps', []),
  activeCharId: load('btv.activeCharacterId', null),
  activeMapId: load('btv.activeMapId', null),
  classes: null,
  spells: null
};
function save(key, val){ localStorage.setItem(key, JSON.stringify(val)); }
function load(key, fallback){ try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } }
function uid(){ return Math.random().toString(36).slice(2)+Date.now().toString(36); }
function byId(arr,id){ return arr.find(x=>x.id===id) || null; }
function escapeHtml(s){ return (s??'').toString().replace(/[&<>"']/g, m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
/* ------------------------------- Canvas Map ----------------------------- */
const els = {
  charList: $('#char-list'),
  mapList: $('#map-list'),
  chkGrid: $('#chk-grid'),
  gridSize: $('#grid-size'),
  hudZoom: $('#hud-zoom'),
  hudPos: $('#hud-pos'),
  hudChar: $('#hud-char'),
  canvas: $('#map-canvas'),
  apiStatus: $('#api-status'),
  chatLog: $('#chat-log'),
  chatForm: $('#chat-form'),
  chatInput: $('#chat-input'),
  dlgChar: $('#dlg-char'),
  dlgMap: $('#dlg-map'),
  charForm: $('#char-form'),
  mapForm: $('#map-form'),
  fileOpen: $('#file-open'),
  selTeam: $('#sel-team'),
  btnAddCombat: $('#btn-combat-add'),
  btnRemoveCombat: $('#btn-combat-remove'),
  btnRollInit: $('#btn-roll-init'),
  btnStartCombat: $('#btn-start-combat'),
  btnNextTurn: $('#btn-next-turn'),
  btnEndCombat: $('#btn-end-combat'),
  turnInfo: $('#turn-info'),
  turnOrder: $('#turn-order'),
  actMove: $('#act-move'),
  actAttack: $('#act-attack'),
  actAbility: $('#act-ability'),
  actDefend: $('#act-defend'),
  actEnd: $('#act-end'),
  charRace: $('#char-race'),
  charGender: $('#char-gender'),
  charClass: $('#char-class'),
  charOrientation: $('#char-orientation')
};
const ctx = els.canvas.getContext('2d');
const view = {
  img: null,
  zoom: 1, minZoom: 0.25, maxZoom: 3,
  pan: {x:0,y:0},
  grid: {show:true, size:64},
  tokens: [],
  selectedTokenId: null,
};
function resizeCanvas(){
  const dpr = window.devicePixelRatio || 1;
  const rect = els.canvas.getBoundingClientRect();
  els.canvas.width = Math.floor(rect.width * dpr);
  els.canvas.height = Math.floor(rect.height* dpr);
  ctx.setTransform(dpr,0,0,dpr,0,0);
  draw();
}
window.addEventListener('resize', resizeCanvas);
function draw(){
  ctx.clearRect(0,0,els.canvas.width,els.canvas.height);
  ctx.save();
  ctx.translate(view.pan.x, view.pan.y);
  ctx.scale(view.zoom, view.zoom);
  if(view.img){
    ctx.drawImage(view.img, 0, 0);
  } else {
    const s=64;
    for(let y=0;y<els.canvas.height;y+=s){
      for(let x=0;x<els.canvas.width;x+=s){
        ctx.fillStyle = ((x+y)/s)%2===0 ? '#0f141e' : '#0c1118';
        ctx.fillRect(x,y,s,s);
      }
    }
  }
  if(view.grid.show){
    const s = view.grid.size;
    ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--grid') || '#2a2f40';
    ctx.lineWidth = 1/ view.zoom;
    ctx.beginPath();
    const W = view.img ? view.img.width : els.canvas.width;
    const H = view.img ? view.img.height: els.canvas.height;
    for(let x=0;x<=W;x+=s){ ctx.moveTo(x,0); ctx.lineTo(x,H); }
    for(let y=0;y<=H;y+=s){ ctx.moveTo(0,y); ctx.lineTo(W,y); }
    ctx.stroke();
  }
  for(const t of view.tokens){
    drawToken(t);
  }
  ctx.restore();
}
function drawToken(t){
  const r = 16;
  const x=t.x, y=t.y;
  const isSelected = view.selectedTokenId===t.id;
  const actor = combat.actors[t.id];
  const isCurrent = combat.inProgress && combat.order[combat.currentIndex]===t.id;
  if(isCurrent){
    ctx.save();
    ctx.translate(view.pan.x, view.pan.y);
    ctx.scale(view.zoom, view.zoom);
    ctx.beginPath();
    ctx.arc(x,y, r+8, 0, Math.PI*2);
    ctx.strokeStyle = '#ffb86c';
    ctx.lineWidth = 2 / view.zoom;
    ctx.stroke();
    ctx.restore();
  }
  ctx.save();
  ctx.fillStyle = t.color || '#8dd3ff';
  ctx.beginPath();
  ctx.arc(x,y,r,0,Math.PI*2);
  ctx.fill();
  if(isSelected){
    ctx.lineWidth = 3 / view.zoom;
    ctx.strokeStyle = '#ffd28a';
    ctx.stroke();
  }
  ctx.fillStyle = '#0b0f18';
  ctx.font = `${12/ view.zoom}px system-ui, Arial`;
  ctx.textAlign='center'; ctx.textBaseline='middle';
  ctx.fillText(t.label ?? 'X', x, y-24/ view.zoom);
  if(actor){
    const w = 44, h = 6, px = x - w/2, py = y - 36/ view.zoom;
    const pct = Math.max(0, Math.min(1, actor.hp/actor.hpMax));
    ctx.fillStyle = '#202636';
    ctx.fillRect(px, py, w, h);
    ctx.fillStyle = pct>0.5 ? '#22c55e' : (pct>0.25 ? '#facc15' : '#ef4444');
    ctx.fillRect(px, py, w*pct, h);
    ctx.strokeStyle = '#0e1420';
    ctx.lineWidth = 1/ view.zoom;
    ctx.strokeRect(px, py, w, h);
  }
  ctx.restore();
}
/* ----------------------------- Input & Utils ---------------------------- */
function screenToWorld(e){
  const rect = els.canvas.getBoundingClientRect();
  const x = (e.clientX - rect.left - view.pan.x)/view.zoom;
  const y = (e.clientY - rect.top - view.pan.y)/view.zoom;
  return {x,y};
}
function hitTestToken(x,y){
  const r=18;
  for(let i=view.tokens.length-1;i>=0;i--){
    const t=view.tokens[i];
    const dx=x-t.x, dy=y-t.y;
    if(dx*dx+dy*dy <= r*r) return t;
  }
  return null;
}
let drag = { mode:null, start:{x:0,y:0}, pan0:{x:0,y:0}, tokenId:null };
els.canvas.addEventListener('wheel', e=>{
  e.preventDefault();
  const delta = Math.sign(e.deltaY);
  const factor = (delta>0)? 0.9 : 1.1;
  const old = view.zoom;
  const nz = Math.min(view.maxZoom, Math.max(view.minZoom, old*factor));
  if(nz===old) return;
  const rect = els.canvas.getBoundingClientRect();
  const cx = (e.clientX-rect.left - view.pan.x)/old;
  const cy = (e.clientY-rect.top - view.pan.y)/old;
  view.pan.x = e.clientX-rect.left - cx*nz;
  view.pan.y = e.clientY-rect.top - cy*nz;
  view.zoom = nz;
  draw(); updateHud();
},{passive:false});
els.canvas.addEventListener('pointerdown', e=>{
  els.canvas.setPointerCapture(e.pointerId);
  const pos = screenToWorld(e);
  if(combat.pending?.type){
    handlePendingActionPointer(pos);
    return;
  }
  const tok = hitTestToken(pos.x,pos.y);
  if(tok){
    drag.mode = 'token';
    drag.tokenId = tok.id;
  } else {
    drag.mode = 'pan';
    drag.pan0 = {...view.pan};
  }
  drag.start = {x:e.clientX, y:e.clientY};
});
els.canvas.addEventListener('pointermove', e=>{
  const pos = screenToWorld(e);
  els.hudPos.textContent = `${Math.round(pos.x)},${Math.round(pos.y)}`;
  if(!drag.mode) return;
  const dx = e.clientX - drag.start.x;
  const dy = e.clientY - drag.start.y;
  if(drag.mode==='pan'){
    view.pan.x = drag.pan0.x + dx;
    view.pan.y = drag.pan0.y + dy;
  } else if(drag.mode==='token'){
    const t = view.tokens.find(t=>t.id===drag.tokenId);
    if(t){
      const w = screenToWorld(e);
      if(e.altKey && view.grid.show){
        t.x = Math.round(w.x / view.grid.size) * view.grid.size;
        t.y = Math.round(w.y / view.grid.size) * view.grid.size;
      } else {
        t.x = w.x; t.y = w.y;
      }
    }
  }
  draw();
});
els.canvas.addEventListener('pointerup', e=>{
  els.canvas.releasePointerCapture(e.pointerId);
  drag.mode=null; drag.tokenId=null;
});
els.canvas.addEventListener('dblclick', e=>{
  const pos = screenToWorld(e);
  const tok = hitTestToken(pos.x,pos.y);
  view.selectedTokenId = tok ? tok.id : null;
  draw();
});
window.addEventListener('keydown', e=>{
  if(e.key==='Delete' && view.selectedTokenId){
    const i = view.tokens.findIndex(t=>t.id===view.selectedTokenId);
    if(i>=0){
      removeFromCombat(view.tokens[i].id);
      view.tokens.splice(i,1);
      view.selectedTokenId=null;
      draw();
      renderCombat();
    }
  } else if(e.key.toLowerCase()==='r'){ resetView(); }
  else if(e.key.toLowerCase()==='g'){
    view.grid.show = !view.grid.show; els.chkGrid.checked = view.grid.show; draw();
  }
});
/* ----------------------------- HUD & Helpers ---------------------------- */
function updateHud(){
  els.hudZoom.textContent = `${Math.round(view.zoom*100)}%`;
  const active = byId(state.characters, state.activeCharId);
  els.hudChar.textContent = active ? active.name : '—';
}
function toast(msg){ pushChat('ai', `ℹ️ ${msg}`); }
function pickColorForRace(r){
  switch((r||'').toLowerCase()){
    case 'human': return '#8dd3ff';
    case 'elf': return '#a7f3d0';
    case 'dwarf': return '#fcd34d';
    case 'ogre': return '#fda4af';
    default: return '#c7d2fe';
  }
}
function resetView(){
  view.zoom = 1; view.pan = {x:0, y:0};
  draw(); updateHud();
}
/* ------------------------------ Characters ------------------------------ */
function renderCharList(){
  els.charList.innerHTML='';
  for(const c of state.characters){
    const li = document.createElement('li');
    const isActive = c.id===state.activeCharId;
    li.innerHTML = `
      <div>
        <strong>${escapeHtml(c.name)}</strong>
        <div class="meta">${escapeHtml(c.race||'?')} • ${escapeHtml(c.class||'')}</div>
      </div>
      <div class="row">
        <button class="btn btn-ghost" data-act="set" data-id="${c.id}">${isActive?'Active':'Set'}</button>
        <button class="btn" data-act="edit" data-id="${c.id}">Edit</button>
        <button class="btn btn-warn" data-act="del" data-id="${c.id}">Del</button>
      </div>`;
    els.charList.appendChild(li);
  }
  updateHud();
}
function createCharacter({name,race,gender,orientation,cls,notes}){
  const ch = {
    id: uid(), name, race, gender, orientation, class: cls, notes: notes||'',
    stats: {str:10,agi:10,int:10,cha:10,tou:10,wil:10,per:10,end:10},
    stance: 'NEUTRAL',
    stress: 0,
    pain: 0,
    corruption: 0,
    fracture: 0,
    flaws: []
  };
  state.characters.push(ch); save(STORAGE.chars, state.characters);
  if(!state.activeCharId){ state.activeCharId = ch.id; save(STORAGE.activeChar, ch.id); }
  renderCharList();
}
function updateCharacter(id, patch){
  const c = byId(state.characters, id); if(!c) return;
  Object.assign(c, patch); save(STORAGE.chars, state.characters); renderCharList();
}
function deleteCharacter(id){
  const i = state.characters.findIndex(c=>c.id===id);
  if(i>=0){ state.characters.splice(i,1); save(STORAGE.chars,state.characters); }
  if(state.activeCharId===id){ state.activeCharId = state.characters[0]?.id || null; save(STORAGE.activeChar, state.activeCharId); }
  renderCharList();
}
/* ----------------------------- Class & Spell Loader ----------------------------- */
async function loadClasses() {
  if (state.classes) return;
  try {
    const res = await fetch('/api/rules/classes.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.classes = await res.json();
  } catch (err) {
    console.error('Failed to load classes.json:', err);
    els.charClass.innerHTML = '<option value="">Load failed</option>';
  }
}
async function loadSpells() {
  if (state.spells) return;
  try {
    const res = await fetch('/api/rules/spells.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.spells = await res.json();
  } catch (err) {
    console.error('Failed to load spells.json:', err);
  }
}
async function populateClasses(race, gender) {
  await loadClasses();
  if (!state.classes) return;
  els.charClass.innerHTML = '<option value="">Select Class</option>';
  for (const [key, data] of Object.entries(state.classes)) {
    if (key === 'meta' || key === 'integration') continue;
    const restrictions = data.restrictions || {};
    const raceLock = data.race_lock || [];
    const genderLock = data.gender_lock || [];
    const raceOk = raceLock.length === 0 || raceLock.includes(race);
    const genderOk = genderLock.length === 0 || genderLock.includes(gender);
    if (raceOk && genderOk) {
      const opt = document.createElement('option');
      opt.value = key;
      opt.textContent = data.label || data.name || key;
      els.charClass.appendChild(opt);
    }
  }
}
/* -------------------------------- Maps ---------------------------------- */
function renderMapList(){
  els.mapList.innerHTML='';
  for(const m of state.maps){
    const li = document.createElement('li');
    const isActive = m.id===state.activeMapId;
    li.innerHTML = `
      <div>
        <strong>${escapeHtml(m.name)}</strong>
        <div class="meta">${m.gridSize||64}px • tokens:${m.tokens?.length||0}</div>
      </div>
      <div class="row">
        <button class="btn btn-ghost" data-map="set" data-id="${m.id}">${isActive?'Active':'Set'}</button>
        <button class="btn" data-map="edit" data-id="${m.id}">Edit</button>
        <button class="btn btn-warn" data-map="del" data-id="${m.id}">Del</button>
      </div>`;
    els.mapList.appendChild(li);
  }
}
function activateMap(id){
  const m = byId(state.maps, id); if(!m) return;
  state.activeMapId = id; save(STORAGE.activeMap, id);
  view.grid.size = m.gridSize || 64;
  view.grid.show = m.showGrid ?? true;
  view.tokens = (m.tokens||[]).map(t=>({...t}));
  els.chkGrid.checked = view.grid.show;
  els.gridSize.value = view.grid.size;
  loadImage(m.imageDataURL).then(img=>{
    view.img = img;
    draw();
  }).catch(()=>{ view.img=null; draw(); });
  loadCombatState();
  renderMapList(); updateHud(); renderCombat();
}
function saveActiveMapState(){
  const m = byId(state.maps, state.activeMapId);
  if(!m){ toast("No active map."); return; }
  Object.assign(m, {
    gridSize: view.grid.size,
    showGrid: view.grid.show,
    tokens: view.tokens,
    imageDataURL: m.imageDataURL
  });
  save(STORAGE.maps, state.maps);
  saveCombatState();
  toast("Map + combat state saved.");
}
function createMap({name, gridSize, imageDataURL}){
  const m = { id: uid(), name, gridSize: gridSize||64, showGrid:true, tokens:[], imageDataURL };
  state.maps.push(m); save(STORAGE.maps, state.maps);
  activateMap(m.id);
}
function updateMap(id, patch){
  const m = byId(state.maps, id); if(!m) return;
  Object.assign(m, patch); save(STORAGE.maps, state.maps);
  if(id===state.activeMapId) activateMap(id); else renderMapList();
}
function deleteMap(id){
  const idx = state.maps.findIndex(m=>m.id===id);
  if(idx>=0){ state.maps.splice(idx,1); save(STORAGE.maps, state.maps); }
  if(state.activeMapId===id){ state.activeMapId = state.maps[0]?.id || null; save(STORAGE.activeMap, state.activeMapId); }
  renderMapList();
  if(state.activeMapId) activateMap(state.activeMapId); else { view.img=null; view.tokens=[]; draw(); }
}
/* ----------------------------- File helpers ----------------------------- */
function fileToDataURL(file){
  return new Promise((res,rej)=>{
    const r = new FileReader();
    r.onload = ()=>res(r.result);
    r.onerror= rej;
    r.readAsDataURL(file);
  });
}
function downloadJson(obj, filename){
  const blob = new Blob([JSON.stringify(obj,null,2)], {type:'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
function loadImage(dataURL){
  return new Promise((res,rej)=>{
    if(!dataURL) { rej(); return; }
    const img = new Image();
    img.onload = ()=>res(img);
    img.onerror= rej;
    img.src = dataURL;
  });
}
/* ------------------------------ Chat (API) ------------------------------ */
async function apiSendChat(message, context={}){
  if(!API_BASE_URL){
    const loreLine = state.lore?.scripture?.[Math.floor(Math.random()*state.lore.scripture.length)];
    const hint = loreLine ? `\n\n> ${loreLine}` : '';
    return { ok:true, reply: `Stub: "${message}" received.${hint}` };
  }
  try{
    const r = await fetch(`${API_BASE_URL}/api/chat`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ message, context })
    });
    if(!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    return { ok:true, reply: data.reply ?? "(no reply)" };
  }catch(err){
    console.error(err);
    return { ok:false, reply: `Error contacting API: ${String(err)}` };
  }
}
function pushChat(role, text){
  const div = document.createElement('div');
  div.className = `chat-msg ${role==='user'?'user':'ai'}`;
  div.textContent = text;
  els.chatLog.appendChild(div);
  els.chatLog.scrollTop = els.chatLog.scrollHeight;
}
/* ------------------------------ Data Loaders ---------------------------- */
function pickFile(onPick){
  els.fileOpen.onchange = async () =>{
    const f = els.fileOpen.files[0]; els.fileOpen.value='';
    if(f) await onPick(f);
  };
  els.fileOpen.click();
}
/* ------------------------------ Combat Core ----------------------------- */
const combat = {
  inProgress: false,
  round: 1,
  order: [],
  actors: {},
  currentIndex: 0,
  pending: null
};
function defaultsForRace(race){
  const g = view.grid.size || 64;
  switch((race||'').toLowerCase()){
    case 'human': return {hpMax:18, armor:1, speedTiles:6, str:10, agi:10};
    case 'elf': return {hpMax:16, armor:0, speedTiles:7, str:9, agi:12};
    case 'dwarf': return {hpMax:22, armor:2, speedTiles:5, str:12, agi:8 };
    case 'ogre': return {hpMax:40, armor:3, speedTiles:5, str:16, agi:6 };
    default: return {hpMax:18, armor:1, speedTiles:6, str:10, agi:10};
  }
}
function deriveAbility(race, cls){
  const C = (cls||'').toLowerCase();
  const R = (race||'').toLowerCase();
  if(R==='human' && (C.includes('crusader')||C.includes('paladin')||C.includes('templar')))
    return 'Breath Smite';
  if(R==='elf' && (C.includes('hollow')||C.includes('sorcer')))
    return 'Veil Bolt';
  if(R==='dwarf' && (C.includes('rune')||C.includes('forge')))
    return 'Rune Lock';
  if(R==='ogre') return 'Ogre Slam';
  return 'Special Action';
}
function addToCombat(tokenId, team='players'){
  const t = view.tokens.find(t=>t.id===tokenId);
  if(!t) return toast('No token selected.');
  if(combat.actors[tokenId]) return toast('Already in combat.');
  const ch = byId(state.characters, t.charId) || { stats: {str:10,agi:10}, race: guessRaceFromToken(t), class: '' };
  const d = defaultsForRace(ch.race || guessRaceFromToken(t) || 'Human');
  combat.actors[tokenId] = {
    tokenId, name: t.label, team,
    hpMax: d.hpMax, hp: d.hpMax, armor: d.armor,
    speedTiles: d.speedTiles, str: ch.stats.str || d.str, agi: ch.stats.agi || d.agi,
    defend: false,
    ability: deriveAbility(ch.race, ch.class),
    class: ch.class || '',
    race: ch.race || guessRaceFromToken(t) || 'Human',
    statuses:[],
    stance: ch.stance || 'NEUTRAL',
    stress: ch.stress || 0,
    pain: ch.pain || 0,
    corruption: ch.corruption || 0,
    fracture: ch.fracture || 0,
    flaws: ch.flaws || []
  };
  renderCombat(); draw();
}
function guessRaceFromToken(t){
  const map = {
    '#8dd3ff':'Human','#a7f3d0':'Elf','#fcd34d':'Dwarf','#fda4af':'Ogre'
  };
  const c = (t.color||'').toLowerCase();
  return map[c] || 'Human';
}
function removeFromCombat(tokenId){
  if(combat.actors[tokenId]) delete combat.actors[tokenId];
  combat.order = combat.order.filter(id=>id!==tokenId);
  if(combat.currentIndex >= combat.order.length) combat.currentIndex = 0;
  renderCombat(); draw();
}
function rollInitiative(){
  const entries = Object.values(combat.actors).map(a=>{
    const roll = d20() + mod(a.agi);
    return { id:a.tokenId, name:a.name, team:a.team, roll };
  });
  entries.sort((a,b)=> b.roll - a.roll);
  combat.order = entries.map(e=>e.id);
  combat.currentIndex = 0;
  renderCombat();
}
function startCombat(){
  if(!combat.order.length) rollInitiative();
  combat.inProgress = true;
  combat.round = 1;
  combat.currentIndex = 0;
  saveCombatState();
  renderCombat(); draw();
}
function nextTurn(){
  if(!combat.inProgress || !combat.order.length) return;
  const prev = combat.order[combat.currentIndex];
  if(prev && combat.actors[prev]) combat.actors[prev].defend = false;
  combat.currentIndex++;
  if(combat.currentIndex >= combat.order.length){
    combat.currentIndex = 0;
    combat.round++;
  }
  combat.pending = null;
  saveCombatState();
  renderCombat(); draw();
}
function endCombat(){
  combat.inProgress = false;
  combat.round = 1;
  combat.order = [];
  combat.currentIndex = 0;
  combat.pending = null;
  combat.actors = {};
  saveCombatState();
  renderCombat(); draw();
}
/* Actions */
function requestMove(actorId){
  combat.pending = {type:'move', actorId};
  toast('Select destination (click on map).');
}
function requestAttack(actorId){
  combat.pending = {type:'attack', actorId};
  toast('Select a target token to attack.');
}
function requestAbility(actorId){
  combat.pending = {type:'ability', actorId};
  const ability = combat.actors[actorId]?.ability || 'Ability';
  toast(`Select a target for ${ability}.`);
}
function defend(actorId){
  const a = combat.actors[actorId]; if(!a) return;
  a.defend = true;
  toast(`${a.name} defends (+2 AC until next turn).`);
  saveCombatState(); renderCombat();
}
async function handlePendingActionPointer(world){
  const p = combat.pending; if(!p) return;
  const actor = combat.actors[p.actorId];
  const token = view.tokens.find(t=>t.id===p.actorId);
  if(!actor || !token){ combat.pending=null; return; }
  if(p.type==='move'){
    const dx = world.x - token.x;
    const dy = world.y - token.y;
    const dist = Math.hypot(dx,dy);
    const maxDist = actor.speedTiles * view.grid.size;
    if(dist <= maxDist){
      const nx = view.grid.show ? Math.round(world.x/view.grid.size)*view.grid.size : world.x;
      const ny = view.grid.show ? Math.round(world.y/view.grid.size)*view.grid.size : world.y;
      token.x = nx; token.y = ny;
      toast(`${actor.name} moves.`);
      combat.pending=null; draw(); saveCombatState();
    } else {
      toast(`Too far. Max ${actor.speedTiles} tiles.`);
    }
    return;
  }
  const targetTok = hitTestToken(world.x, world.y);
  if(!targetTok){ toast('Click a target token.'); return; }
  if(targetTok.id===p.actorId){ toast('Cannot target self.'); return; }
  const targetActor = combat.actors[targetTok.id];
  if(!targetActor){ toast('Target is not in combat.'); return; }
  if(p.type==='attack'){
    await resolveAttack(p.actorId, targetTok.id);
  } else if(p.type==='ability'){
    await resolveAbility(p.actorId, targetTok.id);
  }
  combat.pending=null; draw(); saveCombatState();
}
async function resolveAttack(attId, tgtId) {
  const A = combat.actors[attId];
  const T = combat.actors[tgtId];
  if (!A || !T) return toast('Missing actor');

  try {
    const res = await fetch('http://127.0.0.1:8000/combat/attack', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ attacker: A, defender: T, weapon_damage: 14 }) // 14 = greatsword base; adjust per weapon later
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const result = await res.json();

    // Update defender
    T.hp = result.defender_hp;
    T.pain = result.defender_pain;

    // Cinematic log with race/class flavor
    const raceFlavor = T.race === 'Ogre' ? 'massive frame trembles' : T.race === 'Elf' ? 'grace falters' : 'blood flows';
    const classFlavor = T.class && T.class.includes('Crusader') ? 'holy light dims' : '';
    if (result.hit) {
      toast(`⚔️ ${A.name} (${A.race} ${A.class || ''}) rolls ${result.attack_roll} + ${A.weapon_skill || 0} (WS) + ${Math.floor((A.dexterity || 0)/10)} (Dex) = ${result.atk_total} vs ${result.def_total} (${result.def_type})! Deals ${result.damage} (${result.absorbed} absorbed). ${raceFlavor} ${classFlavor}`);
    } else {
      toast(`❌ ${A.name} misses ${T.name} (${result.def_type})!`);
    }
  } catch (err) {
    toast(`Backend error: ${err.message}`);
    console.error(err);
  }

  renderCombat();
  draw();
}
async function resolveAbility(attId, tgtId){
  const A = combat.actors[attId], T = combat.actors[tgtId];
  if(!A||!T) return;
  const ability = A.ability || 'Special Action';
  const attackerTok = view.tokens.find(t=>t.id===attId);
  const targetTok = view.tokens.find(t=>t.id===tgtId);
  const dist = Math.hypot(attackerTok.x - targetTok.x, attackerTok.y - targetTok.y);
  await loadSpells();
  const spellKey = Object.keys(state.spells).find(k => k.toLowerCase() === ability.toLowerCase());
  const spell = spellKey ? state.spells[spellKey] : null;
  if (!spell) {
    toast(`Unknown spell: ${ability}`);
    return;
  }
  let text = '';
  if (spell.damage > 0) {
    const dmg = spell.damage - Math.floor(T.armor / 2);
    T.hp -= Math.max(0, dmg);
    text = `${A.name} casts ${spell.name} on ${T.name} for ${Math.max(0, dmg)}!`;
  } else if (spell.effect?.defense_bonus) {
    A.defend = true;
    text = `${A.name} casts ${spell.name} — +${spell.effect.defense_bonus} defense!`;
  } else if (spell.effect?.fear_intensity) {
    T.statuses.push({ name: 'Fear', rounds: 1 });
    text = `${A.name} casts ${spell.name} — ${T.name} is terrified!`;
  }
  toast(text);
  postDamageCheck(tgtId);
  renderCombat(); draw();
}
function postDamageCheck(tgtId){
  const T = combat.actors[tgtId]; if(!T) return;
  if(T.hp <= 0){
    T.hp = 0;
    toast(`${T.name} is down!`);
  }
}
function d20(){ return 1 + Math.floor(Math.random()*20); }
function rollDie(sides){ return 1 + Math.floor(Math.random()*sides); }
function mod(stat){ return Math.floor((stat-10)/2); }
/* Combat UI */
function renderCombat(){
  els.turnInfo.textContent = combat.inProgress
    ? `Round ${combat.round} • Turn ${combat.currentIndex+1}/${Math.max(1, combat.order.length)}`
    : `Round — • Turn —`;
  els.turnOrder.innerHTML = '';
  for(const id of combat.order){
    const a = combat.actors[id];
    if(!a) continue;
    const li = document.createElement('li');
    const current = (combat.order[combat.currentIndex]===id && combat.inProgress);
    li.innerHTML = `
      <div>
        <strong>${escapeHtml(a.name)}</strong>
        <div class="meta">${escapeHtml(a.race)} • ${escapeHtml(a.class||'')} • HP ${a.hp}/${a.hpMax}</div>
      </div>
      <div class="row">
        <span class="badge ${a.team==='players'?'green':a.team==='enemies'?'red':'yellow'}">${a.team}</span>
        ${current?'<span class="badge">ACTIVE</span>':''}
      </div>`;
    els.turnOrder.appendChild(li);
  }
  const curId = combat.order[combat.currentIndex];
  const myTurn = combat.inProgress && curId!=null;
  els.actMove.disabled = els.actAttack.disabled = els.actAbility.disabled = els.actDefend.disabled = !myTurn;
}
function saveCombatState(){
  if(!state.activeMapId) return;
  const data = {
    inProgress: combat.inProgress,
    round: combat.round,
    order: combat.order,
    currentIndex: combat.currentIndex,
    actors: combat.actors
  };
  save(STORAGE.combat(state.activeMapId), data);
}
function loadCombatState(){
  const data = load(STORAGE.combat(state.activeMapId), null);
  if(!data){
    combat.inProgress=false; combat.round=1; combat.order=[]; combat.currentIndex=0; combat.actors={}; combat.pending=null;
    return;
  }
  combat.inProgress = data.inProgress;
  combat.round = data.round;
  combat.order = data.order;
  combat.currentIndex = Math.min(data.currentIndex, Math.max(0, data.order.length-1));
  combat.actors = data.actors || {};
  combat.pending = null;
}
/* ------------------------------- Init UI -------------------------------- */
document.addEventListener('DOMContentLoaded', async () => {
  await loadClasses();
  await loadSpells();
  bindUI();
  renderCharList();
  renderMapList();
  if (state.activeMapId) activateMap(state.activeMapId);
  pushChat('ai', 'Welcome. Create a character → Add Token → Combat.');
});
function bindUI(){
  $('#btn-new-char').addEventListener('click', async () => {
    $('#char-form').reset();
    $('#char-name').value = '';
    els.charRace.value = 'Human';
    els.charGender.value = 'Male';
    els.charOrientation.value = 'Straight';
    await populateClasses('Human', 'Male');
    els.dlgChar.showModal();
    els.charForm.onsubmit = async (e) => {
      e.preventDefault();
      const name = $('#char-name').value.trim();
      const race = els.charRace.value;
      const gender = els.charGender.value;
      const orientation = els.charOrientation.value;
      const cls = els.charClass.value;
      const notes = $('#char-notes').value.trim();
      if (name && race && gender && orientation && cls) {
        createCharacter({name, race, gender, orientation, cls, notes});
        els.dlgChar.close();
      }
    };
  });
  els.charRace.addEventListener('change', () => populateClasses(els.charRace.value, els.charGender.value));
  els.charGender.addEventListener('change', () => populateClasses(els.charRace.value, els.charGender.value));
  els.charList.addEventListener('click', async e => {
    const btn = e.target.closest('button');
    if (!btn) return;
    const id = btn.dataset.id;
    const act = btn.dataset.act;
    if (act === 'edit') {
      const c = byId(state.characters, id);
      if (!c) return;
      $('#char-name').value = c.name;
      els.charRace.value = c.race;
      els.charGender.value = c.gender;
      els.charOrientation.value = c.orientation;
      await populateClasses(c.race, c.gender);
      setTimeout(() => els.charClass.value = c.class || '', 50);
      $('#char-notes').value = c.notes || '';
      els.dlgChar.showModal();
      els.charForm.onsubmit = async ev => {
        ev.preventDefault();
        updateCharacter(id, {
          name: $('#char-name').value.trim(),
          race: els.charRace.value,
          gender: els.charGender.value,
          orientation: els.charOrientation.value,
          class: els.charClass.value,
          notes: $('#char-notes').value.trim()
        });
        els.dlgChar.close();
      };
    }
    if (act === 'set') { state.activeCharId = id; save(STORAGE.activeChar, id); renderCharList(); }
    if (act === 'del') { deleteCharacter(id); }
  });
  $('#btn-import-char').addEventListener('click', () => pickFile(async file => {
    const data = JSON.parse(await file.text());
    const arr = Array.isArray(data) ? data : [data];
    for (const c of arr) { if (!c.id) c.id = uid(); state.characters.push(c); }
    save(STORAGE.chars, state.characters);
    if (!state.activeCharId && state.characters.length) { state.activeCharId = state.characters[0].id; save(STORAGE.activeChar, state.activeCharId); }
    renderCharList();
  }));
  $('#btn-export-char').addEventListener('click', () => downloadJson(state.characters, 'characters.json'));
  $('#btn-new-map').addEventListener('click', () => {
    $('#map-form').reset();
    els.dlgMap.showModal();
    els.mapForm.onsubmit = async (e) => {
      e.preventDefault();
      const name = $('#map-name').value.trim();
      const grid = parseInt($('#map-grid').value, 10) || 64;
      const file = $('#map-image').files[0];
      const dataURL = file ? await fileToDataURL(file) : null;
      createMap({ name, gridSize: grid, imageDataURL: dataURL });
      els.dlgMap.close();
      renderMapList();
    };
  });
  $('#btn-import-map').addEventListener('click', () => pickFile(async file => {
    const data = JSON.parse(await file.text());
    const arr = Array.isArray(data) ? data : [data];
    for (const m of arr) { if (!m.id) m.id = uid(); state.maps.push(m); }
    save(STORAGE.maps, state.maps);
    if (!state.activeMapId && state.maps.length) { activateMap(state.maps[0].id); }
    renderMapList();
  }));
  $('#btn-export-map').addEventListener('click', () => downloadJson(state.maps, 'maps.json'));
  els.mapList.addEventListener('click', e => {
    const btn = e.target.closest('button'); if (!btn) return;
    const id = btn.dataset.id, act = btn.dataset.map;
    if (act === 'set') { activateMap(id); }
    if (act === 'edit') {
      const m = byId(state.maps, id); if (!m) return;
      $('#map-form').reset();
      $('#map-name').value = m.name; $('#map-grid').value = m.gridSize || 64;
      els.dlgMap.showModal();
      els.mapForm.onsubmit = async (ev) => {
        ev.preventDefault();
        const patch = { name: $('#map-name').value.trim(), gridSize: parseInt($('#map-grid').value, 10) || 64 };
        const f = $('#map-image').files[0];
        if (f) { patch.imageDataURL = await fileToDataURL(f); }
        updateMap(id, patch);
        els.dlgMap.close();
      };
    }
    if (act === 'del') { deleteMap(id); }
  });
  els.chkGrid.addEventListener('change', () => { view.grid.show = els.chkGrid.checked; draw(); });
  els.gridSize.addEventListener('change', () => { view.grid.size = Math.max(16, parseInt(els.gridSize.value, 10) || 64); draw(); });
  $('#btn-add-token').addEventListener('click', () => {
    const ch = byId(state.characters, state.activeCharId);
    if (!ch) return toast('No active character set.');
    const t = { id: uid(), label: ch.name, color: pickColorForRace(ch.race), x: 64, y: 64, charId: ch.id };
    view.tokens.push(t); draw();
  });
  $('#btn-clear-tokens').addEventListener('click', () => { view.tokens.length = 0; combat.actors = {}; combat.order = []; renderCombat(); draw(); });
  $('#btn-save-mapstate').addEventListener('click', saveActiveMapState);
  els.apiStatus.textContent = API_BASE_URL ? 'live' : 'stub';
  els.chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const msg = els.chatInput.value.trim(); if (!msg) return;
    els.chatInput.value = '';
    pushChat('user', msg);
    const ctx = { activeCharacter: byId(state.characters, state.activeCharId), activeMap: byId(state.maps, state.activeMapId), era: '1670' };
    const res = await apiSendChat(msg, ctx);
    pushChat('ai', res.reply);
  });
  els.btnAddCombat.addEventListener('click', () => {
    if (!view.selectedTokenId) return toast('Select a token (double-click).');
    addToCombat(view.selectedTokenId, els.selTeam.value);
  });
  els.btnRemoveCombat.addEventListener('click', () => {
    if (!view.selectedTokenId) return toast('Select a token to remove.');
    removeFromCombat(view.selectedTokenId);
  });
  els.btnRollInit.addEventListener('click', rollInitiative);
  els.btnStartCombat.addEventListener('click', startCombat);
  els.btnNextTurn.addEventListener('click', nextTurn);
  els.btnEndCombat.addEventListener('click', endCombat);
  els.actMove.addEventListener('click', () => {
    const id = combat.order[combat.currentIndex]; if (!id) return;
    requestMove(id);
  });
  els.actAttack.addEventListener('click', () => {
    const id = combat.order[combat.currentIndex]; if (!id) return;
    requestAttack(id);
  });
  els.actAbility.addEventListener('click', () => {
    const id = combat.order[combat.currentIndex]; if (!id) return;
    requestAbility(id);
  });
  els.actDefend.addEventListener('click', () => {
    const id = combat.order[combat.currentIndex]; if (!id) return;
    defend(id); renderCombat();
  });
  els.actEnd.addEventListener('click', nextTurn);
  resizeCanvas();
}