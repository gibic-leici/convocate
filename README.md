# Convocatorias

Aplicación web para el seguimiento, consulta y visualización de convocatorias de investigación, becas y financiamiento.

Desarrollada para facilitar la búsqueda organizada de convocatorias activas, programadas y pasadas a partir de una planilla centralizada en línea.

---

## Características

- **Carga de datos en tiempo real**: Los datos se leen directamente desde un archivo CSV público publicado en Google Sheets utilizando [PapaParse](https://www.papaparse.com/).
- **Cálculo dinámico de estados**: El estado de cada convocatoria se calcula automáticamente según la fecha actual y las fechas de apertura/cierre:
  - **Abierta**: Convocatoria vigente, mostrando los días restantes para el cierre.
  - **Apertura programada**: Convocatorias cuya fecha de apertura es posterior al día de hoy.
  - **Cerrada**: Convocatorias cuya fecha de cierre ya ha transcurrido.
  - **Informativo**: Registros de carácter permanente o sin calendario estricto.
  - **Falta información**: Convocatorias con fechas pendientes de confirmación.
  - **No hay convocatoria / Discontinuada**: Registros históricos o suspendidos.
- **Filtros interactivos**:
  - Por **Institución** (organismo emisor).
  - Por **Categoría**.
  - Por **Estado**.
- **Diseño ligero y responsivo**: Construido en HTML, CSS y JavaScript estándar, optimizado para carga rápida y visualización en diferentes dispositivos.

---

## Estructura del Proyecto

```text
convocate/
├── index.html     # Estructura de la interfaz y tabla de convocatorias
├── ayuda.html     # Página de ayuda, guía de estados y origen de datos
├── style.css      # Estilos visuales, badges de estado y diseño adaptativo
├── app.js         # Lógica de descarga CSV, cálculo de estados y filtros
├── favicon.ico    # Ícono del sitio
├── LICENSE        # Licencia MIT
└── README.md      # Documentación del proyecto
```

---

## Uso y Ejecución Local

Dado que la aplicación está construida enteramente con tecnologías web estándar (HTML/CSS/JS) sin dependencias de compilación:

1. Clonar o descargar este repositorio:
   ```bash
   git clone https://github.com/gibic-leici/convocate.git
   ```
2. Abrir `index.html` en cualquier navegador web moderno, o servirlo mediante una extensión/servidor local estático (por ejemplo, Live Server en VS Code o `npx serve .`).

---

## Despliegue

La aplicación puede alojarse directamente en cualquier servicio de hosting de sitios estáticos, como **GitHub Pages**:
- Se incluye un archivo `.nojekyll` para asegurar la correcta entrega de los archivos estáticos en GitHub Pages.

---

## Licencia

Este proyecto está bajo la Licencia **MIT** - consulte el archivo [LICENSE](LICENSE) para más detalles.

Copyright (c) 2026 Instituto LEICI.
