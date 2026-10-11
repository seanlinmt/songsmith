export const api = {
  async json(res) {
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch (_) { /* non-JSON */ }
    if (!res.ok) {
      const detail = data && (data.detail || data.error || data.message);
      throw new Error(detail ? (typeof detail === "string" ? detail : JSON.stringify(detail)) : "HTTP " + res.status);
    }
    return data;
  },
  get(path) { return fetch(path).then((r) => this.json(r)); },
  send(path, method, body) {
    return fetch(path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    }).then((r) => this.json(r));
  },
};
