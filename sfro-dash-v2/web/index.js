// State
let pollInterval = 60; 
let currentData = null;

// Clocks
function updateClocks() {
    const now = new Date();
    
    // UK Time (Europe/London)
    const ukTimeStr = new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Europe/London',
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
    }).format(now);
    document.getElementById('time-uk').textContent = ukTimeStr;

    // US Central Time (America/Chicago)
    const usTimeStr = new Intl.DateTimeFormat('en-US', {
        timeZone: 'America/Chicago',
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
    }).format(now);
    document.getElementById('time-us').textContent = usTimeStr;
}
setInterval(updateClocks, 1000);
updateClocks();

// Weather & Roof Data (from Tempest API)
async function fetchWeather() {
    try {
        const response = await fetch('/api/observations');
        if (!response.ok) throw new Error("HTTP error");
        currentData = await response.json();
        
        document.getElementById('conn-status').textContent = "Connected";
        document.getElementById('conn-status').style.color = "#10b981";
        
        updateWeatherUI();
    } catch (error) {
        console.error("Failed to fetch weather:", error);
        document.getElementById('conn-status').textContent = "Offline";
        document.getElementById('conn-status').style.color = "#ef4444";
    }
}

// Map MET Norway symbol codes to emojis
function getSymbolEmoji(symbolCode) {
    if (!symbolCode) return '☁️';
    const code = symbolCode.toLowerCase();
    if (code.includes('clearsky')) return code.includes('night') ? '🌙' : '☀️';
    if (code.includes('fair')) return code.includes('night') ? '🌙' : '🌤️';
    if (code.includes('partlycloudy')) return '⛅';
    if (code.includes('cloudy')) return '☁️';
    if (code.includes('rain') || code.includes('sleet')) return '🌧️';
    if (code.includes('snow')) return '❄️';
    if (code.includes('thunder')) return '⛈️';
    if (code.includes('fog')) return '🌫️';
    return '☁️';
}

function updateWeatherUI() {
    if (!currentData) return;
    const proc = currentData.processed || {};
    const metrics = proc.metrics || {};
    const roof = currentData.roof_status || {};
    
    // Metrics
    document.getElementById('val-temp').textContent = metrics.temp_c !== null ? `${metrics.temp_c.toFixed(1)}°C` : '--';
    document.getElementById('val-hum').textContent = metrics.humidity !== null ? `${metrics.humidity}%` : '--';
    document.getElementById('val-dp').textContent = metrics.dew_point_c !== null ? `${metrics.dew_point_c.toFixed(1)}°C` : '--';
    document.getElementById('val-press').textContent = metrics.pressure_hpa !== null ? `${metrics.pressure_hpa.toFixed(0)} hPa` : '--';
    document.getElementById('val-solar').textContent = metrics.solar_radiation !== null ? `${metrics.solar_radiation} W/m²` : '--';
    document.getElementById('val-precip').textContent = metrics.precip_in !== null ? `${metrics.precip_in.toFixed(2)} in` : '--';
    
    // Roof Opening Tests
    const checks = roof.checks || {};
    
    function setCheck(id, valStr, ok) {
        const el = document.getElementById(id);
        el.textContent = valStr;
        el.style.color = ok ? "#10b981" : "#ef4444";
    }
    
    if (checks.wind) setCheck('test-wind', `${checks.wind.val} mph`, checks.wind.ok);
    if (checks.temperature) setCheck('test-temp', `${checks.temperature.val} °F`, checks.temperature.ok);
    if (checks.humidity) setCheck('test-hum', `${checks.humidity.val} %`, checks.humidity.ok);
    if (checks.dew_point_margin) setCheck('test-dp', `${checks.dew_point_margin.val} °F`, checks.dew_point_margin.ok);
    if (checks.clouds) setCheck('test-clouds', checks.clouds.val !== 'N/A' ? `${checks.clouds.val} %` : 'N/A', checks.clouds.ok);
    
    // 5. Update Night Conditions Forecast
    const nightForecast = proc.night_forecast || [];
    const forecastTimeline = document.getElementById('forecast-timeline');
    
    if (nightForecast && nightForecast.length > 0) {
        forecastTimeline.innerHTML = '';
        const tz = (currentData.raw && currentData.raw.timezone) || 'America/Chicago';
        
        // Chunk forecast size based on screen width
        const width = window.innerWidth;
        const chunkSize = width < 600 ? 5 : (width < 900 ? 8 : 12);
        
        for (let i = 0; i < nightForecast.length; i += chunkSize) {
            const chunk = nightForecast.slice(i, i + chunkSize);
            
            let timeCells = `<td class="fc-row-label">Time</td>`;
            let condCells = `<td class="fc-row-label">Cond</td>`;
            let cloudCells = `<td class="fc-row-label">Cloud</td>`;
            let tempCells = `<td class="fc-row-label">Temp</td>`;

            chunk.forEach(item => {
                const date = new Date(item.timestamp * 1000);
                const timeStr = new Intl.DateTimeFormat('en-US', {
                    hour: 'numeric',
                    timeZone: tz
                }).format(date);
                
                const tempStr = `${item.temp_c.toFixed(0)}°C`;
                const emoji = getSymbolEmoji(item.symbol_code);

                timeCells += `<td>${timeStr}</td>`;
                condCells += `<td class="fc-emoji-cell" title="${item.symbol_code}">${emoji}</td>`;
                cloudCells += `<td>${item.cloud.toFixed(0)}%</td>`;
                tempCells += `<td>${tempStr}</td>`;
            });

            const table = document.createElement('table');
            table.className = 'forecast-table';
            table.innerHTML = `
                <tr>${timeCells}</tr>
                <tr>${condCells}</tr>
                <tr>${cloudCells}</tr>
                <tr>${tempCells}</tr>
            `;
            forecastTimeline.appendChild(table);
        }
    } else {
        forecastTimeline.innerHTML = '<div style="color: #ccc; font-size: 1rem; padding: 1rem;">Night forecast currently unavailable.</div>';
    }
}

// Reports & Captures
async function fetchReports() {
    try {
        const response = await fetch('/api/reports');
        if (response.ok) {
            const data = await response.json();
            
            const captureText = data.capture || "";
            const forecastText = data.forecast || "";
            
            let fraPart = captureText.split("FRA400:")[1] || "";
            if (fraPart) fraPart = fraPart.split("* 75Q:")[0].trim();
            
            let q75Part = captureText.split("75Q:")[1] || "";
            if (q75Part) q75Part = q75Part.split("🏠")[0].trim();
            
            let roofPart = captureText.split("🏠")[1] || "";
            if (roofPart) {
                // Strip out "Roof & Weather" header and "• Latest Roof:"
                roofPart = roofPart.replace("Roof & Weather", "").replace("• Latest Roof:", "").trim();
            }
            
            document.getElementById('fra400-capture-text').textContent = fraPart || "No data.";
            document.getElementById('q75-capture-text').textContent = q75Part || "No data.";
            
            // For roof, just display the payload without the emoji if they wanted it gone
            document.getElementById('roof-info-text').textContent = roofPart || "No roof events recorded.";
            
            document.getElementById('forecast-text').textContent = forecastText;
        }
    } catch (e) {
        console.error("Reports error", e);
    }
}

// FITS Images
async function fetchFITSImage(scope, imgId, titleId) {
    try {
        const response = await fetch(`/api/latest-image/${scope}?t=${Date.now()}`);
        if (response.ok) {
            const blob = await response.blob();
            const objectURL = URL.createObjectURL(blob);
            document.getElementById(imgId).src = objectURL;
            const filenameHeader = response.headers.get("X-Original-Filename");
            if (filenameHeader) {
                const parts = filenameHeader.split(" - ");
                if (parts.length > 1) {
                    const targetEl = document.getElementById(`${scope}-target`);
                    const titleEl = document.getElementById(titleId);
                    if (targetEl) targetEl.textContent = parts[0];
                    if (titleEl) titleEl.textContent = parts.slice(1).join(" - ");
                } else {
                    document.getElementById(titleId).textContent = filenameHeader;
                }
            }
        }
    } catch (e) {
        console.error("FITS error", e);
    }
}

// Initialization and intervals
window.addEventListener('DOMContentLoaded', () => {
    fetchWeather();
    fetchReports();
    fetchFITSImage('fra400', 'fra400-img', 'fra400-title');
    fetchFITSImage('75q', 'q75-img', 'q75-title');
    
    // Poll weather every 60s
    setInterval(fetchWeather, 60000);
    
    // Poll reports & images every 5 minutes
    setInterval(() => {
        fetchReports();
        fetchFITSImage('fra400', 'fra400-img', 'fra400-title');
        fetchFITSImage('75q', 'q75-img', 'q75-title');
    }, 300000);
    
    // Auto-update All-Sky Camera every 15s
    setInterval(() => {
        const allskyImg = document.getElementById('allsky-img');
        if (allskyImg) {
            allskyImg.src = `https://files-api.tx.starfront.space/status-assets-public/building-0009/allsky/images/image.jpg?t=${Date.now()}`;
        }
    }, 15000);
});
