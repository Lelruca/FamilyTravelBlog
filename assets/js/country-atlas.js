(() => {
const root=document.getElementById('country-explorer');if(!root)return;

const data=JSON.parse(root.querySelector("#country-atlas-data").textContent);
const plural=n=>n%10===1&&n%100!==11?'поездка':n%10>=2&&n%10<=4&&(n%100<12||n%100>14)?'поездки':'поездок';
root.querySelectorAll('path[data-key]').forEach(p=>p.classList.toggle('visited',!!data.countries.find(c=>c.key===p.dataset.key)?.trips.length));
const visited=data.countries.filter(c=>c.trips.length);root.querySelector('#stats').textContent=visited.length+' стран · '+data.trips+' поездок в дневнике';
const groups=root.querySelector('#groups');
const regionNames={europe:'Европа',americas:'Северная Америка',south:'Южная Америка',asia:'Азия',africa:'Африка',oceania:'Австралия и Океания'};
const availableRegions=new Set(visited.map(c=>Object.keys(regionNames).find(k=>regionNames[k]===c.region)));
const flags={england:'gb',belgium:'be',germany:'de',netherlands:'nl',spain:'es',portugal:'pt',france:'fr',switzerland:'ch',canada:'ca',mexico:'mx',usa:'us',japan:'jp',italy:'it',vatican:'va'};
function renderCountries(region){
  groups.replaceChildren();
  root.querySelector('.directory-top h2').textContent=regionNames[region]||'Все страны';
  const visibleRegions=region==='world'?Object.keys(regionNames):[region];
  for(const regionKey of visibleRegions){
    const countries=data.countries.filter(c=>c.region===regionNames[regionKey]);
    if(!countries.length)continue;
    const group=document.createElement('div');group.className='group';
    if(region==='world'){const title=document.createElement('h3');title.textContent=regionNames[regionKey];group.append(title)}
    const rows=document.createElement('div');rows.className='rows';group.append(rows);groups.append(group);
    for(const c of countries){
      const card=document.createElement('a');card.className='country';
      if(c.trips.length){card.href=c.url;card.onclick=e=>{e.preventDefault();select(c.key)}}else{card.setAttribute('aria-disabled','true')}
      const flag=document.createElement('img');flag.width=54;flag.height=36;flag.src=root.dataset.flags+flags[c.key]+'.svg';flag.alt='Флаг: '+c.title;
      const text=document.createElement('div');text.className='country-text';
      const name=document.createElement('span');name.textContent=c.title;
      const count=document.createElement('small');count.textContent=c.trips.length?c.trips.length+' '+plural(c.trips.length):'Пока нет рассказов';
      text.append(name,count);card.append(flag,text);rows.append(card);
    }
  }
}
let currentRegion='world';
function select(key){const c=data.countries.find(c=>c.key===key);if(!c?.trips.length)return;const returnRegion=currentRegion;if(currentRegion==='world'){view(Object.keys(regionNames).find(k=>regionNames[k]===c.region))}else if(c.region!==regionNames[currentRegion])return;root.querySelectorAll('[data-key]').forEach(e=>e.classList.toggle('selected',e.dataset.key===key));root.querySelector('.directory-top h2').textContent=c.title+' · путешествия';groups.replaceChildren();const back=document.createElement('button');back.className='back-countries';back.textContent=returnRegion==='world'?'← Все страны':'← Все страны: '+regionNames[returnRegion];back.onclick=()=>view(returnRegion);groups.append(back);const grid=document.createElement('div');grid.className='trip-grid';groups.append(grid);for(const t of c.trips){const a=document.createElement('a');a.className='trip';a.href=t.url;const img=document.createElement('img');img.src=t.image;img.alt='';img.loading='lazy';if(t.position)img.style.objectPosition=t.position;const caption=document.createElement('div');caption.className='caption';const year=document.createElement('span');year.textContent=t.year;const name=document.createElement('strong');name.textContent=t.title;caption.append(year,name);a.append(img,caption);grid.append(a)}if(!c.trips.length){const p=document.createElement('p');p.textContent='Здесь пока нет рассказов о путешествиях.';grid.append(p)}}
const views={world:'0 5 360 155',europe:'165 15 88 65',americas:'12 8 125 80',south:'92 78 66 77',asia:'205 10 140 95',africa:'157 50 81 90',oceania:'285 95 75 65'};
function view(region){if(region!=='world'&&!availableRegions.has(region))return;currentRegion=region;const map=root.querySelector('.map');map.setAttribute('viewBox',views[region]);map.classList.toggle('world',region==='world');map.setAttribute('aria-label',region==='world'?'Выберите континент':'Выберите страну: '+regionNames[region]);root.querySelector('#continent-labels').style.display=region==='world'?'':'none';root.querySelectorAll('[data-key]').forEach(p=>{p.classList.remove('selected');if(region==='world'||!data.countries.find(c=>c.key===p.dataset.key)?.trips.length||data.countries.find(c=>c.key===p.dataset.key)?.region!==regionNames[region]){p.removeAttribute('tabindex');p.removeAttribute('role');p.removeAttribute('aria-label')}else{p.setAttribute('tabindex','0');p.setAttribute('role','button');p.setAttribute('aria-label',data.countries.find(c=>c.key===p.dataset.key)?.title||p.dataset.key)}});root.querySelectorAll('path[data-continent]').forEach(p=>p.classList.toggle('region-selected',region!=='world'&&p.dataset.continent===region));root.querySelectorAll('[data-view]').forEach(x=>{x.classList.toggle('active',x.dataset.view===region);x.setAttribute('aria-pressed',x.dataset.view===region)});root.querySelector('.legend span:last-child').textContent=region==='world'?'Выберите континент на карте':'Выберите страну — путешествия появятся ниже';renderCountries(region)}
root.querySelectorAll('[data-view]').forEach(b=>{b.disabled=b.dataset.view!=='world'&&!availableRegions.has(b.dataset.view);b.onclick=()=>view(b.dataset.view)});root.querySelectorAll('[data-region]').forEach(b=>{const enabled=availableRegions.has(b.dataset.region);b.classList.add(enabled?'available':'unavailable');if(!enabled){b.removeAttribute('tabindex');b.removeAttribute('role');b.setAttribute('aria-disabled','true')}b.onclick=()=>view(b.dataset.region);b.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();view(b.dataset.region)}}});
root.querySelectorAll('path[data-continent]').forEach(p=>{p.classList.toggle('continent-visited',availableRegions.has(p.dataset.continent));p.onclick=()=>{if(currentRegion==='world'){if(views[p.dataset.continent])view(p.dataset.continent)}else if(p.dataset.key)select(p.dataset.key)};p.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();p.onclick()}};p.onmouseenter=()=>{if(window.matchMedia('(hover:hover) and (pointer:fine)').matches&&currentRegion==='world'&&availableRegions.has(p.dataset.continent))root.querySelectorAll('path[data-continent]').forEach(x=>x.classList.toggle('region-hover',x.dataset.continent===p.dataset.continent))};p.onmouseleave=()=>root.querySelectorAll('.region-hover').forEach(x=>x.classList.remove('region-hover'))});view('world');

})();
