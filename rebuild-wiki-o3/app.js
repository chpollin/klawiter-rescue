/* =======================================================================
   Zweig Bibliography – fully client‑side dashboard logic
   ======================================================================= */

const CSV_FILE       = 'zweig_bibliography_enhanced.csv';
const FACET_FIELDS   = ['language', 'publisher'];
const CATEGORY_FIELD = 'categories';
const RESULT_LIMIT   = 300;

/* — Tiny helpers — */
const $  = (q, el=document) => el.querySelector(q);
const $$ = (q, el=document) => Array.from(el.querySelectorAll(q));
const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const hl  = (txt='', term='') => term ? txt.replace(new RegExp(`(${esc(term)})`,'gi'),'<mark>$1</mark>') : txt;

/* — Global state — */
const S = { rows: [], index: null, q: '', filters: {} };
Object.assign(window, { S, FACET_FIELDS });   // exposed for smoke‑tests

/* ───────────── Data + Index ───────────── */
const loadCSV = () => new Promise((res,rej)=>{
  Papa.parse(CSV_FILE,{header:true,download:true,skipEmptyLines:true,complete:({data})=>res(data),error:rej});
});
function buildIndex(rows){
  const {Document}=FlexSearch;
  S.index=new Document({tokenize:'forward',document:{id:'page_id',index:[
    'title','original_title','clean_content','full_bibliographic_entry',
    'publisher','location','language',CATEGORY_FIELD,'main_category','time_period'
  ]}});
  rows.forEach(r=>S.index.add(r));
}

/* ───────────── Sidebar UI ───────────── */
function catTree(){
  const root={};
  S.rows.forEach(r=>{
    const segs=(r[CATEGORY_FIELD]||'').split(/[>;|]/).map(t=>t.trim()).filter(Boolean);
    let n=root; segs.forEach(s=>{n[s]??={c:0,k:{}}; n[s].c++; n=n[s].k;});
  });
  const render=(node,p=[])=>Object.entries(node).sort(([a],[b])=>a.localeCompare(b))
    .map(([l,o])=>{
      const full=[...p,l].join('::');
      return `<li>${
         Object.keys(o.k).length
          ? `<details open><summary data-cat="${full}">${l} <span class=text-gray-500>(${o.c})</span></summary>${render(o.k,[...p,l])}</details>`
          : `<button data-cat="${full}" class="hover:underline">${l} <span class=text-gray-500>(${o.c})</span></button>`
      }</li>`;
    }).join('');
  $('#category-tree').innerHTML=`<ul class=pl-4 space-y-1>${render(root)}</ul>`;
}

/* facets */
function facetPanel(rows){
  const box=$('#facets');
  box.innerHTML=FACET_FIELDS.map(f=>`<details open><summary class="font-medium capitalize cursor-pointer">${f}</summary><ul data-facet="${f}" class="pl-4 space-y-1"></ul></details>`).join('');
  FACET_FIELDS.forEach(f=>{
    const count={}; rows.forEach(r=>{const v=r[f]||'—'; count[v]=(count[v]||0)+1});
    const ul=box.querySelector(`[data-facet="${f}"]`);
    ul.innerHTML=Object.entries(count).sort((a,b)=>b[1]-a[1]).slice(0,30).map(([v,c])=>{
      const chk=S.filters[f]?.has(v)?'checked':''; return `<li><label class="inline-flex items-center gap-1"><input type=checkbox data-field="${f}" data-value="${v}" ${chk}>${v} <span class=text-gray-500>(${c})</span></label></li>`;
    }).join('');
  });
}
function chips(){
  const box=$('#active-filters');
  box.innerHTML=Object.entries(S.filters).flatMap(([f,set])=>[...set].map(v=>`<span class=filter-chip>${f}: ${v} <button data-remove="${f}::${v}">&times;</button></span>`)).join('');
  box.classList.toggle('hidden',!box.innerHTML);
}

/* ───────────── Query & Filter ───────────── */
function applyFilters(){
  let out=S.rows;
  if(S.q.trim()){
    const ids=new Set(S.index.search(S.q,{limit:RESULT_LIMIT*2}).flat());
    out=out.filter(r=>ids.has(r.page_id));
  }
  for(const [field,set] of Object.entries(S.filters)){
    if(!set?.size) continue;
    out=out.filter(r=>{
      if(field===CATEGORY_FIELD){
        const path=(r[field]||'').split(/[>;|]/).map(t=>t.trim());
        return [...set].some(sel=>sel.split('::').every((p,i)=>path[i]===p));
      }
      return set.has(r[field]||'—');
    });
  }
  return out;
}

/* ───────────── Results list ───────────── */
function list(rows){
  $('#stats').textContent=`${rows.length} entries${rows.length>RESULT_LIMIT?` – showing first ${RESULT_LIMIT}`:''}`;
  $('#results-list').innerHTML=rows.slice(0,RESULT_LIMIT).map(r=>`
    <li class="rounded-lg bg-white p-4 shadow-sm">
      <h3 data-open="${r.page_id}" class="text-lg font-semibold cursor-pointer hover:underline">
        ${hl(r.title||'Untitled',S.q)}
      </h3>
      <p class="text-sm text-gray-600">${hl(r.publisher||'—',S.q)} ${r.year?'('+r.year+')':''}</p>
      <p class="line-clamp-2 text-sm mt-1">${hl(r.clean_content||'',S.q)}</p>
    </li>`).join('');
}

/* ───────────── Charts ───────────── */
let tlChart, distChart;
function charts(rows){
  const byYear={}; rows.forEach(r=>{const y=r.year||'—'; byYear[y]=(byYear[y]||0)+1});
  const yrs=Object.keys(byYear).sort();
  tlChart?.destroy();
  tlChart=new Chart($('#timeline-chart'),{type:'bar',data:{labels:yrs,datasets:[{data:yrs.map(y=>byYear[y])}]},options:{plugins:{legend:{display:false}},maintainAspectRatio:false}});

  const byLang={}; rows.forEach(r=>{const l=r.language||'—'; byLang[l]=(byLang[l]||0)+1});
  const lbls=Object.keys(byLang);
  distChart?.destroy();
  distChart=new Chart($('#distribution-chart'),{type:'pie',data:{labels:lbls,datasets:[{data:lbls.map(l=>byLang[l])}]},options:{maintainAspectRatio:false,plugins:{legend:{position:'bottom'}}}});
}

/* ───────────── Network (d3) ───────────── */
function network(rows){
  const svg=$('#network-graph'); svg.innerHTML='';
  const sample=rows.slice(0,120);
  const nodes=sample.map(r=>({id:r.page_id,title:r.title}));
  const links=[];
  const byPub={}; sample.forEach(r=>(byPub[r.publisher]??=[]).push(r));
  Object.values(byPub).forEach(a=>{for(let i=0;i<a.length-1;i++)links.push({source:a[i].page_id,target:a[i+1].page_id})});
  const w=svg.clientWidth,h=svg.clientHeight;
  const sim=d3.forceSimulation(nodes).force('link',d3.forceLink(links).id(d=>d.id).distance(60)).force('charge',d3.forceManyBody().strength(-100)).force('center',d3.forceCenter(w/2,h/2));
  d3.select(svg).append('g').attr('stroke','#bbb').selectAll('line').data(links).enter().append('line');
  const node=d3.select(svg).append('g').selectAll('circle').data(nodes).enter().append('circle').attr('r',4).attr('fill','#6366f1');
  node.append('title').text(d=>d.title);
  sim.on('tick',()=>{d3.select(svg).selectAll('line').attr('x1',d=>d.source.x).attr('y1',d=>d.source.y).attr('x2',d=>d.target.x).attr('y2',d=>d.target.y); d3.select(svg).selectAll('circle').attr('cx',d=>d.x).attr('cy',d=>d.y);});
}

/* ───────────── URL state ───────────── */
const saveURL=()=>{
  const p=new URLSearchParams();
  if(S.q.trim()) p.set('q',S.q.trim());
  if(Object.keys(S.filters).length){
    const o={}; for(const [k,s] of Object.entries(S.filters)) o[k]=[...s];
    p.set('f',btoa(JSON.stringify(o)));
  }
  history.replaceState(null,'','?'+p);
};
const loadURL=()=>{
  const p=new URLSearchParams(location.search);
  if(p.has('q')) {S.q=p.get('q'); $('#search').value=S.q;}
  if(p.has('f')) try{const o=JSON.parse(atob(p.get('f'))); for(const[k,arr]of Object.entries(o)) S.filters[k]=new Set(arr);}catch{}
};

/* ───────────── Render orchestrator ───────────── */
function render(){
  const rows=applyFilters();
  facetPanel(rows);
  chips();
  list(rows);
  charts(rows);
  network(rows);
  saveURL();
}

/* ───────────── Event listeners ───────────── */
function events(){
  $('#search').addEventListener('input',e=>{S.q=e.target.value; suggest(S.q); render();});
  $('#search').addEventListener('keydown',e=>{if(e.key==='Enter')$('#suggestions').classList.add('hidden');});
  $('#suggestions').addEventListener('click',e=>{const v=e.target.closest('[data-suggest]')?.dataset.suggest;if(v){$('#search').value=v;S.q=v;$('#suggestions').classList.add('hidden');render();}});
  $('#category-tree').addEventListener('click',e=>{const c=e.target.closest('[data-cat]')?.dataset.cat;if(!c)return;const s=S.filters[CATEGORY_FIELD]??=new Set();s.has(c)?s.delete(c):s.add(c);render();});
  $('#facets').addEventListener('change',e=>{const{field,value}=e.target.dataset;if(!field)return;const s=S.filters[field]??=new Set();e.target.checked?s.add(value):s.delete(value);if(!s.size)delete S.filters[field];render();});
  $('#active-filters').addEventListener('click',e=>{const k=e.target.dataset.remove;if(!k)return;const[f,v]=k.split('::');S.filters[f]?.delete(v);if(!S.filters[f]?.size)delete S.filters[f];render();});
  $('#results-list').addEventListener('click',e=>{const id=e.target.closest('[data-open]')?.dataset.open;if(!id)return;open(id);});
  $('#close-modal').addEventListener('click',()=>$('#entry-modal').classList.add('hidden'));
  $('#entry-modal').addEventListener('click',e=>{if(e.target===$('#entry-modal'))$('#entry-modal').classList.add('hidden');});
  $$('[data-tab]').forEach(btn=>btn.addEventListener('click',()=>{$$('[data-tab]').forEach(b=>b.setAttribute('aria-selected',b===btn));['timeline','distribution','network'].forEach(id=>(id==='network'?$('#network-graph'):$(`#${id}-chart`)).classList.add('hidden'));const id=btn.dataset.tab;(id==='network'?$('#network-graph'):$(`#${id}-chart`)).classList.remove('hidden');}));
  $('[data-tab="timeline"]').click();
}
function suggest(term){
  const box=$('#suggestions'); if(term.trim().length<2){box.classList.add('hidden');return;}
  const arr=S.rows.filter(r=>(r.title||'').toLowerCase().includes(term.toLowerCase())).slice(0,8);
  box.innerHTML=arr.map(r=>`<li data-suggest="${r.title.replace(/\"/g,'&quot;')}" class="cursor-pointer px-3 py-1 hover:bg-gray-100" role=option>${hl(r.title,term)}</li>`).join('');
  box.classList.toggle('hidden',!arr.length);
}
function open(id){const r=S.rows.find(x=>x.page_id===id);$('#entry-content').innerHTML=`<h2 class="mb-1 font-serif text-2xl">${r.title||'Untitled'}</h2><p class="mb-2 italic">${r.original_title||''}</p><p><strong>Year:</strong> ${r.year||'—'} · <strong>Publisher:</strong> ${r.publisher||'—'}</p><p class="my-2 whitespace-pre-wrap">${r.full_bibliographic_entry||''}</p><h3 class="mt-4 font-semibold">Excerpt</h3><pre class="whitespace-pre-wrap">${r.clean_content||''}</pre>`;$('#entry-modal').classList.remove('hidden');}

/* ───────────── Bootstrap ───────────── */
(async()=>{
  S.rows=await loadCSV();
  buildIndex(S.rows);
  catTree();
  events();
  loadURL();
  render();
})();
