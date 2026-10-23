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
const standaloneTypes={
 'kroller-muller':['museum','gallery'],
 'mcmichael-gallery':['museum','gallery'],
 'ballenberg':['museum'],
 'trummelbachfaelle':['waterfall'],
 'aareschlucht':['canyon'],
 'pilatus':['mountain'],
 'haut-koenigsbourg':['castle'],
 'hohenschwangau':['castle'],
 'neuschwanstein':['castle'],
 'rhine-falls':['waterfall'],
 'le-pin-au-haras':['equestrian_centre'],
 'puy-du-fou':['amusement_park'],
 'chenonceau':['castle','museum'],
 'chambord':['castle','museum'],
 'crawford-lake':['park','lake','archaeological_site']
};
for(const [slug,types] of Object.entries(standaloneTypes)){
 const p=result[slug] ||= {types:[],search_terms:[],classification_sources:[]};
 p.types=[...new Set([...p.types,...types])];
 p.search_terms=[...new Set([...p.search_terms,...p.types.flatMap(t=>vocabulary[t].search_terms)])];
 p.classification_sources.push(`content/places/${slug}/_index.md`);
}
fs.writeFileSync('data/place_types.json',JSON.stringify(result,null,2)+'\n');
console.log(`${Object.keys(result).length} geographic terms have explicit types; visit evidence is separate.`);
