/* ============================================================
   IDEUS — Funciones de UI reutilizables
   Extraídas del demo interactivo (2026-09).
   Son JS puro sin dependencias — se pueden invocar desde NiceGUI vía
   ui.run_javascript(...) o incrustar con ui.add_body_html('<script>...</script>').
   ============================================================ */

/**
 * Indicador deslizante del menú lateral (o de tabs).
 * Mueve/redimensiona un elemento "pastilla" para que coincida
 * exactamente con el ítem activo, sea layout vertical (sidebar
 * desktop) u horizontal (sidebar mobile / tabs).
 *
 * @param {HTMLElement} indicatorEl - el div de la pastilla (position:absolute)
 * @param {HTMLElement} containerEl - el contenedor relativo (sidebar o .tabs)
 * @param {HTMLElement} activeItemEl - el ítem actualmente activo
 */
function ideusMoveIndicator(indicatorEl, containerEl, activeItemEl){
  if(!activeItemEl){ indicatorEl.style.opacity = 0; return; }
  const cRect = containerEl.getBoundingClientRect();
  const iRect = activeItemEl.getBoundingClientRect();
  indicatorEl.style.width = iRect.width + 'px';
  indicatorEl.style.height = iRect.height + 'px';
  indicatorEl.style.transform = `translate(${iRect.left - cRect.left}px, ${iRect.top - cRect.top}px)`;
  indicatorEl.style.opacity = 1;
}

/**
 * Gauge circular (anillo de progreso) para un KPI de tipo "cumplimiento %".
 * Devuelve un string SVG listo para insertar (innerHTML / ui.html).
 *
 * @param {number} pct - valor 0-100
 * @param {string} color - color CSS (puede ser var(--teal), un hex, etc.)
 * @returns {string} SVG
 */
function ideusGaugeSVG(pct, color){
  const r = 24, c = 2 * Math.PI * r;
  const offset = c * (1 - Math.min(pct, 100) / 100);
  return `<svg width="58" height="58" viewBox="0 0 58 58">
    <circle cx="29" cy="29" r="${r}" fill="none" stroke="var(--border)" stroke-width="6"/>
    <circle cx="29" cy="29" r="${r}" fill="none" stroke="${color}" stroke-width="6" stroke-linecap="round" stroke-dasharray="${c.toFixed(1)}" stroke-dashoffset="${offset.toFixed(1)}" transform="rotate(-90 29 29)"/>
    <text x="29" y="34" text-anchor="middle" font-size="12" font-weight="700" fill="#1E293B" font-family="Poppins,sans-serif">${pct}%</text>
  </svg>`;
}

/**
 * Mini gráfico de barras (sparkline de tendencia, últimos N períodos).
 * La última barra se resalta en color; el resto queda gris.
 *
 * @param {number[]} trend - valores históricos, en orden cronológico
 * @param {string} color - color de la última barra
 * @returns {string} SVG
 */
function ideusBarsSVG(trend, color){
  const max = Math.max(...trend, 1);
  const w = 78, h = 32, n = trend.length, bw = (w / n) - 3;
  const bars = trend.map((v, i) => {
    const bh = Math.max((v / max) * h, 2);
    const x = i * (w / n) + 1.5;
    const y = h - bh;
    const isLast = i === n - 1;
    return `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${bh.toFixed(1)}" rx="1.5" fill="${isLast ? color : 'var(--border)'}"/>`;
  }).join('');
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${bars}</svg>`;
}

/**
 * Barra de "racha" (progreso hacia un récord/objetivo), p. ej. "días sin LTA".
 * @param {number} current
 * @param {number} target
 * @param {string} color
 * @returns {string} HTML (no SVG, es un div con % de ancho)
 */
function ideusStreakHTML(current, target, color){
  const pct = Math.min(100, (current / target) * 100);
  return `<div class="ideus-streak-track"><div class="ideus-streak-fill" style="width:${pct}%;background:${color}"></div></div><div class="ideus-streak-note">récord: ${target} días</div>`;
}

/**
 * Arma el bloque de gráfico correcto según el tipo de KPI.
 * @param {{chart:'gauge'|'bars'|'streak', pct?:number, trend?:number[], current?:number, target?:number}} k
 * @param {string} color
 * @returns {string} HTML/SVG
 */
function ideusKpiChartHTML(k, color){
  if(k.chart === 'gauge') return `<div class="ideus-kpi-chart">${ideusGaugeSVG(k.pct, color)}</div>`;
  if(k.chart === 'streak') return `<div class="ideus-kpi-chart">${ideusStreakHTML(k.current, k.target, color)}</div>`;
  return `<div class="ideus-kpi-chart">${ideusBarsSVG(k.trend, color)}</div>`;
}

/* Paleta sugerida por categoría — usar la misma lógica de color que ya
   usa el panel de KPIs actual (Ambiente/Producción teal, SST azul,
   Calidad verde, Riesgos/Documentos naranja) para que el color siga
   significando lo mismo en toda la plataforma. */
const IDEUS_CATEGORY_COLOR = {
  'Panel general': 'var(--teal)', 'Ambiente': 'var(--teal)', 'SST': 'var(--blue)',
  'Calidad': 'var(--green)', 'Riesgos': 'var(--orange)', 'Producción': 'var(--blue)',
  'Logística': 'var(--green)', 'Documentos': 'var(--orange)',
};

/* Exportar para uso desde NiceGUI (ui.run_javascript puede llamar estas
   funciones por nombre una vez que este script está cargado en la página). */
