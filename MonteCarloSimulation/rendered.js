// --- TAB SWITCHING LOGIC ---
const btnTabOverview = document.getElementById('btn-tab-overview');
const btnTabAnalysis = document.getElementById('btn-tab-analysis');
const tabOverview = document.getElementById('tab-overview');
const tabAnalysis = document.getElementById('tab-analysis');

function switchTab(activeBtn, activeTab, inactiveBtn, inactiveTab) {
    // Update button styling
    activeBtn.classList.add('active');
    inactiveBtn.classList.remove('active');
    // Update tab visibility
    activeTab.classList.add('active-tab');
    inactiveTab.classList.remove('active-tab');
}

btnTabOverview.addEventListener('click', () => {
    switchTab(btnTabOverview, tabOverview, btnTabAnalysis, tabAnalysis);
});

btnTabAnalysis.addEventListener('click', () => {
    switchTab(btnTabAnalysis, tabAnalysis, btnTabOverview, tabOverview);
});

// --- UI POPULATION LOGIC ---
// You will eventually call your FastAPI backend to get this list
const smifTickers = ['VSMAX', 'VFIAX', 'AAPL', 'MSFT', 'NVDA', 'BAC']; // Placeholder

function populateUI() {
    const tableBody = document.getElementById('holdings-body');
    const checkboxList = document.getElementById('stock-checkbox-list');

    smifTickers.forEach(ticker => {
        // 1. Populate the Tab 1 Table
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${ticker}</strong></td>
            <td>100</td> <td>$0.00</td> <td>$0.00</td> <td>Click for info...</td>
        `;
        tableBody.appendChild(tr);

        // 2. Populate the Tab 2 Checkboxes
        const div = document.createElement('div');
        div.className = 'checkbox-item';
        div.innerHTML = `
            <input type="checkbox" id="check-${ticker}" value="${ticker}" class="ticker-checkbox">
            <label for="check-${ticker}">${ticker}</label>
        `;
        checkboxList.appendChild(div);
    });
}

// Run this when the app loads
populateUI();

// --- TAB 2 BUTTON LOGIC ---
document.getElementById('btn-select-all').addEventListener('click', () => {
    const checkboxes = document.querySelectorAll('.ticker-checkbox');
    // Toggle based on the first checkbox's state
    const newState = !checkboxes[0].checked; 
    checkboxes.forEach(cb => cb.checked = newState);
});

document.getElementById('btn-run-monte').addEventListener('click', async () => {
    // Get all checked boxes
    const selected = Array.from(document.querySelectorAll('.ticker-checkbox:checked')).map(cb => cb.value);
    
    if (selected.length === 0) {
        alert("Please select at least one asset.");
        return;
    }

    console.log("Running Monte Carlo for:", selected);
    // TODO: Send 'selected' array to your FastAPI backend via fetch()
});