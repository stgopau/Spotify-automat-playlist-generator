import React, { useState } from "react";

const API_BASE = "http://localhost:8000";

async function addToPool(artist) {
  const res = await fetch(`${API_BASE}/api/pool/add`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(artist),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}


export default function ArtistsSearch() {
  const [q, setQ] = useState("");
  const [market, setMarket] = useState("CL");
  const [limit, setLimit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState([]);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!q.trim()) return;
    setLoading(true);
    setError("");
    setResults([]);


    try {
      const res = await fetch(`${API_BASE}/api/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ q, limit: Number(limit), market }),
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`HTTP ${res.status}: ${txt}`);
      }
      const data = await res.json();
      setResults(data.items || []);
    } catch (err) {
      setError(err.message || "Error buscando artistas");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 920, margin: "2rem auto", padding: "0 1rem" }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 12 }}>
        🔎 Buscar artistas (Spotify)
      </h1>

      <form onSubmit={onSubmit} style={{ display: "grid", gap: 12, gridTemplateColumns: "2fr 100px 100px 120px" }}>
        <input
          type="text"
          placeholder="Nombre del artista (p. ej. Arcangel)"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          style={{ padding: "10px", borderRadius: 8, border: "1px solid #ddd" }}
        />
        <select value={market} onChange={(e) => setMarket(e.target.value)} style={{ padding: "10px", borderRadius: 8, border: "1px solid #ddd" }}>
          {["CL","US","ES","MX","AR","BR"].map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        <input
          type="number"
          min={1}
          max={50}
          value={limit}
          onChange={(e) => setLimit(e.target.value)}
          style={{ padding: "10px", borderRadius: 8, border: "1px solid #ddd" }}
        />
        <button
          type="submit"
          disabled={loading}
          style={{
            padding: "10px",
            borderRadius: 8,
            border: "1px solid #222",
            background: "#111",
            color: "#fff",
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Buscando..." : "Buscar"}
        </button>
      </form>

      {error && (
        <div style={{ marginTop: 12, color: "#b00020" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      <div style={{ marginTop: 20 }}>
        {results.length === 0 && !loading ? (
          <div style={{ color: "#666" }}>Sin resultados (aún)</div>
        ) : (
          <table width="100%" cellPadding="8" style={{ borderCollapse: "collapse", marginTop: 8 }}>
            <thead>
              <tr style={{ background: "#f3f4f6" }}>
                <th align="left">Nombre</th>
                <th align="left">Seguidores</th>
                <th align="left">Popularidad</th>
                <th align="left">Géneros</th>
                <th align="left">Link</th>
                <th align="left">Acción</th>
              </tr>
            </thead>
            <tbody>
                {results.map((a) => (
                    <tr key={a.id} style={{ borderTop: "1px solid #eee" }}>
                    <td>{a.name}</td>
                    <td>{a.followers?.toLocaleString?.() ?? a.followers}</td>
                    <td>{a.popularity}</td>
                    <td>{(a.genres || []).slice(0,3).join(", ") || "—"}</td>
                    <td><a href={a.url} target="_blank" rel="noreferrer">Abrir</a></td>
                    <td>
                        <button
                        onClick={async () => {
                            try {
                            await addToPool(a);
                            alert(`Añadido al pool: ${a.name}`);
                            } catch (e) {
                            alert("No se pudo agregar al pool");
                            }
                        }}
                        style={{ padding: "6px 10px", borderRadius: 8, border: "1px solid #111", background: "#111", color: "#fff" }}
                        >
                        Agregar
                        </button>
                    </td>
                    </tr>
                ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
