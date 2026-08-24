import csv
import json
import hashlib
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import urllib.parse

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


def obtener_clave_fuente(fuente):
    """Genera una clave única compuesta para cada fuente."""
    return f"{fuente['institucion']}_{fuente['nombre']}_{fuente['link']}"


def analizar_convocatoria_con_ia(texto, fuente):
    """
    Analiza el texto recuperado utilizando la API de Google Gemini,
    buscando específicamente la convocatoria definida en fuente['nombre'].
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("    [IA Error] GEMINI_API_KEY no está configurada o está vacía en las variables de entorno.")
        return {"convocatoria": None, "fecha_cierre": None, "link_especifico": None}

    fragmento = texto[:8000]

    prompt = (
        f"Analiza el siguiente texto extraído de la página web de {fuente['institucion']} ({fuente['link']}).\n"
        f"Estamos buscando información sobre la convocatoria específica: **{fuente['nombre']}** (categoría: {fuente['categoria']}).\n\n"
        "Instrucciones:\n"
        f"1. Identifica si hay una convocatoria activa o publicación reciente relacionada con '{fuente['nombre']}'.\n"
        "2. Si en el texto hay un enlace/URL específico hacia la noticia o convocatoria detallada de esa oportunidad, inclúyelo.\n"
        "3. Responde ÚNICAMENTE con un objeto JSON válido con las siguientes claves exactas:\n"
        '  "convocatoria": Nombre o título corto oficial de la convocatoria encontrada (string o null si no se encuentra nada sobre esta convocatoria)\n'
        '  "fecha_cierre": Fecha de cierre o límite en formato legible como "DD/MM/YYYY" o "DD de Mes YYYY" (string o null si no especifica)\n'
        '  "link_especifico": URL absoluta o relativa directa a la noticia/convocatoria si existe en el texto (string o null si no hay link directo)\n\n'
        f"Texto de la página:\n{fragmento}"
    )

    modelos = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash-latest", "gemini-2.0-flash-latest"]

    for modelo in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
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
                raw_text = datos_resp["candidates"][0]["content"]["parts"][0]["text"].strip()

                # Limpiar bloques markdown ```json ... ``` si la IA los incluye
                raw_json = raw_text
                if "```" in raw_json:
                    partes = raw_json.split("```")
                    for p in partes:
                        limpio = p.strip()
                        if limpio.startswith("json"):
                            limpio = limpio[4:].strip()
                        if limpio.startswith("{") and limpio.endswith("}"):
                            raw_json = limpio
                            break

                analisis = json.loads(raw_json)
                link_esp = analisis.get("link_especifico")
                if link_esp and not link_esp.startswith("http"):
                    link_esp = urllib.parse.urljoin(fuente["link"], link_esp)
                return {
                    "convocatoria": analisis.get("convocatoria"),
                    "fecha_cierre": analisis.get("fecha_cierre"),
                    "link_especifico": link_esp
                }
            else:
                print(f"    [IA Warning] Modelo {modelo} devolvió HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"    [IA Warning] Fallo al consultar Gemini con modelo {modelo}: {e}")

    print("    [IA Error] Ningún modelo de Gemini pudo procesar la solicitud.")
    return {"convocatoria": None, "fecha_cierre": None, "link_especifico": None}


def cargar_resultados_previos():
    """Carga los resultados anteriores si existen, usando clave compuesta."""
    if not RESULTADOS_FILE.exists():
        return {}

    try:
        with open(RESULTADOS_FILE, "r", encoding="utf-8") as f:
            datos = json.load(f)

        previos = {}
        for resultado in datos:
            clave = obtener_clave_fuente(resultado)
            previos[clave] = resultado
            # Mantener compatibilidad por link
            if resultado.get("link") not in previos:
                previos[resultado.get("link")] = resultado

        return previos

    except (json.JSONDecodeError, KeyError, TypeError):
        print("Advertencia: no se pudieron leer los resultados anteriores.")
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
    clave = obtener_clave_fuente(fuente)
    anterior = resultados_previos.get(clave) or resultados_previos.get(url)
    anio_actual = datetime.now(timezone.utc).year

    # ----------------------------------------------------
    # Caché Anual: Si ya se encontró la convocatoria para el año actual
    # ----------------------------------------------------
    if anterior and anterior.get("convocatoria_ia") and anterior.get("anio_procesado") == anio_actual:
        print(f"    [CACHE ANUAL] Convocatoria '{anterior.get('convocatoria_ia')}' ya registrada para {anio_actual}. Se reutilizan los datos.")
        resultado = {
            **anterior,
            "ultimo_acceso": datetime.now(timezone.utc).isoformat(),
            "informacion_nueva": False,
        }
        return resultado

    resultado = {
        **fuente,
        "ultimo_acceso": datetime.now(timezone.utc).isoformat(),

        "funciono": False,
        "codigo_http": None,
        "tiempo_respuesta_s": None,

        "contenido_extraido": False,
        "cantidad_caracteres": 0,

        "hash": None,
        "informacion_nueva": False,

        "archivo_texto": None,
        "link_especifico": None,
        "anio_procesado": None,
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

        resultado["tiempo_respuesta_s"] = round(tiempo, 3)
        resultado["codigo_http"] = respuesta.status_code

        respuesta.raise_for_status()

        texto = extraer_texto(respuesta.text)

        resultado["funciono"] = True
        resultado["contenido_extraido"] = len(texto) > 0
        resultado["cantidad_caracteres"] = len(texto)
        resultado["hash"] = calcular_hash(texto)

        # ----------------------------------------------------
        # Comparar con la ejecución anterior
        # ----------------------------------------------------
        if anterior is None:
            resultado["informacion_nueva"] = True
            hubo_cambio = True
        elif anterior.get("hash") != resultado["hash"]:
            resultado["informacion_nueva"] = True
            hubo_cambio = True
        else:
            resultado["informacion_nueva"] = False
            hubo_cambio = False

        # ----------------------------------------------------
        # Guardar texto
        # ----------------------------------------------------
        if resultado["contenido_extraido"] and hubo_cambio:
            resultado["archivo_texto"] = guardar_texto(fuente, texto)
        elif anterior is not None:
            resultado["archivo_texto"] = anterior.get("archivo_texto")

        # ----------------------------------------------------
        # Análisis con IA (gemini)
        # ----------------------------------------------------
        necesita_ia = hubo_cambio or (anterior is not None and not anterior.get("convocatoria_ia"))

        if resultado["contenido_extraido"] and necesita_ia:
            print(f"    Analizando convocatoria '{fuente['nombre']}' con IA (Gemini)...")
            datos_ia = analizar_convocatoria_con_ia(texto, fuente)

            # Si Gemini sugiere una URL más específica a la noticia y no se obtuvo fecha exacta
            link_esp = datos_ia.get("link_especifico")
            if link_esp and link_esp != url:
                print(f"    [Navegación] Siguiendo enlace a noticia específica: {link_esp}")
                try:
                    resp_sub = requests.get(link_esp, headers=HEADERS, timeout=TIMEOUT)
                    if resp_sub.status_code == 200:
                        texto_sub = extraer_texto(resp_sub.text)
                        if len(texto_sub) > 0:
                            datos_ia_sub = analizar_convocatoria_con_ia(texto_sub, {**fuente, "link": link_esp})
                            if datos_ia_sub.get("convocatoria"):
                                datos_ia["convocatoria"] = datos_ia_sub.get("convocatoria")
                            if datos_ia_sub.get("fecha_cierre"):
                                datos_ia["fecha_cierre"] = datos_ia_sub.get("fecha_cierre")
                except Exception as sub_e:
                    print(f"    [Advertencia] No se pudo acceder a la sub-página: {sub_e}")

            resultado["convocatoria_ia"] = datos_ia.get("convocatoria")
            resultado["fecha_cierre_ia"] = datos_ia.get("fecha_cierre")
            resultado["link_especifico"] = datos_ia.get("link_especifico")

            if resultado["convocatoria_ia"]:
                resultado["anio_procesado"] = anio_actual

        elif anterior is not None:
            resultado["convocatoria_ia"] = anterior.get("convocatoria_ia")
            resultado["fecha_cierre_ia"] = anterior.get("fecha_cierre_ia")
            resultado["link_especifico"] = anterior.get("link_especifico")
            resultado["anio_procesado"] = anterior.get("anio_procesado")
        else:
            resultado["convocatoria_ia"] = None
            resultado["fecha_cierre_ia"] = None
            resultado["link_especifico"] = None
            resultado["anio_procesado"] = None

    except requests.exceptions.RequestException as e:

        tiempo = time.perf_counter() - inicio

        resultado["tiempo_respuesta_s"] = round(tiempo, 3)
        resultado["error"] = str(e)

    except Exception as e:

        resultado["error"] = f"Error inesperado: {e}"

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