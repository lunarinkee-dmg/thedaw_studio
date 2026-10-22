const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const html=fs.readFileSync('index.html','utf8');
const scripts=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(m=>m[1]).filter(s=>s.trim());
test('every inline script parses',()=>{assert.equal(scripts.length,2);scripts.forEach(s=>new vm.Script(s));new vm.Script(fs.readFileSync('studio.js','utf8'));});
function fn(name){const start=html.indexOf('function '+name+'(');assert.ok(start>=0);let end=html.indexOf('\n}',start)+2;return html.slice(start,end);}
test('originality warning detects seven Russian words and ignores unrelated text',()=>{
 const context=vm.createContext({});vm.runInContext(fn('dawOriginalityOverlap'),context);
 const source='Сегодня музей открыл новую выставку современного искусства';
 assert.equal(context.dawOriginalityOverlap(source,source.toUpperCase()).length,1);
 assert.equal(context.dawOriginalityOverlap(source,'Это совершенно другой текст о музыке и фильмах').length,0);
});
test('feed URLs cannot execute scripts',()=>{
 const context=vm.createContext({URL});vm.runInContext(fn('dawSafeUrl'),context);
 for(const url of ['javascript:alert(1)','data:text/html,test','//evil.test',undefined])assert.equal(context.dawSafeUrl(url),'#');
 assert.equal(context.dawSafeUrl('https://example.com/news'),'https://example.com/news');
});
