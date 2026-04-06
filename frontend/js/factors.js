import { post } from "./api.js";

export function init() {
    document.getElementById("btn-run-ff").addEventListener("click", runFF);
    document.getElementById("btn-run-rolling").addEventListener("click", runRolling);
}

async function runFF() {
    const years = parseInt(document.getElementById("ff-lookback").value) || 3;
    setStatus("Running Fama-French regression...");
    try {
        const data = await post("/factors/fama_french", { lookback_years: years });

        const fig = JSON.parse(data.figure);
        Plotly.react("factors-plot", fig.data, fig.layout, { responsive: true });

        const fl = data.factor_loadings;
        document.getElementById("factors-results").innerHTML = `
            <table>
                <thead><tr><th>Factor</th><th>Beta</th><th>t-stat</th><th>p-value</th><th>Interpretation</th></tr></thead>
                <tbody>
                    <tr>
                        <td>Market (Mkt-RF)</td>
                        <td>${fl["Mkt-RF"].beta.toFixed(4)}</td>
                        <td>${fl["Mkt-RF"].t_stat.toFixed(3)}</td>
                        <td>${fl["Mkt-RF"].p_value.toFixed(4)}</td>
                        <td>${fl["Mkt-RF"].beta > 1.1 ? "Aggressive (>1)" : fl["Mkt-RF"].beta < 0.9 ? "Defensive (<1)" : "Market-like"}</td>
                    </tr>
                    <tr>
                        <td>Size (SMB)</td>
                        <td>${fl["SMB"].beta.toFixed(4)}</td>
                        <td>${fl["SMB"].t_stat.toFixed(3)}</td>
                        <td>${fl["SMB"].p_value.toFixed(4)}</td>
                        <td>${fl["SMB"].beta > 0.1 ? "Tilted small-cap" : fl["SMB"].beta < -0.1 ? "Tilted large-cap" : "Neutral"}</td>
                    </tr>
                    <tr>
                        <td>Value (HML)</td>
                        <td>${fl["HML"].beta.toFixed(4)}</td>
                        <td>${fl["HML"].t_stat.toFixed(3)}</td>
                        <td>${fl["HML"].p_value.toFixed(4)}</td>
                        <td>${fl["HML"].beta > 0.1 ? "Tilted value" : fl["HML"].beta < -0.1 ? "Tilted growth" : "Neutral"}</td>
                    </tr>
                </tbody>
            </table>
            <div class="metric-cards" style="margin-top:16px">
                <div class="metric-card">
                    <div class="metric-label">Alpha (Annualized)</div>
                    <div class="metric-value" style="color:${data.alpha_annualized >= 0 ? '#5cb85c' : '#d9534f'}">
                        ${(data.alpha_annualized * 100).toFixed(2)}%
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">R² (Explained)</div>
                    <div class="metric-value">${(data.r_squared * 100).toFixed(1)}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Observations</div>
                    <div class="metric-value">${data.observations.toLocaleString()} days</div>
                </div>
            </div>
            <p style="color:#888;font-size:0.85em;margin-top:8px">${data.period} · ${data.note}</p>
        `;
        setStatus("Regression complete.");
    } catch (err) {
        setStatus("Error: " + err.message);
    }
}

async function runRolling() {
    const window = parseInt(document.getElementById("ff-window").value) || 12;
    const years = parseInt(document.getElementById("ff-lookback").value) || 3;
    setStatus("Computing rolling betas...");
    try {
        const data = await post("/factors/rolling_betas", { window_months: window, lookback_years: years });
        const fig = JSON.parse(data.figure);
        Plotly.react("factors-plot", fig.data, fig.layout, { responsive: true });

        const cb = data.current_betas;
        document.getElementById("factors-results").innerHTML = `
            <div class="metric-cards">
                <div class="metric-card">
                    <div class="metric-label">Current Market Beta</div>
                    <div class="metric-value">${cb["Mkt-RF"] != null ? cb["Mkt-RF"].toFixed(3) : "N/A"}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Current Size Beta</div>
                    <div class="metric-value">${cb["SMB"] != null ? cb["SMB"].toFixed(3) : "N/A"}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Current Value Beta</div>
                    <div class="metric-value">${cb["HML"] != null ? cb["HML"].toFixed(3) : "N/A"}</div>
                </div>
            </div>
        `;
        setStatus("Rolling betas complete.");
    } catch (err) {
        setStatus("Error: " + err.message);
    }
}

function setStatus(msg) {
    const el = document.getElementById("factors-status");
    if (el) el.innerText = msg;
}
