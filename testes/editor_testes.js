// Testes da interface do editor, rodados dentro da janela do app pelo cdp.py.
// Funciona com o motor do Windows (servidor) e com o do celular/site (abrir com ?motor=js).
// Devolve JSON {modo, falhas, log}. Apaga no fim o que gravou no aparelho (textos e carimbos salvos).
(async()=>{
const sl=ms=>new Promise(r=>setTimeout(r,ms));const log=[];let falhas=0;
const ok=(c,m)=>{log.push((c?'OK      ':'FALHOU  ')+m);if(!c)falhas++};
const dec=b=>Uint8Array.from(atob(b),c=>c.charCodeAt(0));
for(let t=0;t<80&&!(S.srv||MOTOR);t++)await sl(250);await sl(800);
const modo=MOTOR?'motor do celular/site':'servidor do Windows';
ok(S.srv,'motor carregado ('+modo+')');
if(!MOTOR)ok(S.docx===true&&S.ocr===true,'Windows: Word e OCR disponíveis (conferidos sem atrasar a abertura)');
// salvar não abre janela: guarda o que seria salvo
window.confirm=()=>true; // "perder alterações?" não trava o teste
let salvo=null;download=(by)=>{salvo=by instanceof Uint8Array?by:new Uint8Array(by);return 'baixado'};

// 1) PDF com senha
try{
  const p=openFile(new File([dec('__SENHA_B64__')],'contrato.pdf',{type:'application/pdf'}));
  for(let t=0;t<20&&!document.querySelector('#senhaAbrir');t++)await sl(200);
  ok(!!document.querySelector('#senhaAbrir'),'PDF com senha: pede a senha');
  document.querySelector('#senhaAbrir').value='errada';document.querySelector('.modal [data-ok]').click();
  for(let t=0;t<30&&!(document.querySelector('.modal')||{innerText:''}).innerText.includes('Senha incorreta');t++)await sl(200);
  ok((document.querySelector('.modal')||{innerText:''}).innerText.includes('Senha incorreta'),'PDF com senha: avisa senha errada');
  document.querySelector('#senhaAbrir').value='abc123';document.querySelector('.modal [data-ok]').click();await p;await sl(500);
  const tx=await (await S.doc.getPage(1)).getTextContent();
  ok(tx.items.map(i=>i.str).join('').includes('Contrato secreto'),'PDF com senha: abre com a senha certa');
  await save();await sl(1000);
  let protegido=false;try{await pdfjsLib.getDocument({data:salvo.slice()}).promise}catch(e){protegido=e.name==='PasswordException'}
  ok(protegido,'PDF com senha: salva ainda protegido');
}catch(e){ok(false,'PDF com senha: '+e.message)}

// 2) PDF escaneado: oferta de OCR e edição
try{
  await openFile(new File([dec('__ESCANEADO_B64__')],'recibo.pdf',{type:'application/pdf'}));await sl(500);
  setTool('edittext');for(let t=0;t<30&&!document.querySelector('.modal');t++)await sl(200);
  const m=document.querySelector('.modal');ok(!!m&&m.innerText.includes('escaneada'),'escaneado: oferece reconhecer o texto');
  if(m)m.querySelector('[data-ok]').click();
  for(let t=0;t<240&&(S.busy||!document.querySelector('.tl'));t++)await sl(500);
  const bl=await getBlocks(0)||[];ok(bl.length>=2&&bl.every(b=>b.ocr),'escaneado: texto reconhecido vira blocos editáveis ('+bl.length+')');
  await startReplaceBlock(0,0);await sl(300);const o=S.objs[S.objs.length-1];o.text=o.text.replace('4521','7777');o.edited=true;
  const out=await bake(S.bytes,S.objs);const d=await pdfjsLib.getDocument({data:out}).promise;
  const tt=(await (await d.getPage(1)).getTextContent()).items.map(i=>i.str).join(' ');
  ok(tt.includes('7777')&&!tt.includes('4521'),'escaneado: troca o texto ao salvar');
  S.objs=[];setTool('select');
}catch(e){ok(false,'escaneado: '+e.message)}

// 2b) "Editar texto" num PDF de 60 páginas só analisa as páginas perto da tela (antes analisava todas)
try{
  const pdg=await PDFDocument.create();const fo=await pdg.embedFont(StandardFonts.Helvetica);
  for(let i=0;i<60;i++)pdg.addPage([595,842]).drawText('Pagina '+(i+1)+' texto para editar',{x:72,y:760,size:14,font:fo});
  await openFile(new File([await pdg.save()],'paginas.pdf',{type:'application/pdf'}));await sl(500);
  setTool('edittext');await sl(1500);
  const pedidas=S.pages.filter(p=>p.blocksP).length;ok(pedidas>0&&pedidas<20,'Editar texto analisa só as páginas perto da tela ('+pedidas+' de 60)');
  const v=document.querySelector('#view');v.scrollTop=v.scrollHeight;for(let t=0;t<40&&!S.pages[59].blocksP;t++)await sl(100);
  for(let t=0;t<40&&!$('.tl',S.pages[59].el);t++)await sl(100);
  ok(!!$('.tl',S.pages[59].el),'ao rolar até o fim, a última página ganha as caixas de texto');
  v.scrollTop=0;setTool('select');
}catch(e){ok(false,'páginas perto da tela: '+e.message)}

// 3) textos e carimbos salvos, seleção múltipla
try{
  const pd=await PDFDocument.create();const pg=pd.addPage([595,842]);pg.drawText('Documento de teste',{x:72,y:770,size:18,font:await pd.embedFont(StandardFonts.Helvetica)});
  await openFile(new File([await pd.save()],'teste.pdf',{type:'application/pdf'}));await sl(500);
  const guardT=localStorage.getItem('editorpdf-textos'),guardC=localStorage.getItem('editorpdf-carimbos');
  localStorage.removeItem('editorpdf-textos');localStorage.removeItem('editorpdf-carimbos');
  setTool('text');await sl(200);document.querySelector('#tsNovo').value='Recebido em {data}';document.querySelector('#tsAdd').click();await sl(200);
  document.querySelector('[data-ts="0"]').click();await sl(200);
  const tx=S.objs.find(o=>o.type==='text');ok(tx&&tx.text==='Recebido em '+new Date().toLocaleDateString('pt-BR'),'texto salvo entra com a data do dia');
  setTool('stamp');for(let t=0;t<30&&!document.querySelector('.modal #stTxt');t++)await sl(100);let m=document.querySelector('.modal');m.querySelector('input[value=x]').checked=true;m.querySelector('#stTxt').value='LANÇADO NO SAP';m.querySelector('[data-ok]').click();await sl(500);
  setTool('stamp');for(let t=0;t<30&&!document.querySelector('.modal #stTxt');t++)await sl(100);m=document.querySelector('.modal');ok(m.innerText.includes('LANÇADO NO SAP'),'carimbo "Outro" fica salvo para a próxima vez');
  m.querySelector('[data-x]').click();await sl(200);
  setTool('select');S.objs.push({id:uid(),page:0,type:'rect',x:300,y:400,w:80,h:40,color:'#e53935',sw:2});renderLayer(0);
  const L=document.querySelector('.layer'),R=L.getBoundingClientRect(),k=S.scale;
  const ev=(t,x,y)=>L.dispatchEvent(new PointerEvent(t,{bubbles:true,pointerId:1,pointerType:'mouse',button:0,clientX:R.left+x*k,clientY:R.top+y*k}));
  ev('pointerdown',5,5);ev('pointermove',590,835);ev('pointerup',590,835);await sl(200);
  const n=selecionados().length;ok(n===S.objs.length&&n>=2,'caixa de seleção pega todos os objetos ('+n+')');
  const antes=selecionados().map(o=>o.x);const alvo=selecionados()[0];const el=L.querySelector(`.o[data-id="${alvo.id}"]`),er=el.getBoundingClientRect();
  const ev2=(t,dx)=>el.dispatchEvent(new PointerEvent(t,{bubbles:true,pointerId:2,pointerType:'mouse',button:0,clientX:er.left+5+dx,clientY:er.top+5}));
  ev2('pointerdown',0);ev2('pointermove',50*k);ev2('pointerup',50*k);await sl(200);
  ok(selecionados().every((o,j)=>Math.round(o.x-antes[j])===50),'arrastar um objeto move o grupo todo');
  document.querySelector('[data-al="esq"]').click();await sl(200);
  const xs=selecionados().map(o=>L.querySelector(`.o[data-id="${o.id}"]`).offsetLeft);ok(xs.every(x=>Math.abs(x-xs[0])<1),'alinhar à esquerda');
  document.querySelector('#gDel').click();await sl(200);ok(S.objs.length===0,'apagar o grupo');
  undo();await sl(400);ok(S.objs.length===n,'desfazer traz o grupo de volta');
  // devolve o que o aparelho tinha antes do teste
  if(guardT==null)localStorage.removeItem('editorpdf-textos');else localStorage.setItem('editorpdf-textos',guardT);
  if(guardC==null)localStorage.removeItem('editorpdf-carimbos');else localStorage.setItem('editorpdf-carimbos',guardC);
}catch(e){ok(false,'textos/carimbos/seleção: '+e.message)}

// 3b) mesa de vários PDFs: adicionar, marcar, separar, mover, girar, juntar, salvar cada (zip) e imprimir
try{
  const mk=async(rot,n)=>{const d=await PDFDocument.create(),f=await d.embedFont(StandardFonts.Helvetica);for(let i=1;i<=n;i++)d.addPage([595,842]).drawText(rot+i,{x:72,y:760,size:30,font:f});return new File([await d.save()],rot+'.pdf',{type:'application/pdf'})};
  if(S.doc){S.objs=[];S.form={};S.recSalvo=chaveEdicao()}
  openMesa();await mesaAdicionar([await mk('A',3),await mk('B',2)]);await sl(300);
  ok(M.arqs.length===2&&M.arqs[0].pags.length===3&&M.arqs[1].pags.length===2,'mesa: abre 2 PDFs (3 e 2 páginas)');
  const cl=k=>M.el.querySelector(`.mp[data-k="${k}"]`).click();
  cl(M.arqs[0].pags[2].k);cl(M.arqs[1].pags[0].k);await sl(100); // marca A3 e B1
  ok(M.sel.size===2&&!M.el.querySelector('#mSel').hidden,'mesa: marcar páginas mostra as ações');
  M.el.querySelector('[data-m=separar]').click();await sl(100);
  ok(M.arqs.length===3&&M.arqs[2].pags.length===2,'mesa: separar leva as marcadas para um arquivo novo');
  const textos=async by=>{const d=await pdfjsLib.getDocument({data:by.slice()}).promise,o=[];for(let i=1;i<=d.numPages;i++)o.push((await (await d.getPage(i)).getTextContent()).items.map(x=>x.str).join(''));return o};
  let t=await textos(await mesaMontar(M.arqs.flatMap(a=>a.pags)));
  ok(t.join(',')==='A1,A2,B2,A3,B1','mesa: juntar sai na ordem da mesa ('+t.join(',')+')');
  cl(M.arqs[2].pags[0].k);M.el.querySelector('[data-m=girar]').click();await sl(50);
  const lib=await PDFDocument.load(await mesaMontar(M.arqs[2].pags));ok(lib.getPage(0).getRotation().angle===90,'mesa: girar página');
  M.sel.clear();cl(M.arqs[1].pags[0].k);const mv=M.el.querySelector('#mMover');mv.value=M.arqs[0].k;mv.dispatchEvent(new Event('change'));await sl(50);
  ok(M.arqs[0].pags.length===3&&M.arqs.length===2,'mesa: mover página para outro arquivo');
  const z=zipArquivos([['a.pdf',new Uint8Array([1,2,3])],['b.pdf',new Uint8Array([4])]]);
  ok(z[0]===0x50&&z[1]===0x4b&&new DataView(z.buffer).getUint16(z.length-12,true)===2,'mesa: "Salvar cada arquivo" monta um .zip');
  const pr=window.print;let impressas=0;window.print=()=>{impressas=document.querySelectorAll('#impressao img').length};
  M.sel.clear();cl(M.arqs[0].pags[0].k);cl(M.arqs[1].pags[0].k);M.el.querySelector('#mImp').click();await sl(200);
  document.querySelector('.modal-bg:not(.mesa-bg) [data-ok]').click();for(let k=0;k<50&&!impressas;k++)await sl(200);window.print=pr;
  ok(impressas===2,'mesa: imprimir só as páginas marcadas ('+impressas+')');
  const ia=document.querySelector('#impressao');if(ia)ia.remove();
  M.arqs=[];M.el.querySelector('#mFechar').click();await sl(100);ok(!M.el,'mesa: fechar');
}catch(e){ok(false,'mesa: '+e.message);try{M.arqs=[];if(M.el)M.el.querySelector('#mFechar').click()}catch(_){}}

// 4) Sobre e licenças, barra de cima
try{
  await goHome();await sl(300);document.querySelector('#bSobre').click();await sl(300);
  const m=document.querySelector('.modal');ok(m&&m.querySelectorAll('a[data-url]').length>=15&&m.innerText.includes('AGPL'),'"Sobre e licenças" com licença e componentes');
  if(m)m.querySelector('[data-ok]').click();
  if(innerWidth>700)ok(getComputedStyle(document.querySelector('#bProps')).display==='none','barra do computador sem botões de painel');
  // barra de ferramentas: nomes inteiros e efeito Dock (precisa de um PDF aberto para a barra aparecer)
  const pd2=await PDFDocument.create();pd2.addPage([595,842]);await openFile(new File([await pd2.save()],'barra.pdf',{type:'application/pdf'}));await sl(400);
  const ts=[...document.querySelectorAll('.tool')];
  ok(ts.length>10&&ts.every(b=>{const s=b.querySelector('span');return s.scrollWidth<=s.clientWidth+1}),'barra de ferramentas: nenhum nome cortado');
  if(innerWidth>700){const rail=document.querySelector('#rail'),b=document.querySelector('[data-tool=draw]'),r=b.getBoundingClientRect();
    rail.dispatchEvent(new PointerEvent('pointermove',{bubbles:true,pointerType:'mouse',clientX:r.x+r.width/2,clientY:r.y+r.height/2}));
    for(let t=0;t<20&&!+b.style.getPropertyValue('--k');t++)await sl(50); // o efeito roda no próximo quadro de animação
    const k=+b.style.getPropertyValue('--k'),kLonge=+document.querySelector('[data-tool=select]').style.getPropertyValue('--k');
    ok(k>0.9&&kLonge===0,'efeito Dock: o ícone sob o mouse cresce e o distante não (k='+k+', longe='+kLonge+', visível='+document.visibilityState+')');
    rail.dispatchEvent(new PointerEvent('pointerleave',{pointerType:'mouse'}));await sl(50);
    ok(ts.every(x=>!+x.style.getPropertyValue('--k')),'efeito Dock: volta ao normal quando o mouse sai');
    // barra de cima
    const top=document.querySelector('.top'),bs=document.querySelector('#bSave'),rs=bs.getBoundingClientRect();
    top.dispatchEvent(new PointerEvent('pointermove',{bubbles:true,pointerType:'mouse',clientX:rs.x+rs.width/2,clientY:rs.y+5}));
    for(let t=0;t<20&&!+bs.style.getPropertyValue('--k');t++)await sl(50);
    ok(+bs.style.getPropertyValue('--k')>0.9&&!+document.querySelector('#bOpen').style.getPropertyValue('--k'),'efeito Dock na barra de cima');
    top.dispatchEvent(new PointerEvent('pointerleave',{pointerType:'mouse'}));
    // Configurações: desligar o efeito
    const guardD=localStorage.getItem('editorpdf-dock');
    document.querySelector('#bConfig').click();await sl(200);const cfg=document.querySelector('#cfgDock');
    ok(!!cfg&&cfg.checked,'Configurações abre com o efeito ligado');
    cfg.checked=false;cfg.dispatchEvent(new Event('change'));document.querySelector('.modal [data-ok]').click();await sl(100);
    rail.dispatchEvent(new PointerEvent('pointermove',{bubbles:true,pointerType:'mouse',clientX:r.x+r.width/2,clientY:r.y+r.height/2}));await sl(300);
    ok(!+b.style.getPropertyValue('--k'),'efeito desligado nas Configurações não amplia');
    rail.dispatchEvent(new PointerEvent('pointerleave',{pointerType:'mouse'}));
    if(guardD==null)localStorage.removeItem('editorpdf-dock');else localStorage.setItem('editorpdf-dock',guardD);}
}catch(e){ok(false,'sobre/barra: '+e.message)}

return JSON.stringify({modo,falhas,log});
})()
