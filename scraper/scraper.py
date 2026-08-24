import csv
import hashlib
import io
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


# ============================================================
# Configuración
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

SHEET_URL = os.environ.get(
    "SHEET_URL",
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vRKpXv5RpvVGTnzv1QMOEVwx2gEqnmCLg3Fm39oLRo52SERr4SYJEkyrINTrPwy1GLqNV-OEgdEjC1v/pub?gid=0&single=true&output=csv"
)

RESULTADOS_FILE = BASE_DIR / "data" / "resultados.json"

TIMEOUT = 20

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; VerificadorConvocatorias/2.0)"
}


# ============================================================
# Funciones auxiliares
# ============================================================

def leer_fuentes():
    """Descarga y parsea el CSV del Google Sheet."""
    resp = requests.get(SHEET_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    reader = csv.DictReader(io.StringIO(resp.text))
    fuentes = []
    for fila in reader:
        link = fila.get("LINK", "").strip()
        if not link:
            continue
        fuentes.append({
            "institucion":    fila.get("INSTITUCION", "").strip(),
            "categoria":      fila.get("CATEGORIA", "").strip(),
            "nombre":         fila.get("NOMBRE", "").strip(),
            "link":           link,
            "fecha_apertura": fila.get("FECHA_APERTURA", "").strip(),
            "fecha_cierre":   fila.get("FECHA_CIERRE", "").strip(),
        })
    return fuentes


def calcular_hash(texto):
    """Calcula el SHA-256 del contenido."""
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def cargar_resultados_previos():
    """Carga los resultados anteriores si existen, indexados por link+nombre."""
    if not RESULTADOS_FILE.exists():
        return {}
    try:
        with open(RESULTADOS_FILE, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return {f"{r['link']}|{r['nombre']}": r for r in datos}
    except Exception:
        return {}


def verificar_fuente(fuente, resultados_previos):
    """Visita la URL, verifica acceso y detecta cambios de contenido."""

    clave = f"{fuente['link']}|{fuente['nombre']}"
    anterior = resultados_previos.get(clave)

    resultado = {
        **fuente,
        "ultimo_acceso":   datetime.now(timezone.utc).isoformat(),
        "funciono":        False,
        "codigo_http":     None,
        "tiempo_respuesta_s": None,
        "hash":            None,
        "contenido_cambio": False,
        "error":           None,
    }

    inicio = time.perf_counter()
    try:
        respuesta = requests.get(fuente["link"], headers=HEADERS, timeout=TIMEOUT)
        resultado["tiempo_respuesta_s"] = round(time.perf_counter() - inicio, 3)
        resultado["codigo_http"] = respuesta.status_code
        respuesta.raise_for_status()

        resultado["funciono"] = True
        resultado["hash"] = calcular_hash(respuesta.text)

        if anterior and anterior.get("hash"):
            resultado["contenido_cambio"] = anterior["hash"] != resultado["hash"]
        else:
            resultado["contenido_cambio"] = False  # Primera vez: no alertar

    except requests.exceptions.RequestException as e:
        resultado["tiempo_respuesta_s"] = round(time.perf_counter() - inicio, 3)
        resultado["error"] = str(e)

    return resultado


def guardar_resultados(resultados):
    """Guarda los resultados en JSON."""
    RESULTADOS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTADOS_FILE, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)


# ============================================================
# Programa principal
# ============================================================

def main():
    print("==========================================")
    print("   VERIFICADOR DE CONVOCATORIAS v2")
    print("==========================================")
    print()

    print("Leyendo fuentes desde Google Sheet...")
    fuentes = leer_fuentes()
    print(f"Fuentes encontradas: {len(fuentes)}")
    print()

    resultados_previos = cargar_resultados_previos()
    resultados = []

    for i, fuente in enumerate(fuentes, start=1):
        print(f"[{i}/{len(fuentes)}] {fuente['institucion']} - {fuente['nombre']}")
        print(f"    {fuente['link']}")

        resultado = verificar_fuente(fuente, resultados_previos)
        resultados.append(resultado)

        if resultado["funciono"]:
            alerta = " [!] CONTENIDO CAMBIO - verificar fechas" if resultado["contenido_cambio"] else ""
            print(f"    OK - HTTP {resultado['codigo_http']} - {resultado['tiempo_respuesta_s']}s{alerta}")
        else:
            print(f"    ERROR - {resultado['error']}")
        print()

    guardar_resultados(resultados)

    cambios = sum(1 for r in resultados if r.get("contenido_cambio"))
    errores = sum(1 for r in resultados if not r.get("funciono"))

    print("------------------------------------------")
    print(f"Resultados: {len(resultados)} fuentes verificadas")
    print(f"  [!] Cambios detectados: {cambios} -> verificar fechas en el Sheet")
    print(f"  [X] Errores de acceso: {errores}")
    print(f"  Guardado en: {RESULTADOS_FILE}")
    print("------------------------------------------")


if __name__ == "__main__":
    main()