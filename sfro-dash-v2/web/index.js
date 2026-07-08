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
    
    // 4. Update Atmospheric Data & Tests
    const checks = roof.checks || {};
    
    function setCheck(id, valStr, ok) {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = valStr;
            el.style.color = ok ? "#10b981" : "#ef4444";
        }
    }
    
    // Wind and Clouds from tests
    if (checks.wind) setCheck('test-wind', `${checks.wind.val} mph`, checks.wind.ok);
    
    // Wind Gust
    const wg = metrics.wind_gust_mph !== null ? `${metrics.wind_gust_mph.toFixed(1)} mph` : '--';
    if (checks.wind_gust) {
        setCheck('test-wg', wg, checks.wind_gust.ok);
    } else {
        const el = document.getElementById('test-wg');
        if (el) el.textContent = wg;
    }
    
    if (checks.clouds) setCheck('test-clouds', checks.clouds.val !== 'N/A' ? `${checks.clouds.val} %` : 'N/A', checks.clouds.ok);
    
    // Temp (Requested in C)
    const tempC = metrics.temp_c !== null ? `${metrics.temp_c.toFixed(1)} °C` : '--';
    if (checks.temperature) setCheck('test-temp', tempC, checks.temperature.ok);
    
    // Humidity
    if (checks.humidity) setCheck('test-hum', `${checks.humidity.val} %`, checks.humidity.ok);
    
    // Dew Point and Margin
    const dpC = metrics.dew_point_c !== null ? `${metrics.dew_point_c.toFixed(1)} °C` : '--';
    const dpMarginC = metrics.dew_point_margin_c !== null ? `${metrics.dew_point_margin_c.toFixed(1)} °C` : '--';
    
    if (document.getElementById('val-dp')) {
        document.getElementById('val-dp').textContent = dpC;
        // Make it inherit the normal white color, not explicitly color-coded unless it's a test
    }
    if (checks.dew_point_margin) setCheck('test-dp', dpMarginC, checks.dew_point_margin.ok);
    
    // Precip
    if (document.getElementById('val-precip')) {
        document.getElementById('val-precip').textContent = metrics.precip_mm !== null ? `${metrics.precip_mm.toFixed(2)} mm` : '--';
    }
    
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

            chunk.forEach(item => {
                const date = new Date(item.timestamp * 1000);
                const timeStr = new Intl.DateTimeFormat('en-US', {
                    hour: 'numeric',
                    timeZone: tz
                }).format(date);
                
                const emoji = getSymbolEmoji(item.symbol_code);

                timeCells += `<td>${timeStr}</td>`;
                condCells += `<td class="fc-emoji-cell" title="${item.symbol_code}">${emoji}</td>`;
                cloudCells += `<td>${item.cloud.toFixed(0)}%</td>`;
            });

            const table = document.createElement('table');
            table.className = 'forecast-table';
            table.innerHTML = `
                <tr>${timeCells}</tr>
                <tr>${condCells}</tr>
                <tr>${cloudCells}</tr>
            `;
            forecastTimeline.appendChild(table);
        }
    } else {
        forecastTimeline.innerHTML = '<div style="color: #ccc; font-size: 1rem; padding: 1rem;">Night forecast currently unavailable.</div>';
    }
}

// Auto-scale font size for roof status so it never clips
function fitRoofText() {
    const el = document.getElementById('roof-info-text');
    if (!el) return;
    
    // Reset to maximum desired size
    let fontSize = 1.6;
    el.style.fontSize = fontSize + 'rem';
    
    // Shrink while content overflows container
    while (el.scrollHeight > el.clientHeight && fontSize > 0.8) {
        fontSize -= 0.1;
        el.style.fontSize = fontSize + 'rem';
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
            
            // Adjust font size dynamically
            setTimeout(fitRoofText, 50);
            
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
                const targetEl = document.getElementById(`${scope}-target`);
                const titleEl = document.getElementById(titleId);
                
                if (parts.length > 1) {
                    if (targetEl) targetEl.textContent = `${scope.toUpperCase()} - ${parts[0]}`;
                    if (titleEl) titleEl.textContent = parts.slice(1).join(" - ");
                } else {
                    if (targetEl) targetEl.textContent = scope.toUpperCase();
                    if (titleEl) titleEl.textContent = filenameHeader;
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
    fetchFITSImage('75q', '75q-img', '75q-title');
    
    // Poll weather every 60s
    setInterval(fetchWeather, 60000);
    
    // Poll reports & images every 5 minutes
    setInterval(() => {
        fetchReports();
        fetchFITSImage('fra400', 'fra400-img', 'fra400-title');
        fetchFITSImage('75q', '75q-img', '75q-title');
    }, 300000);
    
    // Auto-update All-Sky Camera every 15s
    setInterval(() => {
        const allskyImg = document.getElementById('allsky-img');
        if (allskyImg) {
            allskyImg.src = `https://files-api.tx.starfront.space/status-assets-public/building-0009/allsky/images/image.jpg?t=${Date.now()}`;
        }
    }, 15000);
    
    // Handle resizing for roof text
    window.addEventListener('resize', fitRoofText);
});
