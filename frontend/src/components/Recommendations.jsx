import React, { useEffect, useState } from "react";
import SearchAddToPool from "./SearchAddToPool";
const API_BASE = "http://localhost:8000";

export default function Recommendations() {
  // Form recs
  const [size, setSize] = useState(150);
  const [minPopularity, setMinPopularity] = useState(60);
  const [dateFilter, setDateFilter] = useState("");
  const [market, setMarket] = useState("CL");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Datos
  const [tracks, setTracks] = useState([]);
  const [pool, setPool] = useState([]);
  const [poolLoading, setPoolLoading] = useState(false);

  // Modal playlist
  const [showModal, setShowModal] = useState(false);
  const [plName, setPlName] = useState("AutoMix");
  const [plDesc, setPlDesc] = useState("");
  const [creatingPlaylist, setCreatingPlaylist] = useState(false);
  const [playlistInfo, setPlaylistInfo] = useState(null);
  const [addResult, setAddResult] = useState(null);
  const [plError, setPlError] = useState("");

  // --- Pool: cargar y eliminar ---
  async function fetchPool() {
    setPoolLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/pool`);
      const data = await res.json();
      setPool(data.artists || []);
    } catch (e) {
      // no hard fail
    } finally {
      setPoolLoading(false);
    }
  }

  async function clearAll() {
    if (!window.confirm("¿Vaciar el pool completo?")) return;
    const res = await fetch(`${API_BASE}/api/pool`, { method: "DELETE" });
    if (!res.ok) { alert("No se pudo vaciar"); return; }
    const data = await res.json();
    setPool(data.artists || []);
  }

  async function removeFromPool(id) {
    const res = await fetch(`${API_BASE}/api/pool/${id}`, { method: "DELETE" });
    if (res.ok) {
      const data = await res.json();
      setPool(data.artists || []);
    }
  }

  useEffect(() => { fetchPool(); }, []);

  // --- Generar recomendaciones ---
  const onGenerate = async (e) => {
    e.preventDefault();
    setLoading(true); setError(""); setTracks([]);
    try {
      const res = await fetch(`${API_BASE}/api/recs`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({
          total: Number(size),
          min_popularity: Number.isFinite(+minPopularity) ? +minPopularity : null,
          date_filter: (dateFilter || "").trim(),
          market
        })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      const data = await res.json();
      setTracks(data.tracks || []);
    } catch (err) {
      setError(err.message || "Error generando recomendaciones");
    } finally {
      setLoading(false);
    }
  };

  // --- Crear playlist (modal -> create + add) ---
  async function createAndAddPlaylist() {
    setCreatingPlaylist(true);
    setPlError(""); setPlaylistInfo(null); setAddResult(null);
    try {
      // 1) crear
      const r1 = await fetch(`${API_BASE}/api/playlists/create`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ name: plName, description: plDesc, public: true })
      });
      if (!r1.ok) throw new Error(`Create HTTP ${r1.status}: ${await r1.text()}`);
      const pl = await r1.json();
      setPlaylistInfo(pl);

      // 2) agregar últimas recomendaciones persistidas (el backend usa playlist_recs.json)
      // Como ya llamaste /api/recs, ese JSON debería estar actualizado.
      const r2 = await fetch(`${API_BASE}/api/playlists/add`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ playlist_id: pl.id })
      });
      if (!r2.ok) throw new Error(`Add HTTP ${r2.status}: ${await r2.text()}`);
      const added = await r2.json();
      setAddResult(added);
    } catch (e) {
      setPlError(e.message || "Error creando/agregando playlist");
    } finally {
      setCreatingPlaylist(false);
    }
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 16, maxWidth: 1300, margin: "1.5rem auto", padding: "0 1rem" }}>
      {/* Sidebar Pool */}
      <aside style={{ border: "1px solid #e5e7eb", borderRadius: 12, padding: 12, height: "fit-content" }}>
        <div style={{ marginBottom: 10 }}>
          <SearchAddToPool
            market={market /* si lo tienes en estado, o "CL" */}
            onAdded={() => fetchPool()} // refresca pool al agregar
          />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Pool de artistas</div>
          <button onClick={clearAll} style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #b00020", color: "#b00020" }}>
            🗑️ Vaciar pool
          </button>
        </div>
        {/* <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <button onClick={fetchPool} style={{ padding: "6px 10px", borderRadius: 8, border: "1px solid #111" }}>🔄 Refrescar</button>
        </div> */}
        {poolLoading ? (
          <div style={{ color: "#666" }}>Cargando…</div>
        ) : pool.length === 0 ? (
          <div style={{ color: "#666" }}>Tu pool está vacío.</div>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 6 }}>
            {pool.map((a) => (
              <li key={a.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, border: "1px solid #eee", padding: "6px 8px", borderRadius: 8 }}>
                <span style={{ fontSize: 14, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{a.name}</span>
                <button
                  onClick={() => removeFromPool(a.id)}
                  title="Quitar"
                  aria-label={`Quitar ${a.name}`}
                  style={{ border: "1px solid #b00020", color: "#b00020", background: "transparent", borderRadius: 8, padding: "2px 8px", fontWeight: 700 }}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      {/* Main */}
      <section>
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 12 }}>🎼 Recomendaciones</h1>

        <form onSubmit={onGenerate} style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end", marginBottom: 12 }}>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <label className="block text-sm">Tamaño</label>
            <input type="number" min={1} max={200} value={size} onChange={(e)=>setSize(e.target.value)}
              style={{ padding: 10, borderRadius: 8, border: "1px solid #ddd", width: 120 }} />
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <label className="block text-sm">Min Popularidad</label>
            <input type="number" min={0} max={100} value={minPopularity} onChange={(e)=>setMinPopularity(e.target.value)}
              style={{ padding: 10, borderRadius: 8, border: "1px solid #ddd", width: 150 }} />
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <label className="block text-sm">Filtro fecha</label>
            <input placeholder='Opcional: "6m", "2a", o "2010"' value={dateFilter} onChange={(e)=>setDateFilter(e.target.value)}
              style={{ padding: 10, borderRadius: 8, border: "1px solid #ddd", width: 180 }} />
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <label className="block text-sm">Market</label>
            <select value={market} onChange={(e)=>setMarket(e.target.value)}
              style={{ padding: 10, borderRadius: 8, border: "1px solid #ddd", width: 120 }}>
              {["CL","US","ES","MX","AR","BR"].map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <button type="submit" disabled={loading}
            style={{ padding:"10px 14px", borderRadius:8, border:"1px solid #111", background:"#111", color:"#fff" }}>
            {loading ? "Generando..." : "Generar"}
          </button>

          {/* Botón Crear Playlist con modal */}
          <button
            type="button"
            onClick={() => setShowModal(true)}
            disabled={tracks.length === 0}
            style={{ padding:"10px 14px", borderRadius:8, border:"1px solid #111", background:"#fff", color:"#111", opacity: tracks.length ? 1 : 0.5 }}
            title={tracks.length ? "Crear playlist con estas canciones" : "Genera recomendaciones primero"}
          >
            Crear playlist
          </button>
        </form>

        {error && <div style={{ marginBottom: 8, color: "#b00020" }}><strong>Error:</strong> {error}</div>}

        {/* Tabla de resultados con índice 1..N */}
        <div>
          {tracks.length === 0 && !loading ? (
            <div style={{ color: "#666" }}>Sin resultados aún.</div>
          ) : (
            <table width="100%" cellPadding="8" style={{ borderCollapse: "collapse", marginTop: 8 }}>
              <thead>
                <tr style={{ background: "#f3f4f6" }}>
                  <th align="left" style={{ width: 60 }}>#</th>
                  <th align="left">Canción</th>
                  <th align="left">Artista(s)</th>
                  <th align="left">Popularidad</th>
                  <th align="left">Fecha</th>
                  <th align="left">Link</th>
                </tr>
              </thead>
              <tbody>
                {tracks.map((t, idx) => (
                  <tr key={t.id} style={{ borderTop: "1px solid #eee" }}>
                    <td>{idx + 1}</td>
                    <td>{t.name}</td>
                    <td>{(t.artists || []).join(", ")}</td>
                    <td>{t.popularity ?? "—"}</td>
                    <td>{t.release_date || "—"}</td>
                    <td><a href={t.url} target="_blank" rel="noreferrer">Abrir</a></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* Modal: crear playlist */}
      {showModal && (
        <div style={{
          position:"fixed", inset:0, background:"rgba(0,0,0,0.4)", display:"flex", alignItems:"center", justifyContent:"center", zIndex: 50
        }}>
          <div style={{ background:"#fff", color:"#111", minWidth: 420, borderRadius: 12, padding: 16, boxShadow:"0 10px 30px rgba(0,0,0,0.2)" }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom: 8 }}>
              <div style={{ fontWeight: 700 }}>Crear playlist</div>
              <button onClick={()=>setShowModal(false)} style={{ border:"none", background:"transparent", fontSize: 20, lineHeight: 1 }}>×</button>
            </div>

            <div style={{ display:"grid", gap: 8 }}>
              <input placeholder="Nombre de la playlist" value={plName} onChange={(e)=>setPlName(e.target.value)}
                style={{ padding: 10, borderRadius: 8, border: "1px solid #ddd" }} />
              <textarea placeholder="Descripción (opcional)" value={plDesc} onChange={(e)=>setPlDesc(e.target.value)}
                style={{ padding: 10, borderRadius: 8, border: "1px solid #ddd", minHeight: 80 }} />
            </div>

            {plError && <div style={{ marginTop: 8, color:"#b00020" }}><strong>Error:</strong> {plError}</div>}
            {playlistInfo && (
              <div style={{ marginTop: 8 }}>
                ✔ Playlist creada: <strong>{playlistInfo.name}</strong>{" "}
                {playlistInfo.url && (<a href={playlistInfo.url} target="_blank" rel="noreferrer">Abrir</a>)}
              </div>
            )}
            {addResult && (
              <div style={{ marginTop: 4 }}>
                ✔ Canciones agregadas: <strong>{addResult.added}</strong>
              </div>
            )}

            <div style={{ display:"flex", gap: 8, justifyContent:"flex-end", marginTop: 12 }}>
              <button onClick={()=>setShowModal(false)} style={{ padding:"8px 12px", borderRadius:8, border:"1px solid #ccc" }}>
                Cancelar
              </button>
              <button
                onClick={createAndAddPlaylist}
                disabled={creatingPlaylist || tracks.length === 0}
                style={{ padding:"8px 12px", borderRadius:8, border:"1px solid #111", background:"#111", color:"#fff", opacity: tracks.length ? 1 : 0.6 }}
              >
                {creatingPlaylist ? "Creando…" : "Crear y agregar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
