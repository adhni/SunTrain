const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const {move,shiftMonth}=require('../assets/01_calendar.js');
const en=require('../dashboard/locales/en.json'),id=require('../dashboard/locales/id.json');
function context(saved,blocked=false){
 const writes=[],events=[],handlers={},elements=[];
 const document={readyState:'loading',documentElement:{},addEventListener:(key,value)=>handlers[key]=value,
  dispatchEvent:event=>events.push(event),getElementById:()=>null,
  querySelectorAll:selector=>selector==='[data-l10n]'?elements.filter(el=>el.getAttribute('data-l10n')):[]};
 const root={document,console,suntrainCatalogues:{en,id},queueMicrotask,
  CustomEvent:class {constructor(type,options){this.type=type;this.detail=options.detail;}},
  localStorage:{getItem:()=>{if(blocked)throw Error('blocked');return saved;},setItem:(...args)=>{if(blocked)throw Error('blocked');writes.push(args);}}};
 root.window=root;vm.runInNewContext(fs.readFileSync(require.resolve('../assets/00_i18n.js'),'utf8'),root);
 function element(){const attrs=new Map();const el={textContent:'',setAttribute:(k,v)=>attrs.set(k,String(v)),getAttribute:k=>attrs.get(k)||null,removeAttribute:k=>attrs.delete(k)};elements.push(el);return el;}
 return {api:root.suntrainI18n,document,writes,events,element};
}
test('English is default regardless of browser, valid explicit preferences restore safely',()=>{
 for(const saved of [null,'fr','__proto__','EN'])assert.equal(context(saved).api.language,'en');
 assert.equal(context('id').api.language,'id');
 const ctx=context('id',true);assert.equal(ctx.api.language,'en');ctx.api.setLanguage('id');assert.equal(ctx.api.language,'id');
});
test('messages, numbers and bound open content round-trip without changing source names',()=>{
 const ctx=context(null),el=ctx.element();ctx.api.bind(el,'1,234 matching stops');ctx.api.sourceNames.add('Flinders Street');
 ctx.api.setLanguage('id');assert.equal(el.textContent,'1.234 pemberhentian yang cocok');
 assert.equal(ctx.api.translate('Flinders Street'),'Flinders Street');assert.equal(ctx.api.number(1234),'1.234');
 assert.equal(ctx.document.documentElement.lang,'id');assert.equal(ctx.writes.at(-1)[1],'id');
 ctx.api.setLanguage('en');assert.equal(el.textContent,'1,234 matching stops');
 ctx.api.setLanguage('id');ctx.api.bind(el,'1.234 matching stops');ctx.api.setLanguage('en');assert.equal(el.textContent,'1,234 matching stops');
 assert.equal(ctx.api.translate('Busiest hour: 07:00 · 263 departures'),'Busiest hour: 07:00 · 263 departures');
 ctx.api.setLanguage('id');assert.equal(ctx.api.translate('Busiest hour: 07:00 · 263 departures'),'Jam tersibuk: 07:00 · 263 keberangkatan');
 assert.equal(ctx.api.translate('Unknown source caveat'),'Unknown source caveat');
});
test('translation substitutions stay text and preserve complete message parameters',()=>{
 const ctx=context('id'),el=ctx.element();ctx.api.bind(el,'From <img src=x onerror=alert(1)>');
 assert.equal(el.textContent,'Dari <img src=x onerror=alert(1)>');assert.equal(el.innerHTML,undefined);
 assert.equal(ctx.api.t('Last {n} minutes',{n:30}),'30 menit terakhir');
});
test('calendar arithmetic preserves ISO dates through leap years and month/year boundaries',()=>{
 assert.equal(move('2024-02-28',1),'2024-02-29');assert.equal(move('2024-02-29',1),'2024-03-01');
 assert.equal(shiftMonth('2024-01-31',1),'2024-02-29');assert.equal(shiftMonth('2025-01-31',1),'2025-02-28');
 assert.equal(shiftMonth('2024-12-31',1),'2025-01-31');assert.equal(move('2026-04-05',-7),'2026-03-29');
});
