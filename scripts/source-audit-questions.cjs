// One owner-facing list, rebuilt from explicit questions; never infers visits.
const fs=require('node:fs');
const dirs=['reviews/source-audit/trips','reviews/source-audit/supplemental'].filter(fs.existsSync);
let out='# Вопросы по исходным материалам\n\nАудит продолжается. Вопросы не останавливают чтение других глав. Здесь собраны все открытые вопросы из проверенных поездок; непрочитанные материалы перечислены в inventory.json. Названия и посещения не угадываются.\n';
let count=0;
const limitations=[];
for(const file of dirs.flatMap(dir=>fs.readdirSync(dir).filter(f=>f.endsWith('.json')).map(f=>dir+'/'+f)).sort()){
 const r=JSON.parse(fs.readFileSync(file,'utf8')),q=r.reconciliation?.questions||[];
 for(const item of r.reconciliation?.limitations||[])limitations.push({trip:r.trip_path||r.title,...item});
 if(!q.length)continue;
 out+=`\n## ${r.trip_path||r.title}\n\n`;
 for(const item of q){count++;out+=typeof item==='string'?`- ${item}\n`:`- **${item.object||'Уточнение'}**: ${item.question||JSON.stringify(item)}${item.chapter?` (глава: ${item.chapter})`:''}\n`;}
}
if(fs.existsSync('reviews/source-audit/source-gaps.json')){
 const gaps=JSON.parse(fs.readFileSync('reviews/source-audit/source-gaps.json','utf8'));
 out+='\n## Материалы, отсутствующие в текущем составе поездок\n\n';
 for(const item of gaps.items.filter(x=>x.data_status!=='reconciled')){count++;out+=`- **${item.label}**: ${item.question}\n`;}
}
if(limitations.length){
 out+='\n## Незавершённая сверка исходников и материалов\n\nЭто ограничения аудита, а не просьбы остановить работу до ответа. Прочитанная глава не означает, что её независимый первоисточник найден.\n\n';
 for(const item of limitations)out+=`- **${item.trip}${item.chapter?` / ${item.chapter}`:''}**: ${item.detail}\n`;
}
out+=`\nВсего открытых вопросов: ${count}; отдельно ограничений: ${limitations.length}. Основания и решения сохранены в отчётах trips/*.json и source-gaps.json.\n`;
fs.writeFileSync('reviews/source-audit/QUESTIONS.md',out);
console.log(`${count} questions collected in reviews/source-audit/QUESTIONS.md`);
