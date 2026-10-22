(() => {
  const root = document.getElementById('place-explorer');
  if (!root) return;
  const input = root.querySelector('#place-search'), country = root.querySelector('#place-country');
  const rows = [...root.querySelectorAll('[data-place-item]')], groups = [...root.querySelectorAll('[data-place-group]')];
  const list = root.querySelector('#places-list'), panel = root.querySelector('#place-map-panel');
  const status = root.querySelector('#place-map-status'), jump = root.querySelector('#place-jump');
  const sightsBox = root.querySelector('#sights-found'), sightsList = root.querySelector('#sights-list');
  let sights = []; try { sights = JSON.parse(root.querySelector('#sights-data').textContent) || []; } catch (e) {}
  let map, clusters, mode = 'list', sightsFound = [];
  const normalize = value => value.toLocaleLowerCase('ru').normalize('NFD').replace(/\p{M}/gu, '').replace(/ё/g, 'е');
  sights.forEach(s => { s.n = normalize(`${s.t} ${s.s || ''}`); s.cn = normalize(s.c); });
  // a sight is found by its name and type words together; the city may narrow a longer query («музей Флоренция»),
  // but the city alone never lists all its sights
  const sightMatches = (s, words) => words.some(w => s.n.includes(w))
    && words.every(w => s.n.includes(w) || (words.length > 1 && s.cn.includes(w)));
  const visible = () => rows.filter(row => !row.hidden);
  const key = 'placeSearch';
  const remember = () => { try { sessionStorage.setItem(key, JSON.stringify({ q: input.value, c: country.value, m: mode })); } catch (e) {} };

  // map: a point opens a small window with the place's name and a way to its page
  function fit() { if (clusters?.getLayers().length) map.fitBounds(clusters.getBounds(), {padding:[30,30],maxZoom:12}); }
  function renderMap(refit = true) {
    if (!window.L?.markerClusterGroup) { status.textContent='Карта не загрузилась. Все места доступны в списке.'; return; }
    if (!map) {
      map = L.map('place-map', {scrollWheelZoom:false,zoomControl:false}).setView([45,-25],3);
      L.control.zoom({zoomInTitle:'Приблизить',zoomOutTitle:'Отдалить'}).addTo(map);
      const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(map);
      tiles.on('tileerror', () => { status.textContent='Подложка карты недоступна. Точки и список остаются доступны.'; });
      clusters = L.markerClusterGroup({maxClusterRadius:45,iconCreateFunction:c=>L.divIcon({html:String(c.getChildCount()),className:'place-cluster',iconSize:[40,40]}),showCoverageOnHover:false});
      map.addLayer(clusters);
      map.on('resize', fit);
    }
    clusters.clearLayers();
    // found sights are shown by the point of their city, with their names in its window
    const byCity = new Map();
    sightsFound.forEach(s => { if (!byCity.has(s.p)) byCity.set(s.p, []); byCity.get(s.p).push(s); });
    const found = rows.filter(row => !row.hidden || (byCity.has(row.dataset.slug) && (!country.value || row.dataset.country === country.value)));
    const located = found.filter(row=>row.dataset.lat && row.dataset.lon);
    located.forEach(row => {
      const title=row.querySelector('.place-title').textContent, here=row.hidden ? byCity.get(row.dataset.slug) : null;
      const marker=L.marker([Number(row.dataset.lat),Number(row.dataset.lon)],{title,alt:title,icon:L.divIcon({className:'place-pin',html:'<span></span>',iconSize:[28,28]})});
      const box=document.createElement('div');box.className='place-pop';
      const name=document.createElement('a');name.className='place-pop-name';name.href=row.href;name.textContent=title;
      box.append(name);
      if (here) here.slice(0, 6).forEach(s => { const a=document.createElement('a');a.className='place-pop-sight';a.href=s.u;a.textContent=s.t;box.append(a); });
      if (here && here.length > 6) { const more=document.createElement('span');more.className='place-pop-more';more.textContent=`и ещё ${here.length - 6}`;box.append(more); }
      const go=document.createElement('a');go.className='place-pop-go';go.href=here ? here[0].u.replace(/#.*/, '') : row.href;go.textContent='К заметкам →';
      box.append(go);marker.bindPopup(box,{closeButton:true,autoPanPadding:[24,24]});
      clusters.addLayer(marker);
    });
    status.textContent = found.length === located.length ? 'Выберите точку на карте.' : `На карте ${located.length} из ${found.length} мест. Остальные — в списке.`;
    map.invalidateSize(); if(refit) fit();
  }

  // search: places in the list, and sights with their city below
  function filter() {
    const words=normalize(input.value.trim()).split(/\s+/).filter(Boolean);
    rows.forEach(row => { row.hidden = (country.value && row.dataset.country!==country.value) || !words.every(word=>normalize(row.dataset.search).includes(word)); });
    groups.forEach(group=>{group.hidden=![...group.querySelectorAll('[data-place-item]')].some(row=>!row.hidden);});
    const found = words.length ? sights.filter(s => (!country.value || s.k === country.value) && sightMatches(s, words))
      .sort((a, b) => a.t.localeCompare(b.t, 'ru')) : [];
    sightsList.replaceChildren(...found.map(s => { const a=document.createElement('a');a.className='place-row';a.href=s.u;
      const t=document.createElement('span');t.className='place-title';t.textContent=s.t;const c=document.createElement('span');c.className='place-orig';c.textContent=s.c;a.append(t,c);return a; }));
    sightsBox.hidden = !found.length; sightsFound = found;
    const n=visible().length;
    root.querySelector('#place-results').textContent = words.length ? `Найдено мест: ${n}${found.length ? `, достопримечательностей: ${found.length}` : ''}` : `Мест: ${n}`;
    root.querySelector('#places-empty').hidden = n !== 0 || found.length !== 0;
    if(mode==='map') renderMap();
    remember();
  }
  function setMode(m) {
    mode=m;
    root.querySelectorAll('[data-place-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.placeMode===m)));
    list.hidden=mode!=='list';panel.hidden=mode!=='map';filter(); // the map draws only what the search found
  }
  root.querySelectorAll('[data-place-mode]').forEach(button=>button.addEventListener('click',()=>setMode(button.dataset.placeMode)));
  root.querySelector('#place-map-reset').addEventListener('click',fit);
  input.addEventListener('input',filter);country.addEventListener('change',filter);

  // the country headings stay on top while scrolling; tapping one opens the list of countries to jump to
  root.querySelectorAll('.place-country-jump').forEach(b => b.addEventListener('click', () => jump.showModal()));
  let target = null;
  jump.addEventListener('click', e => {
    const b = e.target.closest('[data-jump]');
    target = b ? groups.find(x => x.dataset.country === b.dataset.jump) : null;
    if (target && target.hidden) { country.value = ''; filter(); }
    jump.close();
  });
  // scroll once the dialog has handed the focus back, or the browser scrolls back to the heading that opened it
  jump.addEventListener('close', () => { const g = target; target = null; if (!g) return;
    setTimeout(() => { g.querySelector('.place-country-jump').focus({ preventScroll: true }); g.scrollIntoView({ block: 'start' }); }, 30); });

  // coming back from a place page restores the search, the country and the view
  try { const s = JSON.parse(sessionStorage.getItem(key) || '{}'); if (s.q) input.value = s.q; if (s.c) country.value = s.c; if (s.m === 'map') mode = 'map'; } catch (e) {}
  if (mode === 'map') setMode('map'); else filter();
})();
