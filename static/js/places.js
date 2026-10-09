(() => {
  const root = document.getElementById('place-explorer');
  if (!root) return;
  const input = root.querySelector('#place-search'), country = root.querySelector('#place-country');
  const rows = [...root.querySelectorAll('[data-place-item]')], groups = [...root.querySelectorAll('[data-place-group]')];
  const dialog = root.querySelector('#place-dialog'), list = root.querySelector('#places-list'), panel = root.querySelector('#place-map-panel');
  const status = root.querySelector('#place-map-status');
  let map, clusters, mode = 'list', opener;
  const normalize = value => value.toLocaleLowerCase('ru').normalize('NFD').replace(/\p{M}/gu, '').replace(/ё/g, 'е');
  const visible = () => rows.filter(row => !row.hidden);
  function openPlace(row, trigger) {
    opener = trigger;
    root.querySelector('#place-dialog-title').textContent = row.querySelector('.place-title').textContent;
    root.querySelector('#place-dialog-country').textContent = row.dataset.country;
    root.querySelector('#place-dialog-content').replaceChildren(row.querySelector('.place-detail-content').cloneNode(true));
    dialog.showModal();
    document.body.classList.add('place-dialog-open');
  }
  rows.forEach(row => row.querySelector('summary').addEventListener('click', event => {
    if (!dialog.showModal) return;
    event.preventDefault(); openPlace(row, event.currentTarget);
  }));
  root.querySelector('#place-dialog-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) { const r=dialog.getBoundingClientRect(); if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom) dialog.close(); } });
  dialog.addEventListener('close', () => { document.body.classList.remove('place-dialog-open'); opener?.focus(); });
  function fit() {
    if (clusters?.getLayers().length) map.fitBounds(clusters.getBounds(), {padding:[30,30],maxZoom:12});
  }
  function renderMap(refit = true) {
    if (!window.L?.markerClusterGroup) { status.textContent='Карта не загрузилась. Все места доступны в списке.'; return; }
    if (!map) {
      map = L.map('place-map', {scrollWheelZoom:false,zoomControl:false}).setView([45,-25],3);
      L.control.zoom({zoomInTitle:'Приблизить',zoomOutTitle:'Отдалить'}).addTo(map);
      const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(map);
      tiles.on('tileerror', () => { status.textContent='Подложка карты недоступна. Точки и список глав остаются доступны.'; });
      clusters = L.markerClusterGroup({maxClusterRadius:45,iconCreateFunction:c=>L.divIcon({html:String(c.getChildCount()),className:'place-cluster',iconSize:[40,40]}),showCoverageOnHover:false});
      map.addLayer(clusters);
      map.on('resize', fit);
    }
    clusters.clearLayers();
    const found = visible(), located = found.filter(row=>row.dataset.lat && row.dataset.lon);
    located.forEach(row => {
      const title=row.querySelector('.place-title').textContent;
      const marker=L.marker([Number(row.dataset.lat),Number(row.dataset.lon)],{title,alt:title,icon:L.divIcon({className:'place-pin',html:'<span></span>',iconSize:[28,28]})});
      const tooltip=document.createElement('span');tooltip.textContent=title;marker.bindTooltip(tooltip);
      marker.on('click',()=>openPlace(row, marker.getElement()));clusters.addLayer(marker);
    });
    status.textContent = found.length === located.length ? 'Выберите точку — откроются главы об этом месте.' : `На карте ${located.length} из ${found.length} мест. Остальные доступны в списке.`;
    map.invalidateSize(); if(refit) fit();
  }
  function filter() {
    const words=normalize(input.value.trim()).split(/\s+/).filter(Boolean);
    rows.forEach(row => { row.hidden = (country.value && row.dataset.country!==country.value) || !words.every(word=>normalize(row.dataset.search).includes(word)); });
    groups.forEach(group=>{group.hidden=![...group.querySelectorAll('[data-place-item]')].some(row=>!row.hidden);});
    const n=visible().length;
    root.querySelector('#place-results').textContent=`Мест: ${n}`;
    root.querySelector('#places-empty').hidden=n!==0;
    if(mode==='map') renderMap();
  }
  root.querySelectorAll('[data-place-mode]').forEach(button=>button.addEventListener('click',()=>{
    mode=button.dataset.placeMode;
    root.querySelectorAll('[data-place-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
    list.hidden=mode!=='list';panel.hidden=mode!=='map';if(mode==='map') renderMap();
  }));
  root.querySelector('#place-map-reset').addEventListener('click',fit);
  input.addEventListener('input',filter);country.addEventListener('change',filter);filter();
})();
