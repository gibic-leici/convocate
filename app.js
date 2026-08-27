const CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTIEHTQiDz-03BbqdigDPQ_ypQS3ybXdD3FKgcXLXVZjcBF4ClMplm-PeReVrIMblvByNhGG2Vex9hA/pub?output=csv';

let convocatoriasData = [];

document.addEventListener('DOMContentLoaded', () => {
    cargarDatos();

    // Escuchar cambios en los filtros para re-dibujar
    document.getElementById('filtro-institucion').addEventListener('change', renderizarTarjetas);
    document.getElementById('filtro-categoria').addEventListener('change', renderizarTarjetas);
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

function poblarFiltros() {
    const instituciones = new Set();
    const categorias = new Set();

    // Recorremos los datos para encontrar todas las opciones únicas
    convocatoriasData.forEach(item => {
        if (item.INSTITUCION && item.INSTITUCION !== '-') instituciones.add(item.INSTITUCION.trim());
        if (item.CATEGORIA && item.CATEGORIA !== '-') categorias.add(item.CATEGORIA.trim());
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
}

function parseFecha(fechaStr) {
    if (!fechaStr || fechaStr.trim() === '-' || fechaStr.trim() === '') return null;
    const partes = fechaStr.split('/');
    if (partes.length !== 3) return null; // Formato esperado DD/MM/YYYY
    return new Date(partes[2], partes[1] - 1, partes[0]);
}

function renderizarTarjetas() {
    const contenedor = document.getElementById('contenedor-convocatorias');
    const filtroInst = document.getElementById('filtro-institucion').value;
    const filtroCat = document.getElementById('filtro-categoria').value;

    contenedor.innerHTML = '';
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0); // Normalizar a medianoche para cálculo justo

    const filtrados = convocatoriasData.filter(item => {
        const inst = item.INSTITUCION ? item.INSTITUCION.trim() : '';
        const cat = item.CATEGORIA ? item.CATEGORIA.trim() : '';

        const pasaInst = filtroInst === '' || inst === filtroInst;
        const pasaCat = filtroCat === '' || cat === filtroCat;
        return pasaInst && pasaCat;
    });

    if (filtrados.length === 0) {
        contenedor.innerHTML = '<p>No se encontraron convocatorias que coincidan con los filtros.</p>';
        return;
    }

    filtrados.forEach(item => {
        const fechaAperturaStr = item.FECHA_APERTURA && item.FECHA_APERTURA !== '-' ? item.FECHA_APERTURA : '?';
        const fechaCierreStr = item.FECHA_CIERRE && item.FECHA_CIERRE !== '-' ? item.FECHA_CIERRE : '?';

        const fechaApertura = parseFecha(item.FECHA_APERTURA);
        const fechaCierre = parseFecha(item.FECHA_CIERRE);

        let estado = '';
        let claseEstado = ''; 

        // Lógica de estado explícito
        if (item.NOMBRE && item.NOMBRE.toLowerCase().includes('sin convocatoria')) {
            estado = 'No hay convocatoria';
            claseEstado = 'estado-gris';
        } else if (!fechaCierre || !fechaApertura) {
            estado = 'Falta información';
            claseEstado = 'estado-naranja';
        } else {
            if (hoy < fechaApertura) {
                estado = 'Próxima a abrir';
                claseEstado = 'estado-gris';
            } else if (hoy > fechaCierre) {
                estado = 'Vencida';
                claseEstado = 'estado-gris';
            } else {
                const diffTiempo = Math.ceil((fechaCierre - hoy) / (1000 * 60 * 60 * 24));
                estado = `Abierta (cierra en ${diffTiempo} días)`;
                claseEstado = 'estado-verde';
            }
        }
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
            <td><span class="badge ${claseEstado}">${estado}</span></td>
            <td>${fechaAperturaStr}</td>
            <td>${fechaCierreStr}</td>
            <td>${linkHTML}</td>
        `;
        
        contenedor.appendChild(tr);
    });
}