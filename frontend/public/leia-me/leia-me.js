(function(){
const $=id=>document.getElementById(id);
/* ---------- Fluxo ---------- */
const ETAPAS=[
 {n:'Cadastro',t:'Tudo começa no cadastro',quem:'Gestores e admin · Empresas e Obrigações',
  o:['A <b>empresa</b> diz o regime, o segmento, o dia do fechamento e quais setores a BPS4 atende, com o responsável de cada um.','A <b>obrigação</b> é o modelo: setor, quando acontece, de onde vem o vencimento, o prazo interno, para que lado vai o documento e quais empresas recebe.','Se a obrigação estiver errada, todas as tarefas do mês nascem erradas. A linha "Tarefas de..." da tela mostra as datas antes de salvar.'],
  ex:'<b>Clínica Sorriso Feliz</b>: Lucro Presumido, serviço, fechamento dia 20, Fiscal atendido por Rafael Souza. <b>DCTFWeb</b>: mensal, competência do mês anterior, prazo legal no último dia útil, prazo interno 7 dias corridos antes, sentido "Transmitir ao órgão".'},
 {n:'Geração do mês',t:'As tarefas nascem para cada empresa',quem:'Quem tem a permissão de gerar · Obrigações › Gerar tarefas do mês',
  o:['Um clique cria as tarefas do mês de todas as obrigações ativas, uma por empresa alcançada.','A empresa entra se passar pelos três filtros: <b>regime e segmento</b> da obrigação, <b>vínculo ou exceção</b>, e <b>setor atendido</b> na empresa.','Responsável = o primeiro nome da matriz empresa × setor. Supervisor = gestor do responsável, ou gestor do setor, ou o supervisor da obrigação.','Gerar de novo não duplica: tarefa que já existe, até cancelada, é pulada.'],
  ex:'O gestor gera <b>outubro/2026</b>. Nasce "DCTFWeb · Clínica Sorriso Feliz", competência <b>09/2026</b>, vencimento <b>30/10 (sexta)</b>, prazo interno <b>23/10 (sexta)</b>, responsável Rafael Souza.'},
 {n:'Execução',t:'Quem faz acompanha pela cor',quem:'Responsável · Tarefas e Painel',
  o:['A cor segue o <b>prazo interno</b>: verde com folga, amarela na semana, vermelha quando passou.','Mude a situação para <b>Em andamento</b> quando começar: é isso que faz o Painel falar a verdade.','No cartão: anexar, transferir, observações e <b>Não se aplica</b>, que exige o motivo.','Férias? A substituição manda as tarefas para quem cobre.'],
  ex:'Em <b>16/10</b> o cartão de Rafael fica amarelo (falta uma semana para o prazo interno). Ele marca Em andamento e prepara a declaração.'},
 {n:'Documento',t:'O comprovante entra no sistema',quem:'Responsável · e-validador ou link de envio',
  o:['<b>Transmitir ao órgão</b>: o recibo de entrega sobe no e-validador.','<b>Entregar ao cliente</b>: a guia (DAS, DARF) sobe no e-validador ou é anexada na tarefa.','<b>Receber do cliente</b>: o cliente manda pelo link de envio, sem login.','<b>Tarefa interna</b>: sem documento, baixa pela situação.'],
  ex:'Rafael transmite a DCTFWeb e arrasta o recibo para o <b>e-validador</b>.'},
 {n:'Baixa',t:'O sistema acha a tarefa certa',quem:'Automático',
  o:['O e-validador lê o <b>CNPJ</b>, a <b>competência</b> e o tipo do documento pelo identificador da obrigação.','Achou uma tarefa aberta que casa: conclui. Não achou ou achou duas: avisa na tela (Sem tarefa, Ambíguo).','Obrigação marcada "Exige documento" só conclui pelo documento, nunca pelo clique.'],
  ex:'O recibo traz o CNPJ da Clínica e a competência <b>09/2026</b>. Resultado: <b>Baixada</b>. A tarefa fica verde-escura, concluída.'},
 {n:'Entrega',t:'A guia chega ao cliente',quem:'Automático, ou "Enviar ao cliente" na tarefa',
  o:['Guia reconhecida sai por <b>e-mail e WhatsApp</b> com um link próprio para cada destinatário.','O assunto usa o <b>mininome</b> da obrigação: "BPS4 | DAS, setembro/2026, Empresa".','Se o CNPJ ou a competência não vieram da própria guia, nada sai: fica "Aguardando conferência".','A empresa precisa ter e-mail ou telefone no cadastro.'],
  ex:'A DCTFWeb é "Transmitir ao órgão", então nada vai ao cliente. Se fosse o <b>DAS</b>, o cliente receberia o link e a tela Documentos mostraria "Já baixou".'},
 {n:'Acompanhamento',t:'O gestor vê tudo no Painel',quem:'Gestores · Painel',
  o:['Números do mês: em aberto, atrasadas, a vencer em 7 dias, que geram multa e que esperam documento.','Agrupe por setor, colaborador ou empresa para achar a fila parada.','Filtre pela competência (MM/AAAA) para fechar um mês.'],
  ex:'No Painel de outubro, a DCTFWeb da Clínica sai de "em aberto" e entra nas concluídas do setor Fiscal.'}
];
/* Cada etapa: uma ação para fazer (FACA) e uma pergunta (PERG). A próxima só abre
   com as duas feitas. O progresso fica no navegador de quem lê, se ele permitir. */
const PERG=[
 {p:'O que decide se a Clínica recebe a DCTFWeb?',r:['O regime e o segmento da empresa, e o setor Fiscal marcado nela','O nome do responsável pelo Fiscal','A data em que a empresa foi cadastrada'],c:0,
  ok:'Isso. A regra da obrigação olha regime e segmento, e a matriz da empresa diz se o setor foi contratado.',nao:'Não é isso. Quem decide é a regra da obrigação (regime e segmento) somada ao setor marcado na empresa.'},
 {p:'O gestor clicou duas vezes em "Gerar tarefas do mês" para outubro. O que acontece?',r:['Nasce uma segunda DCTFWeb para a Clínica','Nada: a tarefa que já existe é pulada','A tarefa antiga é apagada e criada de novo'],c:1,
  ok:'Isso. Gerar de novo não duplica: a tarefa que já existe, até cancelada, é pulada.',nao:'Não. A geração pula a tarefa que já existe para aquela empresa, obrigação e competência.'},
 {p:'O que deixa o cartão da tarefa vermelho?',r:['Passar o vencimento legal','Passar o prazo interno','A tarefa estar sem anexo'],c:1,
  ok:'Isso. A cor segue o prazo interno, que vem antes do vencimento: o vermelho é o aviso para não chegar perto da multa.',nao:'Não. A cor segue o prazo interno da equipe, e não o vencimento legal.'},
 {p:'Na DCTFWeb, que tem o sentido "Transmitir ao órgão", o que sobe no e-validador?',r:['A guia de pagamento','O recibo de entrega da declaração','Nada, a baixa é manual'],c:1,
  ok:'Isso. Em "Transmitir ao órgão" quem dá a baixa é o recibo de entrega.',nao:'Não. Em "Transmitir ao órgão" o documento que dá a baixa é o recibo de entrega.'},
 {p:'Como o e-validador sabe qual tarefa concluir?',r:['Pelo nome do arquivo','Pelo CNPJ, pela competência e pelo identificador da obrigação','Pelo responsável que subiu o arquivo'],c:1,
  ok:'Isso. O nome do arquivo não importa: o que vale é o que está escrito dentro do documento.',nao:'Não. O que vale é o que está dentro do documento: CNPJ, competência e o trecho identificador.'},
 {p:'Quando uma guia reconhecida NÃO sai sozinha para o cliente?',r:['Quando o CNPJ ou a competência não foram lidos na própria guia','Nunca: toda guia reconhecida sai','Quando o envio é numa sexta-feira'],c:0,
  ok:'Isso. Nesse caso a guia fica "Aguardando conferência": alguém confere e envia pela tarefa.',nao:'Não. A trava existe para não mandar guia ao cliente errado: sem CNPJ e competência lidos na guia, nada sai.'},
 {p:'Onde o gestor descobre em que pessoa a fila está parada?',r:['No Painel, agrupando por colaborador','Na tela Documentos','Na tela Modelos'],c:0,
  ok:'Isso. No Painel, o agrupamento por colaborador mostra quanto cada pessoa tem em aberto e atrasado.',nao:'Não. É no Painel, agrupando por colaborador.'}
];
const FACA=[
 {tit:'Configure a Clínica e a DCTFWeb',html:`
  <div class="mini">
   <div class="mini-cab">Empresa · Clínica Sorriso Feliz</div>
   <label class="mini-linha">Regime <select id="f1reg"><option value="">Escolha</option><option value="simples">Simples Nacional</option><option value="presumido">Lucro Presumido</option></select></label>
   <label class="mini-linha">Fechamento <select id="f1fech"><option value="">Escolha</option><option>13</option><option>20</option><option>25</option></select></label>
   <label class="mini-chk"><input type="checkbox" id="f1fiscal"> Setor Fiscal (Rafael Souza)</label>
   <div class="mini-cab">Obrigação · DCTFWeb</div>
   <label class="mini-chk"><input type="checkbox" id="f1etapa"> Etapa do fechamento contábil</label>
   <p class="mini-dica">Dica: a Clínica é do Presumido, que fecha dia 20. A DCTFWeb tem prazo em lei.</p>
  </div>`,
  liga(fim){const v=()=>{const ok=$('f1reg').value==='presumido'&&$('f1fech').value==='20'&&$('f1fiscal').checked&&!$('f1etapa').checked;
   $('f1st').innerHTML=ok?'<span class="feito">Cadastro certo: a DCTFWeb vai alcançar a Clínica.</span>':($('f1etapa').checked?'<span class="falta">A DCTFWeb tem prazo legal: não é etapa do fechamento.</span>':'<span class="falta">Falta: regime, fechamento e setor Fiscal.</span>');if(ok)fim();};
   ['f1reg','f1fech','f1fiscal','f1etapa'].forEach(id=>$(id).addEventListener('change',v));v();}},
 {tit:'Gere as tarefas de outubro',html:`
  <div class="mini">
   <div class="mini-cab">Obrigações</div>
   <button class="btn primario" type="button" id="f2gerar">Gerar tarefas do mês · outubro/2026</button>
   <div id="f2saida"></div>
  </div>`,
  liga(fim){let n=0;$('f2gerar').onclick=()=>{n++;
   $('f2saida').innerHTML=n===1?`<div class="tarefa verde nova"><b>DCTFWeb · Clínica Sorriso Feliz</b><span>Competência 09/2026 · Resp. Rafael Souza</span><span>Prazo interno 23/10 (sexta) · Vencimento 30/10 (sexta)</span></div><p class="mini-dica">1 tarefa criada.</p>`
    :`<div class="tarefa verde"><b>DCTFWeb · Clínica Sorriso Feliz</b><span>Competência 09/2026 · Resp. Rafael Souza</span><span>Prazo interno 23/10 (sexta) · Vencimento 30/10 (sexta)</span></div><p class="mini-dica">0 criadas, 1 pulada: ela já existia.</p>`;fim();};}},
 {tit:'Ande com a tarefa no tempo',html:`
  <div class="mini">
   <label class="mini-linha" for="f3dia">Hoje é <b id="f3hoje">01/10</b></label>
   <input type="range" id="f3dia" min="1" max="31" value="1" aria-label="Dia de outubro">
   <div class="tarefa" id="f3card"><b>DCTFWeb · Clínica Sorriso Feliz</b><span id="f3cor"></span>
    <label class="mini-linha">Situação <select id="f3sit"><option value="pendente">Pendente</option><option value="andamento">Em andamento</option></select></label></div>
   <p class="mini-dica">Arraste até a semana do prazo interno e marque "Em andamento".</p>
  </div>`,
  liga(fim){let viuAmarelo=false;const v=()=>{const d=+$('f3dia').value;$('f3hoje').textContent=String(d).padStart(2,'0')+'/10';
   let cls,txt;if(d>23){cls='vermelho';txt='Atrasada: o prazo interno (23/10) passou';}else if(d===23){cls='amarelo';txt='Vence hoje';}else if(d>=16){cls='amarelo';txt='Até 7 dias: planeje agora';}else{cls='verde';txt='Em dia: '+(23-d)+' dias de folga';}
   if(cls==='amarelo')viuAmarelo=true;$('f3card').className='tarefa '+cls;$('f3cor').textContent=txt;
   const ok=viuAmarelo&&$('f3sit').value==='andamento';$('f3st').innerHTML=ok?'<span class="feito">Tarefa em andamento, dentro do prazo interno.</span>':'<span class="falta">'+(viuAmarelo?'Agora marque Em andamento.':'Arraste o dia até ficar amarelo.')+'</span>';if(ok)fim();};
   $('f3dia').addEventListener('input',v);$('f3sit').addEventListener('change',v);v();}},
 {tit:'Escolha o documento certo',html:`
  <div class="mini">
   <div class="mini-cab">Arquivos na sua pasta</div>
   <div class="docs" id="f4docs">
    <button type="button" class="doc" data-d="guia" draggable="true">DAS_setembro.pdf</button>
    <button type="button" class="doc" data-d="recibo" draggable="true">Recibo_DCTFWeb_09-2026.pdf</button>
    <button type="button" class="doc" data-d="extrato" draggable="true">Extrato_banco.pdf</button>
   </div>
   <div class="zona" id="f4zona" tabindex="0">Arraste para cá, ou clique num arquivo</div>
  </div>`,
  liga(fim){const usa=(d,nome)=>{if(d==='recibo'){$('f4zona').innerHTML='<b>'+nome+'</b> pronto para processar';$('f4zona').classList.add('cheia');$('f4st').innerHTML='<span class="feito">Recibo de entrega no e-validador.</span>';fim();}
    else{$('f4zona').textContent=nome+': não é este';$('f4st').innerHTML='<span class="falta">'+(d==='guia'?'Guia é para obrigação de entregar ao cliente.':'Extrato é documento que o cliente envia.')+' Para a DCTFWeb, use o recibo.</span>';}};
   document.querySelectorAll('#f4docs .doc').forEach(b=>{b.onclick=()=>usa(b.dataset.d,b.textContent);b.ondragstart=e=>e.dataTransfer.setData('text',b.dataset.d+'|'+b.textContent);});
   const z=$('f4zona');z.ondragover=e=>{e.preventDefault();z.classList.add('sobre');};z.ondragleave=()=>z.classList.remove('sobre');
   z.ondrop=e=>{e.preventDefault();z.classList.remove('sobre');const [d,n]=(e.dataTransfer.getData('text')||'|').split('|');usa(d,n);};
   $('f4st').innerHTML='<span class="falta">Escolha um arquivo.</span>';}},
 {tit:'Processe e veja o que o sistema lê',html:`
  <div class="mini">
   <div class="mini-cab">e-validador · Recibo_DCTFWeb_09-2026.pdf</div>
   <button class="btn primario" type="button" id="f5proc">Processar</button>
   <ul class="leitura" id="f5lista"></ul>
  </div>`,
  liga(fim){$('f5st').innerHTML='<span class="falta">Clique em Processar.</span>';$('f5proc').onclick=()=>{$('f5proc').disabled=true;const L=['CNPJ lido: 33.444.555/0001-81 (Clínica Sorriso Feliz)','Competência lida: 09/2026','Identificador encontrado: DCTFWeb','Tarefa aberta que casa: 1','Resultado: Baixada'];
   const ul=$('f5lista');ul.innerHTML='';let i=0;const passo=()=>{if(i<L.length){const li=document.createElement('li');li.textContent=L[i];if(i===L.length-1)li.className='fim';ul.appendChild(li);i++;setTimeout(passo,380);}else{$('f5st').innerHTML='<span class="feito">Tarefa concluída pelo documento.</span>';fim();}};passo();};}},
 {tit:'Veja como sairia uma guia',html:`
  <div class="mini">
   <p>A DCTFWeb não vai ao cliente. Se fosse uma guia de <b>entregar ao cliente</b>, como o DAS:</p>
   <button class="btn" type="button" id="f6ver">Mostrar o e-mail do DAS</button>
   <div id="f6mail"></div>
  </div>`,
  liga(fim){$('f6st').innerHTML='<span class="falta">Abra o exemplo de e-mail.</span>';$('f6ver').onclick=()=>{$('f6mail').innerHTML=`<div class="email"><div class="email-cab">Assunto: BPS4 | DAS, setembro/2026, Padaria Estrela Ltda</div><p>Olá! Segue a guia da competência setembro/2026, com vencimento em 20/10/2026.</p><span class="email-btn">Baixar a guia</span><p class="mini-dica">O mesmo texto vai por WhatsApp. Em Documentos aparece "Já baixou" quando o cliente abre o link.</p></div>`;
   $('f6st').innerHTML='<span class="feito">É assim que o cliente recebe.</span>';fim();};}},
 {tit:'Atualize o Painel',html:`
  <div class="mini">
   <div class="mini-cab">Painel · Fiscal · outubro/2026</div>
   <div class="kpis"><div><b id="f7ab">1</b><span>em aberto</span></div><div><b id="f7co">0</b><span>concluídas</span></div></div>
   <button class="btn primario" type="button" id="f7atu">Atualizar o Painel</button>
  </div>`,
  liga(fim){$('f7st').innerHTML='<span class="falta">Clique em Atualizar.</span>';$('f7atu').onclick=()=>{$('f7ab').textContent='0';$('f7co').textContent='1';$('f7st').innerHTML='<span class="feito">A DCTFWeb da Clínica saiu de "em aberto".</span>';fim();};}}
];
const trilha=document.getElementById('trilha'),painel=document.getElementById('painelEtapa');
const CHAVE='tareffas-manual-fluxo';
let atual=0,liberada=0,estado=ETAPAS.map(()=>({acao:false,resp:false}));
try{const s=JSON.parse(localStorage.getItem(CHAVE)||'null');if(s&&Array.isArray(s.estado)&&s.estado.length===ETAPAS.length){estado=s.estado;liberada=s.liberada|0;}}catch(e){}
const salvaLocal=()=>{try{localStorage.setItem(CHAVE,JSON.stringify({estado,liberada}));}catch(e){}};
const salva=()=>{salvaLocal();registra();};
const concluida=i=>estado[i].acao&&estado[i].resp;
ETAPAS.forEach((e,i)=>{const b=document.createElement('button');b.type='button';b.className='etapa';b.setAttribute('role','tab');b.id='et'+i;
 b.innerHTML='<span class="bola">'+(i+1)+'</span><span class="nome">'+e.n+'</span>';b.onclick=()=>{if(i<=liberada)mostra(i);};trilha.appendChild(b);});
function barra(){const feitas=estado.filter((s,i)=>concluida(i)).length;$('progresso').style.width=(100*feitas/ETAPAS.length)+'%';$('progTxt').textContent=feitas+' de '+ETAPAS.length+' etapas concluídas';
 [...trilha.children].forEach((b,j)=>{b.setAttribute('aria-selected',j===atual);b.classList.toggle('feita',concluida(j));b.disabled=j>liberada;b.tabIndex=j===atual?0:-1;
  b.title=j>liberada?'Conclua a etapa anterior para abrir esta':'';});
 const tudo=feitas===ETAPAS.length;$('fimFluxo').hidden=!tudo;$('prox').disabled=!concluida(atual)||atual===ETAPAS.length-1;$('ant').disabled=atual===0;
 $('posEtapa').textContent=concluida(atual)?(atual===ETAPAS.length-1?'Última etapa concluída':'Etapa concluída: pode seguir'):'Faça a ação e responda a pergunta para seguir';}
function mostra(i){atual=Math.max(0,Math.min(liberada,i));const e=ETAPAS[atual],f=FACA[atual],q=PERG[atual],st=estado[atual];
 painel.innerHTML='<div class="col-esq"><span class="rotulo">Etapa '+(atual+1)+' de '+ETAPAS.length+'</span><h3>'+e.t+'</h3><p class="quem">'+e.quem+'</p><ul class="lista">'+e.o.map(x=>'<li>'+x+'</li>').join('')+'</ul><div class="exemplo"><b>No exemplo.</b> '+e.ex+'</div></div>'+
  '<div class="col-dir"><div class="passo"><span class="rotulo">1 · Faça você</span><h4>'+f.tit+'</h4>'+f.html+'<p class="status" id="f'+(atual+1)+'st" aria-live="polite"></p></div>'+
  '<div class="passo'+(st.acao?'':' travado')+'" id="blocoPerg"><span class="rotulo">2 · Responda</span><h4>'+q.p+'</h4><div class="opcoes" role="radiogroup" aria-label="'+q.p.replace(/"/g,'')+'">'+
  q.r.map((r,k)=>'<button type="button" role="radio" aria-checked="false" class="opcao" data-k="'+k+'"'+(st.acao?'':' disabled')+'>'+r+'</button>').join('')+'</div><p class="status" id="respSt" aria-live="polite">'+(st.acao?(st.resp?'<span class="feito">'+q.ok+'</span>':''):'<span class="falta">Faça a ação acima para liberar a pergunta.</span>')+'</p></div></div>';
 if(st.resp){const b=painel.querySelector('.opcao[data-k="'+q.c+'"]');b.classList.add('certa');b.setAttribute('aria-checked','true');}
 const fim=()=>{if(!estado[atual].acao){estado[atual].acao=true;salva();const bp=$('blocoPerg');bp.classList.remove('travado');bp.querySelectorAll('.opcao').forEach(o=>o.disabled=false);if(!estado[atual].resp)$('respSt').innerHTML='';}barra();};
 f.liga(fim);
 if(st.acao){const el=$('f'+(atual+1)+'st');if(el)el.innerHTML='<span class="feito">Ação feita. Pode repetir para ver de novo.</span>';}
 painel.querySelectorAll('.opcao').forEach(o=>o.onclick=()=>{const k=+o.dataset.k;painel.querySelectorAll('.opcao').forEach(x=>{x.setAttribute('aria-checked',x===o);x.classList.remove('certa','errada');});
  if(k===q.c){o.classList.add('certa');estado[atual].resp=true;if(atual===liberada&&liberada<ETAPAS.length-1)liberada++;salva();$('respSt').innerHTML='<span class="feito">'+q.ok+'</span>';}
  else{o.classList.add('errada');estado[atual].erros=(estado[atual].erros||0)+1;salva();$('respSt').innerHTML='<span class="falta">'+q.nao+' Tente de novo.</span>';}
  barra();});
 barra();}
document.getElementById('ant').onclick=()=>mostra(atual-1);
document.getElementById('prox').onclick=()=>{if(concluida(atual))mostra(atual+1);document.getElementById('fluxo').scrollIntoView({block:'start'});};
document.getElementById('recomecar').onclick=()=>{estado=ETAPAS.map(()=>({acao:false,resp:false}));liberada=0;salva();mostra(0);document.getElementById('fluxo').scrollIntoView({block:'start'});};
trilha.addEventListener('keydown',ev=>{if(ev.key==='ArrowRight'&&atual<liberada){mostra(atual+1);trilha.children[atual].focus();}if(ev.key==='ArrowLeft'){mostra(atual-1);trilha.children[atual].focus();}});
mostra(Math.min(liberada,ETAPAS.length-1));
/* ---------- Registro de quem fez o fluxo ----------
   Cada pessoa grava só o próprio documento (conclusoes/<id>); o dono e os
   editores da página leem todos. Sem conta ou sem permissão, o fluxo funciona
   igual e só não registra. */
let reg={db:null,uid:null,ok:false,fila:Promise.resolve(),inicio:null,concluidoEm:null};
function corpoRegistro(){const feitas=estado.filter((s,i)=>concluida(i)).length;const agora=new Date().toISOString();
 if(!reg.inicio)reg.inicio=agora;if(feitas===ETAPAS.length&&!reg.concluidoEm)reg.concluidoEm=agora;
 return {etapas:feitas,total:ETAPAS.length,concluido:feitas===ETAPAS.length||!!reg.concluidoEm,erros:estado.reduce((t,s)=>t+(s.erros||0),0),
  inicio:reg.inicio,atualizado:agora,concluidoEm:reg.concluidoEm||null,liberada,estado:estado.map(s=>({acao:!!s.acao,resp:!!s.resp,erros:s.erros||0}))};}
function registra(){if(!reg.ok)return;const corpo=corpoRegistro();
 reg.fila=reg.fila.then(()=>reg.db.doc('conclusoes/'+reg.uid).set(corpo)).then(()=>{msgReg('Seu progresso fica registrado para o gestor.');})
  .catch(()=>{reg.ok=false;msgReg('Seu progresso não pôde ser registrado nesta página. Peça ao gestor acesso de Contribuidor.');});}
function msgReg(t){const el=$('regStatus');if(el)el.textContent=t;}
(async()=>{try{
 if(!window.claude||!window.claude.use){msgReg('');return;}
 const [db,user]=await Promise.all([window.claude.use('db'),window.claude.use('user')]);
 if(!db||!user){msgReg('Abra pelo link do Claude, com a sua conta, para registrar a conclusão.');return;}
 const uid=await user.id();
 if(!uid){msgReg('Entre com a sua conta do Claude para registrar a conclusão.');return;}
 reg.db=db;reg.uid=uid;reg.ok=true;
 const meu=await db.doc('conclusoes/'+uid).get();
 if(meu.exists){const d=meu.data();reg.inicio=d.inicio||null;reg.concluidoEm=d.concluidoEm||null;
  if(Array.isArray(d.estado)&&d.estado.length===ETAPAS.length&&(d.liberada|0)>liberada){estado=d.estado.map(s=>({acao:!!s.acao,resp:!!s.resp,erros:s.erros|0}));liberada=d.liberada|0;salvaLocal();mostra(liberada);}}
 if(estado.some(s=>s.acao||s.resp))registra();else msgReg('Seu progresso vai ficar registrado para o gestor.');
 if(await user.canEdit())montaQuadro(db,user);
}catch(e){msgReg('');}})();

function montaQuadro(db,user){const q=$('painelQuem');q.hidden=false;
 db.collection('conclusoes').onSnapshot(async snap=>{
  const docs=snap.docs.filter(d=>d.exists).map(d=>({id:d.id,...d.data()}));
  const ps=await user.profiles(docs.map(d=>d.id));
  docs.sort((a,b)=>(b.concluido-a.concluido)||((b.etapas|0)-(a.etapas|0)));
  const fim=docs.filter(d=>d.concluido).length;
  $('quemResumo').textContent=docs.length?(fim+' de '+docs.length+(docs.length===1?' pessoa concluiu':' pessoas concluíram')+' o fluxo'):'Ninguém começou o fluxo ainda.';
  const tb=$('quemLinhas');tb.innerHTML='';
  const dt=s=>s?new Date(s).toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}):'';
  docs.forEach(d=>{const tr=document.createElement('tr');const p=ps[d.id]||{};
   const nome=document.createElement('td');nome.textContent=(p.name||'Pessoa sem nome visível')+(p.isMe?' (você)':'');
   const prog=document.createElement('td');prog.textContent=(d.etapas|0)+' de '+(d.total||ETAPAS.length);
   const sit=document.createElement('td');sit.innerHTML=d.concluido?'<span class="feito">Concluiu</span>':'<span class="falta">Em andamento</span>';
   const quando=document.createElement('td');quando.textContent=d.concluido?dt(d.concluidoEm):('última vez '+dt(d.atualizado));
   const err=document.createElement('td');err.textContent=String(d.erros|0);
   [nome,prog,sit,quando,err].forEach(c=>tr.appendChild(c));tb.appendChild(tr);});
 },()=>{$('quemResumo').textContent='Não consegui ler o registro agora. Recarregue a página.';});}



/* ---------- Passeio ---------- */
(function(){
const P=[
 {r:'Cadastro',t:'Aqui nasce a regra',x:'A Clínica conta quem é: Lucro Presumido, fecha dia 20, Fiscal com o Rafael. A DCTFWeb conta quando vence: no último dia útil, com a equipe trabalhando 7 dias antes.',
  c:'<div class="c-ficha"><b>Clínica Sorriso Feliz</b><i class="ok"></i><i class="ok" style="animation-delay:.3s"></i><i class="ok" style="animation-delay:.6s"></i></div>'},
 {r:'Geração',t:'Um clique e as tarefas nascem',x:'Todo mês o gestor clica em "Gerar tarefas do mês". Cada empresa ganha a sua tarefa, já com dono, prazo interno e vencimento.',
  c:'<div class="c-cartoes"><span></span><span></span><span></span><span></span></div>'},
 {r:'Mesa da equipe',t:'A cor avisa a hora',x:'O cartão fica verde com folga, amarelo na semana do prazo interno e vermelho quando passou. O Rafael marca "Em andamento" e trabalha.',
  c:'<div class="c-cor">DCTFWeb</div>'},
 {r:'e-validador',t:'O recibo entra no sistema',x:'Transmitida a declaração, o Rafael solta o recibo no e-validador. O sistema lê o CNPJ, a competência e o tipo do documento.',
  c:'<div class="c-doc"></div><div class="c-caixa"></div>'},
 {r:'Baixa',t:'Concluída, sem ninguém clicar',x:'O recibo casa com a tarefa certa e ela se conclui sozinha. Recibo de outra empresa ou de outro mês não baixa nada por engano.',
  c:'<div class="c-check"></div>'},
 {r:'Cliente',t:'A guia chega com um link',x:'Quando é guia, como o DAS, ela sai por e-mail e WhatsApp. Cada cliente tem o próprio link, e você vê quem já baixou.',
  c:'<div class="c-env"></div>'},
 {r:'Painel',t:'O gestor vê tudo de uma vez',x:'No Painel aparecem as tarefas em aberto, as atrasadas e as concluídas, por setor, pessoa e empresa. A DCTFWeb da Clínica já está nas concluídas.',
  c:'<div class="c-barras"><span></span><span></span><span></span><span></span></div>'}
];
const svg=document.getElementById('mapaSvg'),estrada=document.getElementById('estrada'),feita=document.getElementById('estradaFeita'),token=document.getElementById('token'),g=document.getElementById('paradas');
const L=estrada.getTotalLength(),frac=P.map((_,i)=>i/(P.length-1)),comp=frac.map(f=>f*L);
const reduz=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
feita.style.strokeDasharray=L;feita.style.strokeDashoffset=L;
P.forEach((p,i)=>{const pt=estrada.getPointAtLength(comp[i]);const ns='http://www.w3.org/2000/svg';const gg=document.createElementNS(ns,'g');gg.setAttribute('class','parada');
 const c=document.createElementNS(ns,'circle');c.setAttribute('cx',pt.x);c.setAttribute('cy',pt.y);c.setAttribute('r',22);
 const n=document.createElementNS(ns,'text');n.setAttribute('class','n');n.setAttribute('x',pt.x);n.setAttribute('y',pt.y);n.textContent=i+1;
 const r=document.createElementNS(ns,'text');r.setAttribute('class','r');r.setAttribute('x',pt.x);r.setAttribute('y',pt.y<170?pt.y-38:pt.y+50);r.textContent=p.r;
 gg.append(c,n,r);g.appendChild(gg);});
let pos=-1,emCurso=false,auto=false,timer=null,lenAtual=0;
function poeToken(len){const pt=estrada.getPointAtLength(len);token.setAttribute('transform','translate('+pt.x+' '+(pt.y-42)+')');feita.style.strokeDashoffset=L-len;}
poeToken(0);token.style.opacity=.35;
function anda(ate,fim){if(reduz){lenAtual=ate;poeToken(ate);fim();return;}
 const de=lenAtual,t0=performance.now(),dur=900;emCurso=true;
 let feito=false;const acaba=()=>{if(feito)return;feito=true;lenAtual=ate;poeToken(ate);emCurso=false;fim();};
 const passo=t=>{if(feito)return;const k=Math.min(1,(t-t0)/dur),e=k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2;lenAtual=de+(ate-de)*e;poeToken(lenAtual);if(k<1)requestAnimationFrame(passo);else acaba();};requestAnimationFrame(passo);
 setTimeout(acaba,dur+400);}
function mostraParada(i){[...g.children].forEach((gg,j)=>{gg.classList.toggle('viva',j<=i);gg.classList.toggle('agora',j===i);});
 const p=P[i];document.getElementById('pParada').textContent='Parada '+(i+1)+' de '+P.length+' · '+p.r;document.getElementById('pTitulo').textContent=p.t;document.getElementById('pTexto').textContent=p.x;
 const cena=document.getElementById('cena');cena.innerHTML=p.c;
 const fim=i===P.length-1;const av=document.getElementById('pAvanca');av.textContent=fim?'Chegou':'Próxima parada';av.disabled=fim;
 document.getElementById('pReinicia').hidden=!fim;document.getElementById('pIrFluxo').hidden=!fim;
 if(fim){pararAuto();festa(cena);document.getElementById('pTexto').textContent=p.x+' Fim da viagem: agora faça cada passo no fluxo guiado.';}
 else if(auto){timer=setTimeout(avanca,3800);}}
function avanca(){if(emCurso||pos>=P.length-1)return;clearTimeout(timer);pos++;token.style.opacity=1;anda(comp[pos],()=>mostraParada(pos));}
function pararAuto(){auto=false;clearTimeout(timer);const b=document.getElementById('pAuto');b.setAttribute('aria-pressed','false');b.textContent='Automático';}
function festa(el){if(reduz)return;const cores=['var(--oliva)','var(--ouro)','var(--verde)','var(--azul)','var(--verm)'];
 for(let k=0;k<26;k++){const s=document.createElement('span');s.className='confete';s.style.left='50%';s.style.top='50%';s.style.background=cores[k%cores.length];
  s.style.setProperty('--dx',(Math.random()*240-120)+'px');s.style.setProperty('--dy',(Math.random()*-140+20)+'px');s.style.animationDelay=(Math.random()*.2)+'s';el.appendChild(s);}}
document.getElementById('pAvanca').onclick=avanca;
document.getElementById('pAuto').onclick=e=>{if(auto){pararAuto();return;}auto=true;e.currentTarget.setAttribute('aria-pressed','true');e.currentTarget.textContent='Pausar';if(pos>=P.length-1){reinicia();}avanca();};
function reinicia(){clearTimeout(timer);pos=-1;lenAtual=0;poeToken(0);token.style.opacity=.35;[...g.children].forEach(gg=>gg.classList.remove('viva','agora'));
 document.getElementById('pParada').textContent='Antes de começar';document.getElementById('pTitulo').textContent='Uma tarefa, sete paradas';
 document.getElementById('pTexto').textContent='Aperte "Próxima parada" ou deixe no automático.';document.getElementById('cena').innerHTML='<span class="c-largada">Largada</span>';
 const av=document.getElementById('pAvanca');av.disabled=false;av.textContent='Começar o passeio';document.getElementById('pReinicia').hidden=true;document.getElementById('pIrFluxo').hidden=true;}
document.getElementById('pReinicia').onclick=()=>{pararAuto();reinicia();};
document.getElementById('cena').innerHTML='<span class="c-largada">Largada</span>';
})();

/* ---------- Simulador de datas ---------- */
const MESES=['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'];
const SEM=['domingo','segunda','terça','quarta','quinta','sexta','sábado'];
const selMes=document.getElementById('mes');MESES.forEach((m,i)=>{const o=document.createElement('option');o.value=i+1;o.textContent=m;selMes.appendChild(o);});selMes.value=10;
let origem='legal';
const seg=$('origemSeg');
[['fechamento','Fechamento do cliente'],['legal','Prazo legal']].forEach(([v,t])=>{const b=document.createElement('button');b.type='button';b.setAttribute('role','radio');b.dataset.v=v;b.textContent=t;b.onclick=()=>{origem=v;calcula();};seg.appendChild(b);});
const D=(a,m,d)=>new Date(Date.UTC(a,m-1,d));
const add=(d,n)=>new Date(d.getTime()+n*86400000);
const util=(d)=>{const w=d.getUTCDay();return (w>=1&&w<=5)||(w===6&&$('sab').checked);};
const ant=(d)=>{while(!util(d))d=add(d,-1);return d;};
const pos=(d)=>{while(!util(d))d=add(d,1);return d;};
const ultimoDia=(a,m)=>new Date(Date.UTC(a,m,0)).getUTCDate();
function prazo(a,m,tipo,dia,ajuste){
 if(tipo==='ultimo')return ant(D(a,m,ultimoDia(a,m)));
 if(tipo==='primeiro')return pos(D(a,m,1));
 if(tipo==='dia_util'){let n=Math.max(1,dia||1),d=D(a,m,1),c=0;for(let i=0;i<62;i++){if(util(d)){c++;if(c===n)return d;}d=add(d,1);}return d;}
 const d=D(a,m,Math.min(Math.max(1,dia||1),ultimoDia(a,m)));
 if(util(d)||ajuste==='nenhum')return d;return ajuste==='postergar'?pos(d):ant(d);}
function recua(d,n,tipo){n=Math.max(0,n|0);if(n===0)return ant(d);
 if(tipo==='uteis'){let x=d,c=0;for(let i=0;i<400;i++){x=add(x,-1);if(util(x)){c++;if(c>=n)return x;}}return x;}
 return ant(add(d,-n));}
const fmt=d=>String(d.getUTCDate()).padStart(2,'0')+'/'+String(d.getUTCMonth()+1).padStart(2,'0')+'/'+d.getUTCFullYear()+' ('+SEM[d.getUTCDay()]+')';
function calcula(){
 [...seg.children].forEach(b=>b.setAttribute('aria-checked',b.dataset.v===origem));
 $('blocoFech').hidden=origem!=='fechamento';$('blocoLegal').hidden=origem!=='legal';
 $('campoLDia').hidden=!['dia_fixo','dia_util'].includes($('lRegra').value);
 $('lDia').previousElementSibling.textContent=$('lRegra').value==='dia_util'?'Qual dia útil':'Dia do mês';
 const a=+$('ano').value,m=+$('mes').value;let fech=null,venc;
 if(origem==='fechamento'){fech=prazo(a,m,'dia_fixo',+$('fDia').value,'antecipar');venc=recua(fech,+$('fN').value,$('fTipo').value);if(+$('fN').value===0)venc=fech;}
 else venc=prazo(a,m,$('lRegra').value,+$('lDia').value,$('lAjuste').value);
 let int=recua(venc,+$('iN').value,$('iTipo').value);let lim=false;if(int>venc){int=venc;lim=true;}
 $('resultado').innerHTML='Tarefas de '+MESES[m-1]+'/'+a+':<br>vencimento '+fmt(venc)+'<br>prazo interno '+fmt(int)+
  '<small>'+(fech?'Fechamento do cliente em '+fmt(fech)+'. ':'')+(lim?'O prazo interno ficou no vencimento.':'')+'</small>';
 const cal=$('cal');cal.innerHTML='';['dom','seg','ter','qua','qui','sex','sáb'].forEach(x=>{const c=document.createElement('div');c.className='cab';c.textContent=x;cal.appendChild(c);});
 const primeiro=D(a,m,1).getUTCDay();for(let i=0;i<primeiro;i++){const c=document.createElement('div');c.className='d vazio';cal.appendChild(c);}
 const mesmo=(x,y)=>x&&y&&x.getTime()===y.getTime();
 for(let d=1;d<=ultimoDia(a,m);d++){const dt=D(a,m,d),c=document.createElement('div');c.className='d';c.textContent=d;
  if(!util(dt))c.classList.add('fds');if(mesmo(dt,fech))c.classList.add('fech');if(mesmo(dt,venc))c.classList.add('venc');if(mesmo(dt,int))c.classList.add('int');
  const nomes=[];if(mesmo(dt,venc))nomes.push('vencimento');if(mesmo(dt,int))nomes.push('prazo interno');if(mesmo(dt,fech))nomes.push('fechamento');if(nomes.length)c.setAttribute('aria-label',d+': '+nomes.join(', '));
  cal.appendChild(c);}
}
const PRESETS=[
 ['DCTFWeb',{o:'legal',r:'ultimo',iN:7,iT:'corridos',m:10}],
 ['SPED Fiscal',{o:'legal',r:'dia_fixo',d:15,aj:'antecipar',iN:7,iT:'corridos',m:10}],
 ['EFD-Contribuições',{o:'legal',r:'dia_util',d:10,iN:7,iT:'corridos',m:10}],
 ['Conciliação (fecha 20)',{o:'fechamento',fd:20,fN:0,iN:3,iT:'corridos',m:10}],
 ['Simples (fecha 25)',{o:'fechamento',fd:25,fN:0,iN:3,iT:'corridos',m:10}],
 ['ECD',{o:'legal',r:'dia_fixo',d:30,aj:'antecipar',iN:45,iT:'corridos',m:6,a:2027}]];
PRESETS.forEach(([t,p])=>{const b=document.createElement('button');b.type='button';b.className='btn';b.textContent=t;b.onclick=()=>{origem=p.o;
 if(p.r){$('lRegra').value=p.r;}if(p.d)$('lDia').value=p.d;if(p.aj)$('lAjuste').value=p.aj;if(p.fd)$('fDia').value=p.fd;if(p.fN!==undefined)$('fN').value=p.fN;
 $('iN').value=p.iN;$('iTipo').value=p.iT;$('mes').value=p.m;$('ano').value=p.a||2026;calcula();};$('presets').appendChild(b);});
['fDia','fN','fTipo','lRegra','lDia','lAjuste','iN','iTipo','mes','ano','sab'].forEach(id=>{$(id).addEventListener('input',calcula);$(id).addEventListener('change',calcula);});
calcula();

/* ---------- Cadastros ---------- */
const CAD={
 empresas:{t:'Empresas',img:'img/empresa-form.webp',alt:'Formulário de cadastro da empresa com regime, segmento, fechamento contábil e responsável por setor',
  serve:'A ficha de cada cliente. É dela que o sistema tira quais obrigações a empresa recebe, quando vencem as etapas do fechamento e quem cuida de cada setor.',
  campos:[['CNPJ','O e-validador acha a empresa por ele. <em>Errado, o recibo cai em "Sem tarefa".</em>'],
   ['Regime tributário e segmento','Decidem quais obrigações a empresa recebe. <em>Segmento em branco tira a empresa de toda obrigação filtrada por segmento.</em>'],
   ['Fechamento contábil','Dia em que a empresa fecha o mês: 20 no Real e Presumido, 25 no Simples, 13 nas exceções. <em>Preencha sempre: em branco, as etapas caem numa data de reserva.</em>'],
   ['Responsável por setor','Marque só os setores contratados. <em>Setor desmarcado não gera tarefa e cancela as abertas como "não se aplica".</em> O primeiro nome é o responsável.'],
   ['E-mail e telefone','Para onde vai a guia. <em>Sem eles, o e-validador avisa "Sem destinatário".</em>'],
   ['Situação e cadeado','Inativa para quem saiu. O cadeado bloqueia: as tarefas somem das listas e a geração ignora a empresa.']],
  ex:'Padaria Estrela (fictícia): Simples, comércio, fechamento dia 25, Contabilidade e Fiscal marcados, DP desmarcado porque a folha é feita por outro escritório.',
  cuidado:'Muitas de uma vez: Baixar modelo e Importar Excel. Os responsáveis também entram por planilha (Modelo resp. e Importar resp.).'},
 obrigacoes:{t:'Obrigações',img:'img/obrig-legal.webp',alt:'Seção de prazo da obrigação DCTFWeb com periodicidade, prazo interno e prazo legal',
  serve:'O modelo do que se entrega. Cada obrigação vira, todo mês, uma tarefa para cada empresa que ela alcança.',
  campos:[['Nome e mininome','O mininome é o nome que o cliente lê no e-mail: "DAS", "DARF IRPJ". <em>Sem ele, o cliente recebe o nome técnico.</em>'],
   ['Setor e supervisor padrão','Setor é obrigatório: decide quem responde pela matriz da empresa.'],
   ['Identificadores','Trecho único que só aparece naquele comprovante, como "Escrituração Contábil Digital". <em>É o que liga o recibo à obrigação.</em>'],
   ['Quando acontece','Mensal, trimestral, anual ou personalizada, e a competência (mês anterior, 2 meses antes, janeiro do ano anterior).'],
   ['Fechamento do cliente ou prazo legal','Etapa do fechamento vence no fechamento de cada empresa. Prazo legal vence na data da lei. <em>Um ou outro.</em>'],
   ['Prazo interno da equipe','N dias antes do vencimento, antes do fechamento, ou uma regra própria (1º dia útil, dia fixo).'],
   ['Para que lado vai o documento','Receber do cliente, entregar ao cliente, transmitir ao órgão ou tarefa interna. <em>Decide como a tarefa dá baixa.</em>'],
   ['Quem recebe','Regra de regime e segmento, ou só as vinculadas. Exceção tira uma empresa com motivo.']],
  ex:'DCTFWeb: Fiscal, mensal, competência do mês anterior, prazo legal no último dia útil, interno 7 dias corridos antes, transmitir ao órgão, Real e Presumido.',
  cuidado:'Antes de salvar, leia a linha "Tarefas de...": ela mostra as datas que vão nascer. Se não bater, a regra está errada. Excluir obrigação apaga as tarefas geradas e é só para admin e gestor: para parar de gerar, use Inativar.'},
 setores:{t:'Setores',img:'img/empresa-setores.webp',alt:'Matriz de responsáveis por setor no cadastro da empresa',
  serve:'As áreas da BPS4: Contabilidade, Fiscal, Departamento Pessoal, Financeiro e Cliente. Cada obrigação pertence a um setor, e cada empresa diz quais setores contratou.',
  campos:[['Nome','Como o setor aparece nos filtros, no Painel e na matriz da empresa.'],
   ['Gestor do setor','Vira supervisor da tarefa quando o responsável não tem gestor próprio.'],
   ['Na empresa','A matriz empresa × setor diz quem cuida. <em>Setor desmarcado = a empresa não contratou, e nada daquele setor nasce para ela.</em>']],
  ex:'Um grupo que não contratou a Contabilidade da BPS4 fica com o setor desmarcado nas suas empresas, e nenhuma etapa contábil nem a ECD nasce para elas.',
  cuidado:'O print ao lado é a matriz dentro do cadastro da empresa: é ali que o setor faz diferença no dia a dia.'},
 usuarios:{t:'Usuários e grupos',img:null,
  serve:'Quem entra no sistema e o que cada um pode fazer. O grupo define a permissão; o admin pode ajustar pessoa a pessoa.',
  campos:[['Grupo','Admin, gestor, analista, estagiário ou consulta. Veja a tabela abaixo.'],
   ['Gestor da pessoa','Vira o supervisor das tarefas dela.'],
   ['Tipo','Colaborador ou cliente. <em>Cliente vê só a própria empresa, sem editar.</em>'],
   ['Convite','O avião de papel manda o link de primeiro acesso. Para quem já ativou, o mesmo botão reenvia o link para definir uma senha nova.'],
   ['Bloquear','A pessoa não entra. As tarefas dela somem da tela só quando todos os responsáveis estão bloqueados.']],
  ex:'Rafael Souza: analista, gestora Luciana Peres, colaborador. Recebe o convite por e-mail e define a própria senha.',
  cuidado:'O sistema confere a permissão no servidor: esconder o botão é só conforto. Se uma ação não aparece para alguém, é o perfil.',
  extra:'<div class="rolar"><table class="perm"><tr><th>Pode</th><th>Admin</th><th>Gestor</th><th>Analista</th><th>Estagiário</th><th>Consulta</th></tr>'+
   [['Tarefas que enxerga','Todas','Todas','Próprias','Próprias','Todas'],['Editar, anexar e enviar ao cliente','s','s','s','s','n'],['Copiar link de envio','s','s','s','s','n'],['Alterar o prazo interno','s','s','s','n','n'],['Alterar o vencimento legal','s','s','n','n','n'],['Cancelar ou dispensar tarefa','s','s','n','n','n'],['Excluir obrigação','s','s','n','n','n'],['Cadastrar usuários','s','n','n','n','n']]
   .map(l=>'<tr>'+l.map((c,i)=>i===0?'<td>'+c+'</td>':'<td class="'+(c==='n'?'sim-nao':'sim-sim')+'">'+(c==='s'?'Sim':c==='n'?'Não':c)+'</td>').join('')+'</tr>').join('')+'</table></div>'},
 modelos:{t:'Modelos de documento',img:'img/modelos.webp',alt:'Tela de Modelos com a área para soltar arquivos e o repositório',
  serve:'Ensinam o e-validador a reconhecer cada recibo e guia. Você sobe um documento real de exemplo e confirma a qual obrigação ele pertence.',
  campos:[['Documento de exemplo','PDF, XLSX ou XLS, um ou vários de uma vez.'],
   ['Sugestão','O sistema sugere empresa (pelo CNPJ), tipo e obrigação. <em>Confira antes de salvar.</em>'],
   ['Identificador','Ao salvar, o trecho que identifica o documento passa a ligar os próximos à mesma obrigação.']],
  ex:'O recibo da ECD traz "Recibo de entrega de Escrituração Contábil Digital". Esse trecho é o identificador que liga todo recibo de ECD à obrigação ECD.',
  cuidado:'Use quando o e-validador disser "Sem tarefa" ou "Ambíguo" para um documento que deveria reconhecer.'},
 substituicoes:{t:'Substituições',img:'img/substituicoes.webp',alt:'Tela de Substituições com uma substituição temporária por férias',
  serve:'Troca o responsável das tarefas quando alguém sai. Temporária para férias e afastamento, definitiva para quem muda de função.',
  campos:[['Ausente e substituto','De quem saem as tarefas e para quem vão.'],
   ['Tipo e período','Temporária, com início e fim, ou definitiva.'],
   ['Motivo','Férias, afastamento, desligamento. Fica registrado.']],
  ex:'Rafael Souza de férias de 05/10 a 16/10: Bruno Lima cobre as tarefas dele no período.',
  cuidado:'Avise o gestor antes das férias: é ele quem cadastra a substituição.'},
 notificacoes:{t:'Notificações',img:null,
  serve:'Configura os avisos automáticos: e-mail (SMTP) e WhatsApp, os horários de envio e as regras de alerta de vencimento. Só o admin mexe.',
  campos:[['E-mail e WhatsApp','Contas usadas para mandar convites, guias e alertas. As senhas aparecem mascaradas.'],
   ['Horários e regras','Quando os alertas saem e para quem.']],
  ex:'O convite de acesso e a guia ao cliente saem pelas contas configuradas aqui.',
  cuidado:'Se e-mail ou WhatsApp pararem de sair, comece por esta tela.'}
};
const abas=$('abas'),pc=$('painelCad');let abaAtual='empresas';
Object.entries(CAD).forEach(([k,c])=>{const b=document.createElement('button');b.type='button';b.setAttribute('role','tab');b.dataset.k=k;b.textContent=c.t;b.onclick=()=>abre(k);abas.appendChild(b);});
function abre(k){abaAtual=k;const c=CAD[k];[...abas.children].forEach(b=>b.setAttribute('aria-selected',b.dataset.k===k));
 pc.innerHTML='<div class="cad"><div class="col"><p class="lead" style="font-size:1rem">'+c.serve+'</p><dl class="campos">'+c.campos.map(([a,b])=>'<div><dt>'+a+'</dt><dd>'+b+'</dd></div>').join('')+'</dl>'+(c.extra||'')+'</div>'+
 '<div class="col">'+(c.img?'<figure><img src="'+c.img+'" alt="'+c.alt+'" loading="lazy"><figcaption>Clique para ampliar. Dados fictícios.</figcaption></figure>':'')+
 '<div class="exemplo"><b>Exemplo.</b> '+c.ex+'</div><div class="nota">'+c.cuidado+'</div></div></div>';
 ligaZoom();}
abre('empresas');
document.querySelectorAll('[data-aba]').forEach(a=>a.addEventListener('click',()=>abre(a.dataset.aba)));
document.querySelectorAll('[data-etapa]').forEach(a=>a.addEventListener('click',()=>mostra(+a.dataset.etapa)));

/* ---------- Glossário ---------- */
const G=[['Obrigação','O modelo de algo que se entrega todo período: DCTFWeb, DAS, conciliação bancária.'],['Tarefa','Uma obrigação de uma empresa num mês. É o que a equipe executa.'],
 ['Competência','O mês a que a tarefa se refere (MM/AAAA). Normalmente o mês anterior ao da entrega. É por ela que o e-validador casa o recibo.'],
 ['Mês de entrega','O mês em que a tarefa nasce e é entregue. "Tarefas de outubro" têm, em geral, competência de setembro.'],
 ['Vencimento','A data que gera multa. Vem da lei (prazo legal) ou do fechamento do cliente.'],['Prazo interno','A data da equipe, antes do vencimento. Comanda a cor e os alertas.'],
 ['Fechamento do cliente','O dia em que a empresa fecha o mês contábil: 13, 20 ou 25. As etapas do fechamento vencem por ele.'],
 ['Etapa do fechamento','Obrigação que é parte do processo contábil (conciliar, lançar, balancete) e vence no fechamento de cada empresa.'],
 ['Prazo legal','Data em lei, igual para todas as empresas. Fiscal, ECD e ECF.'],['Sentido do documento','Receber do cliente, entregar ao cliente, transmitir ao órgão ou tarefa interna. Decide como a tarefa dá baixa.'],
 ['Mininome','Nome curto e legível da obrigação, usado no e-mail ao cliente.'],['Identificador','Trecho único de um comprovante que liga o documento à obrigação certa.'],
 ['e-validador','A tela que lê os documentos e dá baixa nas tarefas.'],['Matriz empresa × setor','Quais setores a empresa contratou e quem cuida de cada um.'],
 ['Não se aplica','Dispensa da tarefa naquele mês, sempre com motivo.'],['Vínculo','Empresa incluída à mão numa obrigação, mesmo fora da regra.'],
 ['Exceção','Empresa tirada de uma obrigação, com motivo e autor registrados.'],['Substituição','Troca temporária ou definitiva do responsável pelas tarefas.'],
 ['Supervisor','Quem acompanha a tarefa: gestor do responsável, gestor do setor ou o supervisor da obrigação.'],['Gerar tarefas do mês','Botão em Obrigações que cria as tarefas de todas as empresas alcançadas.']];
const gl=$('gloss');function desenhaG(q){q=(q||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();gl.innerHTML='';let n=0;
 G.forEach(([t,d])=>{const s=(t+' '+d).normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();if(q&&!s.includes(q))return;n++;
  const c=document.createElement('div');c.className='cartao';c.innerHTML='<h4>'+t+'</h4><p>'+d+'</p>';gl.appendChild(c);});$('semTermo').hidden=n>0;}
$('busca').addEventListener('input',e=>desenhaG(e.target.value));desenhaG('');

/* ---------- Ampliar print ---------- */
const zoom=$('zoom'),zi=$('zoomImg');
function ligaZoom(){document.querySelectorAll('figure img').forEach(im=>{if(im.dataset.z)return;im.dataset.z=1;im.tabIndex=0;
 const abrir=()=>{zi.src=im.src;zi.alt=im.alt;if(zoom.showModal)zoom.showModal();};im.addEventListener('click',abrir);im.addEventListener('keydown',e=>{if(e.key==='Enter')abrir();});});}
$('zoomFechar').onclick=()=>zoom.close();zoom.addEventListener('click',e=>{if(e.target===zoom)zoom.close();});ligaZoom();

/* ---------- Índice ativo ---------- */
const links=[...document.querySelectorAll('nav.indice a')];
const obs=new IntersectionObserver(es=>{es.forEach(en=>{if(en.isIntersecting){links.forEach(l=>l.classList.toggle('ativo',l.getAttribute('href')==='#'+en.target.id));}});},{rootMargin:'-40% 0px -55% 0px'});
document.querySelectorAll('main>section').forEach(s=>obs.observe(s));
})();
