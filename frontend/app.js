const form = document.querySelector("#flight-search-form");
const sourceInput = document.querySelector("#source");
const destinationInput = document.querySelector("#destination");
const searchButton = document.querySelector("#search-button");
const message = document.querySelector("#message");
const resultCount = document.querySelector("#result-count");
const tableBody = document.querySelector("#flights-table-body");
const analyticsStatus = document.querySelector("#analytics-status");
const averageFare = document.querySelector("#average-fare");
const baselineFare = document.querySelector("#baseline-fare");
const priceIndex = document.querySelector("#price-index");
const percentageChange = document.querySelector("#percentage-change");
const cheapestFlight = document.querySelector("#cheapest-flight");
const expensiveFlight = document.querySelector("#expensive-flight");
const historyCount = document.querySelector("#history-count");
const historySource = document.querySelector("#history-source");
const airlineComparison = document.querySelector("#airline-comparison");
const historyChart = document.querySelector("#price-history-chart");
const chartContext = historyChart.getContext("2d");
const sourceSuggestions = document.querySelector("#source-suggestions");
const destinationSuggestions = document.querySelector("#destination-suggestions");

const searchState = {
  page: 1,
  limit: 10,
  sort: "price",
  order: "asc",
};

// ---- Airport autocomplete ----

let airportAbortController = null;

async function fetchAirportSuggestions(query) {
  if (airportAbortController) {
    airportAbortController.abort();
  }
  airportAbortController = new AbortController();

  const params = new URLSearchParams({ q: query, limit: "8" });

  try {
    const response = await fetch(`/api/airports?${params.toString()}`, {
      signal: airportAbortController.signal,
    });
    if (!response.ok) {
      return [];
    }
    const data = await response.json();
    return data.airports || [];
  } catch (error) {
    if (error.name === "AbortError") {
      return null; // Superseded by a newer keystroke
    }
    return [];
  }
}

function renderSuggestions(container, airports, onSelect) {
  container.innerHTML = "";

  if (!airports || !airports.length) {
    container.hidden = true;
    return;
  }

  airports.forEach((airport) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "suggestion-item";
    item.innerHTML = `
      <span class="suggestion-code">${escapeHtml(airport.iata_code)}</span>
      <span class="suggestion-detail">
        <strong>${escapeHtml(airport.name)}</strong>
        <small>${escapeHtml(airport.city)}, ${escapeHtml(airport.country)}</small>
      </span>
    `;
    item.addEventListener("click", () => onSelect(airport));
    container.appendChild(item);
  });

  container.hidden = false;
}

function hideSuggestions() {
  sourceSuggestions.hidden = true;
  destinationSuggestions.hidden = true;
}

function setupAutocomplete(input, container) {
  let debounceTimer = null;

  input.addEventListener("input", () => {
    const value = input.value.trim();
    if (value.length < 1) {
      clearTimeout(debounceTimer);
      container.hidden = true;
      return;
    }

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      const airports = await fetchAirportSuggestions(value);
      if (airports === null) {
        return; // Superseded
      }
      renderSuggestions(container, airports, (airport) => {
        input.value = airport.iata_code;
        container.hidden = true;
      });
    }, 150);
  });

  input.addEventListener("focus", () => {
    const value = input.value.trim();
    if (value.length >= 1) {
      input.dispatchEvent(new Event("input"));
    }
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      container.hidden = true;
    }
  });

  document.addEventListener("click", (event) => {
    if (!container.contains(event.target) && event.target !== input) {
      container.hidden = true;
    }
  });
}

setupAutocomplete(sourceInput, sourceSuggestions);
setupAutocomplete(destinationInput, destinationSuggestions);

function normalizeAirportCode(value) {
  return value.trim().toUpperCase();
}

function setMessage(text, type = "info") {
  message.textContent = text;
  message.className = type === "error" ? "message error" : "message";
}

function setLoading(isLoading) {
  searchButton.disabled = isLoading;
  searchButton.textContent = isLoading ? "Searching..." : "Search flights";
}

function formatPrice(price) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(price || 0));
}

function formatDateTime(value) {
  const date = new Date(value);
  if (!value || Number.isNaN(date.getTime())) {
    return "Schedule not provided by API";
  }

  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatPercentage(value) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return "-";
  }

  const sign = numericValue > 0 ? "+" : "";
  return `${sign}${numericValue.toFixed(1)}%`;
}

// Non-genuine airline names to hide from the UI (e.g. "Duffel Airways"
// returned by the FlightAPI.io API).  Kept in sync with the backend filter.
const NON_GENUINE_AIRLINES = ["duffel airways"];

function isGenuineAirline(airline) {
  if (!airline) return false;
  const lower = airline.toLowerCase();
  return !NON_GENUINE_AIRLINES.some((name) => lower.includes(name));
}

function filterGenuineFlights(flights) {
  return flights.filter((flight) => isGenuineAirline(flight.airline));
}

function escapeHtml(value) {
  // Build HTML entities via concatenation so the source file itself never
  // contains literal entities that could be mangled by tooling.
  const amp = "&" + "amp;";
  const lt = "&" + "lt;";
  const gt = "&" + "gt;";
  const quot = "&" + "quot;";
  const apos = "&" + "#039;";
  return String(value ?? "")
    .replaceAll("&", amp)
    .replaceAll("<", lt)
    .replaceAll(">", gt)
    .replaceAll('"', quot)
    .replaceAll("'", apos);
}

function renderEmptyState(text) {
  tableBody.innerHTML = `
    <tr class="empty-row">
      <td colspan="4">${escapeHtml(text)}</td>
    </tr>
  `;
}

function renderFlights(flights) {
  if (!flights.length) {
    renderEmptyState("No matching flights were found for this route.");
    return;
  }

  tableBody.innerHTML = flights.map((flight) => {
    const source = escapeHtml(flight.source);
    const destination = escapeHtml(flight.destination);

    return `
      <tr>
        <td>
          <span class="airline-name">${escapeHtml(flight.airline)}</span>
        </td>
        <td>
          <span class="route-code">
            ${source}
            <span class="route-separator">to</span>
            ${destination}
          </span>
        </td>
        <td>
          <div class="departure-cell">
            <strong>${source}</strong>
            <span>${escapeHtml(flight.flight_number || "-")} · ${escapeHtml(formatDateTime(flight.departure_time))}</span>
          </div>
        </td>
        <td class="price-column">
          <span class="price-value">${formatPrice(flight.price)}</span>
        </td>
      </tr>
    `;
  }).join("");
}

function formatDay(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value ?? "");
  }

  return date.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
  });
}

function resetAnalytics(status = "Waiting for search") {
  analyticsStatus.textContent = status;
  averageFare.textContent = "-";
  baselineFare.textContent = "-";
  priceIndex.textContent = "-";
  percentageChange.textContent = "-";
  cheapestFlight.textContent = "-";
  expensiveFlight.textContent = "-";
  historyCount.textContent = "No data";
  historySource.textContent = "Historical data: No data";
  airlineComparison.innerHTML = '<p class="muted-note">Search a route to compare airlines.</p>';
  hoverIndex = -1;
  drawHistoryChart([], "hourly");
}

function renderFlightExtremes(flights) {
  if (!flights.length) {
    cheapestFlight.textContent = "-";
    expensiveFlight.textContent = "-";
    return;
  }

  const sortedFlights = [...flights].sort((a, b) => Number(a.price) - Number(b.price));
  const cheapest = sortedFlights[0];
  const expensive = sortedFlights[sortedFlights.length - 1];

  cheapestFlight.textContent = `${cheapest.airline} ${formatPrice(cheapest.price)}`;
  expensiveFlight.textContent = `${expensive.airline} ${formatPrice(expensive.price)}`;
}

function renderAirlineComparison(flights) {
  if (!flights.length) {
    airlineComparison.innerHTML = '<p class="muted-note">No airlines to compare for this route.</p>';
    return;
  }

  const groups = new Map();
  flights.forEach((flight) => {
    const airline = flight.airline || "Unknown airline";
    const existing = groups.get(airline) || { total: 0, count: 0 };
    existing.total += Number(flight.price || 0);
    existing.count += 1;
    groups.set(airline, existing);
  });

  const rows = [...groups.entries()]
    .map(([airline, data]) => ({
      airline,
      average: data.total / data.count,
      count: data.count,
    }))
    .sort((a, b) => a.average - b.average);

  const maxAverage = Math.max(...rows.map((row) => row.average), 1);

  airlineComparison.innerHTML = rows.map((row) => {
    const width = Math.max((row.average / maxAverage) * 100, 8);
    return `
      <div class="airline-row">
        <div class="airline-row-top">
          <span>${escapeHtml(row.airline)} (${row.count})</span>
          <span>${formatPrice(row.average)}</span>
        </div>
        <div class="bar-track">
          <div class="bar-fill" style="width: ${width}%"></div>
        </div>
      </div>
    `;
  }).join("");
}

// ---- Historical price chart ----
// Plots collection-time buckets (one average fare per collection run),
// NOT individual flight snapshots.  Several airlines are recorded during
// one collection run; they are aggregated server-side into a single
// bucket so the line connects bucket averages, never airline-to-airline.

let lastChartHistory = [];
let lastChartGranularity = "hourly";
let lastChartPoints = [];
let lastChartGeometry = null;
let hoverIndex = -1;

function formatAxisPrice(value, step) {
  const decimals = step >= 1 ? 0 : 2;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(Number(value || 0));
}

function formatTimeLabel(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function formatFullTimestamp(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value ?? "");
  }
  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function localDateKey(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toLocaleDateString("en-CA"); // YYYY-MM-DD in local time
}

function niceStepSize(range, targetTicks) {
  if (range <= 0) {
    return 1;
  }
  const rawStep = range / Math.max(targetTicks, 1);
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const normalized = rawStep / magnitude;
  let factor;
  if (normalized <= 1) factor = 1;
  else if (normalized <= 2) factor = 2;
  else if (normalized <= 2.5) factor = 2.5;
  else if (normalized <= 5) factor = 5;
  else factor = 10;
  return factor * magnitude;
}

function buildPriceTicks(yMin, yMax, targetTicks = 4) {
  const step = niceStepSize(yMax - yMin, targetTicks);
  const ticks = [];
  const first = Math.ceil(yMin / step) * step;
  for (let value = first; value <= yMax + step * 1e-6; value += step) {
    ticks.push(Number(value.toFixed(6)));
  }
  return { ticks, step };
}

const TIME_TICK_STEPS_MS = [
  15 * 60 * 1000,
  30 * 60 * 1000,
  60 * 60 * 1000,
  2 * 60 * 60 * 1000,
  3 * 60 * 60 * 1000,
  6 * 60 * 60 * 1000,
  12 * 60 * 60 * 1000,
  24 * 60 * 60 * 1000,
];

function buildTimeTicks(tMin, tMax, maxTicks = 5) {
  const span = tMax - tMin;
  if (span <= 0) {
    return [tMin];
  }
  const rawStep = span / Math.max(maxTicks - 1, 1);
  const step =
    TIME_TICK_STEPS_MS.find((candidate) => candidate >= rawStep) ||
    24 * 60 * 60 * 1000;

  const first = new Date(tMin);
  if (step >= 60 * 60 * 1000) {
    first.setMinutes(0, 0, 0);
  } else {
    const stepMinutes = step / (60 * 1000);
    first.setMinutes(
      Math.floor(first.getMinutes() / stepMinutes) * stepMinutes,
      0,
      0,
    );
  }

  const ticks = [];
  for (let t = first.getTime(); t <= tMax; t += step) {
    ticks.push(t);
  }
  return ticks;
}

function toChartPoints(history) {
  return (history || [])
    .map((entry) => ({
      t: entry.timestamp ? new Date(entry.timestamp).getTime() : NaN,
      price: Number(entry.average_fare),
      raw: entry,
    }))
    .filter((point) => Number.isFinite(point.t) && Number.isFinite(point.price))
    .sort((a, b) => a.t - b.t); // chronological collection-time buckets
}

function drawHistoryChart(history, granularity = "hourly") {
  const canvas = historyChart;
  const context = chartContext;
  const width = canvas.width;
  const height = canvas.height;
  const padding = { top: 24, right: 16, bottom: 44, left: 64 };

  lastChartHistory = history || [];
  lastChartGranularity = granularity;
  const points = toChartPoints(lastChartHistory);
  lastChartPoints = points;

  context.clearRect(0, 0, width, height);
  context.fillStyle = "#f8fafc";
  context.fillRect(0, 0, width, height);

  if (!points.length) {
    lastChartGeometry = null;
    context.fillStyle = "#94a3b8";
    context.font = "15px system-ui, sans-serif";
    context.textAlign = "center";
    context.fillText("History builds here as scheduled collections run", width / 2, height / 2);
    return;
  }

  const plotLeft = padding.left;
  const plotRight = width - padding.right;
  const plotTop = padding.top;
  const plotBottom = height - padding.bottom;
  const plotWidth = plotRight - plotLeft;
  const plotHeight = plotBottom - plotTop;

  // X axis = collection timestamp (time-proportional).  Exactly one
  // point per bucket, so duplicate timestamps never draw vertical lines.
  const tMin = points[0].t;
  const tMax = points[points.length - 1].t;
  const tSpan = Math.max(tMax - tMin, 1);
  const getX = (t) => plotLeft + ((t - tMin) / tSpan) * plotWidth;

  // Y axis: min/max from the displayed bucket averages with padding, so
  // even small fare differences stay clearly visible.
  const prices = points.map((point) => point.price);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const priceRange = maxPrice - minPrice;
  const yPad =
    priceRange > 0 ? priceRange * 0.18 : Math.max(Math.abs(maxPrice) * 0.05, 1);
  const yMin = minPrice - yPad;
  const yMax = maxPrice + yPad;
  const getY = (price) =>
    plotBottom - ((price - yMin) / (yMax - yMin)) * plotHeight;

  lastChartGeometry = { getX, plotLeft, plotRight, plotTop, plotBottom };

  // Horizontal gridlines + y-axis price labels at nice tick values
  // (few, well-spaced ticks so labels never overlap).
  const { ticks, step } = buildPriceTicks(yMin, yMax, 4);
  context.strokeStyle = "#e2e8f0";
  context.fillStyle = "#94a3b8";
  context.font = "11px system-ui, sans-serif";
  context.textAlign = "right";
  context.textBaseline = "middle";
  ticks.forEach((value) => {
    const y = getY(value);
    context.beginPath();
    context.moveTo(plotLeft, y);
    context.lineTo(plotRight, y);
    context.stroke();
    context.fillText(formatAxisPrice(value, step), plotLeft - 8, y);
  });

  // Axes
  context.strokeStyle = "#cbd5e1";
  context.lineWidth = 1;
  context.beginPath();
  context.moveTo(plotLeft, plotTop);
  context.lineTo(plotLeft, plotBottom);
  context.lineTo(plotRight, plotBottom);
  context.stroke();

  // Area fill under the line
  const gradient = context.createLinearGradient(plotLeft, plotTop, plotLeft, plotBottom);
  gradient.addColorStop(0, "rgba(15, 118, 110, 0.12)");
  gradient.addColorStop(1, "rgba(15, 118, 110, 0.02)");
  context.fillStyle = gradient;
  context.beginPath();
  context.moveTo(getX(points[0].t), getY(points[0].price));
  for (let i = 1; i < points.length; i++) {
    context.lineTo(getX(points[i].t), getY(points[i].price));
  }
  context.lineTo(getX(points[points.length - 1].t), plotBottom);
  context.lineTo(getX(points[0].t), plotBottom);
  context.closePath();
  context.fill();

  // Straight line segments between bucket averages: no curvature that
  // could visually imply fares that were never collected.
  context.strokeStyle = "#0f766e";
  context.lineWidth = 2;
  context.lineCap = "round";
  context.lineJoin = "round";
  context.beginPath();
  context.moveTo(getX(points[0].t), getY(points[0].price));
  for (let i = 1; i < points.length; i++) {
    context.lineTo(getX(points[i].t), getY(points[i].price));
  }
  context.stroke();

  // One dot per collection-time bucket.
  context.fillStyle = "#f59e0b";
  points.forEach((point) => {
    context.beginPath();
    context.arc(getX(point.t), getY(point.price), 4, 0, Math.PI * 2);
    context.fill();
  });

  // Hover crosshair + tooltip: date/time, average, min, max, snapshots.
  if (hoverIndex >= 0 && hoverIndex < points.length) {
    const point = points[hoverIndex];
    const x = getX(point.t);
    const y = getY(point.price);

    context.strokeStyle = "#94a3b8";
    context.setLineDash([4, 4]);
    context.beginPath();
    context.moveTo(x, plotTop);
    context.lineTo(x, plotBottom);
    context.stroke();
    context.setLineDash([]);

    const lines = [
      formatFullTimestamp(point.raw.timestamp),
      `Avg ${formatPrice(point.raw.average_fare)}`,
      `Min ${formatPrice(point.raw.minimum_fare)}  ·  Max ${formatPrice(point.raw.maximum_fare)}`,
      `${point.raw.snapshot_count} snapshot${point.raw.snapshot_count === 1 ? "" : "s"}`,
    ];

    context.font = "11px system-ui, sans-serif";
    let boxWidth = 0;
    lines.forEach((line) => {
      boxWidth = Math.max(boxWidth, context.measureText(line).width);
    });
    boxWidth += 20;
    const lineHeight = 14;
    const boxHeight = lines.length * lineHeight + 10;
    const boxX = Math.min(Math.max(x - boxWidth / 2, plotLeft), plotRight - boxWidth);
    const boxY = Math.max(y - boxHeight - 10, plotTop);

    context.fillStyle = "rgba(15, 118, 110, 0.94)";
    context.fillRect(boxX, boxY, boxWidth, boxHeight);
    context.textAlign = "left";
    context.textBaseline = "middle";
    lines.forEach((line, index) => {
      context.fillStyle = index === 0 ? "#a7f3d0" : "#ffffff";
      context.fillText(line, boxX + 10, boxY + 8 + index * lineHeight);
    });
  }

  // X-axis labels: clock times for hourly buckets, dates for daily ones.
  context.fillStyle = "#94a3b8";
  context.font = "11px system-ui, sans-serif";
  context.textAlign = "center";
  context.textBaseline = "top";
  if (lastChartGranularity === "hourly") {
    buildTimeTicks(tMin, tMax, 5).forEach((t) => {
      context.fillText(formatTimeLabel(t), getX(t), plotBottom + 6);
    });
  } else {
    const labelIndices = [0, Math.floor(points.length / 2), points.length - 1];
    [...new Set(labelIndices)].forEach((index) => {
      context.fillText(
        formatDay(localDateKey(points[index].t)),
        getX(points[index].t),
        plotBottom + 6,
      );
    });
  }
}

historyChart.style.cursor = "crosshair";
historyChart.addEventListener("mousemove", (event) => {
  if (!lastChartPoints.length || !lastChartGeometry) {
    return;
  }
  const rect = historyChart.getBoundingClientRect();
  const scaleX = historyChart.width / rect.width;
  const x = (event.clientX - rect.left) * scaleX;

  let nearest = -1;
  let nearestDistance = Infinity;
  lastChartPoints.forEach((point, index) => {
    const distance = Math.abs(lastChartGeometry.getX(point.t) - x);
    if (distance < nearestDistance) {
      nearestDistance = distance;
      nearest = index;
    }
  });
  if (nearestDistance > 28) {
    nearest = -1;
  }

  if (nearest !== hoverIndex) {
    hoverIndex = nearest;
    drawHistoryChart(lastChartHistory, lastChartGranularity);
  }
});

historyChart.addEventListener("mouseleave", () => {
  if (hoverIndex !== -1) {
    hoverIndex = -1;
    drawHistoryChart(lastChartHistory, lastChartGranularity);
  }
});

async function fetchPriceIndex(source, destination) {
  const params = new URLSearchParams({ source, destination });
  const response = await fetch(`/api/analytics/price-index?${params.toString()}`);

  if (!response.ok) {
    return null;
  }

  return response.json();
}

async function fetchRoutePriceHistory(source, destination, days = 30) {
  const params = new URLSearchParams({
    source,
    destination,
    days: String(days),
  });
  const response = await fetch(`/api/analytics/price-history?${params.toString()}`);

  if (!response.ok) {
    return null;
  }

  return response.json();
}

async function renderAnalytics(source, destination, flights) {
  analyticsStatus.textContent = "Loading analytics";
  renderFlightExtremes(flights);
  renderAirlineComparison(flights);

  const indexData = await fetchPriceIndex(source, destination);
  if (indexData) {
    averageFare.textContent = formatPrice(indexData.current_average_price);
    baselineFare.textContent = formatPrice(indexData.baseline_price);
    priceIndex.textContent = Number(indexData.price_index).toFixed(1);
    percentageChange.textContent = formatPercentage(indexData.percentage_change);
  } else {
    averageFare.textContent = "-";
    baselineFare.textContent = "-";
    priceIndex.textContent = "-";
    percentageChange.textContent = "-";
  }

  const historyData = await fetchRoutePriceHistory(source, destination);
  const historyPoints = historyData ? historyData.history : [];
  const granularity = historyData ? historyData.granularity : "hourly";
  const historicalSource = historyData ? historyData.historical_source : "none";
  const totalSnapshots = historyPoints.reduce(
    (sum, point) => sum + (point.snapshot_count || 0),
    0,
  );
  const distinctDays = new Set(
    historyPoints
      .map((point) => localDateKey(point.timestamp))
      .filter(Boolean),
  ).size;

  historyCount.textContent = totalSnapshots
    ? `${totalSnapshots} snapshot${totalSnapshots === 1 ? "" : "s"} (${distinctDays} day${distinctDays === 1 ? "" : "s"})`
    : "No data";
  historySource.textContent = historicalSource === "synthetic"
    ? "Historical data: Demo/Synthetic"
    : historicalSource === "mixed"
      ? "Historical data: Mixed API and Demo/Synthetic"
      : historicalSource === "flightapi"
        ? "Historical data: FlightAPI.io"
        : "Historical data: No data";
  hoverIndex = -1;
  drawHistoryChart(historyPoints, granularity);
  analyticsStatus.textContent = indexData ? "Updated" : "Needs price history";
}

async function searchFlights(source, destination) {
  const params = new URLSearchParams({
    source,
    destination,
    page: String(searchState.page),
    limit: String(searchState.limit),
    sort: searchState.sort,
    order: searchState.order,
  });

  const response = await fetch(`/api/search?${params.toString()}`);

  if (!response.ok) {
    throw new Error(`Search failed with status ${response.status}`);
  }

  return response.json();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const source = normalizeAirportCode(sourceInput.value);
  const destination = normalizeAirportCode(destinationInput.value);

  sourceInput.value = source;
  destinationInput.value = destination;

  if (!source || !destination) {
    setMessage("Please enter both source and destination airports.", "error");
    return;
  }

  setLoading(true);
  resetAnalytics("Loading analytics");
  setMessage("Searching live fares...");
  resultCount.textContent = "Loading";
  renderEmptyState("Loading flight results...");

  try {
    const data = await searchFlights(source, destination);
    const flights = Array.isArray(data) ? data : data.flights || [];

    // Client-side safety net: hide non-genuine airlines (e.g. "Duffel Airways")
    // that may have been cached before the backend filter was applied.
    const genuineFlights = filterGenuineFlights(flights);

    renderFlights(genuineFlights);

    const total = typeof data.total === "number" ? data.total : genuineFlights.length;
    resultCount.textContent = `${total} result${total === 1 ? "" : "s"}`;
    setMessage(`Showing ${genuineFlights.length} fare${genuineFlights.length === 1 ? "" : "s"} for ${source} to ${destination}.`);
    await renderAnalytics(source, destination, genuineFlights);
  } catch (error) {
    renderEmptyState("Unable to load flight results.");
    resultCount.textContent = "Search failed";
    resetAnalytics("Search failed");
    setMessage("Could not reach the flight search API. Make sure FastAPI is running and try again.", "error");
  } finally {
    setLoading(false);
  }
});

resetAnalytics();
