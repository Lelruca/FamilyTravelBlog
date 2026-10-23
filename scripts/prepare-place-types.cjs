// Data export for standalone geographic results; no interface changes.
// A taxonomy place can be a museum even when it has no attractions entry.
const fs=require('node:fs');
const attractions=JSON.parse(fs.readFileSync('data/attractions.json','utf8'));
const vocabulary=JSON.parse(fs.readFileSync('data/attraction_types.json','utf8'));
const result={};
for(const [id,a] of Object.entries(attractions))if(a.place){
 const p=result[a.place] ||= {types:[],search_terms:[],classification_sources:[]};
 p.types=[...new Set([...p.types,...a.types])];
 p.search_terms=[...new Set([...p.search_terms,...a.search_terms])];
 p.classification_sources.push(`data/attractions.json#${id}`);
}
for(const slug of ['kroller-muller','mcmichael-gallery']){
 const p=result[slug] ||= {types:[],search_terms:[],classification_sources:[]};
 p.types=[...new Set([...p.types,'museum','gallery'])];
 p.search_terms=[...new Set([...p.search_terms,...p.types.flatMap(t=>vocabulary[t].search_terms)])];
 p.classification_sources.push(`content/places/${slug}/_index.md`);
}
fs.writeFileSync('data/place_types.json',JSON.stringify(result,null,2)+'\n');
console.log(`${Object.keys(result).length} geographic terms have explicit types; visit evidence is separate.`);
