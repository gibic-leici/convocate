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

        if (!respuesta.ok) {
            throw new Error(`HTTP ${respuesta.status}`);
        }

        resultados = await respuesta.json();

        inicializarFiltros();

        actualizarResumen();

        mostrarResultados();

        actualizarFecha();

    } catch (error) {

        console.error(error);

        document.getElementById("tabla-resultados").innerHTML = `
            <tr>
                <td colspan="8" class="cargando">
                    No se pudieron cargar los resultados.
                </td>
            </tr>
        `;
    }
}


// ============================================================
// Filtros
// ============================================================

function inicializarFiltros() {

    const instituciones =
        [...new Set(
            resultados.map(
                r => r.institucion
            )
        )].sort();


    const categorias =
        [...new Set(
            resultados.map(
                r => r.categoria
            )
        )].sort();


    const filtroInstitucion =
        document.getElementById(
            "filtro-institucion"
        );


    const filtroCategoria =
        document.getElementById(
            "filtro-categoria"
        );


    instituciones.forEach(institucion => {

        const option =
            document.createElement("option");

        option.value = institucion;

        option.textContent = institucion;

        filtroInstitucion.appendChild(
            option
        );

    });


    categorias.forEach(categoria => {

        const option =
            document.createElement("option");

        option.value = categoria;

        option.textContent = categoria;

        filtroCategoria.appendChild(
            option
        );

    });


    filtroInstitucion.addEventListener(
        "change",
        mostrarResultados
    );


    filtroCategoria.addEventListener(
        "change",
        mostrarResultados
    );


    document.getElementById(
        "filtro-estado"
    ).addEventListener(
        "change",
        mostrarResultados
    );
}


// ============================================================
// Resumen
// ============================================================

function actualizarResumen() {

    const total =
        resultados.length;


    const ok =
        resultados.filter(
            r => r.funciono
        ).length;


    const errores =
        resultados.filter(
            r => !r.funciono
        ).length;


    const cambios =
        resultados.filter(
            r => r.informacion_nueva
        ).length;


    document.getElementById(
        "total-fuentes"
    ).textContent = total;


    document.getElementById(
        "fuentes-ok"
    ).textContent = ok;


    document.getElementById(
        "fuentes-error"
    ).textContent = errores;


    document.getElementById(
        "fuentes-cambio"
    ).textContent = cambios;
}


// ============================================================
// Mostrar tabla
// ============================================================

function mostrarResultados() {

    const institucion =
        document.getElementById(
            "filtro-institucion"
        ).value;


    const categoria =
        document.getElementById(
            "filtro-categoria"
        ).value;


    const estado =
        document.getElementById(
            "filtro-estado"
        ).value;


    const filtrados =
        resultados.filter(r => {

            if (
                institucion &&
                r.institucion !== institucion
            ) {
                return false;
            }


            if (
                categoria &&
                r.categoria !== categoria
            ) {
                return false;
            }


            if (
                estado === "ok" &&
                !r.funciono
            ) {
                return false;
            }


            if (
                estado === "error" &&
                r.funciono
            ) {
                return false;
            }


            if (
                estado === "cambio" &&
                !r.informacion_nueva
            ) {
                return false;
            }


            return true;
        });


    const tbody =
        document.getElementById(
            "tabla-resultados"
        );


    tbody.innerHTML = "";


    filtrados.forEach(r => {

        const fila =
            document.createElement("tr");


        // ----------------------------------------------------
        // Acceso
        // ----------------------------------------------------

        let accesoHtml;


        if (r.funciono) {

            accesoHtml = `
                <span
                    class="estado estado-ok"
                >
                    ● OK
                </span>
                <br>
                <small>
                    HTTP ${r.codigo_http}
                </small>
            `;

        } else {

            accesoHtml = `
                <span
                    class="estado estado-error"
                >
                    ● ERROR
                </span>
                <br>
                <small>
                    ${escaparHtml(
                r.error || "Sin información"
            )}
                </small>
            `;
        }


        // ----------------------------------------------------
        // Cambio
        // ----------------------------------------------------

        let cambioHtml;

        if (r.informacion_nueva) {

            cambioHtml = `
                <span
                    class="estado estado-cambio"
                >
                    ● NUEVO
                </span>
            `;

        } else {

            cambioHtml = `
                <span
                    class="estado estado-sin-cambio"
                >
                    Sin cambios
                </span>
            `;
        }


        // ----------------------------------------------------
        // IA
        // ----------------------------------------------------

        let convocatoriaHtml;
        if (r.convocatoria_ia) {
            convocatoriaHtml = `<strong>${escaparHtml(r.convocatoria_ia)}</strong>`;
        } else {
            convocatoriaHtml = `<span class="ia-pendiente">${r.funciono ? "Sin datos" : "—"}</span>`;
        }

        let fechaHtml;
        if (r.fecha_cierre_ia) {
            fechaHtml = `<span class="badge-fecha">${escaparHtml(r.fecha_cierre_ia)}</span>`;
        } else {
            fechaHtml = `<span class="ia-pendiente">—</span>`;
        }


        // ----------------------------------------------------
        // Fila
        // ----------------------------------------------------

        fila.innerHTML = `

            <td>
                <strong>
                    ${escaparHtml(
            r.institucion
        )}
                </strong>
            </td>


            <td>
                ${escaparHtml(
            r.categoria
        )}
            </td>


            <td>

                <a
                    href="${escaparHtml(
            r.link_especifico || r.link
        )}"
                    target="_blank"
                    rel="noopener noreferrer"
                    title="${r.link_especifico ? 'Ver noticia específica' : 'Ver portal'}"
                >
                    ${escaparHtml(
            r.nombre
        )}
                </a>

            </td>


            <td>
                ${accesoHtml}
            </td>


            <td class="fecha">
                ${formatearFecha(
            r.ultimo_acceso
        )}
            </td>


            <td>
                ${cambioHtml}
            </td>


            <td>
                ${convocatoriaHtml}
            </td>


            <td>
                ${fechaHtml}
            </td>

        `;


        tbody.appendChild(fila);

    });


    if (filtrados.length === 0) {

        tbody.innerHTML = `
            <tr>
                <td
                    colspan="8"
                    class="cargando"
                >
                    No hay fuentes que coincidan
                    con los filtros.
                </td>
            </tr>
        `;
    }
}


// ============================================================
// Fecha
// ============================================================

function formatearFecha(fecha) {

    if (!fecha) {
        return "—";
    }

    const d = new Date(fecha);

    return d.toLocaleString(
        "es-AR",
        {
            dateStyle: "short",
            timeStyle: "short"
        }
    );
}


function actualizarFecha() {

    if (resultados.length === 0) {
        return;
    }


    const fechas =
        resultados
            .map(r => r.ultimo_acceso)
            .filter(Boolean)
            .map(f => new Date(f));


    const ultima =
        new Date(
            Math.max(
                ...fechas
            )
        );


    document.getElementById(
        "ultima-actualizacion"
    ).textContent =
        "Último chequeo: " +
        ultima.toLocaleString(
            "es-AR"
        );
}


// ============================================================
// Seguridad básica
// ============================================================

function escaparHtml(texto) {

    if (texto === null ||
        texto === undefined) {

        return "";
    }


    const div =
        document.createElement("div");

    div.textContent = String(texto);

    return div.innerHTML;
}


// ============================================================
// Inicio
// ============================================================

cargarResultados();