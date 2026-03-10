const API='http://localhost:8000';
const out=document.getElementById('out');
const inp=document.getElementById('inp');
const history=[];
let histIdx=-1;

function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}

function print(html){
  const d=document.createElement('div');
  d.className='line';
  d.innerHTML=html;
  out.appendChild(d);
  out.scrollTop=out.scrollHeight;
}

function printTable(headers,rows){
  let h='<table class="tbl"><tr>'+headers.map(h=>'<th>'+esc(h)+'</th>').join('')+'</tr>';
  rows.forEach(r=>{h+='<tr>'+r.map(c=>'<td>'+c+'</td>').join('')+'</tr>'});
  h+='</table>';
  print(h);
}

async function api(method,path,body){
  try{
    const opts={method,headers:{'Content-Type':'application/json'}};
    if(body)opts.body=JSON.stringify(body);
    const r=await fetch(API+path,opts);
    return await r.json();
  }catch(e){
    print('<span class="err">✕ Cannot reach backend. Is the server running?</span>');
    return null;
  }
}

async function cmdHelp(){
  print('<span class="bold">Commands:</span>');
  const cmds=[
    ['/help','Show this help'],
    ['/schema [table]','Browse schema'],
    ['/reports [id]','List or view reports'],
    ['/sql &lt;id&gt;','Generate SQL for a report'],
    ['/compare &lt;pbi&gt; &lt;sql&gt;','Diff PBI vs SQL data'],
    ['/validate &lt;id&gt;','Run validations on a report'],
    ['/hedis &lt;question&gt;','Ask about HEDIS specs'],
    ['/plan &lt;task&gt;','Break down a task into steps'],
    ['/discover','Connect to DB and discover schema'],
    ['/skills','Browse skills library'],
    ['/health','Backend status'],
    ['/clear','Clear terminal'],
  ];
  cmds.forEach(([c,d])=>print('  <span class="cyan">'+c+'</span> <span class="dim">— '+d+'</span>'));
  print('<span class="dim">Or type a message to chat with the AI.</span>');
}

async function cmdHealth(){
  const d=await api('GET','/api/health');
  if(!d)return;
  print('<span class="ok">✓</span> Status: '+d.status);
  print('  Tables: '+d.schema_tables+' · Joins: '+d.joins+' · Reports: '+d.reports);
  print('  Measures: '+d.hedis_measures+' · Templates: '+d.field_templates);
}

async function cmdSchema(args){
  if(args.length&&args[0]==='edit'){
    await cmdSchemaEdit(args.slice(1));return;
  }
  if(args.length){
    const d=await api('GET','/api/schema/'+args[0]);
    if(!d||d.error){print('<span class="err">✕ '+(d?.error||'Not found')+'</span>');return}
    const cols=d.columns||{};
    print('<span class="bold">'+esc(d.table_name)+'</span> <span class="dim">— '+esc(d.classification||'')+' · '+Object.keys(cols).length+' cols · ~'+(d.row_count_approx||'?')+' rows</span>');
    if(d.description)print('<span class="dim">'+esc(String(d.description).substring(0,200))+'</span>');
    const headers=['#','Column','Type','Role','PK','Description'];
    const rows=Object.entries(cols).map(([n,c],i)=>[
      '<span class="dim">'+(i+1)+'</span>',
      (c.pk?'<span class="warn">'+esc(n)+'</span>':'<span class="bold">'+esc(n)+'</span>'),
      '<span class="cyan">'+esc(c.data_type||'')+'</span>',
      '<span class="mag">'+esc(c.semantic_role||'')+'</span>',
      c.pk?'<span class="warn">PK</span>':'<span class="dim">—</span>',
      '<span class="dim">'+esc((c.description||c.record_level_info||'').substring(0,50))+'</span>'
    ]);
    printTable(headers,rows);
  }else{
    const d=await api('GET','/api/schema');
    if(!d)return;
    print('<span class="bold">Schema — '+(d.total||0)+' tables</span>');
    printTable(['Table','Type','Cols','Rows'],
      (d.tables||[]).map(t=>[
        '<span class="bold">'+esc(t.table_name)+'</span>',
        '<span class="cyan">'+esc(t.classification||'')+'</span>',
        String(t.columns_count),
        '<span class="dim">'+(t.row_count||'—')+'</span>'
      ])
    );
  }
}

async function cmdReports(args){
  if(args.length){
    const d=await api('GET','/api/reports/'+args[0]);
    if(!d||d.error){print('<span class="err">✕ '+(d?.error||'Not found')+'</span>');return}
    print('<span class="bold">'+esc(d.report_name||'')+'</span> <span class="ok">'+esc(d.status||'')+'</span>');
    const fields=d.fields||[];
    printTable(['Field','Type','Null'],fields.map(f=>[
      '<span class="bold">'+esc(f.display_name)+'</span>',
      '<span class="cyan">'+esc(f.data_type||'')+'</span>',
      f.allow_null===false?'<span class="err">✕</span>':'<span class="ok">✓</span>'
    ]));
    print('<span class="bold">Slicers:</span> '+(d.slicers||[]).map(s=>esc(s.name)).join(', '));
  }else{
    const d=await api('GET','/api/reports');
    if(!d)return;
    (d.reports||[]).forEach(r=>{
      print('  <span class="bold">'+esc(r.report_id)+'</span> <span class="dim">— '+esc(r.report_name||'')+' · '+r.fields_count+' fields · '+r.slicers_count+' slicers</span> <span class="ok">'+esc(r.status||'')+'</span>');
    });
  }
}

async function cmdSql(args){
  if(!args.length){print('<span class="err">Usage: /sql &lt;report_id&gt;</span>');return}
  const d=await api('POST','/api/generate-sql',{report_id:args[0],slicers:{}});
  if(!d)return;
  const sql=d.sql||'';
  print('<span class="ok">⚡ Generated '+(sql.split('\n').length)+' lines of SQL</span>');
  print('<span class="mag">'+esc(sql)+'</span>');
}

async function cmdSkills(){
  const d=await api('GET','/api/skills');
  if(!d)return;
  const cats={};
  (d.skills||[]).forEach(s=>{(cats[s.cat]=cats[s.cat]||[]).push(s)});
  for(const[cat,items]of Object.entries(cats)){
    print('<span class="bold cyan">'+cat.toUpperCase()+'</span> <span class="dim">('+items.length+')</span>');
    items.forEach(s=>print('  <span class="bold">'+esc(s.name)+'</span> <span class="dim">— '+esc((s.desc||'').substring(0,70))+'</span>'));
  }
}

async function cmdSchemaEdit(args){
  if(!args.length){print('<span class="err">Usage: /schema edit &lt;table.column&gt;</span>');return}
  const parts=args[0].split('.');
  const table=parts[0];
  const col=parts[1];
  if(!col){print('<span class="err">Usage: /schema edit &lt;table.column&gt; e.g. /schema edit factqualityreport.clinicalonlystatus</span>');return}

  const d=await api('GET','/api/schema/'+table);
  if(!d||d.error){print('<span class="err">✕ '+(d?.error||'Table not found')+'</span>');return}
  const c=d.columns?.[col];
  if(!c){print('<span class="err">✕ Column "'+esc(col)+'" not found in '+esc(table)+'</span>');return}

  print('<span class="bold">✏️ Editing '+esc(table)+'.'+esc(col)+'</span>');
  print('');
  const editable=['business_name','description','semantic_role','aggregatable','default_aggregation','aggregation_behavior','filterable','sortable','groupable','categorical'];
  editable.forEach(k=>{
    const v=c[k]!==undefined?String(c[k]):'—';
    print('  <span class="cyan">'+k+'</span> = <span class="dim">'+esc(v)+'</span>');
  });
  print('');
  print('<span class="dim">Type: field=value (e.g. description=My new description)</span>');
  print('<span class="dim">Type "save" when done, "cancel" to discard.</span>');

  const pending={};
  window._editMode={table,col,pending,editable};
}

async function handleEditInput(input){
  const em=window._editMode;
  if(!em)return false;
  if(input.toLowerCase()==='cancel'){
    delete window._editMode;
    print('<span class="warn">Cancelled.</span>');
    return true;
  }
  if(input.toLowerCase()==='save'){
    if(Object.keys(em.pending).length===0){
      print('<span class="warn">Nothing to save.</span>');
      delete window._editMode;
      return true;
    }
    // Convert booleans
    const updates={};
    for(const[k,v]of Object.entries(em.pending)){
      if(v==='true')updates[k]=true;
      else if(v==='false')updates[k]=false;
      else updates[k]=v;
    }
    const d=await api('POST','/api/schema/edit',{table_name:em.table,column_name:em.col,updates});
    if(d&&d.status==='saved'){
      print('<span class="ok">✓ Saved '+Object.keys(updates).length+' changes to '+esc(em.table)+'.'+esc(em.col)+'</span>');
    }else{
      print('<span class="err">✕ '+(d?.error||'Save failed')+'</span>');
    }
    delete window._editMode;
    return true;
  }
  const eq=input.indexOf('=');
  if(eq>0){
    const key=input.substring(0,eq).trim();
    const val=input.substring(eq+1).trim();
    if(em.editable.includes(key)){
      em.pending[key]=val;
      print('  <span class="ok">✓</span> <span class="cyan">'+esc(key)+'</span> → <span class="bold">'+esc(val)+'</span>');
    }else{
      print('<span class="warn">Unknown field: '+esc(key)+'. Editable: '+em.editable.join(', ')+'</span>');
    }
    return true;
  }
  print('<span class="warn">Type field=value, "save", or "cancel"</span>');
  return true;
}

async function cmdChat(msg){
  print('<span class="dim">thinking...</span>');
  const d=await api('POST','/api/chat',{message:msg});
  out.lastChild?.remove();
  if(!d)return;
  const resp=d.response||'';
  resp.split('\n').forEach(l=>print(esc(l)));
}

async function cmdValidate(args){
  if(!args.length){print('<span class="err">Usage: /validate &lt;report_id&gt;</span>');return}
  print('<span class="dim">validating...</span>');
  const d=await api('GET','/api/validate/'+args[0]);
  out.lastChild?.remove();
  if(!d||d.error){print('<span class="err">✕ '+(d?.error||'Failed')+'</span>');return}
  print('<span class="bold">🔍 Validator Agent — '+esc(args[0])+'</span>');
  (d.results||[]).forEach(r=>{
    const icon=r.status==='pass'?'<span class="ok">✓</span>':r.status==='error'?'<span class="err">✕</span>':'<span class="warn">⚠</span>';
    print('  '+icon+' <span class="dim">['+r.check+']</span> '+esc(r.msg));
  });
  print('');
  print('  Result: <span class="ok">'+d.passed+' passed</span> · <span class="err">'+d.errors+' errors</span> · <span class="warn">'+d.warnings+' warnings</span>');
}

async function cmdHedis(args){
  if(!args.length){print('<span class="err">Usage: /hedis &lt;question&gt;</span>');return}
  print('<span class="dim">searching HEDIS spec...</span>');
  const d=await api('POST','/api/hedis',{message:args.join(' ')});
  out.lastChild?.remove();
  if(!d)return;
  print('<span class="bold">🏥 HEDIS Domain Agent</span>');
  (d.response||'').split('\n').forEach(l=>print(esc(l)));
}

async function cmdPlan(args){
  if(!args.length){print('<span class="err">Usage: /plan &lt;task description&gt;</span>');return}
  print('<span class="dim">planning...</span>');
  const d=await api('POST','/api/plan',{message:args.join(' ')});
  out.lastChild?.remove();
  if(!d)return;
  print('<span class="bold">📋 Planner Agent — '+esc(d.report_type||'')+'</span>');
  (d.steps||[]).forEach((s,i)=>{
    print('  <span class="cyan">Step '+(i+1)+':</span> '+esc(s));
  });
  print('');
  print('<span class="dim">Ready to execute? Type "yes" or modify steps.</span>');
}

async function cmdDiscover(){
  print('<span class="dim">connecting to database and enriching schema...</span>');
  const d=await api('POST','/api/discover',{host:'localhost',port:3306,user:'root',password:'',database:'HEDIS_RDW',schemas:'dbo'});
  out.lastChild?.remove();
  if(!d||d.error){print('<span class="err">✕ '+(d?.error||'Failed')+'</span>');return}
  print('<span class="bold">🔌 Discovery Agent</span>');
  print('<span class="ok">✓</span> Discovered <span class="bold">'+d.tables_count+'</span> tables, <span class="bold">'+d.columns_count+'</span> columns');
  (d.tables||[]).forEach(t=>print('  <span class="ok">✓</span> '+esc(t)));
  const e=d.enrichment||{};
  print('');
  print('<span class="bold">Enrichment:</span>');
  print('  <span class="ok">'+e.cache_hits+'</span> from column mappings cache');
  print('  <span class="cyan">'+e.ollama_hits+'</span> enriched by Ollama');
  print('  <span class="warn">'+e.fallback_hits+'</span> rule-based fallback');
  print('');
  print('<span class="dim">Saved to skills/schema/*.yaml</span>');
}

async function cmdCompare(args){
  if(args.length<2){print('<span class="err">Usage: /compare &lt;pbi.csv&gt; &lt;sql.csv&gt;</span>');return}
  print('<span class="err">✕ File upload not supported in browser terminal. Use the Compare page or the Python CLI.</span>');
}

async function run(input){
  const parts=input.trim().split(/\s+/);
  const cmd=parts[0].toLowerCase();
  const args=parts.slice(1);

  print('<span class="prompt">❯</span> <span class="cmd">'+esc(input)+'</span>');

  // Check if in edit mode
  if(window._editMode){
    await handleEditInput(input);
    return;
  }

  if(cmd==='/help')await cmdHelp();
  else if(cmd==='/health')await cmdHealth();
  else if(cmd==='/schema')await cmdSchema(args);
  else if(cmd==='/reports')await cmdReports(args);
  else if(cmd==='/sql')await cmdSql(args);
  else if(cmd==='/skills')await cmdSkills();
  else if(cmd==='/validate')await cmdValidate(args);
  else if(cmd==='/hedis')await cmdHedis(args);
  else if(cmd==='/plan')await cmdPlan(args);
  else if(cmd==='/discover')await cmdDiscover();
  else if(cmd==='/compare')await cmdCompare(args);
  else if(cmd==='/clear'){out.innerHTML='';banner();}
  else if(cmd.startsWith('/'))print('<span class="err">Unknown command: '+esc(cmd)+'. Type /help</span>');
  else await cmdChat(input);

  print('');
}

async function banner(){
  print('<span class="bold cyan">🔷 AI1X Auditor</span>');
  const d=await api('GET','/api/health');
  if(d&&d.status==='ok'){
    print('<span class="dim">   Connected · '+d.schema_tables+' tables · '+d.reports+' reports · '+d.hedis_measures+' measures</span>');
  }else{
    print('<span class="warn">   ⚠ Backend not reachable</span>');
  }
  print('<span class="dim">   Type /help for commands or just chat.</span>');
  print('');
}

inp.addEventListener('keydown',async e=>{
  if(e.key==='Enter'&&inp.value.trim()){
    const v=inp.value.trim();
    history.unshift(v);histIdx=-1;
    inp.value='';
    await run(v);
  }else if(e.key==='ArrowUp'){
    if(histIdx<history.length-1){histIdx++;inp.value=history[histIdx]}
  }else if(e.key==='ArrowDown'){
    if(histIdx>0){histIdx--;inp.value=history[histIdx]}
    else{histIdx=-1;inp.value=''}
  }
});

document.addEventListener('click',()=>inp.focus());
banner();
