import React, { useState } from "react";
const API_BASE = "http://localhost:8000";

export default function Playlists() {
  const [name, setName] = useState("AutoMix");
  const [description, setDescription] = useState("");
  const [isPublic, setIsPublic] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [playlistInfo, setPlaylistInfo] = useState(null);
  const [addResult, setAddResult] = useState(null);

  const onCreate = async (e) => {
    e.preventDefault();
    setError(""); setAddResult(null); setPlaylistInfo(null);
    setCreating(true);
    try {
      // 1) Crear playlist
      const res = await fetch(`${API_BASE}/api/playlists/create`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ name, description, public: isPublic }),
      });
      if (!res.ok) throw new Error(`Create HTTP ${res.status}: ${await res.text()}`);
      const pl = await res.json();
      setPlaylistInfo(pl);

      // 2) Agregar recs persistidas
      const res2 = await fetch(`${API_BASE}/api/playlists/add`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ playlist_id: pl.id }),
      });
      if (!res2.ok) throw new Error(`Add HTTP ${res2.status}: ${await res2.text()}`);
      const added = await res2.json();
      setAddResult(added);
    } catch (err) {
      setError(err.message || "Error en playlist");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: "2rem auto", padding: "0 1rem" }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 12 }}>🧩 Playlists</h1>
      <form onSubmit={onCreate} style={{ display: "grid", gap: 12, gridTemplateColumns: "1fr 2fr 120px 140px" }}>
        <input placeholder="Nombre" value={name} onChange={(e)=>setName(e.target.value)}
               style={{ padding: 10, borderRadius: 8, border: "1px solid #ddd" }} />
        <input placeholder="Descripción" value={description} onChange={(e)=>setDescription(e.target.value)}
               style={{ padding: 10, borderRadius: 8, border: "1px solid #ddd" }} />
        <label style={{ display:"flex", alignItems:"center", gap:8 }}>
          <input type="checkbox" checked={isPublic} onChange={(e)=>setIsPublic(e.target.checked)} />
          Pública
        </label>
        <button type="submit" disabled={creating}
                style={{ padding:"10px 12px", borderRadius:8, border:"1px solid #111", background:"#111", color:"#fff" }}>
          {creating ? "Creando..." : "Crear y agregar recs"}
        </button>
      </form>

      {error && <div style={{ marginTop: 12, color:"#b00020" }}><strong>Error:</strong> {error}</div>}

      {playlistInfo && (
        <div style={{ marginTop: 16 }}>
          <div>✔ Playlist creada: <strong>{playlistInfo.name}</strong></div>
          {playlistInfo.url && <div>Enlace: <a href={playlistInfo.url} target="_blank" rel="noreferrer">{playlistInfo.url}</a></div>}
        </div>
      )}

      {addResult && (
        <div style={{ marginTop: 8 }}>
          <div>✔ Canciones agregadas: <strong>{addResult.added}</strong></div>
          {addResult.reason === "no_recommendations" && (
            <div style={{ color:"#b00020" }}>No había recomendaciones persistidas. Genera primero en la pestaña Recomendaciones.</div>
          )}
        </div>
      )}
    </div>
  );
}
