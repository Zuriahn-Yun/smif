import { get, post } from "./api.js";

export function init() {
    loadTickerCheckboxes();
    document.getElementById("btn-select-all").addEventListener("click", toggleAll);
    document.getElementById("btn-run-monte").addEventListener("click", runMonte);
    document.getElementById("btn-run-corr").addEventListener("click", runCorrelation);
}

async function loadTickerCheckboxes() {
    try {
        const tickers = await post("/data/smifData", {});
        const list = document.getElementById("stock-checkbox-list");
        list.innerHTML = "";
        tickers.forEach(ticker => {
            const div = document.createElement("div");
            div.className = "checkbox-item";
            div.innerHTML = `
                <input type="checkbox" id="check-${ticker}" value="${ticker}" class="ticker-checkbox">
                <label for="check-${ticker}">${ticker}</label>
            `;
            list.appendChild(div);
        });
    } catch (err) {
        console.error("Failed to load tickers:", err);
    }
}

function toggleAll() {
    const cbs = document.querySelectorAll(".ticker-checkbox");
    const newState = !cbs[0]?.checked;
    cbs.forEach(cb => cb.checked = newState);
}

function getSelected() {
    return Array.from(document.querySelectorAll(".ticker-checkbox:checked")).map(cb => cb.value);
}

function setStatus(msg) {
    document.getElementById("analysis-status").innerText = msg;
}

async function runMonte() {
    const selected = getSelected();
    if (!selected.length) { alert("Select at least one asset."); return; }

    setStatus("Running Monte Carlo...");
    const container = document.getElementById("plot-container");
    container.innerHTML = '<div class="placeholder-text">Calculating...</div>';

    try {
        // Run for first selected ticker as a demo; smif_monte for all
        const figJson = selected.length === 1
            ? await (async () => {
                const res = await fetch(`/monte/generate_display?ticker=${encodeURIComponent(selected[0])}`, { method: "POST" });
                if (!res.ok) throw new Error(await res.text());
                return res.json();
              })()
            : await post("/monte/smif_monte", {});

        const fig = JSON.parse(figJson);
        container.innerHTML = '<div id="monte-plot" style="width:100%;height:100%"></div>';
        Plotly.react("monte-plot", fig.data, fig.layout, { responsive: true });
        setStatus("Monte Carlo complete.");
    } catch (err) {
        setStatus("Error: " + err.message);
    }
}

async function runCorrelation() {
    setStatus("Correlation matrix coming soon...");
}
