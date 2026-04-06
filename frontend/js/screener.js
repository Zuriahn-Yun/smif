import { post } from "./api.js";

const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

export function init() {
    document.getElementById("btn-run-screener").addEventListener("click", runScreener);
    document.getElementById("btn-clear-screener").addEventListener("click", clearResults);
    document.getElementById("screener-ticker-input").addEventListener("keydown", e => {
        if (e.key === "Enter") runScreener();
    });
}

async function runScreener() {
    const raw = document.getElementById("screener-ticker-input").value;
    const tickers = raw.split(/[\s,]+/).map(t => t.trim().toUpperCase()).filter(Boolean);

    if (!tickers.length) { alert("Enter at least one ticker."); return; }
    if (tickers.length > 100) { alert("Maximum 100 tickers per screen."); return; }

    const req = {
        tickers,
        sector: document.getElementById("filter-sector").value || null,
        min_market_cap: parseFloat(document.getElementById("filter-min-cap").value) * 1e9 || null,
        max_pe: parseFloat(document.getElementById("filter-max-pe").value) || null,
        min_pe: parseFloat(document.getElementById("filter-min-pe").value) || null,
        min_revenue_growth: parseFloat(document.getElementById("filter-min-rev-growth").value) / 100 || null,
        min_roe: parseFloat(document.getElementById("filter-min-roe").value) / 100 || null,
    };

    setStatus(`Screening ${tickers.length} tickers... (may take ${Math.ceil(tickers.length * 0.4)}s)`);
    document.getElementById("screener-results-body").innerHTML =
        `<tr><td colspan="10" style="text-align:center">Running screen...</td></tr>`;

    try {
        const data = await post("/screener/screen", req);
        renderResults(data);
        setStatus(`${data.total_passed} of ${data.total_screened} passed. ${data.errors.length ? `(${data.errors.length} tickers failed to load)` : ""}`);
    } catch (err) {
        setStatus("Error: " + err.message);
    }
}

function renderResults(data) {
    const tbody = document.getElementById("screener-results-body");
    if (!data.results.length) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align:center;color:#888">No results matched the filters.</td></tr>`;
        return;
    }

    tbody.innerHTML = "";
    data.results.forEach(r => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><strong>${r.ticker}</strong></td>
            <td style="max-width:180px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="${r.name}">${r.name}</td>
            <td>${r.sector || "N/A"}</td>
            <td>${r.price != null ? currency.format(r.price) : "N/A"}</td>
            <td>${r.market_cap_fmt}</td>
            <td>${r.trailing_pe != null ? r.trailing_pe.toFixed(1) : "N/A"}</td>
            <td>${r.revenue_growth_pct != null ? r.revenue_growth_pct + "%" : "N/A"}</td>
            <td>${r.roe_pct != null ? r.roe_pct + "%" : "N/A"}</td>
            <td>${r.profit_margin_pct != null ? r.profit_margin_pct + "%" : "N/A"}</td>
            <td>${r.dividend_yield_pct != null ? r.dividend_yield_pct + "%" : "—"}</td>
        `;
        tbody.appendChild(tr);
    });
}

function clearResults() {
    document.getElementById("screener-results-body").innerHTML = "";
    document.getElementById("screener-ticker-input").value = "";
    setStatus("");
}

function setStatus(msg) {
    const el = document.getElementById("screener-status");
    if (el) el.innerText = msg;
}
