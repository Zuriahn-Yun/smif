import { post } from "./api.js";

export function init() {
    document.getElementById("btn-summarize").addEventListener("click", summarize);
    document.getElementById("btn-compare").addEventListener("click", compare);
}

async function summarize() {
    const ticker = document.getElementById("ai-ticker-input").value.trim().toUpperCase();
    const query = document.getElementById("ai-query-input").value.trim() ||
        "Summarize the investment thesis, key risks, and recent developments.";

    if (!ticker) { alert("Enter a ticker symbol."); return; }

    setStatus("Querying AI...");
    setResponse("");
    try {
        const data = await post("/ai/summarize_ticker", { ticker, query });
        setResponse(`<h4>${data.ticker} — ${data.query}</h4><p>${data.response.replace(/\n/g, "<br>")}</p>`);
        setStatus("");
    } catch (err) {
        setStatus("Error: " + err.message);
        if (err.message.includes("ANTHROPIC_API_KEY")) {
            setResponse('<p style="color:#888">AI research requires an ANTHROPIC_API_KEY environment variable to be set on the server. See the deployment guide.</p>');
        }
    }
}

async function compare() {
    const raw = document.getElementById("ai-compare-input").value.trim();
    const tickers = raw.split(/[\s,]+/).map(t => t.toUpperCase()).filter(Boolean);
    const focus = document.getElementById("ai-focus-input").value.trim() || "valuation and growth prospects";

    if (tickers.length < 2) { alert("Enter at least 2 tickers to compare."); return; }
    if (tickers.length > 5) { alert("Maximum 5 tickers for comparison."); return; }

    setStatus("Querying AI...");
    setResponse("");
    try {
        const data = await post("/ai/compare_tickers", { tickers, focus });
        setResponse(`<h4>Comparison: ${data.tickers.join(" vs ")} — ${data.focus}</h4><p>${data.response.replace(/\n/g, "<br>")}</p>`);
        setStatus("");
    } catch (err) {
        setStatus("Error: " + err.message);
    }
}

function setStatus(msg) {
    const el = document.getElementById("ai-status");
    if (el) el.innerText = msg;
}

function setResponse(html) {
    const el = document.getElementById("ai-response");
    if (el) el.innerHTML = html;
}
