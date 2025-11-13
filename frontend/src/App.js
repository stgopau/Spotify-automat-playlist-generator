// frontend/src/App.js
import React, { useState } from "react";
import ArtistsSearch from "./components/ArtistsSearch";
import PoolView from "./components/PoolView";
import Recommendations from "./components/Recommendations";
import Playlists from "./components/Playlists";

export default function App() {
  const [tab, setTab] = useState("search");

  return (
    <div>
      <div style={{ display: "flex", gap: 8, padding: "12px", borderBottom: "1px solid #eee" }}>
        <button onClick={() => setTab("search")} style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #111", background: tab==="search"?"#111":"#fff", color: tab==="search"?"#fff":"#111" }}>
          Buscar artistas
        </button>
        <button onClick={() => setTab("pool")} style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #111", background: tab==="pool"?"#111":"#fff", color: tab==="pool"?"#fff":"#111" }}>
          Ver Pool
        </button>
        <button onClick={() => setTab("recs")} style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #111", background: tab==="recs"?"#111":"#fff", color: tab==="recs"?"#fff":"#111"  }}>
          Recomendaciones
        </button>
        <button onClick={() => setTab("pl")} style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #111", background: tab==="pl"?"#111":"#fff", color: tab==="pl"?"#fff":"#111"  }}>
          Playlists
        </button>
      </div>
      {tab === "search" && <ArtistsSearch />}
      {tab === "pool" && <PoolView />}
      {tab === "recs" && <Recommendations />}
      {tab === "pl" && <Playlists />}
    </div>
  );
}


