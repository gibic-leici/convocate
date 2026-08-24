let resultados = [];

// ============================================================
// Cargar datos
// ============================================================

async function cargarResultados() {
    try {
        let respuesta;
        try {
            respuesta = await fetch("data/resultados.json");
            if (!respuesta.ok) throw new Error();
        } catch (e) {
            respuesta = await fetch("../data/resultados.json");
        }
        if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
        resultados = await respuesta.json();
        inicializarFiltros();
        actualizarResumen();
        mostrarResultados();
        actualizarFecha();
    } catch (error) {
        console.error(error);
        document.getElementById("tabla-resultados").innerHTML =
            `<tr><td colspan="8" class="cargando">No se pudieron cargar los resultados.</td></tr>`;
    }
}

// ============================================================
// Filtros
// ============================================================

function inicializarFiltros() {
    const instituciones = [...new Set(resultados.map(r => r.institucion))].sort();
    const categorias    = [...new Set(resultados.map(r => r.categoria))].sort();

    const selInst = document.getElementById("filtro-institucion");
    const selCat  = document.getElementById("filtro-categoria");

    instituciones.forEach(v => { const o = document.createElement("option"); o.value = o.textContent = v; selInst.appendChild(o); });
    categorias.forEach(v    => { const o = document.createElement("option"); o.value = o.textContent = v; selCat.appendChild(o); });

    selInst.addEventListener("change", mostrarResultados);
    selCat.addEventListener("change", mostrarResultados);
    document.getElementById("filtro-estado").addEventListener("change", mostrarResultados);
}

// ============================================================
// Resumen
// ============================================================

function actualizarResumen() {
    document.getElementById("total-fuentes").textContent   = resultados.length;
    document.getElementById("fuentes-ok").textContent      = resultados.filter(r => r.funciono).length;
    document.getElementById("fuentes-error").textContent   = resultados.filter(r => !r.funciono).length;
    document.getElementById("fuentes-cambio").textContent  = resultados.filter(r => r.contenido_cambio).length;
}

// ============================================================
// Mostrar tabla
// ============================================================

function mostrarResultados() {
    const institucion = document.getElementById("filtro-institucion").value;
    const categoria   = document.getElementById("filtro-categoria").value;
    const estado      = document.getElementById("filtro-estado").value;

    const filtrados = resultados.filter(r => {
        if (institucion && r.institucion !== institucion) return false;
        if (categoria   && r.categoria   !== categoria)   return false;
        if (estado === "ok"     && !r.funciono)           return false;
        if (estado === "error"  &&  r.funciono)           return false;
        if (estado === "cambio" && !r.contenido_cambio)   return false;
        return true;
    });

    const tbody = document.getElementById("tabla-resultados");
    tbody.innerHTML = "";

    filtrados.forEach(r => {
        const fila = document.createElement("tr");
        if (r.contenido_cambio) fila.classList.add("fila-alerta");

        // Acceso
        const accesoHtml = r.funciono
            ? `<span class="estado estado-ok">● OK</span><br><small>HTTP ${r.codigo_http}</small>`
            : `<span class="estado estado-error">● ERROR</span><br><small>${escaparHtml(r.error || "Sin información")}</small>`;

        // Cambio
        const cambioHtml = r.contenido_cambio
            ? `<span class="estado estado-cambio">⚠️ Verificar</span>`
            : `<span class="estado estado-sin-cambio">Sin cambios</span>`;

        // Fechas del Sheet
        const aperturaHtml = r.fecha_apertura
            ? `<span class="badge-fecha">${escaparHtml(r.fecha_apertura)}</span>`
            : `<span class="ia-pendiente">—</span>`;

        const cierreHtml = r.fecha_cierre
            ? `<span class="badge-fecha">${escaparHtml(r.fecha_cierre)}</span>`
            : `<span class="ia-pendiente">—</span>`;

        fila.innerHTML = `
            <td><strong>${escaparHtml(r.institucion)}</strong></td>
            <td>${escaparHtml(r.categoria)}</td>
            <td><a href="${escaparHtml(r.link)}" target="_blank" rel="noopener noreferrer">${escaparHtml(r.nombre)}</a></td>
            <td>${accesoHtml}</td>
            <td class="fecha">${formatearFecha(r.ultimo_acceso)}</td>
            <td>${cambioHtml}</td>
            <td>${aperturaHtml}</td>
            <td>${cierreHtml}</td>
        `;
        tbody.appendChild(fila);
    });

    if (filtrados.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="cargando">No hay fuentes que coincidan con los filtros.</td></tr>`;
    }
}

// ============================================================
// Utilidades
// ============================================================

function formatearFecha(fecha) {
    if (!fecha) return "—";
    return new Date(fecha).toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" });
}

function actualizarFecha() {
    if (resultados.length === 0) return;
    const fechas = resultados.map(r => r.ultimo_acceso).filter(Boolean).map(f => new Date(f));
    const ultima = new Date(Math.max(...fechas));
    document.getElementById("ultima-actualizacion").textContent = "Último chequeo: " + ultima.toLocaleString("es-AR");
}

function escaparHtml(texto) {
    if (texto === null || texto === undefined) return "";
    const div = document.createElement("div");
    div.textContent = String(texto);
    return div.innerHTML;
}

// ============================================================
// Inicio
// ============================================================

cargarResultados();