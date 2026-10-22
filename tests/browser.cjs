// Run after installing Playwright + Chromium. All remote APIs are mocked;
// no credentials, uploads or real publications are made.
const {chromium}=require('playwright');
setTimeout(()=>{console.error('Browser test exceeded 90 seconds');process.exit(1);},90000).unref();
const assert=require('node:assert/strict');
const fs=require('node:fs');
const http=require('node:http');
const os=require('node:os');
const path=require('node:path');
(async()=>{
 const root=process.cwd();
 const server=http.createServer((req,res)=>{
   const pathname=new URL(req.url,'http://localhost').pathname;
   const file=path.join(root,pathname==='/'?'index.html':pathname);
   if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}
   try{const body=fs.readFileSync(file);res.setHeader('Content-Type',file.endsWith('.html')?'text/html':file.endsWith('.svg')?'image/svg+xml':file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'application/json');res.end(body);}catch{res.writeHead(404).end();}
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 let browser;
 try{
  console.log('Launching Chromium');
  browser=await chromium.launch({headless:true});
  const context=await browser.newContext();
  await context.route('https://**/*',route=>{
   const url=route.request().url();
   if(url.includes('workers.dev/auth/login'))return route.fulfill({json:{ok:true,session:'test-session'}});
   if(url.includes('workers.dev/auth/session'))return route.fulfill({json:{ok:true,role:'editor'}});
   if(url.includes('workers.dev/instagram/analytics'))return route.fulfill({json:{ok:true,checked_at:new Date().toISOString(),items:[{id:'fixture',caption:'Тестовая публикация',views:100,interactions:12,saves:3}]}});
   if(url.includes('workers.dev/generate'))return route.fulfill({json:{headline:'Новый заголовок',instagram:'Описание новости',tiktok:'Короткий текст'}});
   if(url.includes('workers.dev/schedule/list'))return route.fulfill({json:{items:[]}});
   return route.abort();
  });
  await context.addInitScript(()=>{
   if(!localStorage.getItem('thedaw_studio_v02'))localStorage.setItem('thedaw_studio_v02',JSON.stringify({drafts:[{id:'d1',headline:'Тест',caption:'Подпись',sourceTitle:'Исходник',sourceSummary:'Факты',tiktok:'TikTok'}]}));
  });
  console.log('Chromium ready');
  const page=await context.newPage();page.setDefaultTimeout(10000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const origin='http://127.0.0.1:'+server.address().port;
  await page.goto(origin);console.log('Home loaded');
  await page.locator('.studio-calendar-grid').waitFor();
  await page.screenshot({path:path.join(os.tmpdir(),'thedaw-dashboard-new.png'),fullPage:true});
  await page.locator('#dawHomeGuest').click();await page.locator('#dawGuestHome').click();
  await page.locator('#dawHomeEditor').click();await page.locator('#dawLoginPassword').fill('test-only');await page.locator('#dawLoginSubmit').click();
  await page.locator('#dawEditorHeadline').waitFor();console.log('Editor loaded');
  assert.ok((await page.locator('.design-stage').boundingBox()).width>200);
  await page.screenshot({path:path.join(os.tmpdir(),'thedaw-editor-new.png'),fullPage:true});
  await page.setViewportSize({width:375,height:900});
  await page.screenshot({path:path.join(os.tmpdir(),'thedaw-editor-mobile.png'),fullPage:true});
  await page.setViewportSize({width:1280,height:900});
  await page.locator('#dawEditorHeadline').fill('Изменено');
  assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('thedaw_studio_v02')).drafts[0].headline),'Изменено');
  await page.getByText('Публикация и экспорт',{exact:true}).click();
  await page.locator('#designTikTokCaption').fill('Сохранён TikTok');
  await page.locator('#designInstagramCaption').fill('Сохранён Instagram');
  await page.reload();await page.locator('#dawHomeEditor').click();
  assert.equal(await page.locator('#designTikTokCaption').inputValue(),'Сохранён TikTok');
  assert.equal(await page.locator('#designInstagramCaption').inputValue(),'Сохранён Instagram');
  await page.locator('#dawEditorGenerate').click();await page.waitForFunction(()=>document.querySelector('#dawEditorHeadline')?.value==='Новый заголовок');
  await page.getByText('Публикация и экспорт',{exact:true}).click();
  await page.locator('#designScheduleQueue').click();await page.waitForFunction(()=>document.querySelector('#designScheduleList')?.textContent.includes('пока нет'));
  for(const route of ['home','calendar','inbox','analytics']){
   await page.locator('[data-route="'+route+'"]').click();
   if(route==='home'){
    await page.locator('.studio-notes textarea').fill('Идеи для следующей недели');
   }
   if(route==='calendar'){
    const month=await page.locator('.studio-calendar-top h2').textContent();
    await page.getByRole('button',{name:'Следующий месяц',exact:true}).click();
    assert.notEqual(await page.locator('.studio-calendar-top h2').textContent(),month);
    await page.getByRole('button',{name:'Предыдущий месяц',exact:true}).click();
   }
   if(route==='inbox'){
    await page.locator('.studio-filter').nth(1).click();
    const selected=await page.locator('.studio-filter[aria-pressed="true"]').textContent();
    assert.equal(await page.locator('.daw-news-category').textContent(),selected);
    await page.getByRole('button',{name:'Все',exact:true}).click();
   }
   if(route==='analytics'){
    await page.locator('#dawLoadAnalytics').click();
    await page.waitForFunction(()=>document.querySelector('#studioAnalyticsSummary')?.textContent.includes('100'));
   }
   for(const width of [375,768,1440]){
    await page.setViewportSize({width,height:1000});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,route+' overflow at '+width);
   }
   await page.screenshot({path:path.join(os.tmpdir(),'thedaw-'+route+'-new.png'),fullPage:true});
   if(route==='home'){await page.setViewportSize({width:375,height:900});await page.screenshot({path:path.join(os.tmpdir(),'thedaw-home-mobile.png'),fullPage:true});await page.setViewportSize({width:1440,height:1000});}
  }
  await page.locator('[data-route="design"]').click();
  await page.getByText('Публикация и экспорт',{exact:true}).click();
  // Storage quota failure must preserve the live editor and offer a backup.
  await page.evaluate(()=>{Storage.prototype.setItem=function(){throw new DOMException('Full','QuotaExceededError')};});
  await page.locator('#dawEditorHeadline').fill('В памяти');await page.locator('#dawStorageWarning').waitFor();
  assert.equal(await page.evaluate(()=>data.drafts[0].headline),'В памяти');
  for(const width of [375,768,1440]){
   await page.setViewportSize({width,height:900});
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
   assert.equal(overflow,false,'editor overflow at '+width);
  }
  await page.screenshot({path:path.join(os.tmpdir(),'thedaw-editor.png'),fullPage:true});
  assert.deepEqual(errors,[]);console.log('PASS: navigation, login, drafts, caption persistence, Gemini, queue, storage failure, 375/768/1440 widths; no runtime errors');
  // A 401 clears the session once and returns the user to guest mode.
  let dialogs=0;page.on('dialog',async dialog=>{dialogs++;await dialog.accept();});
  await context.route('**/schedule/list',route=>route.fulfill({status:401,json:{error:'Unauthorized'}}));
  await page.locator('#designScheduleQueue').click();
  await page.waitForFunction(()=>document.documentElement.dataset.dawRole==='guest');
  assert.equal(await page.evaluate(()=>sessionStorage.getItem('daw_editor_session')),null);
  assert.equal(dialogs,1);
  assert.deepEqual(errors,[]);
  console.log('PASS: expired session cleared with one notification');
  await context.close();
 }finally{console.log('Closing browser');if(browser)await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
