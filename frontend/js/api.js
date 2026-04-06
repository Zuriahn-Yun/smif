// Centralized API module — all fetch calls go through here.
// Set window.SMIF_API_URL before loading this script to override (e.g., for local dev).
const BASE_URL = (typeof window !== "undefined" && window.SMIF_API_URL) ? window.SMIF_API_URL : "";

export async function get(path) {
    const res = await fetch(BASE_URL + path);
    if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
    return res.json();
}

export async function post(path, body) {
    const res = await fetch(BASE_URL + path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `POST ${path} failed: ${res.status}`);
    }
    return res.json();
}
