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
}

// Reports & Captures
async function fetchReports() {
    try {
        const response = await fetch('/api/reports');
        if (response.ok) {
            const data = await response.json();
            
            // The capture script returns a single text output containing both scopes and roof info.
            // We can display the raw text in the boxes, or try to split it.
            // For now, since the user wanted FRA400 in Box 6 and 75Q in Box 7, 
            // and Roof & Weather in Box 15, let's split the text based on headings.
            const captureText = data.capture || "";
            const forecastText = data.forecast || "";
            
            // Simple string splitting logic
            let fraPart = captureText.split("FRA400:")[1] || "";
            if (fraPart) fraPart = fraPart.split("* 75Q:")[0].trim();
            
            let q75Part = captureText.split("75Q:")[1] || "";
            if (q75Part) q75Part = q75Part.split("🏠")[0].trim();
            
            let roofPart = captureText.split("🏠")[1] || "";
            
            document.getElementById('fra400-capture-text').textContent = fraPart || "No data.";
            document.getElementById('q75-capture-text').textContent = q75Part || "No data.";
            document.getElementById('roof-info-text').textContent = roofPart ? "🏠" + roofPart : "No roof events recorded.";
            
            document.getElementById('forecast-text').textContent = forecastText || "Forecast unavailable.";
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
            const filename = response.headers.get("X-Original-Filename");
            if (filename) {
                document.getElementById(titleId).textContent = filename;
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
