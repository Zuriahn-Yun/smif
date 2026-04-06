import { get, post } from "./api.js";

export function init() {
    loadSector();
    document.getElementById("btn-fetch-sector-info").addEventListener("click", fetchInfo);
}

async function loadSector() {
    setStatus("Loading sector data...");
    try {
        const data = await get("/sector/exposure");
        if (data.error) { setStatus(data.error); return; }

        renderPlot("sector-treemap", data.treemap);
        renderPlot("sector-pie", data.pie);
        renderPlot("sector-bar", data.bar);

        const infoNote = document.getElementById("sector-info-note");
        if (infoNote) {
            infoNote.innerText = data.info_loaded < data.total_tickers
                ? `Sector detail loaded for ${data.info_loaded}/${data.total_tickers} tickers. Click "Enrich Sector Data" for full breakdown.`
                : `Sector data fully loaded for all ${data.total_tickers} holdings.`;
        }
        setStatus("");
    } catch (err) {
        setStatus("Error loading sector data: " + err.message);
    }
}

async function fetchInfo() {
    const btn = document.getElementById("btn-fetch-sector-info");
    btn.disabled = true;
    btn.innerText = "Fetching... (may take ~30s)";
    try {
        const result = await post("/sector/fetch_info", {});
        btn.innerText = `Done — ${result.total_cached} tickers enriched`;
        await loadSector();
    } catch (err) {
        btn.innerText = "Enrich Sector Data";
        btn.disabled = false;
        setStatus("Error: " + err.message);
    }
}

function renderPlot(divId, figJson) {
    const fig = JSON.parse(figJson);
    Plotly.react(divId, fig.data, fig.layout, { responsive: true });
}

function setStatus(msg) {
    const el = document.getElementById("sector-status");
    if (el) el.innerText = msg;
}
