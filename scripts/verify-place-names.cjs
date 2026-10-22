// Match the current place-names partial: Russian primary, local secondary.
const fs=require('node:fs'),assert=require('node:assert/strict');let count=0;
for(const slug of fs.readdirSync('content/places')){
 const f='content/places/'+slug+'/_index.md';if(!fs.existsSync(f))continue;
 const raw=fs.readFileSync(f,'utf8'),m=raw.match(/^title:[ \t]*(.*?)\r?$/m);assert.ok(m,f);
 const title=JSON.parse(m[1]);assert.ok(!/\s[—–]\s/.test(title),slug+': unsupported separator');
 const t=title.split(', ')[0],parts=t.split(' - '),ru=parts.length>1?parts.slice(1).join(' - '):t;
 assert.ok(/[А-Яа-яЁё]/.test(ru),slug+': no Russian primary name');
 assert.equal(ru[0],ru[0].toLocaleUpperCase('ru'),slug+': lowercase primary name');count++;
}
for(const [slug,expected]of Object.entries({'buenos-aires':'Буэнос-Айрес','incles-valley':'Долина Инклес','mcmichael-gallery':'Музей Макмайкл'})){
 const title=JSON.parse(fs.readFileSync('content/places/'+slug+'/_index.md','utf8').match(/^title:[ \t]*(.*?)\r?$/m)[1]);
 assert.equal(title.split(', ')[0].split(' - ').at(-1),expected,slug);
}
console.log(`Verified ${count} geographic/taxonomy names: consistent delimiter, Russian primary, uppercase navigation label.`);
