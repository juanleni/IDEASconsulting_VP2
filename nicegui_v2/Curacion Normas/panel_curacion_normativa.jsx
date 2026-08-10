import React, { useState, useMemo } from "react";
import {
  Search, ExternalLink, Check, X, Clock, Filter,
  RefreshCw, FileText, ShieldCheck, Leaf, AlertTriangle,
  Sparkles, Database, Radar,
} from "lucide-react";

const FUENTES = [
  { id: "saij", nombre: "SAIJ — Normativa Provincial", tipo: "dataset_abierto", frecuencia: "mensual", activa: true },
  { id: "srt_digesto", nombre: "Digesto SRT — API", tipo: "api", frecuencia: "semanal", activa: true },
  { id: "bo_pba", nombre: "Boletín Oficial PBA", tipo: "scraper", frecuencia: "diaria", activa: false },
];

const SEED = [
  { id: 1, fuente: "saij", provincia: "Buenos Aires", tipo: "ley", numero: "5965", titulo: "Protección a las fuentes de provisión y a los cursos y cuerpos receptores de agua y a la atmósfera", tema: "ambiente", estado: "vigente", fecha_sancion: "1958", fecha_publicacion: "1958", revision: "pendiente", esNuevo: false, link: "https://www.opds.gba.gov.ar/normativas-provinciales" },
  { id: 2, fuente: "saij", provincia: "Buenos Aires", tipo: "ley", numero: "11.459", titulo: "Radicación Industrial — Certificado de Aptitud Ambiental", tema: "ambiente", estado: "vigente", fecha_sancion: "1993", fecha_publicacion: "1993", revision: "aprobada", esNuevo: false, link: "https://www.ambiente.gba.gob.ar/sites/default/files/Ley%2011459.pdf" },
  { id: 3, fuente: "saij", provincia: "Buenos Aires", tipo: "decreto", numero: "531/2019", titulo: "Reglamentario de la Ley 11.459 — Radicación y categorización de industrias", tema: "ambiente", estado: "vigente", fecha_sancion: "2019", fecha_publicacion: "2019", revision: "aprobada", esNuevo: false, link: "#" },
  { id: 4, fuente: "saij", provincia: "Buenos Aires", tipo: "ley", numero: "11.723", titulo: "Ley Integral del Medio Ambiente y los Recursos Naturales", tema: "ambiente", estado: "vigente", fecha_sancion: "1995", fecha_publicacion: "1995", revision: "pendiente", esNuevo: false, link: "#" },
  { id: 5, fuente: "saij", provincia: "Buenos Aires", tipo: "ley", numero: "13.592", titulo: "Gestión Integral de Residuos Sólidos Urbanos", tema: "ambiente", estado: "vigente", fecha_sancion: "2004", fecha_publicacion: "2004", revision: "pendiente", esNuevo: false, link: "#" },
  { id: 6, fuente: "saij", provincia: "Buenos Aires", tipo: "ley", numero: "14.408", titulo: "Comités Mixtos de Salud, Higiene y Seguridad en el Empleo", tema: "sst", estado: "vigente", fecha_sancion: "2012", fecha_publicacion: "2012", revision: "aprobada", esNuevo: false, link: "#" },
  { id: 7, fuente: "saij", provincia: "Buenos Aires", tipo: "decreto", numero: "801/2014", titulo: "Reglamentario de la Ley 14.408 — Comités Mixtos", tema: "sst", estado: "vigente", fecha_sancion: "2014", fecha_publicacion: "2014", revision: "pendiente", esNuevo: false, link: "#" },
  { id: 8, fuente: "saij", provincia: "Buenos Aires", tipo: "ley", numero: "13.168", titulo: "Violencia Laboral — trabajo, maltrato, denuncia, sumario", tema: "sst", estado: "vigente", fecha_sancion: "2004", fecha_publicacion: "2004", revision: "rechazada", esNuevo: false, link: "#" },
  { id: 9, fuente: "saij", provincia: "Nación", tipo: "ley", numero: "19.587", titulo: "Higiene y Seguridad en el Trabajo", tema: "sst", estado: "vigente", fecha_sancion: "1972", fecha_publicacion: "1972", revision: "aprobada", esNuevo: false, link: "#" },
  { id: 10, fuente: "saij", provincia: "Nación", tipo: "decreto", numero: "351/1979", titulo: "Reglamentario de la Ley 19.587 — Anexos I a VIII", tema: "sst", estado: "vigente", fecha_sancion: "1979", fecha_publicacion: "1979", revision: "pendiente", esNuevo: false, link: "#" },
  { id: 11, fuente: "saij", provincia: "Buenos Aires", tipo: "resolucion", numero: "159/1996", titulo: "Método de medición y clasificación de ruidos molestos", tema: "ambiente", estado: "vigente", fecha_sancion: "1996", fecha_publicacion: "1996", revision: "pendiente", esNuevo: false, link: "#" },
  { id: 12, fuente: "saij", provincia: "Buenos Aires", tipo: "ley", numero: "12.257", titulo: "Código de Aguas — protección del recurso hídrico", tema: "ambiente", estado: "derogada", fecha_sancion: "1999", fecha_publicacion: "1999", revision: "aprobada", esNuevo: false, link: "#" },
];

// (la corrida real reemplaza esto: ver actualizarCorrida más abajo, que llama
// en vivo a la API de Digesto SRT)

const TEMA_META = {
  ambiente: { label: "Ambiente", icon: Leaf, ring: "ring-emerald-200", text: "text-emerald-700", bg: "bg-emerald-50" },
  sst: { label: "SST", icon: ShieldCheck, ring: "ring-sky-200", text: "text-sky-700", bg: "bg-sky-50" },
};

const ESTADO_META = {
  vigente: { label: "Vigente", dot: "bg-emerald-500" },
  derogada: { label: "Derogada", dot: "bg-rose-400" },
  desconocido: { label: "A verificar", dot: "bg-slate-300" },
};

const REVISION_META = {
  pendiente: { label: "Pendiente", text: "text-amber-700", bg: "bg-amber-50", ring: "ring-amber-200" },
  aprobada: { label: "Aprobada", text: "text-emerald-700", bg: "bg-emerald-50", ring: "ring-emerald-200" },
  rechazada: { label: "Rechazada", text: "text-slate-500", bg: "bg-slate-100", ring: "ring-slate-200" },
};

function Pill({ children, className = "" }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${className}`}>
      {children}
    </span>
  );
}

export default function PanelCuracionNormativa() {
  const [rows, setRows] = useState(SEED);
  const [query, setQuery] = useState("");
  const [temaFilter, setTemaFilter] = useState("todos");
  const [revisionFilter, setRevisionFilter] = useState("todos");
  const [fuenteFilter, setFuenteFilter] = useState("todas");
  const [selected, setSelected] = useState(null);
  const [actualizando, setActualizando] = useState(false);
  const [ultimaCorrida, setUltimaCorrida] = useState("todavía no corrió");
  const [errorActualizacion, setErrorActualizacion] = useState(null);

  const filtered = useMemo(() => {
    return rows.filter((r) => {
      const matchQuery =
        query.trim() === "" ||
        r.titulo.toLowerCase().includes(query.toLowerCase()) ||
        r.numero.toLowerCase().includes(query.toLowerCase());
      const matchTema = temaFilter === "todos" || r.tema === temaFilter;
      const matchRevision = revisionFilter === "todos" || r.revision === revisionFilter;
      const matchFuente = fuenteFilter === "todas" || r.fuente === fuenteFilter;
      return matchQuery && matchTema && matchRevision && matchFuente;
    });
  }, [rows, query, temaFilter, revisionFilter, fuenteFilter]);

  const stats = useMemo(() => {
    const pendientes = rows.filter((r) => r.revision === "pendiente").length;
    const aprobadas = rows.filter((r) => r.revision === "aprobada").length;
    const nuevas = rows.filter((r) => r.esNuevo).length;
    const total = rows.length;
    return { pendientes, aprobadas, nuevas, total };
  }, [rows]);

  function setRevision(id, revision) {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, revision, esNuevo: false } : r)));
    setSelected((prev) => (prev && prev.id === id ? { ...prev, revision, esNuevo: false } : prev));
  }

  async function actualizarCorrida() {
    setActualizando(true);
    setErrorActualizacion(null);
    try {
      const hoy = new Date().toISOString();
      const payload = {
        NroResolucion: null,
        Cantidad: "80",
        Asunto: null,
        OrganismoEmisor: "",
        TipoNorma: "",
        BoletinOficial: null,
        FechaDesde: "2020-01-01T03:00:00.000Z",
        FechaHasta: hoy,
        NroExpediente: null,
        Voces: [],
      };
      const resp = await fetch("https://api.srt.gob.ar/v1/resoluciones/full", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error(`La API respondió con estado ${resp.status}`);
      const data = await resp.json();
      const items = Array.isArray(data)
        ? data
        : data?.Resultados || data?.Items || data?.Data || [];

      if (!Array.isArray(items) || items.length === 0) {
        throw new Error("La API respondió pero no se encontraron normas en ese rango.");
      }

      setRows((prev) => {
        const yaExistian = new Set(
          prev.filter((r) => r.fuente === "srt_digesto").map((r) => r.numero)
        );
        const nuevas = items
          .filter((it) => !yaExistian.has(it.NumeroAnio))
          .map((it) => ({
            id: `srt-${it.OID}`,
            fuente: "srt_digesto",
            provincia: it.Organismo || "Nación",
            tipo: (it.Tipo || "otro").toLowerCase(),
            numero: it.NumeroAnio || String(it.Numero || "s/n"),
            titulo: it.Asunto || `${it.Tipo || ""} ${it.NumeroAnio || ""}`.trim(),
            tema: "sst",
            estado: "desconocido",
            fecha_sancion: it.Fecha ? it.Fecha.slice(0, 10) : "",
            fecha_publicacion: "",
            revision: "pendiente",
            esNuevo: true,
            link: it.Link || "#",
          }));
        return [...nuevas, ...prev];
      });
      setUltimaCorrida("recién ahora");
    } catch (e) {
      setErrorActualizacion(e.message || "No se pudo completar la corrida.");
    } finally {
      setActualizando(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex">
      {/* Rail lateral */}
      <aside className="w-60 shrink-0 border-r border-slate-200 bg-white flex flex-col">
        <div className="h-16 flex items-center gap-2 px-5 border-b border-slate-200">
          <div className="h-7 w-7 rounded-md bg-slate-900 flex items-center justify-center">
            <Database className="h-4 w-4 text-white" />
          </div>
          <div className="leading-none">
            <div className="text-sm font-semibold tracking-tight">IDEAS Consulting</div>
            <div className="text-[11px] text-slate-400">Matriz Legal Digital</div>
          </div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1 text-sm">
          <div className="px-2 pb-2 text-[11px] font-medium uppercase tracking-wider text-slate-400">
            Curación
          </div>
          <a className="flex items-center justify-between rounded-md bg-slate-900 text-white px-3 py-2 font-medium">
            <span>Normas recolectadas</span>
            <span className="text-[11px] bg-white/15 rounded px-1.5">{stats.total}</span>
          </a>
          <div className="px-1 pt-1 space-y-1">
            {FUENTES.map((f) => (
              <div
                key={f.id}
                className="flex items-center justify-between rounded-md px-3 py-2 text-slate-600"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${f.activa ? "bg-emerald-500" : "bg-slate-300"}`} />
                  <span className="truncate text-[13px]">{f.nombre}</span>
                </div>
                <span className="text-[10px] text-slate-400 shrink-0">{f.frecuencia}</span>
              </div>
            ))}
          </div>
          <a className="flex items-center justify-between rounded-md px-3 py-2 text-slate-600 hover:bg-slate-50 text-[13px]">
            <span>Historial de corridas</span>
          </a>
          <div className="px-2 pt-4 pb-2 text-[11px] font-medium uppercase tracking-wider text-slate-400">
            Matriz publicada
          </div>
          <a className="flex items-center justify-between rounded-md px-3 py-2 text-slate-600 hover:bg-slate-50">
            <span>Vista por empresa</span>
          </a>
          <a className="flex items-center justify-between rounded-md px-3 py-2 text-slate-600 hover:bg-slate-50">
            <span>Alertas activas</span>
          </a>
        </nav>
        <div className="p-4 border-t border-slate-200 text-[11px] text-slate-400">
          Rol: <span className="font-medium text-slate-600">IDEAS_ADMIN</span>
        </div>
      </aside>

      {/* Contenido principal */}
      <main className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b border-slate-200 bg-white flex items-center justify-between px-6">
          <div>
            <h1 className="text-base font-semibold tracking-tight">Normas recolectadas</h1>
            <p className="text-xs text-slate-400">
              {FUENTES.filter((f) => f.activa).length} fuentes activas · última corrida {ultimaCorrida}
            </p>
          </div>
          <div className="flex items-center gap-3 text-xs">
            {errorActualizacion && (
              <Pill className="bg-rose-50 text-rose-700 ring-rose-200 max-w-xs">
                <AlertTriangle className="h-3 w-3 shrink-0" />
                <span className="truncate">{errorActualizacion}</span>
              </Pill>
            )}
            {stats.nuevas > 0 && (
              <Pill className="bg-violet-50 text-violet-700 ring-violet-200">
                <Sparkles className="h-3 w-3" /> {stats.nuevas} nuevas
              </Pill>
            )}
            <Pill className="bg-amber-50 text-amber-700 ring-amber-200">
              <Clock className="h-3 w-3" /> {stats.pendientes} pendientes
            </Pill>
            <Pill className="bg-emerald-50 text-emerald-700 ring-emerald-200">
              <Check className="h-3 w-3" /> {stats.aprobadas} aprobadas
            </Pill>
            <button
              onClick={actualizarCorrida}
              disabled={actualizando}
              className="flex items-center gap-1.5 rounded-md bg-slate-900 text-white text-xs font-medium px-3 py-2 hover:bg-slate-800 disabled:opacity-60"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${actualizando ? "animate-spin" : ""}`} />
              {actualizando ? "Buscando novedades..." : "Actualizar"}
            </button>
          </div>
        </header>

        {/* Filtros */}
        <div className="px-6 py-4 flex flex-wrap items-center gap-3 border-b border-slate-200 bg-white">
          <div className="relative flex-1 min-w-[220px] max-w-sm">
            <Search className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar por número o título..."
              className="w-full rounded-md border border-slate-200 bg-slate-50 pl-9 pr-3 py-2 text-sm outline-none focus:ring-2 focus:ring-slate-300 focus:bg-white"
            />
          </div>

          <div className="flex items-center gap-1 rounded-md border border-slate-200 p-1 bg-slate-50">
            {["todos", "ambiente", "sst"].map((t) => (
              <button
                key={t}
                onClick={() => setTemaFilter(t)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition ${
                  temaFilter === t ? "bg-white shadow-sm text-slate-900" : "text-slate-500 hover:text-slate-700"
                }`}
              >
                {t === "todos" ? "Todos los temas" : TEMA_META[t].label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1 rounded-md border border-slate-200 p-1 bg-slate-50">
            <button
              onClick={() => setFuenteFilter("todas")}
              className={`px-3 py-1.5 rounded text-xs font-medium transition ${
                fuenteFilter === "todas" ? "bg-white shadow-sm text-slate-900" : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Todas las fuentes
            </button>
            {FUENTES.map((f) => (
              <button
                key={f.id}
                onClick={() => setFuenteFilter(f.id)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition ${
                  fuenteFilter === f.id ? "bg-white shadow-sm text-slate-900" : "text-slate-500 hover:text-slate-700"
                }`}
              >
                {f.nombre.split(" — ")[0]}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1 rounded-md border border-slate-200 p-1 bg-slate-50">
            {["todos", "pendiente", "aprobada", "rechazada"].map((r) => (
              <button
                key={r}
                onClick={() => setRevisionFilter(r)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition capitalize ${
                  revisionFilter === r ? "bg-white shadow-sm text-slate-900" : "text-slate-500 hover:text-slate-700"
                }`}
              >
                {r === "todos" ? "Todo estado" : REVISION_META[r].label}
              </button>
            ))}
          </div>

          <button className="ml-auto flex items-center gap-1.5 text-xs font-medium text-slate-500 border border-slate-200 rounded-md px-3 py-2 hover:bg-slate-50">
            <Filter className="h-3.5 w-3.5" /> Más filtros
          </button>
        </div>

        {/* Tabla + panel de detalle */}
        <div className="flex-1 flex min-h-0">
          <div className="flex-1 overflow-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-slate-50 border-b border-slate-200 text-left text-[11px] uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-6 py-3 font-medium">Norma</th>
                  <th className="px-4 py-3 font-medium">Jurisdicción</th>
                  <th className="px-4 py-3 font-medium">Tema</th>
                  <th className="px-4 py-3 font-medium">Vigencia</th>
                  <th className="px-4 py-3 font-medium">Revisión</th>
                  <th className="px-4 py-3 font-medium text-right">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => {
                  const tema = TEMA_META[r.tema];
                  const estado = ESTADO_META[r.estado] || ESTADO_META.desconocido;
                  const revision = REVISION_META[r.revision];
                  const TemaIcon = tema.icon;
                  return (
                    <tr
                      key={r.id}
                      onClick={() => setSelected(r)}
                      className={`border-b border-slate-100 cursor-pointer transition ${
                        selected?.id === r.id ? "bg-slate-50" : "hover:bg-slate-50/60"
                      }`}
                    >
                      <td className="px-6 py-3.5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[13px] text-slate-500 shrink-0">
                            {r.tipo === "ley" ? "Ley" : r.tipo === "decreto" ? "Dec." : "Res."} {r.numero}
                          </span>
                          {r.esNuevo && (
                            <Pill className="bg-violet-50 text-violet-700 ring-violet-200 py-0.5">
                              <Sparkles className="h-2.5 w-2.5" /> Nuevo
                            </Pill>
                          )}
                        </div>
                        <div className="text-slate-700 text-[13px] mt-0.5 line-clamp-1 max-w-md">{r.titulo}</div>
                      </td>
                      <td className="px-4 py-3.5 text-slate-500 text-[13px]">{r.provincia}</td>
                      <td className="px-4 py-3.5">
                        <Pill className={`${tema.bg} ${tema.text} ${tema.ring}`}>
                          <TemaIcon className="h-3 w-3" /> {tema.label}
                        </Pill>
                      </td>
                      <td className="px-4 py-3.5">
                        <span className="inline-flex items-center gap-1.5 text-[13px] text-slate-600">
                          <span className={`h-1.5 w-1.5 rounded-full ${estado.dot}`} /> {estado.label}
                        </span>
                      </td>
                      <td className="px-4 py-3.5">
                        <Pill className={`${revision.bg} ${revision.text} ${revision.ring}`}>{revision.label}</Pill>
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={(e) => { e.stopPropagation(); setRevision(r.id, "aprobada"); }}
                            className="h-7 w-7 flex items-center justify-center rounded-md border border-slate-200 text-emerald-600 hover:bg-emerald-50"
                            title="Aprobar"
                          >
                            <Check className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); setRevision(r.id, "rechazada"); }}
                            className="h-7 w-7 flex items-center justify-center rounded-md border border-slate-200 text-slate-400 hover:bg-slate-100"
                            title="Rechazar"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-6 py-16 text-center text-slate-400 text-sm">
                      No hay normas que coincidan con estos filtros.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Panel de detalle */}
          <aside className="w-96 shrink-0 border-l border-slate-200 bg-white overflow-y-auto">
            {selected ? (
              <div className="p-6">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-sm text-slate-500">
                    {selected.tipo === "ley" ? "Ley" : selected.tipo === "decreto" ? "Decreto" : "Resolución"} {selected.numero}
                  </span>
                  <Pill className={`${REVISION_META[selected.revision].bg} ${REVISION_META[selected.revision].text} ${REVISION_META[selected.revision].ring}`}>
                    {REVISION_META[selected.revision].label}
                  </Pill>
                </div>
                <h2 className="text-lg font-semibold leading-snug mb-4">{selected.titulo}</h2>

                <dl className="space-y-3 text-sm mb-6">
                  <div className="flex justify-between border-b border-slate-100 pb-2">
                    <dt className="text-slate-400">Jurisdicción</dt>
                    <dd className="font-medium">{selected.provincia}</dd>
                  </div>
                  <div className="flex justify-between border-b border-slate-100 pb-2">
                    <dt className="text-slate-400">Tema</dt>
                    <dd className="font-medium">{TEMA_META[selected.tema].label}</dd>
                  </div>
                  <div className="flex justify-between border-b border-slate-100 pb-2">
                    <dt className="text-slate-400">Fecha de sanción</dt>
                    <dd className="font-medium">{selected.fecha_sancion}</dd>
                  </div>
                  <div className="flex justify-between border-b border-slate-100 pb-2">
                    <dt className="text-slate-400">Publicación</dt>
                    <dd className="font-medium">{selected.fecha_publicacion}</dd>
                  </div>
                  <div className="flex justify-between border-b border-slate-100 pb-2">
                    <dt className="text-slate-400">Estado</dt>
                    <dd className="font-medium">{(ESTADO_META[selected.estado] || ESTADO_META.desconocido).label}</dd>
                  </div>
                  <div className="flex justify-between border-b border-slate-100 pb-2">
                    <dt className="text-slate-400">Fuente</dt>
                    <dd className="font-medium">{FUENTES.find((f) => f.id === selected.fuente)?.nombre}</dd>
                  </div>
                </dl>

                {selected.tema === "" && (
                  <div className="flex items-start gap-2 rounded-md bg-amber-50 ring-1 ring-amber-200 p-3 text-xs text-amber-700 mb-4">
                    <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                    Requiere clasificación manual de tema.
                  </div>
                )}

                <a
                  href={selected.link}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900 mb-6"
                >
                  <ExternalLink className="h-3.5 w-3.5" /> Ver texto fuente
                </a>

                <div className="flex gap-2">
                  <button
                    onClick={() => setRevision(selected.id, "aprobada")}
                    className="flex-1 flex items-center justify-center gap-1.5 rounded-md bg-slate-900 text-white text-sm font-medium py-2.5 hover:bg-slate-800"
                  >
                    <Check className="h-4 w-4" /> Aprobar y publicar
                  </button>
                  <button
                    onClick={() => setRevision(selected.id, "rechazada")}
                    className="rounded-md border border-slate-200 text-slate-500 text-sm font-medium px-4 hover:bg-slate-50"
                  >
                    Rechazar
                  </button>
                </div>
                <p className="text-[11px] text-slate-400 mt-3 leading-relaxed">
                  Al aprobar, la norma pasa a <span className="font-mono">legal_requirements</span> y queda visible
                  para las empresas cuya matriz corresponda a esta jurisdicción y rubro.
                </p>
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center px-8 text-slate-400">
                <FileText className="h-8 w-8 mb-3" />
                <p className="text-sm">Seleccioná una norma de la lista para ver su detalle y aprobarla.</p>
              </div>
            )}
          </aside>
        </div>
      </main>
    </div>
  );
}
