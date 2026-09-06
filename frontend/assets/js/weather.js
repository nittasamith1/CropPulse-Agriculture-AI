/**
 * CropPulse - Weather Intelligence JS
 * Fetches weather data from backend and renders current conditions,
 * 7-day forecast, agricultural metrics, and weather alerts.
 */

const WEATHER_CODE_MAP = {
  0: { icon: "Sunny", label: "Clear sky" },
  1: { icon: "Mainly Clear", label: "Mainly clear" },
  2: { icon: "Partly Cloudy", label: "Partly cloudy" },
  3: { icon: "Overcast", label: "Overcast" },
  45: { icon: "Foggy", label: "Foggy" },
  51: { icon: "Light Drizzle", label: "Light drizzle" },
  61: { icon: "Rain", label: "Slight rain" },
  63: { icon: "Rain", label: "Moderate rain" },
  65: { icon: "Heavy Rain", label: "Heavy rain" },
  71: { icon: "Snow", label: "Slight snow" },
  80: { icon: "Showers", label: "Rain showers" },
  95: { icon: "Thunderstorm", label: "Thunderstorm" },
};

const WEATHER_EMOJI_MAP = {
  0: "&#9728;&#65039;", 1: "&#127780;&#65039;", 2: "&#9925;", 3: "&#9729;&#65039;",
  45: "&#127787;&#65039;", 51: "&#127782;&#65039;", 61: "&#127783;&#65039;",
  63: "&#127783;&#65039;", 65: "&#127783;&#65039;", 71: "&#10052;&#65039;",
  80: "&#127782;&#65039;", 95: "&#9928;&#65039;", 99: "&#9928;&#65039;"
};

function getWeatherInfo(code) {
  return {
    icon: WEATHER_EMOJI_MAP[code] || "&#127777;&#65039;",
    label: (WEATHER_CODE_MAP[code] || { label: "Unknown" }).label
  };
}

document.addEventListener("DOMContentLoaded", () => {
  Auth.requireAuth();
  const latInput = document.getElementById("lat-input");
  const lonInput = document.getElementById("lon-input");

  function detectLocation(callback) {
    if (!navigator.geolocation) {
      Utils.showToast("Geolocation not supported.", "warning"); return;
    }
    navigator.geolocation.getCurrentPosition(pos => {
      if (latInput) latInput.value = pos.coords.latitude.toFixed(6);
      if (lonInput) lonInput.value = pos.coords.longitude.toFixed(6);
      Utils.showToast("Location detected!", "success");
      if (callback) callback(pos.coords.latitude, pos.coords.longitude);
    }, () => Utils.showToast("Could not get location.", "error"));
  }

  document.getElementById("get-location-btn")?.addEventListener("click", () => detectLocation());
  document.getElementById("auto-detect-empty")?.addEventListener("click", () => detectLocation(fetchWeather));
  document.getElementById("fetch-weather-btn")?.addEventListener("click", () => {
    const lat = parseFloat(latInput?.value);
    const lon = parseFloat(lonInput?.value);
    if (isNaN(lat) || isNaN(lon)) {
      Utils.showToast("Please enter valid coordinates.", "warning"); return;
    }
    fetchWeather(lat, lon);
  });
});

async function fetchWeather(lat, lon) {
  const emptyState = document.getElementById("empty-state");
  emptyState?.classList.add("hidden");
  Utils.showLoading("Fetching weather data...");
  try {
    const [current, forecast] = await Promise.all([
      CropPulseAPI.weather.getCurrent(lat, lon),
      CropPulseAPI.weather.getForecast(lat, lon, 7),
    ]);
    Utils.hideLoading();
    renderCurrent(current);
    renderForecast(forecast);
    try {
      const agri = await CropPulseAPI.weather.getAgri(lat, lon);
      renderAgri(agri);
    } catch (e) { /* agri metrics optional */ }
  } catch (err) {
    Utils.hideLoading();
    Utils.showToast(err.message || "Failed to fetch weather.", "error");
    emptyState?.classList.remove("hidden");
  }
}

function renderCurrent(data) {
  const el = document.getElementById("current-weather");
  if (!el) return;
  const wInfo = getWeatherInfo(data.weather_code ?? 0);
  const setText = (id, val) => { const e = document.getElementById(id); if (e) e.innerHTML = val ?? "--"; };
  setText("weather-icon", wInfo.icon);
  setText("weather-temp", (data.temperature?.toFixed(1) ?? "--") + "&#176;C");
  setText("weather-condition", wInfo.label);
  setText("weather-location", "Lat: " + (data.latitude?.toFixed(4) ?? "--") + ", Lon: " + (data.longitude?.toFixed(4) ?? "--"));
  setText("met-humidity", (data.relative_humidity ?? "--") + "%");
  setText("met-wind", (data.wind_speed_10m?.toFixed(1) ?? "--") + " km/h");
  setText("met-precip", (data.precipitation?.toFixed(1) ?? "--") + " mm");
  setText("met-uv", data.uv_index ?? "--");
  el.classList.remove("hidden");
}

function renderForecast(data) {
  const section = document.getElementById("forecast-section");
  const container = document.getElementById("forecast-cards");
  if (!container || !data?.daily) return;
  const days = data.daily;
  const dates = days.time || [];
  container.innerHTML = dates.map((d, i) => {
    const wInfo = getWeatherInfo((days.weather_code || [])[i] ?? 0);
    const dayName = new Date(d).toLocaleDateString("en-IN", { weekday: "short", month: "short", day: "numeric" });
    const maxT = (days.temperature_2m_max || [])[i]?.toFixed(0) ?? "--";
    const minT = (days.temperature_2m_min || [])[i]?.toFixed(0) ?? "--";
    const rain = (days.precipitation_sum || [])[i]?.toFixed(1) ?? "0";
    return '<div class="col-6 col-md-4 col-lg-3"><div class="forecast-card">' +
      '<div class="forecast-day">' + dayName + '</div>' +
      '<div class="forecast-icon" style="font-size:1.8rem;">' + wInfo.icon + '</div>' +
      '<div class="forecast-temp">' + maxT + '&#176; / ' + minT + '&#176;</div>' +
      '<div class="forecast-rain">&#128167; ' + rain + ' mm</div>' +
      '<div style="font-size:0.7rem;color:var(--text-muted);margin-top:0.3rem;">' + wInfo.label + '</div>' +
      '</div></div>';
  }).join("");
  section.classList.remove("hidden");
}

function renderAgri(data) {
  const section = document.getElementById("agri-section");
  const container = document.getElementById("agri-metrics");
  if (!container) return;
  const metrics = [
    { label: "ET0 Evapotranspiration", val: (data.et0_fao_evapotranspiration?.toFixed(1) ?? "--") + " mm/day", icon: "&#128167;" },
    { label: "Sunshine Hours", val: (data.sunshine_duration?.toFixed(1) ?? "--") + " hrs", icon: "&#9728;&#65039;" },
    { label: "Soil Temp (6cm)", val: (data.soil_temperature_6cm?.toFixed(1) ?? "--") + "&#176;C", icon: "&#127777;&#65039;" },
  ];
  container.innerHTML = metrics.map(m =>
    '<div class="col-md-6 col-lg-4"><div class="agri-metric d-flex align-items-center gap-3">' +
    '<span style="font-size:1.8rem;">' + m.icon + '</span>' +
    '<div><div class="agri-metric-val">' + m.val + '</div><div class="agri-metric-lbl">' + m.label + '</div></div>' +
    '</div></div>'
  ).join("");
  section.classList.remove("hidden");
}
