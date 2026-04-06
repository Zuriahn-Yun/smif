import { get, post } from "./api.js";

const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
let _currentAllocation = null;

export function init() {
    loadAllocation();
    document.getElementById("btn-equal-weight").addEventListener("click", applyEqualWeight);
    document.getElementById("btn-calculate-trades").addEventListener("click", calculateTrades);
}

async function loadAllocation() {
    setStatus("Loading current allocation...");
    try {
        const data = await get("/rebalance/current_allocation");
        if (data.status === "loading") {
            setStatus(data.message);
            setTimeout(loadAllocation, 4000);
            return;
        }
        _currentAllocation = data;
        renderAllocationTable(data);
        setStatus("");
    } catch (err) {
        setStatus("Error: " + err.message);
    }
}

function renderAllocationTable(data) {
    const tbody = document.getElementById("rebalance-holdings-body");
    tbody.innerHTML = "";
    data.assets.forEach(asset => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><strong>${asset.ticker}</strong></td>
            <td>${asset.shares.toLocaleString()}</td>
            <td>${currency.format(asset.price)}</td>
            <td>${currency.format(asset.value)}</td>
            <td>${(asset.current_weight * 100).toFixed(2)}%</td>
            <td>${asset.sector}</td>
            <td><input type="number" class="weight-input" data-ticker="${asset.ticker}"
                 value="${(asset.current_weight * 100).toFixed(2)}"
                 min="0" max="100" step="0.01" style="width:70px"></td>
        `;
        tbody.appendChild(tr);
    });

    document.getElementById("rebalance-total-value").innerText =
        `Current portfolio value: ${currency.format(data.total_value)}`;
}

async function applyEqualWeight() {
    try {
        const weights = await get("/rebalance/equal_weight_target");
        document.querySelectorAll(".weight-input").forEach(input => {
            const ticker = input.dataset.ticker;
            if (ticker in weights) {
                input.value = (weights[ticker] * 100).toFixed(2);
            }
        });
        setStatus("Equal weights applied. Click 'Calculate Trades' to see required trades.");
    } catch (err) {
        setStatus("Error: " + err.message);
    }
}

async function calculateTrades() {
    const inputs = document.querySelectorAll(".weight-input");
    const targetWeights = {};
    let total = 0;

    inputs.forEach(input => {
        const w = parseFloat(input.value) / 100;
        targetWeights[input.dataset.ticker] = w;
        total += w;
    });

    if (Math.abs(total - 1.0) > 0.01) {
        setStatus(`Error: Weights sum to ${(total * 100).toFixed(2)}% — must equal 100%.`);
        return;
    }

    setStatus("Calculating trades...");
    try {
        const result = await post("/rebalance/calculate_trades", {
            target_weights: targetWeights,
            total_budget: 0,
        });
        renderTrades(result);
        setStatus("");
    } catch (err) {
        setStatus("Error: " + err.message);
    }
}

function renderTrades(result) {
    const tbody = document.getElementById("trades-body");
    tbody.innerHTML = "";

    result.trades.forEach(t => {
        if (t.action === "HOLD") return;
        const tr = document.createElement("tr");
        tr.className = t.action === "BUY" ? "trade-buy" : "trade-sell";
        tr.innerHTML = `
            <td><strong>${t.ticker}</strong></td>
            <td class="${t.action === "BUY" ? "text-green" : "text-red"}">${t.action}</td>
            <td>${t.shares_delta > 0 ? "+" : ""}${t.shares_delta}</td>
            <td>${currency.format(t.price)}</td>
            <td>${currency.format(t.trade_value)}</td>
            <td>${(t.current_weight * 100).toFixed(2)}%</td>
            <td>${(t.target_weight * 100).toFixed(2)}%</td>
            <td>${(t.drift * 100).toFixed(2)}%</td>
        `;
        tbody.appendChild(tr);
    });

    const s = result.summary;
    document.getElementById("trades-summary").innerHTML = `
        <span>Total Buys: <strong>${currency.format(s.total_buys)}</strong></span>
        &nbsp;|&nbsp;
        <span>Total Sells: <strong>${currency.format(s.total_sells)}</strong></span>
        &nbsp;|&nbsp;
        <span>Turnover: <strong>${s.turnover_pct}%</strong></span>
    `;

    // Drift bar chart
    const drifts = result.trades.filter(t => t.action !== "HOLD");
    const colors = drifts.map(t => t.drift > 0 ? "#d9534f" : "#5cb85c");
    const fig = {
        data: [{
            type: "bar",
            x: drifts.map(t => t.ticker),
            y: drifts.map(t => +(t.drift * 100).toFixed(2)),
            marker: { color: colors },
            hovertemplate: "%{x}: %{y:.2f}% drift<extra></extra>",
        }],
        layout: {
            title: "Portfolio Drift (Current − Target Weight %)",
            xaxis: { tickangle: -45 },
            yaxis: { title: "Drift (%)" },
            shapes: [{ type: "line", x0: 0, x1: 1, xref: "paper", y0: 0, y1: 0, line: { color: "#333", dash: "dot" } }],
            margin: { b: 100 },
        }
    };
    Plotly.react("drift-chart", fig.data, fig.layout, { responsive: true });
}

function setStatus(msg) {
    const el = document.getElementById("rebalance-status");
    if (el) el.innerText = msg;
}
