import React, { useEffect, useState } from "react";
const API_BASE = "http://localhost:8000";

export default function PoolView() {
  const [loading, setLoading] = useState(true);
  const [pool, setPool] = useState([]);
  const [error, setError] = useState("");

  async function fetchPool() {
    setLoading(true); setError("");
    try {
      const res = await fetch(`${API_BASE}/api/pool`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setPool(data.artists || []);
    } catch (e) {
      setError(e.message || "Error cargando pool");
    } finally {
      setLoading(false);
    }
  }

  async function removeOne(id) {
    const res = await fetch(`${API_BASE}/api/pool/${id}`, { method: "DELETE" });
    if (!res.ok) { alert("No se pudo eliminar"); return; }
    const data = await res.json();
    setPool(data.artists || []);
  }

  async function clearAll() {
    if (!window.confirm("¿Vaciar el pool completo?")) return;
    const res = await fetch(`${API_BASE}/api/pool`, { method: "DELETE" });
    if (!res.ok) { alert("No se pudo vaciar"); return; }
    const data = await res.json();
    setPool(data.artists || []);
  }

  useEffect(() => { fetchPool(); }, []);

  return (
    <div style={{ maxWidth: 920, margin: "2rem auto", padding: "0 1rem" }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 12 }}>
        🎒 Pool de artistas
      </h1>

      <div style={{ marginBottom: 12 }}>
        <button onClick={fetchPool} style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #111", marginRight: 8 }}>
          🔄 Refrescar
        </button>
        <button onClick={clearAll} style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #b00020", color: "#b00020" }}>
          🗑️ Vaciar pool
        </button>
      </div>

      {loading ? (
        <div>Cargando…</div>
      ) : error ? (
        <div style={{ color: "#b00020" }}><strong>Error:</strong> {error}</div>
      ) : pool.length === 0 ? (
        <div style={{ color: "#666" }}>Tu pool está vacío.</div>
      ) : (
        <table width="100%" cellPadding="8" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#f3f4f6" }}>
              <th align="left">Nombre</th>
              <th align="left">Seguidores</th>
              <th align="left">Popularidad</th>
              <th align="left">Géneros</th>
              <th align="left">Acción</th>
            </tr>
          </thead>
          <tbody>
            {pool.map((a) => (
              <tr key={a.id} style={{ borderTop: "1px solid #eee" }}>
                <td>{a.name}</td>
                <td>{a.followers?.toLocaleString?.() ?? a.followers}</td>
                <td>{a.popularity}</td>
                <td>{(a.genres || []).slice(0,3).join(", ") || "—"}</td>
                <td>
                  <button onClick={() => removeOne(a.id)}
                    style={{ padding: "6px 10px", borderRadius: 8, border: "1px solid #b00020", color: "#b00020" }}>
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
