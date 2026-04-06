import { get, post } from "./api.js";

export function init() {
    loadTickerCheckboxes();
    document.getElementById("btn-run-frontier").addEventListener("click", runFrontier);
    document.getElementById("btn-run-max-sharpe").addEventListener("click", runMaxSharpe);
    document.getElementById("btn-select-all-opt").addEventListener("click", toggleAll);
}

async function loadTickerCheckboxes() {
    try {
        const tickers = await post("/data/smifData", {});
        const list = document.getElementById("optimizer-checkbox-list");
        list.innerHTML = "";
        tickers.forEach(t => {
            const div = document.createElement("div");
            div.className = "checkbox-item";
            div.innerHTML = `
                <input type="checkbox" id="opt-check-${t}" value="${t}" class="opt-ticker-checkbox">
                <label for="opt-check-${t}">${t}</label>
            `;
            list.appendChild(div);
        });
    } catch (err) {
        console.error("Failed to load tickers:", err);
    }
}

function toggleAll() {
    const cbs = document.querySelectorAll(".opt-ticker-checkbox");
    const newState = !cbs[0]?.checked;
    cbs.forEach(cb => cb.checked = newState);
}

function getSelected() {
    return Array.from(document.querySelectorAll(".opt-ticker-checkbox:checked")).map(cb => cb.value);
}

async function runFrontier() {
    const tickers = getSelected();
    if (tickers.length < 2) { alert("Select at least 2 assets."); return; }
    if (tickers.length > 20) { alert("Maximum 20 assets for optimization."); return; }

    setStatus("Running efficient frontier...");
    try {
        const years = parseInt(document.getElementById("opt-lookback").value) || 2;
        const numP = parseInt(document.getElementById("opt-num-portfolios").value) || 500;

        const data = await post("/optimizer/efficient_frontier", {
            tickers, lookback_years: years, num_portfolios: numP
        });

        const fig = JSON.parse(data.figure);
        Plotly.react("optimizer-plot", fig.data, fig.layout, { responsive: true });
        renderWeightsTable(data.max_sharpe, data.min_variance, data.tickers);
        setStatus("Frontier complete.");
    } catch (err) {
        setStatus("Error: " + err.message);
    }
}

async function runMaxSharpe() {
    const tickers = getSelected();
    if (tickers.length < 2) { alert("Select at least 2 assets."); return; }

    setStatus("Optimizing max Sharpe ratio...");
    try {
        const years = parseInt(document.getElementById("opt-lookback").value) || 2;
        const data = await post("/optimizer/max_sharpe", { tickers, lookback_years: years });

        const weights = data.weights;
        const sorted = Object.entries(weights).sort((a, b) => b[1] - a[1]);

        const fig = {
            data: [{
                type: "pie", hole: 0.4,
                labels: sorted.map(([t]) => t),
                values: sorted.map(([, w]) => +(w * 100).toFixed(2)),
                textinfo: "label+percent",
            }],
            layout: {
                title: `Max Sharpe Portfolio (Sharpe: ${data.sharpe_ratio.toFixed(3)})`,
                annotations: [{ text: `Return: ${(data.annualized_return * 100).toFixed(1)}%<br>Vol: ${(data.annualized_volatility * 100).toFixed(1)}%`, showarrow: false, x: 0.5, y: 0.5, font: { size: 11 } }]
            }
        };
        Plotly.react("optimizer-plot", fig.data, fig.layout, { responsive: true });

        document.getElementById("optimizer-weights-table").innerHTML = `
            <table><thead><tr><th>Ticker</th><th>Weight</th></tr></thead><tbody>
            ${sorted.map(([t, w]) => `<tr><td>${t}</td><td>${(w * 100).toFixed(2)}%</td></tr>`).join("")}
            </tbody></table>
        `;
        setStatus(`Max Sharpe: ${data.sharpe_ratio.toFixed(3)} | Return: ${(data.annualized_return * 100).toFixed(1)}% | Vol: ${(data.annualized_volatility * 100).toFixed(1)}%`);
    } catch (err) {
        setStatus("Error: " + err.message);
    }
}

function renderWeightsTable(maxSharpe, minVar, tickers) {
    const el = document.getElementById("optimizer-weights-table");
    el.innerHTML = `
        <table>
            <thead><tr><th>Ticker</th><th>Max Sharpe</th><th>Min Variance</th></tr></thead>
            <tbody>
                ${tickers.map(t => `
                    <tr>
                        <td>${t}</td>
                        <td>${((maxSharpe.weights[t] || 0) * 100).toFixed(2)}%</td>
                        <td>${((minVar.weights[t] || 0) * 100).toFixed(2)}%</td>
                    </tr>
                `).join("")}
                <tr style="font-weight:bold;border-top:2px solid #ddd">
                    <td>Metrics</td>
                    <td>Return: ${(maxSharpe.return * 100).toFixed(1)}%<br>Vol: ${(maxSharpe.volatility * 100).toFixed(1)}%<br>Sharpe: ${maxSharpe.sharpe.toFixed(3)}</td>
                    <td>Return: ${(minVar.return * 100).toFixed(1)}%<br>Vol: ${(minVar.volatility * 100).toFixed(1)}%<br>Sharpe: ${minVar.sharpe.toFixed(3)}</td>
                </tr>
            </tbody>
        </table>
    `;
}

function setStatus(msg) {
    const el = document.getElementById("optimizer-status");
    if (el) el.innerText = msg;
}
