import { get } from "./api.js";

const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

export function init() {
    loadOverview();
}

async function loadOverview() {
    const totalEl = document.getElementById("total-fund-value");
    const tbody = document.getElementById("holdings-body");

    try {
        const data = await get("/monte/portfolio_overview");

        if (data.status === "loading") {
            totalEl.innerText = "Loading Market Data...";
            tbody.innerHTML = `<tr><td colspan="5" style="text-align:center">${data.message}</td></tr>`;
            setTimeout(loadOverview, 3000);
            return;
        }

        totalEl.innerText = currency.format(data.total_value);
        tbody.innerHTML = "";

        data.assets.forEach(asset => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${asset.ticker}</strong></td>
                <td>${asset.shares.toLocaleString()}</td>
                <td>${currency.format(asset.last_price)}</td>
                <td style="color:#005A9C;font-weight:bold">${currency.format(asset.estimated_value)}</td>
                <td style="color:#666;font-size:0.9em">${asset.description}</td>
            `;
            tr.addEventListener("click", () => {
                // Open fundamentals tab for this ticker
                import("./router.js").then(r => r.activateTab("tab-fundamentals"));
                import("./fundamentals.js").then(m => m.loadTicker(asset.ticker));
            });
            tbody.appendChild(tr);
        });

    } catch (err) {
        totalEl.innerText = "Connection Error";
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:red">Could not connect to backend. Retrying...</td></tr>`;
        setTimeout(loadOverview, 3000);
    }
}
