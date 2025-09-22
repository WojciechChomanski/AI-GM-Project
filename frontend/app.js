/* =========================================================================
   The Breath & The Veil — Minimal Frontend (Turn-Based v0.2)
   Files: index.html, styles.css, app.js
   ========================================================================= */

const API_BASE_URL = ""; // e.g., "http://localhost:8000" — leave empty for stub
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
  races: null,
  lore: null
};

function save(key, val){ localStorage.setItem(key, JSON.stringify(val)); }
function load(key, fallback){ try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } }
function uid(){ return Math.random().toString(36).slice(2)+Date.now().toString(36); }
function byId(arr,id){ return arr.find(x=>x.id===id) || null; }
function escapeHtml(s){ return (s??'').toString().replace(/[&<>"']/g, m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }

/* ------------------------------- Canvas Map ----------------------------- */
const els = {
  charList: $('#char-list'),
  mapList:  $('#map-list'),
  chkGrid:  $('#chk-grid'),
  gridSize: $('#grid-size'),
  hudZoom:  $('#hud-zoom'),
  hudPos:   $('#hud-pos'),
  hudChar:  $('#hud-char'),
  canvas:   $('#map-canvas'),
  apiStatus: $('#api-status'),
  chatLog:  $('#chat-log'),
  chatForm: $('#chat-form'),
  chatInput: $('#chat-input'),
  dlgChar:  $('#dlg-char'),
  dlgMap:   $('#dlg-map'),
  charForm: $('#char-form'),
  mapForm:  $('#map-form'),
  fileOpen: $('#file-open'),
  // combat
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
  actEnd: $('#act-end')
};

const ctx = els.canvas.getContext('2d');
const view = {
  img: null,
  zoom: 1, minZoom: 0.25, maxZoom: 3,
  pan: {x:0,y:0},
  grid: {show:true, size:64},
  tokens: [], // {id,label,color,x,y,charId?}
  selectedTokenId: null,
};

function resizeCanvas(){
  const dpr = window.devicePixelRatio || 1;
  const rect = els.canvas.getBoundingClientRect();
  els.canvas.width  = Math.floor(rect.width * dpr);
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

  // background
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

  // grid
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

  // tokens
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

  // ring if current turn
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

  // outline
  if(isSelected){
    ctx.lineWidth = 3 / view.zoom;
    ctx.strokeStyle = '#ffd28a';
    ctx.stroke();
  }

  // name
  ctx.fillStyle = '#0b0f18';
  ctx.font = `${12/ view.zoom}px system-ui, Arial`;
  ctx.textAlign='center'; ctx.textBaseline='middle';
  ctx.fillText(t.label ?? 'X', x, y-24/ view.zoom);

  // HP bar if in combat
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
  const y = (e.clientY - rect.top  - view.pan.y)/view.zoom;
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
  const cy = (e.clientY-rect.top  - view.pan.y)/old;
  view.pan.x = e.clientX-rect.left - cx*nz;
  view.pan.y = e.clientY-rect.top  - cy*nz;
  view.zoom = nz;
  draw(); updateHud();
},{passive:false});

els.canvas.addEventListener('pointerdown', e=>{
  els.canvas.setPointerCapture(e.pointerId);
  const pos = screenToWorld(e);
  // pending combat actions take precedence
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
      // remove from combat as well
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
function createCharacter({name,race,cls,notes}){
  const ch = {
    id: uid(), name, race, class: cls, notes: notes||'',
    stats: {str:10,agi:10,int:10,cha:10,tou:10,wil:10,per:10,end:10}
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
  if(state.activeCharId===id){ state.activeCharId = state.characters[0]?.id || null; save(STORAGE.activeChar,state.activeCharId); }
  renderCharList();
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

  // Load combat state for this map
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
  order: [],          // array of tokenIds in initiative order
  actors: {},         // tokenId -> actor
  currentIndex: 0,
  pending: null       // {type:'move'|'attack'|'ability', actorId}
};

// defaults per race (quick-start; plug your real rules any time)
function defaultsForRace(race){
  const g = view.grid.size || 64; // speed is in tiles; distance = tiles * grid
  switch((race||'').toLowerCase()){
    case 'human': return {hpMax:18, armor:1, speedTiles:6, str:10, agi:10};
    case 'elf':   return {hpMax:16, armor:0, speedTiles:7, str:9,  agi:12};
    case 'dwarf': return {hpMax:22, armor:2, speedTiles:5, str:12, agi:8 };
    case 'ogre':  return {hpMax:40, armor:3, speedTiles:5, str:16, agi:6 };
    default:      return {hpMax:18, armor:1, speedTiles:6, str:10, agi:10};
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
  // derive from character if linked
  const ch = byId(state.characters, t.charId);
  const d = defaultsForRace(ch?.race || guessRaceFromToken(t) || 'Human');
  combat.actors[tokenId] = {
    tokenId, name: t.label, team,
    hpMax: d.hpMax, hp: d.hpMax, armor: d.armor,
    speedTiles: d.speedTiles, str: d.str, agi: d.agi,
    defend: false,
    ability: deriveAbility(ch?.race, ch?.class),
    class: ch?.class || '',
    race: ch?.race || guessRaceFromToken(t) || 'Human',
    statuses:[]
  };
  renderCombat(); draw();
}
function guessRaceFromToken(t){
  // color mapping
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
  // clear defend on actor who just had turn (if any)
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

function handlePendingActionPointer(world){
  const p = combat.pending; if(!p) return;
  const actor = combat.actors[p.actorId];
  const token = view.tokens.find(t=>t.id===p.actorId);
  if(!actor || !token){ combat.pending=null; return; }

  if(p.type==='move'){
    // distance in tiles
    const dx = world.x - token.x;
    const dy = world.y - token.y;
    const dist = Math.hypot(dx,dy);
    const maxDist = actor.speedTiles * view.grid.size;
    if(dist <= maxDist){
      // snap to grid if grid on
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

  // attack/ability need a target token
  const targetTok = hitTestToken(world.x, world.y);
  if(!targetTok){ toast('Click a target token.'); return; }
  if(targetTok.id===p.actorId){ toast('Cannot target self.'); return; }
  const targetActor = combat.actors[targetTok.id];
  if(!targetActor){ toast('Target is not in combat.'); return; }

  if(p.type==='attack'){
    resolveAttack(p.actorId, targetTok.id);
  } else if(p.type==='ability'){
    resolveAbility(p.actorId, targetTok.id);
  }
  combat.pending=null; draw(); saveCombatState();
}

function resolveAttack(attId, tgtId){
  const A = combat.actors[attId], T = combat.actors[tgtId];
  if(!A||!T) return;
  const attackerTok = view.tokens.find(t=>t.id===attId);
  const targetTok = view.tokens.find(t=>t.id===tgtId);
  // simple melee range: 1 tile
  const dist = Math.hypot(attackerTok.x - targetTok.x, attackerTok.y - targetTok.y);
  const inRange = dist <= (view.grid.size * 1.25);
  if(!inRange){ toast('Out of melee range.'); return; }

  const roll = d20();
  const atk = roll + mod(A.str);
  const def = 10 + mod(T.agi) + (T.defend?2:0);
  if(roll===20){ // crit
    const dmg = Math.max(0, rollDie(8) + mod(A.str) + 4 - T.armor);
    T.hp -= dmg;
    toast(`${A.name} CRITS ${T.name} for ${dmg}.`);
  } else if(atk >= def){
    const dmg = Math.max(0, rollDie(8) + mod(A.str) - T.armor);
    T.hp -= dmg;
    toast(`${A.name} hits ${T.name} for ${dmg}.`);
  } else {
    toast(`${A.name} misses ${T.name}.`);
  }
  postDamageCheck(tgtId);
  renderCombat(); draw();
}

function resolveAbility(attId, tgtId){
  const A = combat.actors[attId], T = combat.actors[tgtId];
  if(!A||!T) return;
  const ability = A.ability || 'Special Action';
  const attackerTok = view.tokens.find(t=>t.id===attId);
  const targetTok = view.tokens.find(t=>t.id===tgtId);
  const dist = Math.hypot(attackerTok.x - targetTok.x, attackerTok.y - targetTok.y);

  let text='';
  switch(ability){
    case 'Breath Smite': {
      if(dist > view.grid.size * 1.5){ toast('Smite: melee range.'); return; }
      const roll = d20(); const atk = roll + mod(A.str);
      const def = 10 + mod(T.agi) + (T.defend?2:0);
      if(roll===20 || atk>=def){
        const dmg = rollDie(10) + 2; // radiant, ignore armor
        T.hp -= dmg;
        text = `${A.name} smites ${T.name} for ${dmg} (radiant).`;
      } else { text = `${A.name}'s smite misses.`; }
      break;
    }
    case 'Veil Bolt': {
      const range = view.grid.size * 6; // ranged
      if(dist > range){ toast('Veil Bolt out of range.'); return; }
      const dmg = rollDie(8) + 1 - Math.floor(T.armor/2); // partial armor
      T.hp -= Math.max(0,dmg);
      text = `${A.name} lashes ${T.name} with Veil Bolt for ${Math.max(0,dmg)}.`;
      break;
    }
    case 'Rune Lock': {
      const range = view.grid.size * 4;
      if(dist > range){ toast('Rune Lock out of range.'); return; }
      T.statuses.push({name:'Locked', rounds:2, effect:'-2 damage'});
      text = `${A.name} binds ${T.name} (Locked 2r).`;
      break;
    }
    case 'Ogre Slam': {
      if(dist > view.grid.size * 1.5){ toast('Slam: melee range.'); return; }
      const dmg = rollDie(12) + mod(A.str) - Math.floor(T.armor/2);
      T.hp -= Math.max(0,dmg);
      text = `${A.name} slams ${T.name} for ${Math.max(0,dmg)}.`;
      break;
    }
    default: {
      const dmg = rollDie(6) + mod(A.str) - T.armor;
      T.hp -= Math.max(0,dmg);
      text = `${A.name} uses ${ability}: ${T.name} takes ${Math.max(0,dmg)}.`;
    }
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
    // optional: remove from order
    // combat.order = combat.order.filter(id=>id!==tgtId);
  }
}

/* Dice helpers */
function d20(){ return 1 + Math.floor(Math.random()*20); }
function rollDie(sides){ return 1 + Math.floor(Math.random()*sides); }
function mod(stat){ return Math.floor((stat-10)/2); }

/* ------------------------------ Combat UI -------------------------------- */
function renderCombat(){
  // header
  els.turnInfo.textContent = combat.inProgress
    ? `Round ${combat.round} • Turn ${combat.currentIndex+1}/${Math.max(1, combat.order.length)}`
    : `Round — • Turn —`;

  // turn order list
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

  // enable/disable action buttons based on turn
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
  if(!data){ // reset
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
document.addEventListener('DOMContentLoaded', ()=>{
  bindUI();
  pushChat('ai', 'Welcome. Load a map image, create a character, and drop a token. Then open Combat: Add Selected → Roll Init → Start.');
});

function bindUI(){
  // Characters
  $('#btn-new-char').addEventListener('click', ()=>{
    $('#char-form').reset();
    $('#char-name').value = '';
    els.dlgChar.showModal();
    els.charForm.onsubmit = (e)=>{
      e.preventDefault();
      const name = $('#char-name').value.trim();
      const race = $('#char-race').value.trim();
      const cls  = $('#char-class').value.trim();
      const notes= $('#char-notes').value.trim();
      if(name){ createCharacter({name, race, cls, notes}); }
      els.dlgChar.close();
    };
  });
  $('#btn-import-char').addEventListener('click', ()=> pickFile(async file=>{
    const data = JSON.parse(await file.text());
    const arr = Array.isArray(data)? data : [data];
    for(const c of arr){ if(!c.id) c.id = uid(); state.characters.push(c); }
    save(STORAGE.chars, state.characters);
    if(!state.activeCharId && state.characters.length) { state.activeCharId = state.characters[0].id; save(STORAGE.activeChar,state.activeCharId); }
    renderCharList();
  }));
  $('#btn-export-char').addEventListener('click', ()=> downloadJson(state.characters, 'characters.json'));
  els.charList.addEventListener('click', e=>{
    const btn = e.target.closest('button'); if(!btn) return;
    const id = btn.dataset.id, act= btn.dataset.act;
    if(act==='set'){ state.activeCharId = id; save(STORAGE.activeChar,id); renderCharList(); }
    if(act==='edit'){
      const c = byId(state.characters, id); if(!c) return;
      $('#char-form').reset();
      $('#char-name').value = c.name; $('#char-race').value = c.race||'Human';
      $('#char-class').value = c.class||''; $('#char-notes').value = c.notes||'';
      els.dlgChar.showModal();
      els.charForm.onsubmit = (ev)=>{
        ev.preventDefault();
        updateCharacter(id, {
          name: $('#char-name').value.trim(),
          race: $('#char-race').value.trim(),
          class:$('#char-class').value.trim(),
          notes:$('#char-notes').value.trim()
        });
        els.dlgChar.close();
      };
    }
    if(act==='del'){ deleteCharacter(id); }
  });

  // Maps
  $('#btn-new-map').addEventListener('click', ()=>{
    $('#map-form').reset();
    els.dlgMap.showModal();
    els.mapForm.onsubmit = async (e)=>{
      e.preventDefault();
      const name = $('#map-name').value.trim();
      const grid = parseInt($('#map-grid').value,10)||64;
      const file = $('#map-image').files[0];
      const dataURL = file ? await fileToDataURL(file) : null;
      createMap({name, gridSize:grid, imageDataURL: dataURL});
      els.dlgMap.close();
      renderMapList();
    };
  });
  $('#btn-import-map').addEventListener('click', ()=> pickFile(async file=>{
    const data = JSON.parse(await file.text());
    const arr = Array.isArray(data)? data : [data];
    for(const m of arr){ if(!m.id) m.id = uid(); state.maps.push(m); }
    save(STORAGE.maps, state.maps);
    if(!state.activeMapId && state.maps.length){ activateMap(state.maps[0].id); }
    renderMapList();
  }));
  $('#btn-export-map').addEventListener('click', ()=> downloadJson(state.maps, 'maps.json'));
  els.mapList.addEventListener('click', e=>{
    const btn = e.target.closest('button'); if(!btn) return;
    const id = btn.dataset.id, act= btn.dataset.map;
    if(act==='set'){ activateMap(id); }
    if(act==='edit'){
      const m = byId(state.maps,id); if(!m) return;
      $('#map-form').reset();
      $('#map-name').value = m.name; $('#map-grid').value = m.gridSize||64;
      els.dlgMap.showModal();
      els.mapForm.onsubmit = async (ev)=>{
        ev.preventDefault();
        const patch = {
          name: $('#map-name').value.trim(),
          gridSize: parseInt($('#map-grid').value,10)||64
        };
        const f = $('#map-image').files[0];
        if(f){ patch.imageDataURL = await fileToDataURL(f); }
        updateMap(id, patch);
        els.dlgMap.close();
      };
    }
    if(act==='del'){ deleteMap(id); }
  });

  // Tools
  els.chkGrid.addEventListener('change', ()=>{ view.grid.show = els.chkGrid.checked; draw(); });
  els.gridSize.addEventListener('change', ()=>{ view.grid.size = Math.max(16, parseInt(els.gridSize.value,10)||64); draw(); });
  $('#btn-add-token').addEventListener('click', ()=>{
    const ch = byId(state.characters, state.activeCharId);
    if(!ch) return toast('No active character set.');
    const t = { id: uid(), label: ch.name, color: pickColorForRace(ch.race), x: 64, y: 64, charId: ch.id };
    view.tokens.push(t); draw();
  });
  $('#btn-clear-tokens').addEventListener('click', ()=>{ view.tokens.length=0; combat.actors={}; combat.order=[]; renderCombat(); draw(); });
  $('#btn-save-mapstate').addEventListener('click', saveActiveMapState);

  // Chat
  els.apiStatus.textContent = API_BASE_URL ? 'live' : 'stub';
  els.chatForm.addEventListener('submit', async (e)=>{
    e.preventDefault();
    const msg = els.chatInput.value.trim(); if(!msg) return;
    els.chatInput.value='';
    pushChat('user', msg);
    const ctx = { activeCharacter: byId(state.characters, state.activeCharId), activeMap: byId(state.maps, state.activeMapId), era: '1670' };
    const res = await apiSendChat(msg, ctx);
    pushChat('ai', res.reply);
  });

  // Data loaders
  $('#btn-load-races').addEventListener('click', ()=> pickFile(async file=>{
    state.races = JSON.parse(await file.text());
    toast('races.json loaded.');
    const opts = Object.keys(state.races);
    if(opts.length){
      const sel = $('#char-race');
      sel.innerHTML = opts.map(n=>`<option>${escapeHtml(n)}</option>`).join('');
    }
  }));
  $('#btn-load-lore').addEventListener('click', ()=> pickFile(async file=>{
    state.lore = JSON.parse(await file.text());
    toast('lore loaded.');
  }));

  // Combat UI
  els.btnAddCombat.addEventListener('click', ()=>{
    if(!view.selectedTokenId) return toast('Select a token (double-click).');
    addToCombat(view.selectedTokenId, els.selTeam.value);
  });
  els.btnRemoveCombat.addEventListener('click', ()=>{
    if(!view.selectedTokenId) return toast('Select a token to remove.');
    removeFromCombat(view.selectedTokenId);
  });
  els.btnRollInit.addEventListener('click', rollInitiative);
  els.btnStartCombat.addEventListener('click', startCombat);
  els.btnNextTurn.addEventListener('click', nextTurn);
  els.btnEndCombat.addEventListener('click', endCombat);

  els.actMove.addEventListener('click', ()=>{
    const id = combat.order[combat.currentIndex]; if(!id) return;
    requestMove(id);
  });
  els.actAttack.addEventListener('click', ()=>{
    const id = combat.order[combat.currentIndex]; if(!id) return;
    requestAttack(id);
  });
  els.actAbility.addEventListener('click', ()=>{
    const id = combat.order[combat.currentIndex]; if(!id) return;
    requestAbility(id);
  });
  els.actDefend.addEventListener('click', ()=>{
    const id = combat.order[combat.currentIndex]; if(!id) return;
    defend(id); renderCombat();
  });
  els.actEnd.addEventListener('click', nextTurn);

  // Boot
  resizeCanvas();
  renderCharList();
  renderMapList();
  if(state.activeMapId) activateMap(state.activeMapId);
}
