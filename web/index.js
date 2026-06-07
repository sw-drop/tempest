// Configuration and State
const API_URL = '/api/observations';
let pollInterval = 60; 
let nextPollSeconds = pollInterval;
let timerId = null;
let currentData = null; // Cache the latest observations

// Local Settings from Storage (persisted)
let tempUnit = localStorage.getItem('temp_unit') || 'C'; // 'C' or 'F'
let windUnit = localStorage.getItem('wind_unit') || 'mps'; // 'mps', 'kmh', 'mph', 'kn'

// DOM Elements
const stationNameEl = document.getElementById('station-name');
const pollTimerEl = document.getElementById('poll-timer');
const lastUpdateEl = document.getElementById('last-update-ts');

// Toggles
const btnTempC = document.getElementById('btn-temp-c');
const btnTempF = document.getElementById('btn-temp-f');
const btnWindMps = document.getElementById('btn-wind-mps');
const btnWindKmh = document.getElementById('btn-wind-kmh');
const btnWindMph = document.getElementById('btn-wind-mph');
const btnWindKn = document.getElementById('btn-wind-kn');

// Roof Banner
const roofBannerEl = document.getElementById('roof-status-banner');
const roofTitleEl = document.getElementById('roof-status-title');
const roofDescEl = document.getElementById('roof-status-desc');

// Checklist rules
const ruleElements = {
    wind: document.getElementById('rule-wind'),
    wind_gust: document.getElementById('rule-wind-gust'),
    temperature: document.getElementById('rule-temperature'),
    humidity: document.getElementById('rule-humidity'),
    dew_point_margin: document.getElementById('rule-dew-point-margin'),
    clouds: document.getElementById('rule-clouds')
};

// Warnings
const warningsBox = document.getElementById('safety-warnings');
const warningsList = document.getElementById('warnings-list');

// Wind Card
const compassNeedle = document.getElementById('compass-needle');
const windSpeedEl = document.getElementById('wind-speed-val');
const windGustEl = document.getElementById('wind-gust-val');
const windDirDegEl = document.getElementById('wind-dir-deg');
const windUnitLabel = document.getElementById('wind-unit-label');

// Metric Cards
const tempEl = document.getElementById('temp-val');
const tempAltEl = document.getElementById('temp-alt-val');
const humidityEl = document.getElementById('humidity-val');
const dewPointEl = document.getElementById('dew-point-val');
const dpMarginEl = document.getElementById('dp-margin-val');
const dpMarginStatusEl = document.getElementById('dp-margin-status');
const solarEl = document.getElementById('solar-val');
const uvEl = document.getElementById('uv-val');
const pressureEl = document.getElementById('pressure-val');
const pressureHpaEl = document.getElementById('pressure-hpa-val');
const precipEl = document.getElementById('precip-val');
const lightningEl = document.getElementById('lightning-val');

// Forecast Elements
const forecastHeader = document.getElementById('forecast-header');
const forecastTimeline = document.getElementById('forecast-timeline');

// Helper unit conversions
function formatTemp(valC, valF, unit = tempUnit) {
    if (valC === null || valC === undefined) return '--';
    return unit === 'C' ? `${valC.toFixed(1)}°C` : `${valF.toFixed(1)}°F`;
}

function formatTempDiff(valF, unit = tempUnit) {
    if (valF === null || valF === undefined) return '--';
    if (unit === 'C') {
        const valC = valF * (5/9); // delta temp conversion
        return `${valC.toFixed(1)}°C`;
    }
    return `${valF.toFixed(1)}°F`;
}

function convertWind(mps, unit = windUnit) {
    if (mps === null || mps === undefined) return 0;
    switch(unit) {
        case 'mps': return mps;
        case 'kmh': return mps * 3.6;
        case 'mph': return mps * 2.23694;
        case 'kn': return mps * 1.94384;
        default: return mps;
    }
}

function getWindUnitLabel(unit = windUnit) {
    switch(unit) {
        case 'mps': return 'm/s';
        case 'kmh': return 'km/h';
        case 'mph': return 'mph';
        case 'kn': return 'kn';
        default: return 'm/s';
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

// Fetch observations
async function fetchWeather() {
    if (document.hidden) return;
    
    try {
        const response = await fetch(API_URL);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        currentData = await response.json();
        updateDashboard();
        resetTimer();
    } catch (error) {
        console.error("Failed to fetch observations:", error);
        setBannerError(error.message);
    }
}

// Reset Countdown Timer
function resetTimer() {
    nextPollSeconds = pollInterval;
    updateTimerDisplay();
}

// Update Timer Display
function updateTimerDisplay() {
    if (document.hidden) {
        pollTimerEl.textContent = "Standby";
    } else {
        pollTimerEl.textContent = `Next update: ${nextPollSeconds}s`;
    }
}

// Set Banner to Error State
function setBannerError(message) {
    roofBannerEl.className = 'roof-banner status-warning';
    roofTitleEl.textContent = 'CONNECTION ERROR';
    roofDescEl.textContent = `Unable to fetch from API: ${message}. Retrying in ${nextPollSeconds}s...`;
}

// Render Dashboard based on selected units
function updateDashboard() {
    if (!currentData) return;

    // 1. Header Information
    stationNameEl.textContent = currentData.station_name || `ID: ${currentData.station_id}`;
    
    if (currentData.raw && currentData.raw.poll_interval) {
        pollInterval = currentData.raw.poll_interval;
    }

    const lastFetched = currentData.last_fetched;
    if (lastFetched) {
        const date = new Date(lastFetched * 1000);
        lastUpdateEl.textContent = `Last fetch: ${date.toLocaleTimeString()} (${date.toLocaleDateString()})`;
    }

    const proc = currentData.processed || {};
    const metrics = proc.metrics || {};
    const roof = currentData.roof_status || {};
    const daytimeStatus = proc.daytime_status || 'nighttime';

    // 2. Primary Status Banner (Daytime Override vs Nighttime safety rules)
    if (daytimeStatus === 'daytime') {
        roofBannerEl.className = 'roof-banner status-allowed';
        roofTitleEl.textContent = 'Daytime: Safe conditions';
        roofDescEl.textContent = 'Astronomical observations suspended during daylight hours. Observatory closed.';
    } else {
        if (roof.allowed) {
            roofBannerEl.className = 'roof-banner status-allowed';
            roofTitleEl.textContent = 'Safe conditions';
            roofDescEl.textContent = 'All safety thresholds are clear. Safe for night observing.';
        } else {
            roofBannerEl.className = 'roof-banner status-warning';
            roofTitleEl.textContent = 'Unsafe conditions';
            if (roof.reasons && roof.reasons.length > 0) {
                roofDescEl.textContent = `Triggered closure: ${roof.reasons.join(', ')}.`;
            } else {
                roofDescEl.textContent = 'Observatory safety rules violated. Roof must remain closed.';
            }
        }
    }

    // Update Checklist rule labels dynamically depending on temperature unit
    const tempRuleName = ruleElements.temperature.querySelector('.rule-name');
    const dpMarginRuleName = ruleElements.dew_point_margin.querySelector('.rule-name');
    if (tempUnit === 'C') {
        tempRuleName.innerHTML = 'Temperature (-2.2&deg;C - 43.3&deg;C)';
        dpMarginRuleName.innerHTML = 'Dew Point Margin (&ge; 1.7&deg;C)';
    } else {
        tempRuleName.innerHTML = 'Temperature (28&deg;F - 110&deg;F)';
        dpMarginRuleName.innerHTML = 'Dew Point Margin (&ge; 3&deg;F)';
    }

    // 3. Update Roof Opening Tests Checklist
    const checks = roof.checks || {};
    for (const [key, check] of Object.entries(checks)) {
        const el = ruleElements[key];
        if (el) {
            const valSpan = el.querySelector('.rule-value');
            const indicator = el.querySelector('.rule-indicator');
            
            if (check.val !== undefined && check.val !== null) {
                if (key === 'temperature') {
                    const valC = (check.val - 32) * 5/9;
                    valSpan.textContent = tempUnit === 'C' ? `${valC.toFixed(1)} °C` : `${check.val}°F`;
                } else if (key === 'dew_point_margin') {
                    const valC = check.val * 5/9;
                    valSpan.textContent = tempUnit === 'C' ? `${valC.toFixed(1)} °C` : `${check.val}°F`;
                } else if (key === 'wind' || key === 'wind_gust') {
                    const mps = check.val / 2.23694;
                    const converted = convertWind(mps);
                    valSpan.textContent = `${converted.toFixed(1)} ${getWindUnitLabel()}`;
                } else if (key === 'clouds') {
                    valSpan.textContent = check.val !== 'N/A' ? `${check.val}%` : 'N/A';
                } else {
                    valSpan.textContent = `${check.val} ${check.unit || ''}`;
                }
                
                if (check.ok) {
                    el.className = 'rule-pass';
                } else {
                    el.className = 'rule-fail';
                }
            } else {
                valSpan.textContent = check.reason || 'N/A';
                el.className = 'rule-fail';
            }
        }
    }

    // Warnings Box (Only active at night)
    if (daytimeStatus === 'nighttime' && !roof.allowed && roof.reasons && roof.reasons.length > 0) {
        warningsBox.classList.remove('hidden');
        warningsList.innerHTML = '';
        roof.reasons.forEach(reason => {
            const li = document.createElement('li');
            li.textContent = reason;
            warningsList.appendChild(li);
        });
    } else {
        warningsBox.classList.add('hidden');
    }

    // 4. Update Core Metric Cards

    // Air Temperature
    tempEl.textContent = formatTemp(metrics.temp_c, metrics.temp_f);
    tempAltEl.textContent = tempUnit === 'C' ? `${metrics.temp_f.toFixed(1)} °F` : `${metrics.temp_c.toFixed(1)} °C`;

    // Humidity
    humidityEl.textContent = metrics.humidity !== null ? `${metrics.humidity}%` : '--%';

    // Dedicated Dew Point & Margin Card
    dewPointEl.textContent = formatTemp(metrics.dew_point_c, metrics.dew_point_f);
    
    const dpMarginVal = tempUnit === 'C' ? metrics.dew_point_margin_c : metrics.dew_point_margin_f;
    if (dpMarginVal !== null && dpMarginVal !== undefined) {
        dpMarginEl.textContent = `${dpMarginVal.toFixed(1)}°${tempUnit}`;
        const isSafe = tempUnit === 'C' ? dpMarginVal >= 1.67 : dpMarginVal >= 3.0;
        dpMarginStatusEl.textContent = isSafe ? 'Safe' : 'Risk';
        dpMarginStatusEl.style.color = isSafe ? '#10b981' : '#ef4444';
    } else {
        dpMarginEl.textContent = '--';
        dpMarginStatusEl.textContent = '--';
        dpMarginStatusEl.style.color = 'inherit';
    }

    // Wind Dynamics Card
    const windSpeedConverted = convertWind(metrics.wind_avg_mps);
    const windGustConverted = convertWind(metrics.wind_gust_mps);
    const windUnitLabelStr = getWindUnitLabel();

    windSpeedEl.textContent = windSpeedConverted.toFixed(1);
    windUnitLabel.textContent = windUnitLabelStr;
    windGustEl.textContent = `${windGustConverted.toFixed(1)} ${windUnitLabelStr}`;
    windDirDegEl.textContent = metrics.wind_dir !== null ? `${metrics.wind_dir}°` : '--°';
    
    if (metrics.wind_dir !== null) {
        compassNeedle.style.transform = `rotate(${metrics.wind_dir}deg)`;
    }

    // Solar & UV (Compact style)
    solarEl.textContent = metrics.solar_radiation !== null ? metrics.solar_radiation : '--';
    uvEl.textContent = `UV: ${metrics.uv !== null ? metrics.uv.toFixed(1) : '--'}`;

    // Pressure (Compact style)
    pressureEl.textContent = metrics.pressure_inhg !== null ? metrics.pressure_inhg.toFixed(2) : '--';
    pressureHpaEl.textContent = metrics.pressure_hpa !== null ? `${metrics.pressure_hpa.toFixed(0)} hPa` : '-- hPa';

    // Rain & Storms (Compact style)
    precipEl.textContent = metrics.precip_in !== null ? metrics.precip_in.toFixed(3) : '--';
    lightningEl.textContent = `Storms: ${metrics.lightning_count_1h !== null ? metrics.lightning_count_1h : '--'} strikes`;

    // 5. Update Night Conditions Forecast Timeline
    const nightForecast = proc.night_forecast || [];
    
    if (daytimeStatus === 'daytime') {
        forecastHeader.textContent = "Observing Night Forecast (Upcoming)";
    } else {
        forecastHeader.textContent = "Observing Night Forecast (Remaining)";
    }

    if (nightForecast && nightForecast.length > 0) {
        forecastTimeline.innerHTML = '';
        nightForecast.forEach(item => {
            const date = new Date(item.timestamp * 1000);
            const timeStr = date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
            
            const tempStr = tempUnit === 'C' ? `${item.temp_c.toFixed(1)}°C` : `${item.temp_f.toFixed(1)}°F`;
            const emoji = getSymbolEmoji(item.symbol_code);
            const isCloudUnsafe = item.cloud > 60;

            const itemDiv = document.createElement('div');
            itemDiv.className = 'forecast-item';
            itemDiv.innerHTML = `
                <span class="fc-time">${timeStr}</span>
                <span class="fc-icon" title="${item.symbol_code}">${emoji}</span>
                <span class="fc-cloud ${isCloudUnsafe ? 'cloud-unsafe' : ''}">${item.cloud.toFixed(0)}%</span>
                <span class="fc-temp">${tempStr}</span>
            `;
            forecastTimeline.appendChild(itemDiv);
        });
    } else {
        forecastTimeline.innerHTML = '<div class="forecast-loading">Night forecast currently unavailable.</div>';
    }
}

// Timer loop
function startTimer() {
    if (timerId) clearInterval(timerId);
    
    timerId = setInterval(() => {
        if (document.hidden) {
            updateTimerDisplay();
            return;
        }

        nextPollSeconds--;
        if (nextPollSeconds <= 0) {
            fetchWeather();
        } else {
            updateTimerDisplay();
        }
    }, 1000);
}

// Setup Toggles Event Listeners
function setupToggleListeners() {
    btnTempC.addEventListener('click', () => {
        tempUnit = 'C';
        localStorage.setItem('temp_unit', 'C');
        btnTempC.classList.add('active');
        btnTempF.classList.remove('active');
        updateDashboard();
    });
    btnTempF.addEventListener('click', () => {
        tempUnit = 'F';
        localStorage.setItem('temp_unit', 'F');
        btnTempF.classList.add('active');
        btnTempC.classList.remove('active');
        updateDashboard();
    });

    const windButtons = {
        mps: btnWindMps,
        kmh: btnWindKmh,
        mph: btnWindMph,
        kn: btnWindKn
    };

    Object.entries(windButtons).forEach(([unitKey, btnEl]) => {
        btnEl.addEventListener('click', () => {
            windUnit = unitKey;
            localStorage.setItem('wind_unit', unitKey);
            
            Object.values(windButtons).forEach(btn => btn.classList.remove('active'));
            btnEl.classList.add('active');
            
            updateDashboard();
        });
    });
}

// Apply initial button active classes
function initToggleStates() {
    if (tempUnit === 'C') {
        btnTempC.classList.add('active');
        btnTempF.classList.remove('active');
    } else {
        btnTempF.classList.add('active');
        btnTempC.classList.remove('active');
    }

    btnWindMps.classList.remove('active');
    btnWindKmh.classList.remove('active');
    btnWindMph.classList.remove('active');
    btnWindKn.classList.remove('active');

    const activeWindBtn = document.getElementById(`btn-wind-${windUnit}`);
    if (activeWindBtn) {
        activeWindBtn.classList.add('active');
    }
}

// Page Visibility API handler
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        updateTimerDisplay();
    } else {
        fetchWeather();
        startTimer();
    }
});

// Initialize on Load
window.addEventListener('DOMContentLoaded', () => {
    initToggleStates();
    setupToggleListeners();
    fetchWeather();
    startTimer();
});
