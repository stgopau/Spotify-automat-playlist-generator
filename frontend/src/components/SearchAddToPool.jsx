import React, { useEffect, useRef, useState } from "react";

const API_BASE = "http://localhost:8000";

export default function SearchAddToPool({ market = "CL", onAdded }) {
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const debounceRef = useRef(null);

  useEffect(() => {
    if (!q.trim()) {
      setResults([]);
      setOpen(false);
      return;
    }

    function onClick(e) {
      if (!e.target.closest("[data-search-pool]")) {
        setOpen(false);
        setQ("");
      }
    }
    window.addEventListener("click", onClick);

    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/search`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ q, limit: 8, market }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setResults(data.items || []);
        setOpen(true);
      } catch {
        setResults([]);
        setOpen(false);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(debounceRef.current);
  }, [q, market]);

  async function addToPool(artist) {
    const r = await fetch(`${API_BASE}/api/pool/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(artist),
    });
    if (r.ok) {
      onAdded?.(artist);
      setQ("");          // limpia la búsqueda
      setResults([]);    // cierra el dropdown
      setOpen(false);
    }
  }

  return (
    <div style={{ position: "relative" }} data-search-pool>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Buscar artista…"
        style={{
          width: "90%",
          padding: "8px 10px",
          borderRadius: 8,
          border: "1px solid #ddd",
        }}
      />
      {loading && (
        <div style={{ fontSize: 12, color: "#666", marginTop: 6 }}>Buscando…</div>
      )}

      {open && results.length > 0 && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            background: "#fff",
            border: "1px solid #eee",
            borderRadius: 8,
            marginTop: 6,
            maxHeight: 280,
            overflowY: "auto",
            zIndex: 30,
            boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
          }}
        >
          <ul style={{ listStyle: "none", padding: 6, margin: 0 }}>
            {results.map((a) => (
              <li
                key={a.id}
                onClick={() => addToPool(a)} // 👈 ahora el click entero agrega
                style={{
                  display: "flex",
                  flexDirection: "column",
                  padding: "6px 8px",
                  borderRadius: 8,
                  cursor: "pointer",
                }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.background = "#f3f4f6")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.background = "transparent")
                }
              >
                <div
                  style={{
                    fontSize: 14,
                    fontWeight: 600,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {a.name}
                </div>
                <div
                  style={{
                    fontSize: 12,
                    color: "#666",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {(a.genres || []).slice(0, 2).join(", ") || "—"}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
