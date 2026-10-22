/**
 * theDĀW TikTok Studio desktop assistant (Windows/macOS/Linux).
 * Run: node tools/tiktok-studio-upload.mjs "C:\path\video.mp4" "C:\path\caption.txt"
 * Requires: npm install --no-save playwright && npx playwright install chromium
 * Does not submit, schedule or publish posts automatically.
 */
import { chromium } from 'playwright';
import { resolve } from 'node:path';
import { readFile, stat, mkdir } from 'node:fs/promises';
import { homedir } from 'node:os';
import { join } from 'node:path';

const video = process.argv[2];
const captionPath = process.argv[3];
if (!video || !/\.mp4$/i.test(video)) {
  console.error('Укажи путь к экспортированному MP4: node tools/tiktok-studio-upload.mjs "C:\\Videos\\reels.mp4" ["C:\\Videos\\caption.txt"]');
  process.exit(1);
}
const videoPath = resolve(video);
try { const file = await stat(videoPath); if (!file.isFile()) throw new Error('Не файл'); }
catch { console.error('MP4 не найден: ' + videoPath); process.exit(1); }
const caption = captionPath ? (await readFile(resolve(captionPath),'utf8')).trim() : '';
const profile = join(homedir(), '.thedaw', 'tiktok-studio-browser');
await mkdir(profile,{recursive:true});
console.log('Откроется отдельное окно TikTok Studio. Войди в аккаунт вручную при первом запуске.');
console.log('Пароль не запрашивается и не сохраняется в проекте.');
const context = await chromium.launchPersistentContext(profile, {headless:false, viewport:{width:1280,height:900}});
const page = context.pages()[0] || await context.newPage();
await page.goto('https://www.tiktok.com/tiktokstudio', {waitUntil:'domcontentloaded',timeout:45000});
console.log('Если требуется авторизация, закончи вход вручную. Затем перейди на экран Upload.');
let uploaded = false;
const limit = Date.now()+180000;
while(Date.now()<limit && !uploaded){
  for(const p of context.pages()){
    if(!/^https:\/\/(?:[a-z0-9-]+\.)*tiktok\.com\//i.test(p.url()))continue;
    const input=p.locator('input[type="file"][accept*="video"], input[type="file"][accept*=".mp4"], input[type="file"]').first();
    if(await input.count()){
      try { await input.setInputFiles(videoPath,{timeout:5000}); uploaded=true; break; }
      catch {}
    }
  }
  if(!uploaded)await new Promise(r=>setTimeout(r,1400));
}
if(uploaded){
  console.log('Файл выбран. Дождись обработки видео TikTok.');
  if(caption){
    // Fill only a recognizable editable caption field; never click a publish control.
    let filled=false;
    for(const p of context.pages()){
      if(!/^https:\/\/(?:[a-z0-9-]+\.)*tiktok\.com\//i.test(p.url()))continue;
      const editors=[
        p.locator('[contenteditable="true"][data-placeholder*="caption" i]'),
        p.locator('[contenteditable="true"][aria-label*="caption" i]'),
        p.locator('textarea[placeholder*="caption" i]'),
        p.locator('[contenteditable="true"][data-placeholder*="описан" i]'),
      ];
      for(const target of editors){
        if(await target.count()){
          try { await target.first().fill(caption,{timeout:3000}); filled=true; break; }catch{}
        }
      }
      if(filled)break;
    }
    console.log(filled?'Подпись вставлена. Проверь её перед публикацией.':'Поле подписи не распознано. Вставь текст из caption.txt вручную.');
  }
}else console.log('Поле загрузки не найдено за 3 минуты. Открой Upload в TikTok Studio и выбери MP4 вручную.');
console.log('Проверь ролик, права на музыку, подпись и настройки. Кнопку «Опубликовать» нажимай сам.');
console.log('Окно останется открытым; после завершения закрой его для выхода из помощника.');
await new Promise(resolve => context.on('close',resolve));
