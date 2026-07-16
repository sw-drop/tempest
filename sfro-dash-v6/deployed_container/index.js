/* SFRO-Dash V5 – Minimal JSON‑controlled dashboard
   All data pulled from the local `data/` folder    */

const DATA_PATH = '/data'; // points to /opt/data/scripts/sfro-dash-v5/data under the server

// --------- Utility helpers ---------
function getCloudColor(cloudPct) {
    if (cloudPct <= 30) return '#4CAF50';
    if (cloudPct <= 70) return '#FF9800';
    return '#FFFFFF';
}

function fitText(el, maxSize=1.2) {
    if (!el) return;
    let size = maxSize;
    el.style.fontSize = size + 'rem';
    while ((el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth) && size > 0.6) {
        size -= 0.1;
        el.style.fontSize = size + 'rem';
    }
}

// --------- Time zones ---------
function renderClocks() {
    const now = new Date();
    const uk = now.toLocaleTimeString('en-GB', {timeZone: 'Europe/London', hour12: false});
    const us = now.toLocaleTimeString('en-US', {timeZone: 'America/Chicago', hour12: false});
    document.getElementById('time-uk').textContent = uk;
    document.getElementById('time-us').textContent = us;
}

// --------- Weather and roof status ---------
async function renderWeather() {
    const r = await fetch(`${DATA_PATH}/observations.json?t=${Date.now()}`);
    if (!r.ok) { console.warn('weather fetch failed'); return; }
    const d = await r.json();void d;
    const proc = d.processed || {};
    const roofStat = d.physical_roof_status || 'Unknown';
    const header = document.getElementById("forecast-header");
    if (!header) return;
    header.textContent = `ROOF ${roofStat.toUpperCase()}`;
    header.style.color = roofStat !== 'Closed' ? 'green' : 'red';
}

// For brevity and clarity, the above code only outlines essential parts.
