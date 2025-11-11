const el = (q) => document.querySelector(q);
const resultsEl = el('#results');
const actionsEl = el('#actions');
const selectedCityEl = el('#selected-city');
const provinceSelect = el('#province-select');
const regencySelect = el('#regency-select');

let selectedCity = null;
let lastHourlyRows = null; // reserved for future use

// Handle search tabs
document.querySelectorAll('.search-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        // Remove active class from all tabs and panels
        document.querySelectorAll('.search-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.search-panel').forEach(p => p.classList.remove('active'));
        
        // Add active class to clicked tab and corresponding panel
        tab.classList.add('active');
        const targetPanel = document.getElementById(tab.dataset.target);
        if (targetPanel) {
            targetPanel.classList.add('active');
        }
    });
});

// Load provinces on page load
async function loadProvinces() {
    try {
        const timestamp = new Date().getTime();
        const response = await fetch(`/api/provinces?_=${timestamp}`, {
            cache: 'no-cache',
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        const provinces = data.results || [];
        
        // Sort provinces by name
        provinces.sort((a, b) => a.name.localeCompare(b.name));
        
        // Clear existing options
        provinceSelect.innerHTML = '<option value="">Pilih Provinsi...</option>';
        
        provinces.forEach(province => {
            const option = document.createElement('option');
            option.value = province.id;
            option.textContent = province.name;
            provinceSelect.appendChild(option);
        });
    } catch (error) {
        const errorOption = document.createElement('option');
        errorOption.value = "";
        errorOption.textContent = "Error loading provinces";
        provinceSelect.innerHTML = '';
        provinceSelect.appendChild(errorOption);
    }
}

// Load regencies when province is selected
async function loadRegencies(provinceCode) {
    regencySelect.innerHTML = '<option value="">Pilih Kota/Kabupaten...</option>';
    regencySelect.disabled = !provinceCode;
    
    if (!provinceCode) return;
    
    try {
        // Remove any prefix if present (e.g., "ID-" or similar)
        const cleanCode = provinceCode.replace(/^[A-Za-z]+-/, '');
        
        const timestamp = new Date().getTime();
        const response = await fetch(`/api/regencies/${cleanCode}?_=${timestamp}`, {
            cache: 'no-cache',
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        const regencies = data.results || [];
        
        // Sort regencies by name
        regencies.sort((a, b) => a.name.localeCompare(b.name));
        
        regencies.forEach(regency => {
            const option = document.createElement('option');
            // Try different possible property names for the name
            let name = regency.name || regency.regency_name || regency.nama;
            // Clean up the name for display
            const displayName = name;
            // Clean up the name for search (remove Kabupaten/Kota)
            name = name.replace(/^(Kabupaten|Kota)\s+/i, '');
            option.value = name;  // Use clean name for search
            option.textContent = displayName;  // Show full name in dropdown
            if (name) {
                regencySelect.appendChild(option);
            }
        });
        
        regencySelect.disabled = false;
    } catch (error) {
        const errorOption = document.createElement('option');
        errorOption.value = "";
        errorOption.textContent = "Error loading cities";
        regencySelect.innerHTML = '';
        regencySelect.appendChild(errorOption);
        regencySelect.disabled = true;
    }
}

// Event listeners for region selection
provinceSelect.addEventListener('change', (e) => {
    const selectedValue = e.target.value;
    if (selectedValue && selectedValue !== "") {
        loadRegencies(selectedValue);
    } else {
        // Reset regency select if no province is selected
        regencySelect.innerHTML = '<option value="">Pilih Kota/Kabupaten...</option>';
        regencySelect.disabled = true;
    }
});

regencySelect.addEventListener('change', (e) => {
    const selectedValue = e.target.value;
    if (selectedValue && selectedValue !== "") {
        // Set the search input value
        el('#q').value = selectedValue;
        
        // Switch to text search tab
        document.querySelectorAll('.search-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.search-panel').forEach(p => p.classList.remove('active'));
        
        const textSearchTab = document.querySelector('.search-tab[data-target="text-search"]');
        const textSearchPanel = document.getElementById('text-search');
        if (textSearchTab) textSearchTab.classList.add('active');
        if (textSearchPanel) textSearchPanel.classList.add('active');
        
        // Trigger the search
        el('#btn-search').click();
    }
});

// Load provinces on page load
loadProvinces();

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
  // Hide fun fact when searching for a new city
  const funFactEl = el('#city-funfact');
  if (funFactEl) {
    funFactEl.classList.add('hidden');
    const funFactText = el('#funfact-text');
    if (funFactText) funFactText.textContent = '-';
  }
  
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
    title: {
      text: 'Suhu Harian',
      fontSize: 16,
      subtitle: 'Minimum dan Maksimum',
      subtitleFontSize: 13,
      subtitleColor: '#666'
    },
    data: { values: rows },
    layer: [
      {
        // Area between min and max
        transform: [
          { calculate: "datum.temp_min", as: "lower" },
          { calculate: "datum.temp_max", as: "upper" }
        ],
        mark: { type: "area", opacity: 0.2, color: "#60a5fa" },
        encoding: {
          x: { field: "date", type: "temporal", title: "Tanggal", axis: { format: "%d %b", labelAngle: -45 } },
          y: { field: "lower", type: "quantitative", title: "Suhu (°C)" },
          y2: { field: "upper" }
        }
      },
      {
        transform: [{ fold: ['temp_min', 'temp_max'], as: ['metric', 'value'] }],
        mark: { 
          type: 'line',
          point: true,
          strokeWidth: 2
        },
        encoding: {
          x: { field: 'date', type: 'temporal', title: 'Tanggal' },
          y: { field: 'value', type: 'quantitative', title: 'Suhu (°C)' },
          color: {
            field: 'metric',
            type: 'nominal',
            title: 'Metrik',
            scale: {
              domain: ['temp_min', 'temp_max'],
              range: ['#3b82f6', '#ef4444']
            },
            legend: {
              title: null,
              labelExpr: "datum.label == 'temp_min' ? 'Minimum' : 'Maksimum'"
            }
          },
          tooltip: [
            { field: 'date', type: 'temporal', title: 'Tanggal', format: '%A, %d %B' },
            { field: 'metric', type: 'nominal', title: 'Metrik' },
            { field: 'value', type: 'quantitative', title: 'Suhu', format: '.1f' }
          ]
        }
      },
      { // hot day markers with improved tooltip
        transform: [{ filter: 'datum.is_hot_day === true' }],
        mark: { type: 'point', filled: true, color: '#dc2626', size: 100, shape: 'triangle-up' },
        encoding: {
          x: { field: 'date', type: 'temporal' },
          y: { field: 'temp_max', type: 'quantitative' },
          tooltip: [
            { field: 'date', type: 'temporal', title: 'Tanggal', format: '%A, %d %B' },
            { field: 'temp_max', type: 'quantitative', title: 'Suhu Maksimum', format: '.1f' }
          ]
        }
      }
    ],
    height: 240,
    config: {
      axis: {
        gridColor: '#f0f0f0',
        tickColor: '#888',
        labelFontSize: 11
      }
    }
  };
}

function dailyRainSpec(rows){
  return {
    $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
    title: {
      text: 'Curah Hujan Harian',
      fontSize: 16,
      subtitle: 'Total dalam milimeter (mm)',
      subtitleFontSize: 13,
      subtitleColor: '#666'
    },
    data: { values: rows },
    mark: {
      type: 'bar',
      cornerRadius: 4,
      tooltip: true
    },
    encoding: {
      x: {
        field: 'date',
        type: 'temporal',
        title: 'Tanggal',
        axis: {
          format: '%d %b',
          labelAngle: -45
        }
      },
      y: {
        field: 'total_rain',
        type: 'quantitative',
        title: 'Curah Hujan (mm)'
      },
      color: {
        field: 'total_rain',
        type: 'quantitative',
        title: 'Intensitas',
        scale: {
          type: 'threshold',
          domain: [5, 20, 50],
          range: ['#93c5fd', '#60a5fa', '#3b82f6', '#1d4ed8']
        },
        legend: { title: 'Intensitas Hujan' }
      },
      tooltip: [
        { field: 'date', type: 'temporal', title: 'Tanggal', format: '%A, %d %B' },
        { field: 'total_rain', type: 'quantitative', title: 'Curah Hujan', format: '.1f' }
      ]
    },
    height: 240,
    config: {
      axis: {
        gridColor: '#f0f0f0',
        tickColor: '#888',
        labelFontSize: 11
      }
    }
  };
}

function dailyPm25Spec(rows){
  return {
    $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
    title: {
      text: 'Kualitas Udara (PM2.5)',
      fontSize: 16,
      subtitle: 'Rata-rata harian dalam µg/m³',
      subtitleFontSize: 13,
      subtitleColor: '#666'
    },
    data: { values: rows },
    // compute a simple status field so tooltip can use it
    transform: [
      { calculate: "datum.pm25_avg <= 12 ? 'Baik' : datum.pm25_avg <= 35.4 ? 'Sedang' : 'Tidak Sehat'", as: 'pm25_status' }
    ],
    layer: [
      // Background areas for air quality levels (span full x domain)
      {
        data: {
          values: [
            { level: "Baik", start: 0, end: 12, color: "#22c55e" },
            { level: "Sedang", start: 12, end: 35.4, color: "#eab308" },
            { level: "Tidak Sehat", start: 35.4, end: 100, color: "#dc2626" }
          ]
        },
        mark: { type: "rect", opacity: 0.18 },
        encoding: {
          y: { field: "start", type: "quantitative" },
          y2: { field: "end" },
          color: { field: "level", type: "nominal", legend: { title: "Kategori" } }
        }
      },
      {
        mark: { 
          type: 'line',
          point: true,
          strokeWidth: 2,
          color: '#374151'
        },
        encoding: {
          x: { field: 'date', type: 'temporal', title: 'Tanggal', axis: { format: '%d %b', labelAngle: -45 } },
          y: { field: 'pm25_avg', type: 'quantitative', title: 'PM2.5 (µg/m³)' },
          tooltip: [
            { field: 'date', type: 'temporal', title: 'Tanggal', format: '%A, %d %B' },
            { field: 'pm25_avg', type: 'quantitative', title: 'PM2.5', format: '.1f' },
            { field: 'pm25_status', type: 'nominal', title: 'Status' }
          ]
        }
      },
      { // threshold lines with labels
        data: { values: [ { y: 12, label: "Batas Baik (12)" }, { y: 35.4, label: "Batas Sedang (35.4)" } ] },
        mark: { type: 'rule', strokeDash: [4,4], opacity: 0.6 },
        encoding: { y: { field: 'y', type: 'quantitative' }, tooltip: [ { field: 'label', type: 'nominal' } ] }
      },
      { // unhealthy markers with improved tooltips
        transform: [{ filter: 'datum.is_unhealthy_pm25 === true' }],
        mark: { type: 'point', filled: true, color: '#dc2626', size: 100 },
        encoding: {
          x: { field: 'date', type: 'temporal' },
          y: { field: 'pm25_avg', type: 'quantitative' },
          tooltip: [
            { field: 'date', type: 'temporal', title: 'Tanggal', format: '%A, %d %B' },
            { field: 'pm25_avg', type: 'quantitative', title: 'PM2.5', format: '.1f' },
            { value: "⚠️ Kualitas Udara Tidak Sehat", title: "Peringatan" }
          ]
        }
      }
    ],
    height: 240,
    config: { axis: { gridColor: '#f0f0f0', tickColor: '#888', labelFontSize: 11 } }
  };
}



async function loadDaily() {
  if (!selectedCity) return alert('Select a city first');
  
  // Hide all other sections first
  const todaySection = el('#today');
  const hourlySection = el('#hourly');
  if (todaySection) todaySection.classList.add('hidden');
  if (hourlySection) hourlySection.classList.add('hidden');
  
  // Show Daily section and refresh
  const dailySection = el('#daily');
  dailySection.classList.remove('hidden');
  el('#daily-summary').textContent = 'Loading...';
  const res = await fetch(`/data/daily?city=${encodeURIComponent(selectedCity)}&refresh=true`);
  const data = await res.json();
  const rows = data.data || [];
  if (!rows.length) {
    el('#daily-summary').textContent = 'No rows';
    return;
  }
  // summary with improved styling
  const maxTemp = Math.max(...rows.map(r => Number(r.temp_max ?? NaN)).filter(n => !Number.isNaN(n)));
  const pm25Avg = (rows.map(r => Number(r.pm25_avg ?? NaN)).filter(n => !Number.isNaN(n)).reduce((a,b)=>a+b,0) / rows.length);
  const hotDays = rows.filter(r => r.is_hot_day === true).length;
  
  const summaryHtml = `
    <div class="daily-stats">
      <div class="daily-stat-item temp">
        <div class="icon">🌡️</div>
        <div>
          <div class="label">Temperatur Maksimum</div>
          <div class="value">${fmt.format(maxTemp)}°C</div>
        </div>
      </div>
      <div class="daily-stat-item pm25">
        <div class="icon">💨</div>
        <div>
          <div class="label">Rata-rata PM2.5</div>
          <div class="value">${fmt.format(pm25Avg)} µg/m³</div>
        </div>
      </div>
      <div class="daily-stat-item hot">
        <div class="icon">🔥</div>
        <div>
          <div class="label">Hari Panas</div>
          <div class="value">${hotDays} hari</div>
        </div>
      </div>
    </div>
  `;
  el('#daily-summary').innerHTML = summaryHtml;
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
  
  // Hide all other sections first
  const dailySection = el('#daily');
  const hourlySection = el('#hourly');
  if (dailySection) dailySection.classList.add('hidden');
  if (hourlySection) hourlySection.classList.add('hidden');
  
  // Show Today section and refresh
  const todaySection = el('#today');
  todaySection.classList.remove('hidden');
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
  
  // Hide all other sections first
  const todaySection = el('#today');
  const dailySection = el('#daily');
  if (todaySection) todaySection.classList.add('hidden');
  if (dailySection) dailySection.classList.add('hidden');
  
  // Show Hourly section and refresh
  const hourlySection = el('#hourly');
  hourlySection.classList.remove('hidden');
  const res = await fetch(`/data/hourly?city=${encodeURIComponent(selectedCity)}&refresh=true`);
  const data = await res.json();
  const rows = data.data || [];
  lastHourlyRows = rows;
  renderHourlyList(rows);
}

async function doCompare() {
  // Enhanced compare: read controls and call backend, render Vega-Lite charts and textual summary
  const cmpInput = el('#cmp-input');
  const cmpMetric = el('#cmp-metric');
  const cmpNormalize = el('#cmp-normalize');
  const cmpSmooth = el('#cmp-smooth');
  const cmpRange = el('#cmp-range');
  const cmpLoading = el('#cmp-loading');
  const compareCount = el('#compare-count');
  const compareExplanation = el('#compare-explanation');
  const compareSummary = el('#compare-summary');

  function showLoading(show){ if (cmpLoading) cmpLoading.style.display = show ? 'inline' : 'none'; }

  function normalizeSeries(series){
    const byCity = {};
    series.forEach(d => { byCity[d.city] = byCity[d.city] || []; byCity[d.city].push(d.value); });
    const scales = {};
    Object.entries(byCity).forEach(([city, vals]) => { const min = Math.min(...vals), max = Math.max(...vals); scales[city] = {min, max, range: max - min || 1}; });
    return series.map(d => ({...d, value: (d.value - scales[d.city].min) / scales[d.city].range}));
  }

  function smoothSeries(series, window = 3){
    const out = [];
    const byCity = {};
    series.forEach(d => { byCity[d.city] = byCity[d.city] || []; byCity[d.city].push(d); });
    Object.values(byCity).forEach(arr => {
      for (let i = 0; i < arr.length; i++){
        const start = Math.max(0, i - Math.floor(window/2));
        const slice = arr.slice(start, start + window);
        const avg = slice.reduce((s,x)=>s + x.value, 0) / slice.length;
        out.push({...arr[i], value: avg});
      }
    });
    return out;
  }

  function aggregateSummary(citiesData, metricKey){
    const summary = citiesData.map(city => {
      const vals = (city.daily || []).map(d => d[metricKey]).filter(v => v != null).map(Number);
      const avg = vals.length ? vals.reduce((s,v)=>s+v,0)/vals.length : null;
      const max = vals.length ? Math.max(...vals) : null;
      return {city: city.name, avg, max};
    });
    summary.sort((a,b) => (b.avg || 0) - (a.avg || 0));
    return summary;
  }

  function buildVegaSpec(data, metricLabel){
    // Simplified spec without custom selection to avoid incompatible signal names.
    return {
      "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
      "data": { "values": data },
      "width": "container",
      "height": 220,
      "encoding": {
        "x": {"field":"date","type":"temporal","title":"Date"},
        "y": {"field":"value","type":"quantitative","title":metricLabel,"axis":{"grid":true}},
        "color": {"field":"city","type":"nominal","legend":{"orient":"top","columns":4}},
        "tooltip": [
          {"field":"city","type":"nominal","title":"City"},
          {"field":"date","type":"temporal","title":"Date"},
          {"field":"value","type":"quantitative","title":metricLabel}
        ]
      },
      "layer": [
        { "mark": {"type":"line","point":true,"strokeWidth":2,"opacity":0.95} }
      ],
      "config": {"axis": {"labelFontSize":11,"titleFontSize":12}}
    };
  }

  async function renderCompareAll(cities, rangeDays = 14){
    showLoading(true);
    compareExplanation.textContent = '';
    compareSummary.innerHTML = '';
    compareCount.textContent = `Comparing ${cities.length} city(ies)…`;
    try{
      const q = `/compare?cities=${encodeURIComponent(cities.join(','))}&days=${encodeURIComponent(rangeDays)}&refresh=false`;
      const res = await fetch(q);
      if (!res.ok) throw new Error('Backend compare failed: ' + res.status);
      const payload = await res.json();

      // Build per-metric series arrays
      const tempSeries = [];
      const pmSeries = [];
      let citiesData = [];

      if (Array.isArray(payload.cities)){
        citiesData = payload.cities;
        payload.cities.forEach(city => {
          (city.daily || []).forEach(d => {
            const date = d.date || d.day || d.datetime;
            if (d.temp_max != null) tempSeries.push({ date, city: city.name, value: Number(d.temp_max) });
            const pm = d.pm25_avg ?? d.pm25 ?? d.pm25_mean;
            if (pm != null) pmSeries.push({ date, city: city.name, value: Number(pm) });
          });
        });
      } else if (Array.isArray(payload.data) || Array.isArray(payload)){
        const rows = payload.data || payload;
        const by = {};
        rows.forEach(r => {
          const date = r.date || r.day || r.datetime;
          if (r.temp_max != null) tempSeries.push({ date, city: r.city || r.name || 'City', value: Number(r.temp_max) });
          const pm = r.pm25_avg ?? r.pm25 ?? r.pm25_mean ?? r.pm25Avg;
          if (pm != null) pmSeries.push({ date, city: r.city || r.name || 'City', value: Number(pm) });
          const name = r.city || r.name || 'City';
          by[name] = by[name] || { name, daily: [] };
          by[name].daily.push(r);
        });
        citiesData = Object.values(by);
      }

      // sort series
      tempSeries.sort((a,b) => new Date(a.date) - new Date(b.date));
      pmSeries.sort((a,b) => new Date(a.date) - new Date(b.date));

      // render both charts
      document.getElementById('compare-chart-temp').style.display = '';
      document.getElementById('compare-chart-pm25').style.display = '';
      const tempSpec = buildVegaSpec(tempSeries, 'Temperature (°C)');
      const pmSpec = buildVegaSpec(pmSeries, 'PM2.5 (µg/m³)');
      await Promise.all([
        vegaEmbed('#compare-chart-temp', tempSpec, { actions: false }),
        vegaEmbed('#compare-chart-pm25', pmSpec, { actions: false })
      ]);

      // summaries
      const tempSummary = aggregateSummary(citiesData, 'temp_max');
      const pmSummary = aggregateSummary(citiesData, 'pm25_avg');

      compareSummary.innerHTML = '';
      compareSummary.innerHTML += tempSummary.map(s => `<span class="pill">${s.city}: Temp avg ${s.avg != null ? s.avg.toFixed(1) + ' °C' : '—'}</span>`).join(' ');
      compareSummary.innerHTML += '<br/>' + pmSummary.map(s => `<span class="pill">${s.city}: PM2.5 avg ${s.avg != null ? s.avg.toFixed(1) + ' µg/m³' : '—'}</span>`).join(' ');

      // explanation combining both
      function mkText(top, second, bottom, label){
        if (!top) return '';
        let t = `${top.city} has the highest average ${label} (${top.avg != null ? top.avg.toFixed(1) : '—'}).`;
        if (second && top.avg != null && second.avg != null){
          const diff = ((top.avg - second.avg) / Math.abs(second.avg) * 100).toFixed(0);
          t += ` ${top.city} is ${Math.abs(diff)}% ${top.avg>second.avg? 'higher':'lower'} than ${second.city}.`;
        }
        t += ` ${bottom ? `${bottom.city} recorded the lowest average (${bottom.avg != null ? bottom.avg.toFixed(1) : '—'}).` : ''}`;
        return t;
      }

      const tTop = tempSummary[0], tSecond = tempSummary[1], tBottom = tempSummary[tempSummary.length-1];
      const pTop = pmSummary[0], pSecond = pmSummary[1], pBottom = pmSummary[pmSummary.length-1];
      compareExplanation.innerHTML = `<strong>Quick take</strong><div>${mkText(tTop,tSecond,tBottom,'Temperature (°C)')}</div><div>${mkText(pTop,pSecond,pBottom,'PM2.5 (µg/m³)')}</div>`;

      compareCount.textContent = `Compared ${citiesData.length} city(ies) over last ${rangeDays} days.`;

    } catch(err){
      console.error('Compare error', err);
      compareExplanation.innerHTML = `<span class="error">Failed to fetch comparison data. ${err.message}</span>`;
      document.getElementById('compare-chart-temp').innerHTML = '';
      document.getElementById('compare-chart-pm25').innerHTML = '';
    } finally {
      showLoading(false);
    }
  }

  // handler: read UI and call renderCompareAll
  const raw = el('#cmp-input').value || '';
  const cities = raw.split(',').map(s=>s.trim()).filter(Boolean);
  if (!cities.length){ el('#compare-explanation').innerHTML = '<span class="error">Please enter one or more city names separated by commas.</span>'; return; }
  const rangeDays = 14; // default
  renderCompareAll(cities, rangeDays);
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

// AI status removed - no longer needed

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
