/* ---------- Registro de quem fez o fluxo (versão do Tareffas) ----------
   Usa a sessão do Tareffas (o mesmo token do app, no mesmo endereço). O
   servidor é a fonte da verdade: no mesmo computador, outra pessoa pode ter
   deixado progresso no navegador, então o que vale é o da conta logada. */
let reg={ok:false,token:null,gestor:false,fila:Promise.resolve()};
function msgReg(t){const el=$('regStatus');if(el)el.textContent=t;}
const cabec=()=>({'Authorization':'Bearer '+reg.token,'Content-Type':'application/json'});
function registra(){if(!reg.ok)return;const corpo={estado:estado.map(s=>({acao:!!s.acao,resp:!!s.resp,erros:s.erros|0})),liberada};
 reg.fila=reg.fila.then(()=>fetch('/api/leiame/progresso',{method:'PUT',headers:cabec(),body:JSON.stringify(corpo)}))
  .then(r=>{if(!r.ok)throw new Error(String(r.status));msgReg('Seu progresso fica registrado no Tareffas.');if(reg.gestor)carregaQuadro();})
  .catch(()=>{reg.ok=false;msgReg('Não consegui registrar seu progresso. Entre de novo no Tareffas e recarregue esta página.');});}
(async()=>{let t=null;try{t=localStorage.getItem('token');}catch(e){}
 if(!t){msgReg('Entre no Tareffas e abra o manual pelo botão Leia-me para registrar seu progresso.');return;}
 reg.token=t;
 try{
  const rm=await fetch('/api/auth/me',{headers:cabec()});
  if(!rm.ok){msgReg('Sua sessão no Tareffas expirou. Entre de novo e recarregue esta página.');return;}
  const eu=await rm.json();reg.ok=true;
  const rp=await fetch('/api/leiame/progresso',{headers:cabec()});
  if(rp.ok){const d=await rp.json();
   if(Array.isArray(d.estado)&&d.estado.length===ETAPAS.length){estado=d.estado.map(s=>({acao:!!s.acao,resp:!!s.resp,erros:s.erros|0}));liberada=d.liberada|0;}
   else{estado=ETAPAS.map(()=>({acao:false,resp:false,erros:0}));liberada=0;}
   salvaLocal();mostra(liberada);}
  msgReg('Seu progresso fica registrado no Tareffas.');
  if(['admin','gestor'].includes(eu.grupo)){reg.gestor=true;$('painelQuem').hidden=false;carregaQuadro();setInterval(carregaQuadro,30000);}
 }catch(e){msgReg('');}})();
async function carregaQuadro(){try{
 const r=await fetch('/api/leiame/conclusoes',{headers:cabec()});if(!r.ok){$('quemResumo').textContent='Não consegui ler o registro agora.';return;}
 const docs=await r.json();
 docs.sort((a,b)=>(b.concluido-a.concluido)||((b.etapas|0)-(a.etapas|0))||a.nome.localeCompare(b.nome));
 const fim=docs.filter(d=>d.concluido).length,comecou=docs.filter(d=>(d.etapas|0)>0||d.concluido).length;
 $('quemResumo').textContent=fim+' de '+docs.length+(docs.length===1?' pessoa concluiu':' pessoas concluíram')+' o fluxo. '+(docs.length-comecou)+' ainda não começaram.';
 const dt=s=>s?new Date(s).toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}):'';
 const tb=$('quemLinhas');tb.innerHTML='';
 docs.forEach(d=>{const tr=document.createElement('tr');
  const nome=document.createElement('td');nome.textContent=d.nome;
  const prog=document.createElement('td');prog.textContent=(d.etapas|0)+' de '+(d.total||ETAPAS.length);
  const sit=document.createElement('td');const sp=document.createElement('span');
  if(d.concluido){sp.className='feito';sp.textContent='Concluiu';}else if((d.etapas|0)>0){sp.className='falta';sp.textContent='Em andamento';}else{sp.className='quem';sp.textContent='Não começou';}
  sit.appendChild(sp);
  const quando=document.createElement('td');quando.textContent=d.concluido?dt(d.concluido_em):(d.atualizado_em?'última vez '+dt(d.atualizado_em):'');
  const err=document.createElement('td');err.textContent=String(d.erros|0);
  [nome,prog,sit,quando,err].forEach(c=>tr.appendChild(c));tb.appendChild(tr);});
}catch(e){}}
