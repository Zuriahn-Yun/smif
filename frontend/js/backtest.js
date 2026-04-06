import { get, post } from "./api.js";

export function init() {
    loadTickerCheckboxes();
    document.getElementById("btn-run-backtest").addEventListener("click", runBacktest);
    document.getElementById("btn-select-all-bt").addEventListener("click", toggleAll);
}

async function loadTickerCheckboxes() {
    try {
        const tickers = await post("/data/smifData", {});
        const list = document.getElementById("backtest-checkbox-list");
        list.innerHTML = "";
        tickers.forEach(t => {
            const div = document.createElement("div");
            div.className = "checkbox-item";
            div.innerHTML = `
                <input type="checkbox" id="bt-check-${t}" value="${t}" class="bt-ticker-checkbox" checked>
                <label for="bt-check-${t}">${t}</label>
            `;
            list.appendChild(div);
        });
    } catch (err) {
        console.error("Failed to load tickers:", err);
    }
}

function toggleAll() {
    const cbs = document.querySelectorAll(".bt-ticker-checkbox");
    const newState = !cbs[0]?.checked;
    cbs.forEach(cb => cb.checked = newState);
}

async function runBacktest() {
    const tickers = Array.from(document.querySelectorAll(".bt-ticker-checkbox:checked")).map(cb => cb.value);
    if (!tickers.length) { alert("Select at least one ticker."); return; }

    const req = {
        strategy: document.getElementById("bt-strategy").value,
        tickers,
        start_date: document.getElementById("bt-start-date").value,
        end_date: document.getElementById("bt-end-date").value,
        rebalance_freq: document.getElementById("bt-rebalance-freq").value,
    };

    setStatus("Running backtest... (downloading historical data)");
    try {
        const data = await post("/backtest/run", req);

        const fig = JSON.parse(data.figure);
        Plotly.react("backtest-plot", fig.data, fig.layout, { responsive: true });
        renderMetrics(data.metrics, data.benchmark_metrics, data.tickers_used);
        setStatus("");
    } catch (err) {
        setStatus("Error: " + err.message);
    }
}

function renderMetrics(m, bench, tickers) {
    const pct = v => v != null ? (v * 100).toFixed(2) + "%" : "N/A";
    const fmt = v => v != null ? v.toFixed(3) : "N/A";

    document.getElementById("backtest-metrics").innerHTML = `
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">CAGR</div>
                <div class="metric-value">${pct(m.cagr)}</div>
                ${bench ? `<div class="metric-bench">SPY: ${pct(bench.cagr)}</div>` : ""}
            </div>
            <div class="metric-card">
                <div class="metric-label">Sharpe Ratio</div>
                <div class="metric-value">${fmt(m.sharpe_ratio)}</div>
                ${bench ? `<div class="metric-bench">SPY: ${fmt(bench.sharpe_ratio)}</div>` : ""}
            </div>
            <div class="metric-card">
                <div class="metric-label">Max Drawdown</div>
                <div class="metric-value" style="color:#d9534f">${pct(m.max_drawdown)}</div>
                ${bench ? `<div class="metric-bench">SPY: ${pct(bench.max_drawdown)}</div>` : ""}
            </div>
            <div class="metric-card">
                <div class="metric-label">Volatility (Ann.)</div>
                <div class="metric-value">${pct(m.annualized_volatility)}</div>
                ${bench ? `<div class="metric-bench">SPY: ${pct(bench.annualized_volatility)}</div>` : ""}
            </div>
            <div class="metric-card">
                <div class="metric-label">Calmar Ratio</div>
                <div class="metric-value">${fmt(m.calmar_ratio)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Return</div>
                <div class="metric-value">${pct(m.total_return)}</div>
                ${bench ? `<div class="metric-bench">SPY: ${pct(bench.total_return)}</div>` : ""}
            </div>
        </div>
        <p style="color:#888;font-size:0.85em;margin-top:8px">${tickers.length} tickers used. Transaction costs not included.</p>
    `;
}

function setStatus(msg) {
    const el = document.getElementById("backtest-status");
    if (el) el.innerText = msg;
}
