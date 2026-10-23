// One owner-facing list, rebuilt from explicit questions; never infers visits.
const fs=require('node:fs');
const dir='reviews/source-audit/trips';
let out='# Вопросы по исходным материалам\n\nАудит продолжается. Вопросы не останавливают чтение других глав. Здесь собраны все открытые вопросы из проверенных поездок; непрочитанные материалы перечислены в inventory.json. Названия и посещения не угадываются.\n';
let count=0;
for(const file of fs.readdirSync(dir).filter(f=>f.endsWith('.json')).sort()){
 const r=JSON.parse(fs.readFileSync(`${dir}/${file}`,'utf8')),q=r.reconciliation?.questions||[];
 if(!q.length)continue;
 out+=`\n## ${r.trip_path}\n\n`;
 for(const item of q){count++;out+=typeof item==='string'?`- ${item}\n`:`- **${item.object||'Уточнение'}**: ${item.question||JSON.stringify(item)}${item.chapter?` (глава: ${item.chapter})`:''}\n`;}
}
out+=`\nВсего открытых записей: ${count}. Основания и решения сохранены в отчётах trips/*.json.\n`;
fs.writeFileSync('reviews/source-audit/QUESTIONS.md',out);
console.log(`${count} questions collected in reviews/source-audit/QUESTIONS.md`);
