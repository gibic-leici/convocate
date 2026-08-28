const CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTIEHTQiDz-03BbqdigDPQ_ypQS3ybXdD3FKgcXLXVZjcBF4ClMplm-PeReVrIMblvByNhGG2Vex9hA/pub?output=csv';

let convocatoriasData = [];

document.addEventListener('DOMContentLoaded', () => {
    cargarDatos();

    // Escuchar cambios en los filtros para re-dibujar
    document.getElementById('filtro-institucion').addEventListener('change', renderizarTarjetas);
    document.getElementById('filtro-categoria').addEventListener('change', renderizarTarjetas);
    document.getElementById('filtro-estado').addEventListener('change', renderizarTarjetas);
});

function cargarDatos() {
    Papa.parse(CSV_URL, {
        download: true,
        header: true,
        skipEmptyLines: true,
        complete: function (results) {
            // Guardamos solo las filas que tengan al menos una Institución o Nombre
            convocatoriasData = results.data.filter(row => row.INSTITUCION || row.NOMBRE);
            poblarFiltros();
            renderizarTarjetas();
            document.getElementById('contenedor-convocatorias').setAttribute('aria-busy', 'false');
        },
        error: function (error) {
            console.error("Error al cargar el CSV:", error);
            document.getElementById('contenedor-convocatorias').innerHTML = '<p>Error al cargar los datos. Verifique su conexión o el enlace de la planilla.</p>';
            document.getElementById('contenedor-convocatorias').setAttribute('aria-busy', 'false');
        }
    });
}

function esNoAplica(valor) {
    if (!valor || typeof valor !== 'string') return false;
    const normalizado = valor.toLowerCase().trim().replace(/[\s\-_/.]/g, '');
    return normalizado === 'noaplica' || normalizado === 'na' || normalizado === 'noaplicable';
}

function esDiscontinuada(valor) {
    if (!valor || typeof valor !== 'string') return false;
    const normalizado = valor.toLowerCase().trim().replace(/[\s\-_/.]/g, '');
    return normalizado.includes('discontinua');
}

function formatearFechaColumna(fechaRaw) {
    if (esNoAplica(fechaRaw) || esDiscontinuada(fechaRaw)) return '—';
    if (!fechaRaw || fechaRaw.trim() === '-' || fechaRaw.trim() === '') return '?';
    return fechaRaw;
}

function parseFecha(fechaStr) {
    if (!fechaStr || fechaStr.trim() === '-' || fechaStr.trim() === '' || esNoAplica(fechaStr) || esDiscontinuada(fechaStr)) return null;
    const partes = fechaStr.split('/');
    if (partes.length !== 3) return null; // Formato esperado DD/MM/YYYY
    return new Date(partes[2], partes[1] - 1, partes[0]);
}

function calcularEstado(item, hoy) {
    if (item.NOMBRE && item.NOMBRE.toLowerCase().includes('sin convocatoria')) {
        return {
            tipo: 'No hay convocatoria',
            texto: 'No hay convocatoria',
            clase: 'estado-gris'
        };
    }

    if (esDiscontinuada(item.FECHA_APERTURA) || esDiscontinuada(item.FECHA_CIERRE)) {
        return {
            tipo: 'Discontinuada',
            texto: 'Discontinuada',
            clase: 'estado-gris-oscuro'
        };
    }

    if (esNoAplica(item.FECHA_APERTURA) || esNoAplica(item.FECHA_CIERRE)) {
        return {
            tipo: 'Informativo',
            texto: 'Informativo',
            clase: 'estado-azul'
        };
    }

    const fechaApertura = parseFecha(item.FECHA_APERTURA);
    const fechaCierre = parseFecha(item.FECHA_CIERRE);

    if (!fechaCierre || !fechaApertura) {
        return {
            tipo: 'Falta información',
            texto: 'Falta información',
            clase: 'estado-naranja'
        };
    }

    if (hoy < fechaApertura) {
        return {
            tipo: 'Próxima a abrir',
            texto: 'Próxima a abrir',
            clase: 'estado-violeta'
        };
    }

    if (hoy > fechaCierre) {
        return {
            tipo: 'Vencida',
            texto: 'Vencida',
            clase: 'estado-gris'
        };
    }

    const diffTiempo = Math.ceil((fechaCierre - hoy) / (1000 * 60 * 60 * 24));
    return {
        tipo: 'Abierta',
        texto: `Abierta (cierra en ${diffTiempo} días)`,
        clase: 'estado-verde'
    };
}

function poblarFiltros() {
    const instituciones = new Set();
    const categorias = new Set();
    const estados = new Set();
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);

    // Recorremos los datos para encontrar todas las opciones únicas
    convocatoriasData.forEach(item => {
        if (item.INSTITUCION && item.INSTITUCION !== '-') instituciones.add(item.INSTITUCION.trim());
        if (item.CATEGORIA && item.CATEGORIA !== '-') categorias.add(item.CATEGORIA.trim());
        const estadoInfo = calcularEstado(item, hoy);
        if (estadoInfo && estadoInfo.tipo) estados.add(estadoInfo.tipo);
    });

    const selectInst = document.getElementById('filtro-institucion');
    // Ordenamos alfabéticamente
    Array.from(instituciones).sort().forEach(inst => {
        const option = document.createElement('option');
        option.value = inst;
        option.textContent = inst;
        selectInst.appendChild(option);
    });

    const selectCat = document.getElementById('filtro-categoria');
    Array.from(categorias).sort().forEach(cat => {
        const option = document.createElement('option');
        option.value = cat;
        option.textContent = cat;
        selectCat.appendChild(option);
    });

    const selectEstado = document.getElementById('filtro-estado');
    const ordenPreferido = ['Abierta', 'Próxima a abrir', 'Informativo', 'Falta información', 'Vencida', 'No hay convocatoria', 'Discontinuada'];
    const estadosOrdenados = Array.from(estados).sort((a, b) => {
        const idxA = ordenPreferido.indexOf(a);
        const idxB = ordenPreferido.indexOf(b);
        if (idxA !== -1 && idxB !== -1) return idxA - idxB;
        if (idxA !== -1) return -1;
        if (idxB !== -1) return 1;
        return a.localeCompare(b);
    });

    estadosOrdenados.forEach(est => {
        const option = document.createElement('option');
        option.value = est;
        option.textContent = est;
        selectEstado.appendChild(option);
    });
}

function renderizarTarjetas() {
    const contenedor = document.getElementById('contenedor-convocatorias');
    const filtroInst = document.getElementById('filtro-institucion').value;
    const filtroCat = document.getElementById('filtro-categoria').value;
    const filtroEstado = document.getElementById('filtro-estado').value;

    contenedor.innerHTML = '';
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0); // Normalizar a medianoche para cálculo justo

    const filtrados = convocatoriasData.filter(item => {
        const inst = item.INSTITUCION ? item.INSTITUCION.trim() : '';
        const cat = item.CATEGORIA ? item.CATEGORIA.trim() : '';
        const estadoInfo = calcularEstado(item, hoy);

        const pasaInst = filtroInst === '' || inst === filtroInst;
        const pasaCat = filtroCat === '' || cat === filtroCat;
        const pasaEstado = filtroEstado === '' || estadoInfo.tipo === filtroEstado;
        return pasaInst && pasaCat && pasaEstado;
    });

    if (filtrados.length === 0) {
        contenedor.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 20px; color: #78909c;">No se encontraron convocatorias que coincidan con los filtros.</td></tr>';
        return;
    }

    filtrados.forEach(item => {
        const fechaAperturaStr = formatearFechaColumna(item.FECHA_APERTURA);
        const fechaCierreStr = formatearFechaColumna(item.FECHA_CIERRE);

        const estadoInfo = calcularEstado(item, hoy);

        const linkHTML = item.LINK && item.LINK !== '-' && item.LINK !== ''
            ? `<a href="${item.LINK}" target="_blank">Acceder</a>`
            : '-';

        const institucion = item.INSTITUCION || 'N/A';
        const categoria = item.CATEGORIA || 'N/A';
        const nombre = item.NOMBRE || 'Sin nombre';

        const tr = document.createElement('tr');
        
        tr.innerHTML = `
            <td>${institucion}</td>
            <td>${categoria}</td>
            <td><strong>${nombre}</strong></td>
            <td><span class="badge ${estadoInfo.clase}">${estadoInfo.texto}</span></td>
            <td>${fechaAperturaStr}</td>
            <td>${fechaCierreStr}</td>
            <td>${linkHTML}</td>
        `;
        
        contenedor.appendChild(tr);
    });
}