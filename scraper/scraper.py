import csv
import json
import hashlib
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ============================================================
# Configuración
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

FUENTES_FILE = BASE_DIR / "data" / "fuentes.csv"
RESULTADOS_FILE = BASE_DIR / "data" / "resultados.json"
TEXTOS_DIR = BASE_DIR / "data" / "textos"

TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; "
        "LaboratorioConvocatorias/1.0)"
    )
}


# ============================================================
# Funciones auxiliares
# ============================================================

def leer_fuentes():
    """Lee las fuentes desde el archivo CSV."""

    with open(
        FUENTES_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f, delimiter=";")

        fuentes = []

        for fila in reader:
            fuentes.append({
                "institucion": fila["INSTITUCION"].strip(),
                "categoria": fila["CATEGORIA"].strip(),
                "nombre": fila["NOMBRE"].strip(),
                "link": fila["LINK"].strip(),
            })

    return fuentes


def crear_nombre_archivo(fuente):
    """
    Genera un nombre de archivo seguro a partir
    de institución y nombre de la fuente.
    """

    texto = (
        f"{fuente['institucion']}_"
        f"{fuente['nombre']}"
    )

    caracteres_validos = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        "_-"
    )

    nombre = "".join(
        c if c in caracteres_validos else "_"
        for c in texto
    )

    return nombre.lower() + ".txt"


def extraer_texto(html):
    """Extrae texto legible eliminando HTML innecesario."""

    soup = BeautifulSoup(html, "html.parser")

    for elemento in soup([
        "script",
        "style",
        "noscript",
        "svg"
    ]):
        elemento.decompose()

    texto = soup.get_text(
        separator=" ",
        strip=True
    )

    # Normalizar espacios
    texto = " ".join(texto.split())

    return texto


def calcular_hash(texto):
    """Calcula el SHA-256 del contenido."""

    return hashlib.sha256(
        texto.encode("utf-8")
    ).hexdigest()


def analizar_convocatoria_con_ia(texto):
    """
    Analiza el texto recuperado de la web utilizando la API de Google Gemini.
    Devuelve un diccionario con 'convocatoria' y 'fecha_cierre'.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("    [IA] GEMINI_API_KEY no configurada en el entorno.")
        return {"convocatoria": None, "fecha_cierre": None}

    fragmento = texto[:6000]

    prompt = (
        "Analiza el siguiente texto extraído de una página web universitaria/científica de convocatorias o becas.\n"
        "Identifica si hay una convocatoria activa o fecha importante y responde ÚNICAMENTE con un objeto JSON válido "
        "con las siguientes claves exactas:\n"
        '  "convocatoria": Nombre o título corto de la convocatoria activa (string o null si no se identifica ninguna)\n'
        '  "fecha_cierre": Fecha de cierre o límite en formato legible como "DD/MM/YYYY" o "DD de Mes YYYY" (string o null si no especifica)\n\n'
        f"Texto de la página:\n{fragmento}"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            datos_resp = resp.json()
            raw_json = datos_resp["candidates"][0]["content"]["parts"][0]["text"]
            analisis = json.loads(raw_json)
            return {
                "convocatoria": analisis.get("convocatoria"),
                "fecha_cierre": analisis.get("fecha_cierre")
            }
        else:
            print(f"    [IA Error] API devolvió HTTP {resp.status_code}")
            return {"convocatoria": None, "fecha_cierre": None}
    except Exception as e:
        print(f"    [IA Error] Fallo al consultar Gemini: {e}")
        return {"convocatoria": None, "fecha_cierre": None}


def cargar_resultados_previos():
    """Carga los resultados anteriores si existen."""

    if not RESULTADOS_FILE.exists():
        return {}

    try:

        with open(
            RESULTADOS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            datos = json.load(f)

        return {
            resultado["link"]: resultado
            for resultado in datos
        }

    except (
        json.JSONDecodeError,
        KeyError,
        TypeError
    ):

        print(
            "Advertencia: no se pudieron leer "
            "los resultados anteriores."
        )

        return {}


def guardar_texto(fuente, texto):
    """
    Guarda el texto limpio de la fuente.
    Devuelve la ruta relativa al archivo.
    """

    TEXTOS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    nombre_archivo = crear_nombre_archivo(fuente)

    ruta = TEXTOS_DIR / nombre_archivo

    with open(
        ruta,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(texto)

    # Ruta relativa para guardar en resultados.json
    return str(
        ruta.relative_to(BASE_DIR)
    ).replace("\\", "/")


def comprobar_fuente(fuente, resultados_previos):
    """Visita una fuente y genera su resultado."""

    url = fuente["link"]

    resultado = {
        **fuente,
        "ultimo_acceso": datetime.now(
            timezone.utc
        ).isoformat(),

        "funciono": False,
        "codigo_http": None,
        "tiempo_respuesta_s": None,

        "contenido_extraido": False,
        "cantidad_caracteres": 0,

        "hash": None,
        "informacion_nueva": False,

        "archivo_texto": None,

        "error": None,
    }

    inicio = time.perf_counter()

    try:

        respuesta = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        tiempo = time.perf_counter() - inicio

        resultado["tiempo_respuesta_s"] = round(
            tiempo,
            3
        )

        resultado["codigo_http"] = (
            respuesta.status_code
        )

        respuesta.raise_for_status()

        texto = extraer_texto(
            respuesta.text
        )

        resultado["funciono"] = True

        resultado["contenido_extraido"] = (
            len(texto) > 0
        )

        resultado["cantidad_caracteres"] = (
            len(texto)
        )

        resultado["hash"] = calcular_hash(
            texto
        )

        # ----------------------------------------------------
        # Comparar con la ejecución anterior
        # ----------------------------------------------------

        anterior = resultados_previos.get(url)

        if anterior is None:

            # Primera vez que vemos esta fuente
            resultado["informacion_nueva"] = True

            hubo_cambio = True

        elif anterior.get("hash") != resultado["hash"]:

            # El contenido cambió
            resultado["informacion_nueva"] = True

            hubo_cambio = True

        else:

            # El contenido no cambió
            resultado["informacion_nueva"] = False

            hubo_cambio = False

        # ----------------------------------------------------
        # Guardar texto e invocar IA si es nuevo o cambió
        # ----------------------------------------------------

        if (
            resultado["contenido_extraido"]
            and hubo_cambio
        ):

            resultado["archivo_texto"] = guardar_texto(
                fuente,
                texto
            )

        elif anterior is not None:

            # Conservar la referencia al archivo existente
            resultado["archivo_texto"] = (
                anterior.get("archivo_texto")
            )

        # ----------------------------------------------------
        # Análisis con IA (gemini)
        # ----------------------------------------------------

        necesita_ia = hubo_cambio or (anterior is not None and not anterior.get("convocatoria_ia"))

        if resultado["contenido_extraido"] and necesita_ia:
            print("    Analizando convocatoria con IA (Gemini)...")
            datos_ia = analizar_convocatoria_con_ia(texto)
            resultado["convocatoria_ia"] = datos_ia.get("convocatoria")
            resultado["fecha_cierre_ia"] = datos_ia.get("fecha_cierre")
        elif anterior is not None:
            resultado["convocatoria_ia"] = anterior.get("convocatoria_ia")
            resultado["fecha_cierre_ia"] = anterior.get("fecha_cierre_ia")
        else:
            resultado["convocatoria_ia"] = None
            resultado["fecha_cierre_ia"] = None

    except requests.exceptions.RequestException as e:

        tiempo = time.perf_counter() - inicio

        resultado["tiempo_respuesta_s"] = round(
            tiempo,
            3
        )

        resultado["error"] = str(e)

    except Exception as e:

        resultado["error"] = (
            f"Error inesperado: {e}"
        )

    return resultado

def guardar_resultados(resultados):
    """Guarda los resultados en JSON."""

    RESULTADOS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        RESULTADOS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            resultados,
            f,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# Programa principal
# ============================================================

def main():

    print("==========================================")
    print("   VERIFICADOR DE CONVOCATORIAS")
    print("==========================================")
    print()

    fuentes = leer_fuentes()

    print(
        f"Fuentes encontradas: {len(fuentes)}"
    )
    print()

    resultados_previos = (
        cargar_resultados_previos()
    )

    resultados = []

    for i, fuente in enumerate(
        fuentes,
        start=1
    ):

        print(
            f"[{i}/{len(fuentes)}] "
            f"{fuente['institucion']} - "
            f"{fuente['nombre']}"
        )

        print(
            f"    {fuente['link']}"
        )

        resultado = comprobar_fuente(
            fuente,
            resultados_previos
        )

        resultados.append(resultado)

        if resultado["funciono"]:

            if resultado["informacion_nueva"]:
                estado = "NUEVO/CAMBIO"
            else:
                estado = "sin cambios"

            print(
                f"    OK - HTTP "
                f"{resultado['codigo_http']} "
                f"- {resultado['cantidad_caracteres']} "
                f"caracteres "
                f"- {estado}"
            )

            if resultado["archivo_texto"]:
                print(
                    f"    Texto: "
                    f"{resultado['archivo_texto']}"
                )

            if resultado.get("convocatoria_ia"):
                print(
                    f"    IA Convocatoria: "
                    f"{resultado['convocatoria_ia']}"
                )

            if resultado.get("fecha_cierre_ia"):
                print(
                    f"    IA Fecha Cierre: "
                    f"{resultado['fecha_cierre_ia']}"
                )

        else:

            print(
                f"    ERROR - "
                f"{resultado['error']}"
            )

        print()

    guardar_resultados(resultados)

    print("------------------------------------------")
    print("Resultados guardados en:")
    print(f"  {RESULTADOS_FILE}")
    print("------------------------------------------")


if __name__ == "__main__":
    main()