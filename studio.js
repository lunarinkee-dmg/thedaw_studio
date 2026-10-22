/* Presentation layer: existing editor controls and API handlers stay mounted. */
(()=>{
 document.documentElement.classList.add('studio-ui');
 const state={month:new Date(new Date().getFullYear(),new Date().getMonth(),1),day:new Date().getDate(),items:[],queueLoaded:false,queueError:'',notes:'',analytics:null};
 try{state.notes=localStorage.getItem('daw_workspace_notes')||'';}catch{}
 const make=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;};
 const button=(text,fn,cls='studio-button')=>{const b=make('button',cls,text);b.type='button';b.onclick=fn;return b;};
 const header=document.querySelector('header');
 const nav=make('nav','studio-nav');nav.setAttribute('aria-label','Основная навигация');
 const routes=[['home','⌂','Главная'],['calendar','calendar','Календарь'],['inbox','feed','Лента'],['design','editor','Редактор'],['analytics','analytics','Аналитика']];
 for(const [id,label,title] of routes){const b=button(label,()=>{if(['design','analytics'].includes(id)){constructorTab=id;go('constructor');}else go(id);},'studio-nav-link');b.dataset.route=id;b.title=title;b.setAttribute('aria-label',title);nav.append(b);}
 nav.append(document.getElementById('dawThemeToggle'));header.prepend(nav);
 const legacy=render;
 function heading(title,subtitle){const h=make('div','studio-heading');h.append(make('h1','',title));if(subtitle)h.append(make('p','',subtitle));return h;}
 function footer(){return make('p','studio-footnote','theDĀW Studio · Ваше пространство для контента');}
 function schedulePanel(){
  const panel=make('section','studio-panel studio-scheduled');panel.append(make('h2','',`Публикации · ${state.day}`));
  const date=new Date(state.month.getFullYear(),state.month.getMonth(),state.day);
  const items=state.items.filter(x=>{const d=new Date(x.scheduled_at);return d.toDateString()===date.toDateString();});
  for(const item of items){const row=make('div','studio-post-row');row.append(make('span','studio-post-icon','▷'));const text=make('div');text.append(make('strong','',String(item.caption||'Reels без подписи').slice(0,75)),make('p','muted',new Date(item.scheduled_at).toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'})+' · Instagram'));row.append(text,make('span','studio-status',String(item.status||'—')));panel.append(row);}
  if(!items.length)panel.append(make('p','studio-empty',state.queueError||(!isEditor()?'Войдите как редактор, чтобы загрузить очередь.':state.queueLoaded?'На этот день публикаций нет.':'Загрузите очередь, чтобы увидеть запланированные Reels.')));
  const refresh=button('↻ Обновить очередь',async()=>{
   if(!isEditor()){showEditorLogin();return;}refresh.disabled=true;refresh.textContent='Загрузка…';
   try{const response=await dawFetch(DAW_API+'/schedule/list',{method:'POST',headers:{'Content-Type':'application/json','X-Editor-Session':editorSession},body:'{}',cache:'no-store'});const result=await response.json();if(!response.ok||result.error||!Array.isArray(result.items))throw Error(result.error||'Не удалось получить очередь');state.items=result.items;state.queueLoaded=true;state.queueError='';}
   catch(e){state.queueError='Очередь недоступна: '+e.message;}finally{if(view==='home'||view==='calendar')render();}
  },'studio-button studio-subtle');panel.append(refresh);return panel;
 }
 function calendar(){
  const panel=make('section','studio-panel studio-calendar');const top=make('div','studio-calendar-top');top.append(make('h2','',state.month.toLocaleDateString('ru-RU',{month:'long',year:'numeric'})));
  const controls=make('div','studio-calendar-controls');for(const [label,delta] of [['‹',-1],['›',1]]){const b=button(label,()=>{state.month=new Date(state.month.getFullYear(),state.month.getMonth()+delta,1);state.day=1;render();});b.setAttribute('aria-label',delta<0?'Предыдущий месяц':'Следующий месяц');controls.append(b);}top.append(controls);panel.append(top);
  const grid=make('div','studio-calendar-grid');for(const day of ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'])grid.append(make('span','studio-weekday',day));
  const start=(state.month.getDay()+6)%7;for(let i=0;i<start;i++)grid.append(make('span','studio-calendar-blank'));
  const days=new Date(state.month.getFullYear(),state.month.getMonth()+1,0).getDate();
  for(let day=1;day<=days;day++){
   const b=button(String(day),()=>{state.day=day;render();},'studio-day');b.setAttribute('aria-label',new Date(state.month.getFullYear(),state.month.getMonth(),day).toLocaleDateString('ru-RU'));b.setAttribute('aria-pressed',String(state.day===day));
   if(new Date(state.month.getFullYear(),state.month.getMonth(),day).toDateString()===new Date().toDateString())b.classList.add('is-today');
   if(state.items.some(x=>new Date(x.scheduled_at).toDateString()===new Date(state.month.getFullYear(),state.month.getMonth(),day).toDateString()))b.classList.add('has-post');grid.append(b);
  }panel.append(grid);return panel;
 }
 function dashboard(){
  const main=document.getElementById('main');main.replaceChildren(heading(view==='calendar'?'calendar.':'dashboard.',view==='calendar'?'Планируйте публикации в своём ритме':'Ваше пространство для контента'));
  document.documentElement.classList.remove('daw-home-mode','daw-guest-mode');
  const actions=make('div','studio-dashboard-actions');const create=button('+ Создать публикацию',()=>{constructorTab='design';go('constructor');});create.id='dawHomeEditor';actions.append(create);if(!isEditor()){const guest=button('О проекте',()=>go('guest'),'studio-button studio-ghost');guest.id='dawHomeGuest';actions.append(guest);}main.append(actions);
  const grid=make('div',view==='calendar'?'studio-calendar-layout':'studio-dashboard-grid');grid.append(calendar());
  if(view==='calendar'){grid.append(schedulePanel());}else{
   const performance=make('section','studio-panel studio-performance');performance.append(make('h2','','Работа редакции'));const stats=make('div','studio-local-stats');for(const [label,value] of [['В ленте',data.news.length],['Черновики',data.drafts.length],['Опубликовано здесь',Object.values(data.approved).filter(x=>x.published).length]]){const item=make('div');item.append(make('span','muted',label),make('strong','',String(value)));stats.append(item);}performance.append(stats,make('p','studio-empty','Показатели Instagram доступны в аналитике после загрузки.'),button('Открыть аналитику →',()=>{constructorTab='analytics';go('constructor');},'studio-button studio-white'));grid.append(performance,schedulePanel());
   const notes=make('section','studio-panel studio-notes');notes.append(make('h2','','Заметки'));const area=make('textarea');area.setAttribute('aria-label','Заметки редакции');area.placeholder='Идеи для следующей недели…';area.value=state.notes;const status=make('p','studio-note-status','Сохраняются в этом браузере');area.oninput=()=>{state.notes=area.value;try{localStorage.setItem('daw_workspace_notes',area.value);status.textContent='Сохранено в этом браузере';}catch{status.textContent='Не удалось сохранить. Скопируйте заметку перед закрытием вкладки.';}};notes.append(area,status);grid.append(notes);
  }main.append(grid,footer());
 }
 function editor(){
  const layout=document.querySelector('.daw-editor-layout');if(!layout)return;
  const copy=layout.querySelector('.daw-editor-copy'),settings=layout.querySelector('#designSettings'),preview=layout.querySelector('.design-stage');
  const work=make('section','studio-editor-work');work.append(make('h2','studio-editor-title','ai copywriter + text editor.'));const scroll=make('div','studio-editor-scroll');scroll.append(copy,settings);const publish=document.querySelector('.daw-editor-footer');if(publish)scroll.append(publish);work.append(scroll);
  const rail=make('aside','studio-editor-rail');rail.setAttribute('aria-label','Инструменты редактора');
  for(const [icon,title,index] of [['✦','AI Copywriter',-1],['▧','Текст',0],['▤','Медиа',1],['↗','Публикация и экспорт',3]]){const b=button(icon,()=>{if(index<0){scroll.scrollTo({top:0,behavior:'smooth'});}else{const details=settings.querySelectorAll('details')[index];if(details){details.open=true;scroll.scrollTo({top:details.offsetTop-scroll.offsetTop,behavior:'smooth'});}}},'studio-tool');b.title=title;b.setAttribute('aria-label',title);rail.append(b);}
  const previewTitle=make('div','studio-preview-title');previewTitle.append(make('strong','','live preview.'),make('span','muted','9:16'));preview.prepend(previewTitle);preview.append(make('p','studio-preview-hint','Перенесите текст в шаблон, затем настройте оформление.'));
  layout.replaceChildren(rail,work,preview);
  copy.querySelector('h2').textContent='✦ AI Copywriter';
  const select=copy.querySelector('#dawEditorDraft');const label=make('label','','Одобренные новости из ленты');label.htmlFor=select.id;select.before(label);
  const generate=copy.querySelector('#dawEditorGenerate');generate.textContent='✦ Сгенерировать';
  copy.querySelector('#dawEditorTransfer').textContent='Перенести в шаблон →';
  settings.querySelector('.daw-editor-title').textContent='Оформление и публикация';
 }
 function analyticsSummary(payload=state.analytics){
  const mount=document.getElementById('studioAnalyticsSummary');if(!mount)return;mount.replaceChildren();
  const items=payload?.items;
  for(const [label,key] of [['Просмотры','views'],['Взаимодействия','interactions'],['Сохранения','saves'],['Опубликованные Reels',null]]){
   const card=make('section','studio-panel studio-metric');let value='—';
   if(items){if(key===null)value=String(items.length);else if(items.length&&items.every(i=>Number.isFinite(i[key])))value=new Intl.NumberFormat('ru-RU').format(items.reduce((n,i)=>n+i[key],0));}
   card.append(make('span','',label),make('strong','',value));mount.append(card);
  }
 }
 window.addEventListener('daw:analytics',e=>{state.analytics=e.detail;analyticsSummary();});
 function decorate(){
  const main=document.getElementById('main');const title=view==='inbox'?'feed.':view==='constructor'?(constructorTab==='analytics'?'analytics.':'editor.'):null;
  if(title)main.prepend(heading(title));
  if(view==='constructor'&&constructorTab==='design')editor();
  if(view==='constructor'&&constructorTab==='analytics'){
   const section=main.querySelector('section');section?.querySelector('h1')?.remove();
   const overview=make('div','studio-analytics-overview');overview.id='studioAnalyticsSummary';section?.prepend(overview);analyticsSummary();
   const note=make('p','studio-analytics-note','Instagram · Сумма по Reels, полученным из API. Недоступные показатели обозначены тире.');overview.before(note);
  }
  if(view==='inbox'){
   const filters=make('div','studio-feed-filters');filters.setAttribute('role','group');filters.setAttribute('aria-label','Категории новостей');
   for(const category of ['',...new Set(data.news.map(n=>n.category).filter(Boolean))]){const b=button(category||'Все',()=>{newsCategory=category;newsPage=1;render();},'studio-filter');b.setAttribute('aria-pressed',String(newsCategory===category));filters.append(b);}
   main.querySelector('.daw-news-screen')?.before(filters);
   const category=document.querySelector('.daw-news-category');if(category){const visual=make('div','studio-feed-visual','✧');visual.setAttribute('aria-hidden','true');category.after(visual);}
   const reject=document.getElementById('dawRejectNews'),approve=document.getElementById('dawApproveNews');if(reject)reject.textContent='× Пропустить';if(approve)approve.textContent='✓ Одобрить';
  }
  if(title)main.append(footer());
 }
 render=function(){
  if(!isEditor()){state.items=[];state.queueLoaded=false;state.analytics=null;}
  document.documentElement.dataset.studioView=view==='constructor'?constructorTab:view;
  for(const b of nav.querySelectorAll('[data-route]')){const active=b.dataset.route===(view==='constructor'?constructorTab:view);if(active)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');}
  if(view==='home'||view==='calendar')dashboard();else{legacy();decorate();}
 };
 render();
})();
