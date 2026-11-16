// Dependency-free logic check. This is NOT a rendered-browser/layout check.
import fs from 'node:fs/promises';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const html=await fs.readFile('docs/demo.html','utf8');
const source=html.match(/<script>([\s\S]*?)<\/script>/)[1];
class Element {
 constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.attributes={};this.textContent='';this.innerHTML='';}
 setAttribute(k,v){this.attributes[k]=String(v);}
 appendChild(n){this.children.push(n);return n;}
 replaceChildren(){this.children=[];}
}
const elements=new Map([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element()]));
const handlers={};
const document={getElementById:id=>{assert.ok(elements.has(id),`Missing ${id}`);return elements.get(id);},
 createElementNS:(_,tag)=>new Element(tag),addEventListener:(name,fn)=>{handlers[name]=fn;}};
vm.runInNewContext(source,{document,console},{timeout:10000});
const el=id=>elements.get(id);
assert.equal(el('position').textContent,'1 / 27');
assert.equal(el('clusters').textContent,63);
el('next').onclick();
assert.equal(el('phase').textContent,'move');
assert.ok(el('tree').children.some(g=>g.children.some(c=>c.attributes.stroke==='#e5a52b')));
el('fold').onclick();
assert.equal(el('phase').textContent,'fold');
el('last').onclick();
assert.equal(el('phase').textContent,'finish');
assert.equal(el('clusters').textContent,5);
assert.ok(el('next').disabled);
el('tree').children.find(e=>e.attributes.class==='node').onclick();
assert.match(el('inspect').innerHTML,/64 points/);
handlers.keydown({target:{tagName:'BODY'},key:'ArrowLeft',preventDefault(){}});
assert.equal(el('position').textContent,'26 / 27');
el('first').onclick();
for(let i=0;i<27;i++){
 el('slider').oninput({target:{value:String(i)}});
 assert.equal(el('position').textContent,`${i+1} / 27`);
 assert.ok(Number.isFinite(Number(el('cost').textContent)));
}
assert.ok(!/<script[^>]+src=|<link[^>]+href=|<img[^>]+src=["']https?:/i.test(html));
await fs.mkdir('docs/qa',{recursive:true});
await fs.writeFile('docs/qa/dom-check.json',JSON.stringify({states:27,navigation:true,
 highlights:true,inspector:true,keyboard:true,slider:true,external_assets:0,
 scope:'DOM logic only; see browser-check.json for rendered browser results',
 layout_verified_by_this_check:false},null,2)+'\n');
console.log('All 27 states and control handlers passed the DOM logic check. Browser layout is checked separately by check_demo.mjs.');
