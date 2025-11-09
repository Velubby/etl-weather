const el = (q) => document.querySelector(q);
const resultsEl = el('#results');
const actionsEl = el('#actions');
const selectedCityEl = el('#selected-city');

let selectedCity = null;
let lastHourlyRows = null; // reserved for future use

// Simple DOM helpers and UI state

const fmt = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 });
const dtFmt = new Intl.DateTimeFormat(undefined, { year: 'numeric', month: 'short', day: '2-digit' });
const tmFmt = new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit' });
// short hour like `1 am`, `4 pm`
function shortHour(d){
  if (!d) return '-';
  const h24 = d.getHours();
  const h12 = h24 % 12 || 12;
  const suf = h24 < 12 ? 'am' : 'pm';
  return `${h12} ${suf}`;
}

// Text label for weather code (Open-Meteo)
function weatherDesc(code){
  const c = Number(code);
  if (Number.isNaN(c)) return '';
  if (c === 0) return 'Clear';
  if (c === 1) return 'Mostly Clear';
  if (c === 2) return 'Partly Cloudy';
  if (c === 3) return 'Cloudy';
  if (c === 45 || c === 48) return 'Fog';
  if (c >= 51 && c <= 57) return 'Drizzle';
  if (c >= 61 && c <= 67) return 'Rain';
  if (c >= 71 && c <= 77) return 'Snow';
  if (c >= 80 && c <= 82) return 'Showers';
  if (c === 85 || c === 86) return 'Snow Showers';
  if (c === 95) return 'Thunderstorms';
  if (c === 96 || c === 99) return 'Thunderstorms';
  return '';
}

function windDirInfo(deg){
  const d = Number(deg);
  if (Number.isNaN(d)) return { arrow: uiIcon('wind', 18), label: '' };
  const dirs = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'];
  const arrows = ['↑','↗','↗','↗','→','↘','↘','↘','↓','↙','↙','↙','←','↖','↖','↖'];
  const idx = Math.round(((d % 360) + 360) % 360 / 22.5) % 16;
  return { arrow: arrows[idx], label: dirs[idx] };
}

// Debounce helper and keyboard navigation state for interactive search
function debounce(fn, wait = 300){ let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), wait); }; }
let resultsIndex = -1;
function updateActiveResult(){
  const items = Array.from(resultsEl.querySelectorAll('li'));
  items.forEach((li, i) => li.classList.toggle('active', i === resultsIndex));
  if (resultsIndex >= 0 && items[resultsIndex]){
    items[resultsIndex].scrollIntoView({ block: 'nearest' });
  }
}

async function fetchCityFunFact(city, opts = {}) {
  const { fast = true, fresh = false } = opts;
  const loadingEl = el('#funfact-loading');
  const refreshBtn = el('#btn-funfact-refresh');
  try {
    if (loadingEl) loadingEl.style.display = 'inline';
    if (refreshBtn) refreshBtn.disabled = true;
    const params = new URLSearchParams();
    if (fresh) params.set('fresh', '1');
    else if (fast) params.set('fast', '1');
    params.set('t', String(Date.now()));
    const response = await fetch(`/city/funfact/${encodeURIComponent(city)}?${params.toString()}`);
    if (!response.ok) throw new Error('Failed to fetch fun fact');
    const data = await response.json();
    el('#city-funfact').classList.remove('hidden');
    el('#funfact-text').textContent = data.fun_fact || '-';
  } catch (err) {
    console.error('Error fetching fun fact:', err);
    // keep previous text if any; just show container hidden if none
    const cur = el('#funfact-text')?.textContent || '';
    if (!cur) {
      el('#city-funfact').classList.add('hidden');
      el('#funfact-text').textContent = '-';
    }
  } finally {
    if (loadingEl) loadingEl.style.display = 'none';
    if (refreshBtn) refreshBtn.disabled = false;
  }
}

function pm25Category(v){
  if (v == null || Number.isNaN(Number(v))) return 'Unknown';
  const x = Number(v);
  if (x <= 12) return 'Good';
  if (x <= 35.4) return 'Moderate';
  if (x <= 55.4) return 'Unhealthy (Sensitive)';
  if (x <= 150.4) return 'Unhealthy';
  if (x <= 250.4) return 'Very Unhealthy';
  return 'Hazardous';
}

// Unified inline SVG icon set
function svgWrap(inner, size = 18){
  return `<svg class="i" width="${size}" height="${size}" viewBox="0 0 24 24" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><g fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">${inner}</g></svg>`;
}

function uiIcon(name, size = 18){
  switch(name){
    case 'clock':
      return svgWrap('<circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/>', size);
    case 'thermo':
      return svgWrap('<path d="M14 14V6a2 2 0 1 0-4 0v8"/><circle cx="12" cy="17" r="4"/><path d="M12 12v5"/>', size);
    case 'droplet':
      return svgWrap('<path d="M12 3c4 6 6 7.5 6 10a6 6 0 1 1-12 0c0-2.5 2-4 6-10z"/>', size);
    case 'humidity':
      return svgWrap('<path d="M12 3c4 6 6 7.5 6 10a6 6 0 1 1-12 0c0-2.5 2-4 6-10z"/><path d="M10 12l4 3"/>', size);
    case 'rain':
      return svgWrap('<path d="M6 18h10a4 4 0 0 0 0-8 6 6 0 0 0-11 2"/><path d="M8 20l1-2M12 21l1-2M16 20l1-2"/>', size);
    case 'dew':
      return svgWrap('<path d="M12 3c4 6 6 7.5 6 10a6 6 0 1 1-12 0c0-2.5 2-4 6-10z"/><path d="M7 20h10"/>', size);
    case 'wind':
      return svgWrap('<path d="M3 12h10a3 3 0 1 0 0-6"/><path d="M3 18h13a2 2 0 1 0 0-4"/>', size);
    case 'lungs':
      return svgWrap('<path d="M12 6v13"/><path d="M12 12c-3 0-6-1.8-6-5V7"/><path d="M12 12c3 0 6-1.8 6-5V7"/>', size);
    case 'pm':
      // particle cluster for PM2.5
      return svgWrap('<circle cx="8" cy="9" r="2"/><circle cx="12.5" cy="11" r="1.7"/><circle cx="16" cy="9" r="1.8"/><circle cx="10.5" cy="15" r="1.6"/><circle cx="14.5" cy="15" r="1.4"/>', size);
    case 'sunrise':
      return svgWrap('<path d="M3 20h18"/><path d="M4 16h16"/><path d="M12 10a4 4 0 0 1 4 4H8a4 4 0 0 1 4-4z"/><path d="M12 6v3"/>', size);
    case 'sunset':
      return svgWrap('<path d="M3 20h18"/><path d="M4 16h16"/><path d="M12 14a4 4 0 0 0 4-4H8a4 4 0 0 0 4 4z"/><path d="M12 11v-3"/>', size);
    default:
      return svgWrap('<circle cx="12" cy="12" r="9"/>', size);
  }
}

function weatherIcon(code){
  const c = Number(code);
  if (Number.isNaN(c)) return '🌡️';
  if (c === 0) return '☀️';
  if (c === 1) return '🌤️';
  if (c === 2) return '⛅';
  if (c === 3) return '☁️';
  if (c === 45 || c === 48) return '🌫️';
  if ((c >= 51 && c <= 57)) return '🌦️';
  if ((c >= 61 && c <= 67)) return '🌧️';
  if ((c >= 71 && c <= 77)) return '🌨️';
  if ((c >= 80 && c <= 82)) return '🌧️';
  if (c === 85 || c === 86) return '🌨️';
  if (c === 95) return '⛈️';
  if (c === 96 || c === 99) return '⛈️';
  return '🌡️';
}

function badgeClassForPm25(v){
  if (v == null) return 'badge';
  const x = Number(v);
  if (Number.isNaN(x)) return 'badge';
  if (x <= 12) return 'badge good';
  if (x <= 35.4) return 'badge';
  if (x <= 55.4) return 'badge warn';
  return 'badge bad';
}

// removed legacy table renderer (now using cards/charts for presentation)

function renderDailyCards(rows){
  const container = el('#daily-cards');
  container.innerHTML = '';
  const limit = Math.min(rows.length, 8);
  for (let i = 0; i < limit; i++){
    const r = rows[i];
    const dateStr = r.date ? dtFmt.format(new Date(r.date)) : '-';
    const pm = Number(r.pm25_avg);
    const cat = pm25Category(pm);
    const badgeCls = badgeClassForPm25(pm);
    const sunrise = r.sunrise ? tmFmt.format(new Date(r.sunrise)) : null;
    const sunset = r.sunset ? tmFmt.format(new Date(r.sunset)) : null;
    const alerts = [];
    if (r.is_hot_day === true) alerts.push('🔥 Hot');
    if (r.is_heavy_rain === true) alerts.push('🌧️ Heavy rain');
    if (r.is_unhealthy_pm25 === true) alerts.push('⚠️ PM2.5');
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
          <h3>${dateStr}</h3>
          <div class="with-icon">${uiIcon('thermo', 20)}<strong>${fmt.format(r.temp_min ?? NaN)}°C</strong> → <strong>${fmt.format(r.temp_max ?? NaN)}°C</strong></div>
          <div class="muted with-icon">${uiIcon('rain', 20)}<span>Rain: ${fmt.format(r.total_rain ?? 0)} mm</span></div>
          <div class="badges"><span class="${badgeCls} with-icon">${uiIcon('pm', 18)}<span>PM2.5: ${fmt.format(pm)} (${cat})</span></span></div>
          ${sunrise || sunset ? `<div class="muted with-icon">${uiIcon('sunrise', 20)}<span>${sunrise ?? '-'}<\/span> / ${uiIcon('sunset', 20)}<span>${sunset ?? '-'}<\/span><\/div>` : ''}
      ${alerts.length ? `<div class="badges">${alerts.map(a=>`<span class="badge warn">${a}</span>`).join(' ')}</div>` : ''}
    `;
    container.appendChild(card);
  }
}

// Reset/hide views when city changes to avoid stale content
function resetViewsOnCityChange(){
  // Hide Daily and clear content
  const daily = el('#daily');
  if (daily) {
    daily.classList.add('hidden');
    const ds = el('#daily-summary'); if (ds) ds.textContent = '';
    const dc = el('#daily-cards'); if (dc) dc.innerHTML = '';
    const charts = ['#daily-chart-temp','#daily-chart-rain','#daily-chart-pm25','#daily-chart-feels','#daily-chart-dew'];
    ['#daily-chart-temp','#daily-chart-rain','#daily-chart-pm25'].forEach(id => { const c = el(id); if (c) c.innerHTML = ''; });
  }
  // Hide Hourly and clear list
  const hourly = el('#hourly');
  if (hourly) {
    hourly.classList.add('hidden');
    const hl = el('#hourly-list'); if (hl) hl.innerHTML = '';
  }
  // Hide and clear Today mini strip; hero/details will be reloaded
  const mini = el('#today-mini');
  if (mini){ mini.innerHTML = ''; mini.classList.add('hidden'); }
  lastHourlyRows = null;
}

function renderHourlyList(rows){
  const container = el('#hourly-list');
  container.innerHTML = '';
  const limit = Math.min(rows.length, 24);
  for (let i = 0; i < limit; i++){
    const r = rows[i];
    const t = r.time ? new Date(r.time) : null;
    const timeStr = t ? shortHour(t) : '-';
    const code = r.wcode ?? r.weather_code;
    const icon = weatherIcon(code);
      const row = document.createElement('div');
      row.className = 'hourly-row line';
      const rainValMm = r.rain ?? r.precip ?? r.precipitation; // optional rain (mm)
      const windDeg = r.wind_dir ?? r.wind_direction ?? r.wind_deg;
      const windInfo = windDirInfo(windDeg);
      const tempVal = fmt.format(r.temp ?? r.feels_like ?? NaN);
      const humCol = r.rh!=null ? `<div class="col humidity with-icon" title="Relative humidity (%)">${uiIcon('humidity', 18)}<span>${fmt.format(r.rh)}%</span></div>` : `<div class="col humidity muted" title="Relative humidity (%)">-</div>`;
      const rainText = (rainValMm!=null ? `${fmt.format(rainValMm)} mm` : null);
      const rainTitle = 'Precipitation (mm)';
      const rainCol = rainText!=null ? `<div class="col rain with-icon" title="${rainTitle}">${uiIcon('rain', 18)}<span>${rainText}</span></div>` : `<div class="col rain muted" title="${rainTitle}">-</div>`;
      const windCol = r.wind!=null ? `<div class="col wind" title="Wind speed (km/h)"><span class="arrow">${windInfo.arrow}</span> <span>${windInfo.label? windInfo.label + ' ' : ''}${fmt.format(r.wind)} km/h</span></div>` : `<div class="col wind muted" title="Wind speed (km/h)">-</div>`;
    row.innerHTML = `
      <div class="col time">${timeStr}</div>
      <div class="col temp">${tempVal}°</div>
      <div class="col icon-text"><span class="icon">${icon}</span><span class="desc">${weatherDesc(code) || ''}</span></div>
      ${rainCol}
      ${humCol}
      ${windCol}
    `;
    container.appendChild(row);
  }
}

async function doSearch() {
  const q = el('#q').value.trim();
  if (!q) return;
  resultsEl.innerHTML = '<li>Searching...</li>';
  try {
    const res = await fetch(`/search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    const items = data.results || [];
    resultsEl.innerHTML = '';
    items.forEach((it) => {
      const li = document.createElement('li');
      const qsafe = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const label = `${it.name}${it.admin1?`, ${it.admin1}`:''}${it.country?` ${it.country}`:''}`.trim();
      const rx = new RegExp(qsafe, 'i');
      li.innerHTML = label.replace(rx, (m) => `<span class="highlight">${m}</span>`);
      li.addEventListener('click', () => {
        selectedCity = it.name;
        selectedCityEl.textContent = selectedCity;
        // default to fast mode for immediate UX
        fetchCityFunFact(selectedCity, { fast: true, fresh: false });
        actionsEl.classList.remove('hidden');
        // close dropdown on select
        resultsEl.classList.remove('open');
        resultsEl.innerHTML = '';
        // reset/hide other panels and mini strip
        resetViewsOnCityChange();
        // auto-load Today view and scroll into view
        loadToday();
        const today = document.querySelector('#today');
        if (today) today.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
      resultsEl.appendChild(li);
    });
    if (items.length){
      resultsIndex = 0; updateActiveResult();
      resultsEl.classList.add('open');
    } else {
      resultsIndex = -1; resultsEl.classList.remove('open');
    }
  } catch (e) {
    resultsEl.innerHTML = `<li>Error: ${e}</li>`;
    resultsEl.classList.add('open');
  }
}

function dailyTempSpec(rows){
  return {
    $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
    description: 'Daily Min/Max Temperature',
    data: { values: rows },
    layer: [
      {
        transform: [{ fold: ['temp_min','temp_max'], as: ['metric','value'] }],
        mark: { type: 'line', point: true },
        encoding: {
          x: { field: 'date', type: 'temporal', title: 'Date' },
          y: { field: 'value', type: 'quantitative', title: 'Temp (°C)' },
          color: { field: 'metric', type: 'nominal', title: 'Metric', sort: ['temp_min','temp_max'] },
          tooltip: [ {field:'date', type:'temporal'}, {field:'metric'}, {field:'value', type:'quantitative', format:'.1f'} ]
        }
      },
      { // hot day markers
        transform: [{ filter: 'datum.is_hot_day === true' }],
        mark: { type: 'point', filled: true, color: '#dc2626', size: 80, shape: 'triangle-up' },
        encoding: { x: { field: 'date', type: 'temporal' }, y: { field: 'temp_max', type: 'quantitative' }, tooltip: ['date','temp_max'] }
      },
      { // heavy rain markers
        transform: [{ filter: 'datum.is_heavy_rain === true' }],
        mark: { type: 'point', filled: true, color: '#2563eb', size: 80, shape: 'circle' },
        encoding: { x: { field: 'date', type: 'temporal' }, y: { field: 'temp_min', type: 'quantitative' }, tooltip: ['date','total_rain'] }
      }
    ],
    height: 240
  };
}

function dailyRainSpec(rows){
  return {
    $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
    description: 'Daily Rain',
    data: { values: rows },
    mark: 'bar',
    encoding: {
      x: { field: 'date', type: 'temporal', title: 'Date' },
      y: { field: 'total_rain', type: 'quantitative', title: 'Rain (mm)' },
      tooltip: [ {field:'date', type:'temporal'}, {field:'total_rain', type:'quantitative', format:'.1f'} ]
    },
    height: 240
  };
}

function dailyPm25Spec(rows){
  return {
    $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
    description: 'Daily PM2.5 Avg',
    data: { values: rows },
    layer: [
      {
        mark: { type: 'line', point: true, color: 'crimson' },
        encoding: {
          x: { field: 'date', type: 'temporal', title: 'Date' },
          y: { field: 'pm25_avg', type: 'quantitative', title: 'PM2.5 (µg/m³)' },
          tooltip: [ {field:'date', type:'temporal'}, {field:'pm25_avg', type:'quantitative', format:'.1f'} ]
        }
      },
      { data: { values: [{y:12}, {y:35.4}] }, mark: { type: 'rule', strokeDash: [4,4], color: '#888' }, encoding: { y: { field: 'y', type: 'quantitative' } } },
      { // unhealthy markers
        transform: [{ filter: 'datum.is_unhealthy_pm25 === true' }],
        mark: { type: 'point', filled: true, color: '#ea580c', size: 80, shape: 'square' },
        encoding: { x: { field: 'date', type: 'temporal' }, y: { field: 'pm25_avg', type: 'quantitative' }, tooltip: ['date','pm25_avg'] }
      }
    ],
    height: 240
  };
}



async function loadDaily() {
  if (!selectedCity) return alert('Select a city first');
  el('#daily').classList.remove('hidden');
  el('#daily-summary').textContent = 'Loading...';
  const res = await fetch(`/data/daily?city=${encodeURIComponent(selectedCity)}&refresh=true`);
  const data = await res.json();
  const rows = data.data || [];
  if (!rows.length) {
    el('#daily-summary').textContent = 'No rows';
    return;
  }
  // summary
  const maxTemp = Math.max(...rows.map(r => Number(r.temp_max ?? NaN)).filter(n => !Number.isNaN(n)));
  const pm25Avg = (rows.map(r => Number(r.pm25_avg ?? NaN)).filter(n => !Number.isNaN(n)).reduce((a,b)=>a+b,0) / rows.length);
  const hotDays = rows.filter(r => r.is_hot_day === true).length;
  el('#daily-summary').textContent = `Max temp: ${fmt.format(maxTemp)} °C • Avg PM2.5: ${fmt.format(pm25Avg)} • Hot days: ${hotDays}`;
    // charts
  try {
    await vegaEmbed('#daily-chart-temp', dailyTempSpec(rows), { actions: false });
    await vegaEmbed('#daily-chart-rain', dailyRainSpec(rows), { actions: false });
    await vegaEmbed('#daily-chart-pm25', dailyPm25Spec(rows), { actions: false });
  } catch (e) {
    // quietly skip chart rendering errors in production UI
  }  // friendly cards
  renderDailyCards(rows);

  // raw table intentionally omitted to keep UI focused
}

async function loadToday(){
  if (!selectedCity) return alert('Select a city first');
  el('#today').classList.remove('hidden');
  const hero = el('#today-hero');
  const details = el('#today-details');
  hero.innerHTML = 'Loading…';
  details.innerHTML = '';
  try{
    const [hRes, dRes] = await Promise.all([
      fetch(`/data/hourly?city=${encodeURIComponent(selectedCity)}&refresh=true`),
      fetch(`/data/daily?city=${encodeURIComponent(selectedCity)}&refresh=false`)
    ]);
    const hData = await hRes.json();
    const dData = await dRes.json();
    const hours = hData.data || [];
    const days = dData.data || [];
    const now = Date.now();
    // nearest hour to now
    let cur = null, bestDiff = Infinity;
    for (const r of hours){
      const t = r.time ? new Date(r.time).getTime() : NaN;
      if (!Number.isNaN(t)){
        const diff = Math.abs(now - t);
        if (diff < bestDiff){ bestDiff = diff; cur = r; }
      }
    }
    // today's daily row (by date string)
    const todayStr = new Date().toISOString().slice(0,10);
    const day = days.find(r => (r.date || '').slice(0,10) === todayStr) || days[0] || {};

  const icon = weatherIcon(cur?.wcode ?? cur?.weather_code);
    const curTemp = cur?.temp ?? cur?.feels_like ?? NaN;
    const feels = cur?.feels_like;
    const rh = cur?.rh;
    const wind = cur?.wind;
    const pm = cur?.pm25;
    const pmBadge = pm!=null ? badgeClassForPm25(pm) : 'badge';
    hero.innerHTML = `
      <div class="icon weather">${icon}</div>
      <div>
        <div class="temp-big with-icon">${uiIcon('thermo', 22)}<span>${fmt.format(curTemp)}°</span></div>
        <div class="muted with-icon">${uiIcon('clock', 18)}<span>${selectedCity}${feels!=null?` • Feels like ${fmt.format(feels)}°`:''}</span></div>
      </div>
      <div class="badges">${pm!=null?`<span class="${pmBadge} with-icon">${uiIcon('pm', 18)}<span>PM2.5 ${fmt.format(pm)}</span></span>`:''}</div>
    `;
    // details tiles similar to weather.com today breakdown
    const tiles = [];
    if (day.temp_max!=null || day.temp_min!=null) tiles.push({label:`${uiIcon('thermo',18)} High / Low`, value:`${fmt.format(day.temp_max ?? NaN)}° / ${fmt.format(day.temp_min ?? NaN)}°`});
  if (day.total_rain!=null) tiles.push({label:`${uiIcon('rain',18)} Rain (today)`, value:`${fmt.format(day.total_rain)} mm`});
  if (rh!=null) tiles.push({label:`${uiIcon('humidity',18)} Humidity`, value:`${fmt.format(rh)}%`});
    if (wind!=null) tiles.push({label:`${uiIcon('wind',18)} Wind`, value:`${fmt.format(wind)} km/h`});
    if (day.sunrise || day.sunset){
      const tm = new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit' });
      tiles.push({label:`${uiIcon('sunrise',18)} Sunrise`, value: day.sunrise? tm.format(new Date(day.sunrise)) : '-' });
      tiles.push({label:`${uiIcon('sunset',18)} Sunset`, value: day.sunset? tm.format(new Date(day.sunset)) : '-' });
    }
  if (cur?.dew_point!=null) tiles.push({label:`${uiIcon('dew',18)} Dew Point`, value:`${fmt.format(cur.dew_point)}°`});

    details.innerHTML = tiles.map(t=>`<div class="tile"><div class="muted">${t.label}</div><div><strong>${t.value}</strong></div></div>`).join('');

    // Mini next-hours strip (next 6)
    const mini = el('#today-mini');
    if (mini){
      const nowTs = Date.now();
      const next = (hours||[]).filter(r => r.time && new Date(r.time).getTime() >= nowTs).slice(0,6);
      mini.innerHTML = next.map(r => {
        const t = r.time ? shortHour(new Date(r.time)) : '-';
        const w = weatherIcon(r.wcode ?? r.weather_code);
        const tv = r.temp ?? r.feels_like;
        const rainMm = r.rain ?? r.precip ?? r.precipitation;
        const txt = (rainMm!=null? `${fmt.format(rainMm)}mm` : '-');
        const title = 'Precipitation (mm)';
        return `<div class="mini-item" title="${title}"><div class="t">${t}</div><div class="w">${w}</div><div class="v">${fmt.format(tv)}°</div><div class="r with-icon">${uiIcon('rain',16)}<span>${txt}</span></div></div>`;
      }).join('');
      mini.classList.toggle('hidden', next.length === 0);
    }
  }catch(e){
    hero.innerHTML = 'Failed to load today.';
  }
}

async function loadHourly() {
  if (!selectedCity) return alert('Select a city first');
  el('#hourly').classList.remove('hidden');
  const res = await fetch(`/data/hourly?city=${encodeURIComponent(selectedCity)}&refresh=true`);
  const data = await res.json();
  const rows = data.data || [];
  lastHourlyRows = rows;
  renderHourlyList(rows);
}

async function doCompare() {
  const v = el('#cmp-input').value.trim();
  if (!v) return;
  const res = await fetch(`/compare?cities=${encodeURIComponent(v)}&refresh=false`);
  const data = await res.json();
  const rows = data.data || [];
  el('#compare-count').textContent = `Rows: ${rows.length}`;
  // charts (temp_max & pm25_avg by city)
  const tempSpec = {
    $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
    description: 'Temp Max per City', data: { values: rows },
    mark: { type: 'line', point: true },
    encoding: {
      x: { field: 'date', type: 'temporal' },
      y: { field: 'temp_max', type: 'quantitative', title: 'Temp Max (°C)' },
      color: { field: 'city', type: 'nominal' },
      tooltip: ['date', 'city', {field:'temp_max', type:'quantitative', format:'.1f'}]
    },
    height: 240
  };
  const pmSpec = {
    $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
    description: 'PM2.5 Avg per City', data: { values: rows },
    mark: { type: 'line', point: true, color: 'crimson' },
    encoding: {
      x: { field: 'date', type: 'temporal' },
      y: { field: 'pm25_avg', type: 'quantitative', title: 'PM2.5 (µg/m³)' },
      color: { field: 'city', type: 'nominal' },
      tooltip: ['date', 'city', {field:'pm25_avg', type:'quantitative', format:'.1f'}]
    },
    height: 240
  };
  try {
    await vegaEmbed('#compare-chart-temp', tempSpec, { actions: false });
    await vegaEmbed('#compare-chart-pm25', pmSpec, { actions: false });
  } catch (e) {
    // quietly skip chart rendering errors in production UI
  }
  // summary pills per city
  const byCity = new Map();
  for (const r of rows){
    const c = r.city || 'City';
    if (!byCity.has(c)) byCity.set(c, []);
    byCity.get(c).push(r);
  }
  const pillsEl = el('#compare-summary');
  pillsEl.innerHTML = '';
  for (const [city, arr] of byCity.entries()){
    const tmax = arr.map(r=>Number(r.temp_max??NaN)).filter(n=>!Number.isNaN(n));
    const p25 = arr.map(r=>Number(r.pm25_avg??NaN)).filter(n=>!Number.isNaN(n));
    const tavg = tmax.length? tmax.reduce((a,b)=>a+b,0)/tmax.length : NaN;
    const pavg = p25.length? p25.reduce((a,b)=>a+b,0)/p25.length : NaN;
    const pill = document.createElement('span');
    pill.className = 'pill';
    pill.innerHTML = `<strong>${city}</strong> • TempMax Avg: ${fmt.format(tavg)}°C • <span class="${badgeClassForPm25(pavg)}">PM2.5 Avg: ${fmt.format(pavg)}</span>`;
    pillsEl.appendChild(pill);
  }

  // raw compare table intentionally omitted to keep UI focused
}

el('#btn-search').addEventListener('click', doSearch);
const btnToday = el('#btn-today');
if (btnToday) btnToday.addEventListener('click', loadToday);
el('#btn-daily').addEventListener('click', loadDaily);
el('#btn-hourly').addEventListener('click', loadHourly);
el('#btn-compare').addEventListener('click', doCompare);

// Fun fact: fresh variant button
const btnFunfact = el('#btn-funfact-refresh');
if (btnFunfact){
  btnFunfact.addEventListener('click', () => {
    if (!selectedCity) return alert('Select a city first');
    fetchCityFunFact(selectedCity, { fresh: true });
  });
}

// AI status: fetch /ai/status and update pill
async function fetchAiStatus() {
  const pill = el('#ai-status');
  if (!pill) return;
  try {
    const res = await fetch('/ai/status?t=' + Date.now());
    if (!res.ok) throw new Error('status non-ok');
    const j = await res.json();
    // decide class by generate_ok and api_key presence
    const ok = j.generate_ok === true && (j.api_key_present === true || j.sdk_ok === true);
    const warn = j.generate_ok === false && (j.api_key_present === true || j.sdk_ok === true);
    const model = j.model_used || (Array.isArray(j.models) && j.models[0]) || 'unknown';
    const text = `AI: ${model.split('/').pop()}`;
    const dot = ok ? 'ok' : (warn ? 'warn' : 'bad');
    pill.classList.remove('ok','warn','bad');
    pill.classList.add(ok ? 'ok' : (warn ? 'warn' : 'bad'));
    pill.innerHTML = `<span class="dot ${dot}"></span>${text}`;
    pill.title = `AI status — model: ${model}\ngenerate_ok: ${j.generate_ok}\nsdk_ok: ${j.sdk_ok}\napi_key_present: ${j.api_key_present}${j.error?`\nerror: ${j.error}`:''}`;
  } catch (e){
    pill.classList.remove('ok','warn'); pill.classList.add('bad');
    pill.innerHTML = `<span class="dot bad"></span>AI: unavailable`;
    pill.title = `AI status unreachable`;
  }
}

// initial fetch and periodic refresh
try { fetchAiStatus(); setInterval(fetchAiStatus, 60 * 1000); } catch (e) {}

// Interactive search: debounce + keyboard navigation
const searchInput = el('#q');
searchInput.addEventListener('keydown', (e) => {
  const items = Array.from(resultsEl.querySelectorAll('li'));
  if (e.key === 'Enter'){
    if (resultsIndex>=0 && items[resultsIndex]){ items[resultsIndex].click(); }
    else { doSearch(); }
  } else if (e.key === 'ArrowDown'){
    resultsIndex = Math.min((resultsIndex<0? -1:resultsIndex)+1, items.length-1); updateActiveResult(); e.preventDefault();
  } else if (e.key === 'ArrowUp'){
    resultsIndex = Math.max(resultsIndex-1, 0); updateActiveResult(); e.preventDefault();
  } else if (e.key === 'Escape'){
    resultsEl.classList.remove('open'); resultsEl.innerHTML = '';
  }
});
searchInput.addEventListener('input', debounce(() => {
  if (searchInput.value.trim()){
    resultsEl.innerHTML = '<li>Searching…</li>';
    resultsEl.classList.add('open');
    doSearch();
  } else {
    resultsEl.innerHTML = '';
    resultsEl.classList.remove('open');
  }
}, 300));

// Close search results when clicking outside the searchbox
document.addEventListener('click', (e) => {
  const box = document.querySelector('.searchbox');
  if (box && !box.contains(e.target)){
    resultsEl.classList.remove('open');
    resultsEl.innerHTML = '';
  }
});

// end of app.js
