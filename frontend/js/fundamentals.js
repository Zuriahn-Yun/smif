import { get } from "./api.js";
import { post } from "./api.js";

const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
let _tickers = [];

export function init() {
    loadTickerList();
    document.getElementById("fundamentals-ticker-select").addEventListener("change", e => {
        loadTicker(e.target.value);
    });
}

async function loadTickerList() {
    try {
        const tickers = await post("/data/smifData", {});
        _tickers = tickers;
        const select = document.getElementById("fundamentals-ticker-select");
        select.innerHTML = '<option value="">— Select a holding —</option>';
        tickers.forEach(t => {
            const opt = document.createElement("option");
            opt.value = t;
            opt.textContent = t;
            select.appendChild(opt);
        });
    } catch (err) {
        console.error("Failed to load tickers:", err);
    }
}

export async function loadTicker(ticker) {
    const select = document.getElementById("fundamentals-ticker-select");
    if (select) select.value = ticker;

    setStatus(`Loading ${ticker}...`);
    clearPanels();

    try {
        const [overview, valuation, financials] = await Promise.all([
            get(`/fundamentals/${ticker}/overview`),
            get(`/fundamentals/${ticker}/valuation`),
            get(`/fundamentals/${ticker}/financials`),
        ]);

        renderOverview(overview);
        renderValuation(valuation);
        renderFinancials(financials);
        setStatus("");
    } catch (err) {
        setStatus("Error loading data: " + err.message);
    }
}

function renderOverview(data) {
    const el = document.getElementById("fundamentals-overview");
    el.innerHTML = `
        <h3>${data.name} <span style="color:#888;font-size:0.9em">(${data.ticker})</span></h3>
        <div class="metric-row">
            <span class="metric-chip">${data.sector}</span>
            <span class="metric-chip">${data.industry}</span>
            <span class="metric-chip">${data.country}</span>
            ${data.employees ? `<span class="metric-chip">${Number(data.employees).toLocaleString()} employees</span>` : ""}
            ${data.website ? `<a href="${data.website}" target="_blank" class="metric-chip">Website ↗</a>` : ""}
        </div>
        <p style="margin-top:12px;color:#555;font-size:0.95em;line-height:1.6">${data.summary}</p>
    `;
}

function renderValuation(data) {
    const el = document.getElementById("fundamentals-valuation");
    const metrics = data.metrics.filter(m => m.formatted !== null);
    if (!metrics.length) {
        el.innerHTML = "<p style='color:#888'>No valuation data available (common for ETFs and mutual funds).</p>";
        return;
    }
    el.innerHTML = `
        <div class="metric-cards">
            ${metrics.map(m => `
                <div class="metric-card">
                    <div class="metric-label">${m.label}</div>
                    <div class="metric-value">${m.formatted}</div>
                </div>
            `).join("")}
        </div>
    `;
}

function renderFinancials(data) {
    const el = document.getElementById("fundamentals-financials");
    if (!data.annual || data.annual.length === 0) {
        el.innerHTML = `<p style="color:#888">${data.note || "No financial data available."}</p>`;
        return;
    }

    // Build Plotly bar chart for Revenue and Net Income
    const revenueRow = data.annual.find(r => r.label === "Total Revenue");
    const netIncomeRow = data.annual.find(r => r.label === "Net Income");

    if (revenueRow) {
        const dates = Object.keys(revenueRow.values).sort();
        const traces = [];
        [revenueRow, netIncomeRow].filter(Boolean).forEach((row, i) => {
            traces.push({
                type: "bar",
                name: row.label,
                x: dates,
                y: dates.map(d => row.values[d] ? row.values[d] / 1e9 : null),
                marker: { color: i === 0 ? "#005A9C" : "#5cb85c" },
            });
        });
        const fig = {
            data: traces,
            layout: {
                title: "Annual Financials (USD Billions)",
                barmode: "group",
                yaxis: { title: "USD (B)" },
                xaxis: { title: "Year" },
            }
        };
        el.innerHTML = '<div id="financials-chart" style="width:100%;height:320px"></div>';
        Plotly.react("financials-chart", fig.data, fig.layout, { responsive: true });
    } else {
        el.innerHTML = "<p style='color:#888'>Revenue data not available.</p>";
    }
}

function clearPanels() {
    ["fundamentals-overview", "fundamentals-valuation", "fundamentals-financials"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = "";
    });
}

function setStatus(msg) {
    const el = document.getElementById("fundamentals-status");
    if (el) el.innerText = msg;
}
