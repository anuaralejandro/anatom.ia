/* M05 design-only prototype. No GPU, wasm, networking, service worker or patient data. */
(() => {
  const app = document.getElementById('root');
  const stateSelect = document.getElementById('stateSelect');
  const html = document.documentElement;
  const params = new URLSearchParams(window.location.search);
  const anatomy = {
    "Sacro": {en:"Sacrum",la:"Os sacrum",group:"Sistema esquelético"},
    "Cóccix": {en:"Coccyx",la:"Os coccygis",group:"Sistema esquelético"},
    "Sínfisis púbica": {en:"Pubic symphysis",la:"Symphysis pubica",group:"Sistema esquelético"},
    "Vejiga urinaria": {en:"Urinary bladder",la:"Vesica urinaria",group:"Órganos pélvicos"},
    "Próstata": {en:"Prostate",la:"Prostata",group:"Órganos pélvicos"},
    "Vesículas seminales": {en:"Seminal vesicle",la:"Vesicula seminalis",group:"Órganos pélvicos"},
    "Arteria ilíaca interna": {en:"Internal iliac artery",la:"Arteria iliaca interna",group:"Vasos y nervios"},
    "Nervio femoral": {en:"Femoral nerve",la:"Nervus femoralis",group:"Vasos y nervios"},
  };
  let selection = "Sacro";
  let previousLayout = null;
  let sheetTab = "inspector";
  const previewOnly = new Set(["Sacro","Cóccix","Sínfisis púbica","Vejiga urinaria","Próstata","Vesículas seminales","Arteria ilíaca interna","Nervio femoral"]);
  const capture = params.get('capture') === '1';
  if (capture) document.body.classList.add('capture');

  function layoutFor(width, height) {
    // Use the actual CSS viewport (including Stage Manager/window resizing), never UA.
    if (height < 500) return width < 600 ? 'compact' : 'compact-wide';
    if (width >= 1536 && height >= 650 && width - 64 - 296 - 344 >= 720) return 'pro-wide';
    if (width >= 1120 && width - 56 - 296 >= 640) return 'workstation';
    if (width >= 840 && width >= 540) return 'tablet';
    if (width >= 600) return 'compact-wide';
    return 'compact';
  }
  function applyLayout() {
    const width = document.documentElement.clientWidth;
    const height = document.documentElement.clientHeight;
    const layout = layoutFor(width, height);
    app.dataset.layout = layout;
    app.dataset.short = height < 650 ? 'true' : 'false';
    if (layout !== previousLayout) {
      app.dataset.explorerOpen = 'false';
      app.dataset.inspectorOpen = 'false';
      app.dataset.sheet = 'collapsed';
      previousLayout = layout;
    }
    // Center-stage remains concept only; no camera/view state changes on resize.
    window.__m05Preview = {
      layout, cssViewport: [width,height], state: stateSelect.value,
      selected: selection, theme: html.dataset.theme,
      illustrationOnly: true, engineInstantiated: false
    };
  }
  function closePanels() {
    app.dataset.explorerOpen = 'false';
    app.dataset.inspectorOpen = 'false';
    if(app.dataset.layout === 'compact') app.dataset.sheet = 'collapsed';
  }
  function openPanel(panel) {
    const layout = app.dataset.layout;
    if(layout === 'pro-wide') {
      if(panel === 'explorer')document.querySelector('#anatomySearch')?.focus();
      return;
    }
    if(layout === 'compact') {
      sheetTab = panel === 'explorer' ? 'explorer' : 'inspector';
      renderSheetTab();
      app.dataset.sheet = 'mid';
      return;
    }
    const key = panel === 'explorer' ? 'explorerOpen' : 'inspectorOpen';
    const other = key === 'explorerOpen' ? 'inspectorOpen' : 'explorerOpen';
    const isOpen = app.dataset[key] === 'true';
    app.dataset[other] = 'false';
    app.dataset[key] = isOpen ? 'false' : 'true';
  }
  function renderSheetTab() {
    document.querySelectorAll('.sheet-tab').forEach(x => x.classList.toggle('active', x.dataset.sheetTab === sheetTab));
    const info = anatomy[selection] ?? anatomy.Sacro;
    const list = Object.keys(anatomy).map(x =>
      '<button class="anatomy-row '+ (x===selection?'selected':'') +'" type="button" data-name="'+x+'">'+
        '<span class="row-marker '+ (/Vejiga|Próstata|Vesícula/.test(x)?'organ':'bone')+'"></span>'+
        '<span class="row-label">'+x+'</span><svg class="eye-icon"><use href="#ic-chevron"/></svg></button>'
    ).join('');
    document.getElementById('sheetContent').innerHTML = sheetTab === 'explorer'
      ? '<div class="eyebrow">ESTRUCTURAS DISPONIBLES EN EL MOCKUP</div><div class="sheet-structure-list">'+list+'</div>'
      : '<div class="sheet-name">'+selection+'</div><p>'+info.la+' · '+info.group+'</p>'+
        '<div class="actions-two"><button class="action-primary" type="button"><svg><use href="#ic-focus"/></svg> Enfocar</button>'+
        '<button class="action-neutral" type="button"><svg><use href="#ic-layers"/></svg> Aislar</button></div>'+
        '<div class="meta-row"><span>Inglés</span><strong>'+info.en+'</strong></div>'+
        '<div class="meta-row"><span>Latín</span><strong>'+info.la+'</strong></div>'+
        '<div class="meta-row"><span>Terminología</span><strong>TA2 · Conceptual</strong></div>';
  }
  function changeSelection(name) {
    if(!previewOnly.has(name)) return;
    selection = name;
    document.getElementById('stageSelected').textContent = name;
    document.getElementById('inspectorName').textContent = name;
    document.getElementById('inspectorSecondary').textContent = anatomy[name].en+' · '+anatomy[name].la;
    document.getElementById('metaSpanish').textContent = name;
    document.getElementById('metaEnglish').textContent = anatomy[name].en;
    document.getElementById('metaLatin').textContent = anatomy[name].la;
    document.getElementById('sheetSelected').textContent = name;
    document.querySelectorAll('.anatomy-row').forEach(x => x.classList.toggle('selected', x.dataset.name === name));
    if (app.dataset.layout === 'compact') {
      sheetTab='inspector';renderSheetTab();app.dataset.sheet='mid';
    }
    window.__m05Preview.selected = name;
  }
  function changeState(state) {
    document.body.classList.remove('state-empty','state-selected','state-loading','state-error');
    document.body.classList.add('state-'+state);
    if(state === 'empty') {
      document.getElementById('stageSelected').textContent = 'Ninguna';
      document.getElementById('sheetSelected').textContent = 'Explorar anatomía';
    } else {
      document.getElementById('stageSelected').textContent = selection;
      document.getElementById('sheetSelected').textContent = selection;
    }
    const messages = {
      selected:['',''],
      empty:['Selecciona una estructura','Explora la lista o toca una pieza del modelo para consultar su nomenclatura.'],
      loading:['Preparando el atlas 3D','Se están verificando los paquetes anatómicos y preparando los recursos gráficos.'],
      error:['No se pudo iniciar el visor','Ejemplo de estado de error. La versión real deberá ofrecer reintento y cambio de backend.'],
    };
    document.getElementById('stateTitle').textContent = messages[state][0];
    document.getElementById('stateDescription').textContent = messages[state][1];
    window.__m05Preview.state = state;
  }
  function toggleSheet() {
    const val=app.dataset.sheet;
    app.dataset.sheet = val==='collapsed'?'mid':val==='mid'?'max':'collapsed';
    if (app.dataset.sheet === 'mid' || app.dataset.sheet === 'max')renderSheetTab();
  }
  function themeToggle() {
    html.dataset.theme=html.dataset.theme==='dark'?'light':'dark';
    window.__m05Preview.theme=html.dataset.theme;
  }
  document.addEventListener('click', event => {
    const a = event.target.closest('[data-action]');
    if(a) {
      const op=a.dataset.action;
      if(op==='explorer'||op==='inspector')openPanel(op);
      if(op==='close')closePanels();
      if(op==='sheet')toggleSheet();
      if(op==='theme')themeToggle();
      if(op==='search'){openPanel('explorer');setTimeout(()=>document.getElementById('anatomySearch')?.focus(),0);}
      if(op==='info')alert('Wireframe de revisión M05: ninguna malla clínica ni motor WebGPU está conectado.');
      if(op==='retry'){stateSelect.value='selected';changeState('selected');}
      return;
    }
    const tab=event.target.closest('[data-sheet-tab]');
    if(tab){sheetTab=tab.dataset.sheetTab;renderSheetTab();return;}
    const row=event.target.closest('.anatomy-row[data-name]');
    if(row)changeSelection(row.dataset.name);
  });
  document.addEventListener('keydown', event => {
    if(event.key==='Escape'){closePanels();document.activeElement?.blur();return;}
    if((event.metaKey||event.ctrlKey)&&event.key.toLowerCase()==='k'){
      event.preventDefault();openPanel('explorer');document.getElementById('anatomySearch')?.focus();
    }
  });
  document.getElementById('anatomySearch')?.addEventListener('input',ev=>{
    const q=ev.target.value.toLocaleLowerCase('es-MX').normalize('NFD').replace(/[\u0300-\u036f]/g,'');
    document.querySelectorAll('.explorer-panel .anatomy-row').forEach(row => {
      const text=row.dataset.name.toLocaleLowerCase('es-MX').normalize('NFD').replace(/[\u0300-\u036f]/g,'');
      row.hidden = !!q && !text.includes(q);
    });
  });
  document.getElementById('stateSelect').addEventListener('change',ev=>changeState(ev.target.value));
  document.getElementById('panelBtn').addEventListener('click',()=>{
    app.dataset.layout==='pro-wide'?null:openPanel('inspector');
  });
  const userTheme=params.get('theme');
  if(userTheme==='light'||userTheme==='dark')html.dataset.theme=userTheme;
  const desiredState=params.get('state')||'selected';
  if (['selected','empty','loading','error'].includes(desiredState))stateSelect.value=desiredState;
  applyLayout();renderSheetTab();changeState(stateSelect.value);
  if(params.get('panel')==='inspector')openPanel('inspector');
  if(params.get('panel')==='explorer')openPanel('explorer');
  if(params.get('sheet')==='max'&&app.dataset.layout==='compact'){app.dataset.sheet='max';renderSheetTab();}
  window.addEventListener('resize',applyLayout,{passive:true});
})();