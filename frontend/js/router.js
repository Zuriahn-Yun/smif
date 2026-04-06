// Generic tab router. Reads data-tab-btn and data-tab-id attributes.
// Each tab JS module should export an init() function called on first activation.

const _initialized = new Set();
const _modules = {};

export function registerTab(tabId, initFn) {
    _modules[tabId] = initFn;
}

export function activateTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active-tab"));
    document.querySelectorAll("[data-tab-btn]").forEach(btn => btn.classList.remove("active"));

    const content = document.getElementById(tabId);
    const btn = document.querySelector(`[data-tab-btn="${tabId}"]`);
    if (content) content.classList.add("active-tab");
    if (btn) btn.classList.add("active");

    if (_modules[tabId] && !_initialized.has(tabId)) {
        _initialized.add(tabId);
        _modules[tabId]();
    }
}

export function initRouter(defaultTab) {
    document.querySelectorAll("[data-tab-btn]").forEach(btn => {
        btn.addEventListener("click", () => activateTab(btn.dataset.tabBtn));
    });
    if (defaultTab) activateTab(defaultTab);
}
