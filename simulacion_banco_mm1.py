"""
================================================================================
SIMULACIÓN DE UN PROBLEMA BANCARIO MEDIANTE MODELOS DE COLAS M/M/1
Actividad Didáctica 2-M3 - Simulación (PREICA2602B020045)
Institución Universitaria Digital de Antioquia

Integrantes:
- Raul Santiago Morales Henao
- David Octavio Castro Mora
- Claudia Dilbani Enriquez Botina
Docente: Julián Andrés Loaiza
================================================================================
Descripción:
Este módulo implementa la simulación de eventos discretos (DES) para medir el
desempeño de tres cajeros bancarios modelados como sistemas M/M/1 independientes
durante una jornada laboral de 8 horas (480 minutos) a lo largo de 10 réplicas.

Evalúa y compara cuatro escenarios operativos con Números Aleatorios Comunes (CRN):
1. Modelo Base (3 Cajeros Mixtos M/M/1 independientes)
2. Escenario 2R+1P (2 Cajeros exclusivos para Retiros y 1 exclusivo para Pagos)
3. Escenario 1R+2P (1 Cajero exclusivo para Retiros y 2 exclusivos para Pagos)
4. Escenario Ampliado 4 Cajeros (2 Cajeros Retiros + 2 Cajeros Pagos / Nuevo Cajero)
================================================================================
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Configuración estética global para las gráficas
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = "#333333"
plt.rcParams["axes.linewidth"] = 0.8

# ==============================================================================
# 1. PARÁMETROS DEL MODELO SEGÚN TABLAS 1 Y 2 DEL ENUNCIADO
# ==============================================================================
HORAS_JORNADA: int = 8
TIEMPO_SIMULACION_MIN: float = float(HORAS_JORNADA * 60)  # 480.0 minutos
NUM_REPLICAS: int = 10
NUM_CAJEROS_BASE: int = 3
SEMILLA_BASE: int = 42

# Probabilidades globales por tipo de acción
PROB_ACCION: Dict[str, float] = {
    "Retiro": 0.70,
    "Consignación o pago": 0.30,
}

# Tabla 1 y Tabla 2: Parámetros exponenciales (en minutos) y probabilidades
# Nota: Exponencial con media M -> tasa lambda = 1/M (o mu = 1/M)
PARAMETROS_USUARIOS: Dict[str, Dict[str, Dict[str, float]]] = {
    "Retiro": {
        "Rápido": {"prob": 0.23, "media_servicio": 1.0, "media_llegada": 1.0},
        "Normal": {"prob": 0.40, "media_servicio": 2.0, "media_llegada": 2.0},
        "Lento": {"prob": 0.17, "media_servicio": 3.0, "media_llegada": 3.0},
        "Muy lento": {"prob": 0.20, "media_servicio": 4.0, "media_llegada": 3.0},
    },
    "Consignación o pago": {
        "Rápido": {"prob": 0.10, "media_servicio": 3.0, "media_llegada": 1.0},
        "Normal": {"prob": 0.20, "media_servicio": 3.0, "media_llegada": 2.0},
        "Lento": {"prob": 0.30, "media_servicio": 5.0, "media_llegada": 3.0},
        "Muy lento": {"prob": 0.40, "media_servicio": 7.0, "media_llegada": 4.0},
    },
}

TIPOS_USUARIO_ORDEN: List[str] = ["Rápido", "Normal", "Lento", "Muy lento"]
ACCIONES_ORDEN: List[str] = ["Retiro", "Consignación o pago"]


@dataclass
class EventoCliente:
    """Representa un usuario generado en el proceso estocástico de llegadas."""

    id_cliente: int
    replica: int
    accion: str
    tipo_usuario: str
    media_llegada: float
    media_servicio: float
    tiempo_entre_llegadas: float
    tiempo_llegada: float
    tiempo_servicio: float
    u_asignacion: float  # Uniforme(0,1) para enrutamiento reproducible a cajeros


@dataclass
class RegistroAtencion:
    """Representa el resultado de atención de un usuario en un cajero M/M/1."""

    id_cliente: int
    replica: int
    escenario: str
    cajero: str
    accion: str
    tipo_usuario: str
    tiempo_llegada: float
    inicio_atencion: float
    fin_atencion: float
    tiempo_espera: float
    tiempo_servicio: float
    tiempo_sistema: float


# ==============================================================================
# 2. GENERACIÓN DEL FLUJO DE USUARIOS POR RÉPLICA (MÉTODO DE MONTECARLO)
# ==============================================================================
def seleccionar_categoria(u: float, categorias_prob: Dict[str, float]) -> str:
    """Selecciona una categoría usando la transformada inversa discreta."""
    acumulado = 0.0
    for nombre, prob in categorias_prob.items():
        acumulado += prob
        if u <= acumulado:
            return nombre
    return list(categorias_prob.keys())[-1]


def generar_clientes_replica(
    replica_id: int, tiempo_limite: float, seed: int
) -> List[EventoCliente]:
    """
    Genera la secuencia de llegadas de usuarios durante un día laboral (480 min)
    respetando las probabilidades de las Tablas 1 y 2 y distribuciones exponenciales.
    """
    rng = random.Random(seed + replica_id * 1009)
    reloj = 0.0
    clientes: List[EventoCliente] = []
    contador = 0

    probs_subtipo = {
        accion: {k: v["prob"] for k, v in subtipos.items()}
        for accion, subtipos in PARAMETROS_USUARIOS.items()
    }

    while True:
        # 1. Determinar acción (70% Retiro, 30% Consignación o pago)
        accion = seleccionar_categoria(rng.random(), PROB_ACCION)

        # 2. Determinar tipo de usuario según Tabla 2
        tipo_usuario = seleccionar_categoria(rng.random(), probs_subtipo[accion])

        # 3. Obtener medias exponenciales según Tabla 1
        info = PARAMETROS_USUARIOS[accion][tipo_usuario]
        media_llegada = info["media_llegada"]
        media_servicio = info["media_servicio"]

        # 4. Generar tiempos exponenciales (expovariate recibe lambda = 1/media)
        dt_llegada = rng.expovariate(1.0 / media_llegada)
        t_servicio = rng.expovariate(1.0 / media_servicio)
        u_asig = rng.random()

        reloj += dt_llegada
        if reloj > tiempo_limite:
            break

        contador += 1
        clientes.append(
            EventoCliente(
                id_cliente=contador,
                replica=replica_id,
                accion=accion,
                tipo_usuario=tipo_usuario,
                media_llegada=media_llegada,
                media_servicio=media_servicio,
                tiempo_entre_llegadas=dt_llegada,
                tiempo_llegada=reloj,
                tiempo_servicio=t_servicio,
                u_asignacion=u_asig,
            )
        )

    return clientes


# ==============================================================================
# 3. SIMULADOR DE CAJEROS INDEPENDIENTES COMO MODELOS M/M/1
# ==============================================================================
def simular_escenario_mm1(
    clientes: List[EventoCliente], escenario: str
) -> List[RegistroAtencion]:
    """
    Simula la operación de los cajeros como colas M/M/1 independientes (FIFO).
    Cada cajero mantiene su propio reloj de liberación e historial de atención,
    asumiendo atención inmediata cuando está libre y tiempo de desplazamiento
    despreciable, tal como lo exige el enunciado.

    Escenarios soportados:
    - '3_Mixtos': 3 cajeros M/M/1 independientes que atienden pagos y retiros.
    - '2R_1P': Cajero 1 y 2 exclusivos para Retiros; Cajero 3 exclusivo para Pagos.
    - '1R_2P': Cajero 1 exclusivo para Retiros; Cajero 2 y 3 exclusivos para Pagos.
    - '4_Cajeros_2R_2P': Cajero 1 y 2 para Retiros; Cajero 3 y 4 para Pagos.
    """
    if escenario == "4_Cajeros_2R_2P":
        nombres_cajeros = ["Cajero 1", "Cajero 2", "Cajero 3", "Cajero 4"]
    else:
        nombres_cajeros = ["Cajero 1", "Cajero 2", "Cajero 3"]

    tiempo_libre_cajero: Dict[str, float] = {c: 0.0 for c in nombres_cajeros}
    registros: List[RegistroAtencion] = []

    for cli in clientes:
        # Selección del cajero independiente M/M/1 según la configuración
        if escenario == "3_Mixtos":
            idx = min(int(cli.u_asignacion * 3), 2)
            cajero_asignado = nombres_cajeros[idx]
        elif escenario == "2R_1P":
            if cli.accion == "Retiro":
                cajero_asignado = "Cajero 1" if cli.u_asignacion < 0.5 else "Cajero 2"
            else:
                cajero_asignado = "Cajero 3"
        elif escenario == "1R_2P":
            if cli.accion == "Retiro":
                cajero_asignado = "Cajero 1"
            else:
                cajero_asignado = "Cajero 2" if cli.u_asignacion < 0.5 else "Cajero 3"
        elif escenario == "4_Cajeros_2R_2P":
            if cli.accion == "Retiro":
                cajero_asignado = "Cajero 1" if cli.u_asignacion < 0.5 else "Cajero 2"
            else:
                cajero_asignado = "Cajero 3" if cli.u_asignacion < 0.5 else "Cajero 4"
        else:
            raise ValueError(f"Escenario desconocido: {escenario}")

        # Dinámica de cola M/M/1 FIFO en el cajero asignado
        inicio_servicio = max(cli.tiempo_llegada, tiempo_libre_cajero[cajero_asignado])
        espera_cola = inicio_servicio - cli.tiempo_llegada
        fin_servicio = inicio_servicio + cli.tiempo_servicio
        tiempo_total_sistema = fin_servicio - cli.tiempo_llegada

        tiempo_libre_cajero[cajero_asignado] = fin_servicio

        registros.append(
            RegistroAtencion(
                id_cliente=cli.id_cliente,
                replica=cli.replica,
                escenario=escenario,
                cajero=cajero_asignado,
                accion=cli.accion,
                tipo_usuario=cli.tipo_usuario,
                tiempo_llegada=cli.tiempo_llegada,
                inicio_atencion=inicio_servicio,
                fin_atencion=fin_servicio,
                tiempo_espera=espera_cola,
                tiempo_servicio=cli.tiempo_servicio,
                tiempo_sistema=tiempo_total_sistema,
            )
        )

    return registros


# ==============================================================================
# 4. EJECUCIÓN DE LAS 10 RÉPLICAS Y CÁLCULO DE ESTADÍSTICAS
# ==============================================================================
def ejecutar_estudio_completo() -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """Ejecuta las 10 réplicas para todos los escenarios y compila las tablas."""
    escenarios = ["3_Mixtos", "2R_1P", "1R_2P", "4_Cajeros_2R_2P"]
    todos_registros: List[RegistroAtencion] = []

    for rep in range(1, NUM_REPLICAS + 1):
        clientes_rep = generar_clientes_replica(
            replica_id=rep, tiempo_limite=TIEMPO_SIMULACION_MIN, seed=SEMILLA_BASE
        )
        for esc in escenarios:
            todos_registros.extend(simular_escenario_mm1(clientes_rep, esc))

    df = pd.DataFrame([r.__dict__ for r in todos_registros])

    # Filtrar escenario base (3_Mixtos) para las métricas base de los 3 cajeros
    df_base = df[df["escenario"] == "3_Mixtos"].copy()

    # --------------------------------------------------------------------------
    # PUNTO 1: Estadísticas por cajero (menor y mayor tiempo promedio de atención)
    # --------------------------------------------------------------------------
    # Primero calculamos el promedio por réplica y cajero, y luego agregamos en las 10 réplicas
    rep_cajero_base = (
        df_base.groupby(["replica", "cajero"])
        .agg(
            usuarios_atendidos=("id_cliente", "count"),
            tiempo_atencion_prom=("tiempo_servicio", "mean"),
            tiempo_espera_prom=("tiempo_espera", "mean"),
            tiempo_sistema_prom=("tiempo_sistema", "mean"),
            tiempo_ocupado_total=("tiempo_servicio", "sum"),
        )
        .reset_index()
    )
    rep_cajero_base["utilizacion_pct"] = (
        rep_cajero_base["tiempo_ocupado_total"] / TIEMPO_SIMULACION_MIN
    ) * 100.0

    tabla_punto1_cajeros = (
        rep_cajero_base.groupby("cajero")
        .agg(
            usuarios_prom_replica=("usuarios_atendidos", "mean"),
            usuarios_total_10rep=("usuarios_atendidos", "sum"),
            atencion_media_min=("tiempo_atencion_prom", "mean"),
            atencion_std_min=("tiempo_atencion_prom", "std"),
            atencion_min_rep=("tiempo_atencion_prom", "min"),
            atencion_max_rep=("tiempo_atencion_prom", "max"),
            espera_media_min=("tiempo_espera_prom", "mean"),
            espera_std_min=("tiempo_espera_prom", "std"),
            sistema_media_min=("tiempo_sistema_prom", "mean"),
            utilizacion_media_pct=("utilizacion_pct", "mean"),
        )
        .reset_index()
    )

    # También calculamos el tiempo promedio global ponderado por cajero (sobre todos los clientes)
    global_cajero = (
        df_base.groupby("cajero")
        .agg(
            atencion_global_min=("tiempo_servicio", "mean"),
            atencion_global_std=("tiempo_servicio", "std"),
            espera_global_min=("tiempo_espera", "mean"),
            sistema_global_min=("tiempo_sistema", "mean"),
        )
        .reset_index()
    )
    tabla_punto1_cajeros = pd.merge(tabla_punto1_cajeros, global_cajero, on="cajero")

    # --------------------------------------------------------------------------
    # PUNTO 2: Promedio de usuarios de cada tipo en la totalidad de cajeros
    # --------------------------------------------------------------------------
    # 2A. Por tipo de velocidad de usuario (Rápido, Normal, Lento, Muy lento)
    conteo_tipo_rep = (
        df_base.groupby(["replica", "tipo_usuario"])["id_cliente"]
        .count()
        .unstack(fill_value=0)
        .reindex(columns=TIPOS_USUARIO_ORDEN, fill_value=0)
    )
    conteo_tipo_rep["Total_Replica"] = conteo_tipo_rep.sum(axis=1)

    resumen_punto2_tipo = pd.DataFrame(
        {
            "Tipo de Usuario": TIPOS_USUARIO_ORDEN,
            "Total Usuarios (10 Réplicas)": [
                int(conteo_tipo_rep[t].sum()) for t in TIPOS_USUARIO_ORDEN
            ],
            "Promedio por Réplica (3 Cajeros)": [
                conteo_tipo_rep[t].mean() for t in TIPOS_USUARIO_ORDEN
            ],
            "Desv. Estándar entre Réplicas": [
                conteo_tipo_rep[t].std() for t in TIPOS_USUARIO_ORDEN
            ],
            "Promedio por Cajero por Réplica": [
                conteo_tipo_rep[t].mean() / NUM_CAJEROS_BASE
                for t in TIPOS_USUARIO_ORDEN
            ],
            "Porcentaje Empírico (%)": [
                (conteo_tipo_rep[t].sum() / conteo_tipo_rep["Total_Replica"].sum())
                * 100.0
                for t in TIPOS_USUARIO_ORDEN
            ],
            "Porcentaje Teórico (%)": [
                (0.70 * 0.23 + 0.30 * 0.10) * 100.0,  # Rápido = 19.1%
                (0.70 * 0.40 + 0.30 * 0.20) * 100.0,  # Normal = 34.0%
                (0.70 * 0.17 + 0.30 * 0.30) * 100.0,  # Lento  = 20.9%
                (0.70 * 0.20 + 0.30 * 0.40) * 100.0,  # Muy lento = 26.0%
            ],
        }
    )

    # 2B. Desglosado por Acción + Tipo de Usuario (las 8 subcategorías de Tablas 1 y 2)
    df_base["accion_tipo"] = df_base["accion"] + " - " + df_base["tipo_usuario"]
    orden_8_cat = [
        f"{acc} - {t}" for acc in ACCIONES_ORDEN for t in TIPOS_USUARIO_ORDEN
    ]
    conteo_8cat_rep = (
        df_base.groupby(["replica", "accion_tipo"])["id_cliente"]
        .count()
        .unstack(fill_value=0)
        .reindex(columns=orden_8_cat, fill_value=0)
    )

    filas_8cat = []
    total_gen = len(df_base)
    for acc in ACCIONES_ORDEN:
        for t in TIPOS_USUARIO_ORDEN:
            col = f"{acc} - {t}"
            p_teo = (
                PROB_ACCION[acc] * PARAMETROS_USUARIOS[acc][t]["prob"] * 100.0
            )
            sub_df = df_base[(df_base["accion"] == acc) & (df_base["tipo_usuario"] == t)]
            filas_8cat.append(
                {
                    "Tipo de Acción": acc,
                    "Tipo de Usuario": t,
                    "Total (10 Réplicas)": int(conteo_8cat_rep[col].sum()),
                    "Promedio por Réplica": conteo_8cat_rep[col].mean(),
                    "Desv. Estándar": conteo_8cat_rep[col].std(),
                    "Porcentaje Empírico (%)": (conteo_8cat_rep[col].sum() / total_gen)
                    * 100.0,
                    "Porcentaje Teórico (%)": p_teo,
                    "Atención Media Empírica (min)": sub_df["tiempo_servicio"].mean(),
                    "Atención Media Teórica (min)": PARAMETROS_USUARIOS[acc][t][
                        "media_servicio"
                    ],
                }
            )
    resumen_punto2_8cat = pd.DataFrame(filas_8cat)

    # --------------------------------------------------------------------------
    # PUNTO 3: Total de usuarios de cada tipo en cada réplica y menor cantidad
    # --------------------------------------------------------------------------
    tabla_punto3_replicas = conteo_tipo_rep.copy()
    # Agregar conteos por acción (Retiro vs Pago) en cada réplica
    conteo_accion_rep = (
        df_base.groupby(["replica", "accion"])["id_cliente"]
        .count()
        .unstack(fill_value=0)
        .reindex(columns=ACCIONES_ORDEN, fill_value=0)
    )
    tabla_punto3_replicas["Retiros"] = conteo_accion_rep["Retiro"]
    tabla_punto3_replicas["Pagos"] = conteo_accion_rep["Consignación o pago"]
    tabla_punto3_replicas.index.name = "Réplica"
    tabla_punto3_replicas = tabla_punto3_replicas.reset_index()

    # --------------------------------------------------------------------------
    # PUNTOS 4 Y 5: Comparación de criterios, tiempos de espera, exclusividad y
    # evaluación de nuevo cajero
    # --------------------------------------------------------------------------
    # Métricas por escenario y cajero
    esc_cajero_rep = (
        df.groupby(["escenario", "replica", "cajero"])
        .agg(
            usuarios=("id_cliente", "count"),
            atencion_prom=("tiempo_servicio", "mean"),
            espera_prom=("tiempo_espera", "mean"),
            sistema_prom=("tiempo_sistema", "mean"),
            ocupacion_min=("tiempo_servicio", "sum"),
        )
        .reset_index()
    )
    esc_cajero_rep["utilizacion_pct"] = (
        esc_cajero_rep["ocupacion_min"] / TIEMPO_SIMULACION_MIN
    ) * 100.0

    tabla_escenarios_cajero = (
        esc_cajero_rep.groupby(["escenario", "cajero"])
        .agg(
            usuarios_prom_dia=("usuarios", "mean"),
            atencion_media_min=("atencion_prom", "mean"),
            espera_media_min=("espera_prom", "mean"),
            sistema_media_min=("sistema_prom", "mean"),
            utilizacion_media_pct=("utilizacion_pct", "mean"),
        )
        .reset_index()
    )

    # Métricas globales y por tipo de acción en cada escenario
    esc_global_rep = (
        df.groupby(["escenario", "replica"])
        .agg(
            usuarios_totales=("id_cliente", "count"),
            atencion_prom=("tiempo_servicio", "mean"),
            espera_prom_global=("tiempo_espera", "mean"),
            espera_max_global=("tiempo_espera", "max"),
            sistema_prom_global=("tiempo_sistema", "mean"),
        )
        .reset_index()
    )

    esc_accion_rep = (
        df.groupby(["escenario", "replica", "accion"])["tiempo_espera"]
        .mean()
        .unstack()
        .reset_index()
        .rename(
            columns={
                "Retiro": "espera_retiro_min",
                "Consignación o pago": "espera_pago_min",
            }
        )
    )
    esc_merged = pd.merge(
        esc_global_rep, esc_accion_rep, on=["escenario", "replica"]
    )

    tabla_comparativa_escenarios = (
        esc_merged.groupby("escenario")
        .agg(
            usuarios_prom_dia=("usuarios_totales", "mean"),
            atencion_media_min=("atencion_prom", "mean"),
            espera_global_min=("espera_prom_global", "mean"),
            espera_global_std=("espera_prom_global", "std"),
            espera_retiros_min=("espera_retiro_min", "mean"),
            espera_pagos_min=("espera_pago_min", "mean"),
            sistema_global_min=("sistema_prom_global", "mean"),
            espera_maxima_prom_min=("espera_max_global", "mean"),
        )
        .reindex(["3_Mixtos", "2R_1P", "1R_2P", "4_Cajeros_2R_2P"])
        .reset_index()
    )

    tablas = {
        "punto1_cajeros": tabla_punto1_cajeros,
        "punto2_tipo_usuario": resumen_punto2_tipo,
        "punto2_8categorias": resumen_punto2_8cat,
        "punto3_replicas": tabla_punto3_replicas,
        "punto3_8cat_replicas": conteo_8cat_rep.reset_index(),
        "punto4_5_escenarios_global": tabla_comparativa_escenarios,
        "punto4_5_escenarios_cajero": tabla_escenarios_cajero,
    }
    return df, tablas


# ==============================================================================
# 5. GENERACIÓN DE GRÁFICAS PROFESIONALES PARA EL INFORME Y GITHUB
# ==============================================================================
def generar_graficas(
    df: pd.DataFrame, tablas: Dict[str, pd.DataFrame], out_dir: str
) -> List[str]:
    """Genera y guarda las gráficas analíticas de alta resolución (300 DPI)."""
    os.makedirs(out_dir, exist_ok=True)
    rutas_generadas: List[str] = []

    # --------------------------------------------------------------------------
    # GRÁFICA 1: Tiempo promedio de atención y espera por cajero (Punto 1)
    # --------------------------------------------------------------------------
    t1 = tablas["punto1_cajeros"]
    fig, ax = plt.subplots(figsize=(8.5, 4.8), dpi=300)
    x = np.arange(len(t1["cajero"]))
    width = 0.26

    b1 = ax.bar(
        x - width,
        t1["atencion_media_min"],
        width,
        label="Tiempo Promedio de Atención (Servicio)",
        color="#1f4e78",
        edgecolor="black",
    )
    b2 = ax.bar(
        x,
        t1["espera_media_min"],
        width,
        label="Tiempo Promedio de Espera en Cola (Wq)",
        color="#2e75b6",
        edgecolor="black",
    )
    b3 = ax.bar(
        x + width,
        t1["sistema_media_min"],
        width,
        label="Tiempo Promedio en el Sistema (Ws)",
        color="#9bc2e6",
        edgecolor="black",
    )

    for bars in [b1, b2, b3]:
        for bar in bars:
            h = bar.get_height()
            ax.annotate(
                f"{h:.2f}",
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8.5,
                fontweight="bold",
            )

    ax.set_title(
        "Desempeño por Cajero en el Modelo Base M/M/1 (Promedio de 10 Réplicas)",
        fontsize=11.5,
        fontweight="bold",
        pad=12,
    )
    ax.set_ylabel("Tiempo Promedio (minutos)", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(t1["cajero"], fontsize=10, fontweight="bold")
    ax.set_ylim(0, max(t1["sistema_media_min"]) * 1.22)
    ax.grid(axis="y", linestyle="--", alpha=0.45)
    ax.legend(frameon=True, fontsize=9)
    plt.tight_layout()
    ruta1 = os.path.join(out_dir, "fig1_tiempos_por_cajero.png")
    plt.savefig(ruta1, dpi=300)
    plt.close(fig)
    rutas_generadas.append(ruta1)

    # --------------------------------------------------------------------------
    # GRÁFICA 2: Distribución promedio de usuarios por tipo y acción (Punto 2)
    # --------------------------------------------------------------------------
    t2 = tablas["punto2_tipo_usuario"]
    t2_8 = tablas["punto2_8categorias"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.8), dpi=300)

    # Subplot 1: Promedio por tipo de usuario (4 tipos)
    colores_tipo = ["#1b4f72", "#2874a6", "#5499c7", "#85c1e9"]
    bars1 = ax1.bar(
        t2["Tipo de Usuario"],
        t2["Promedio por Réplica (3 Cajeros)"],
        yerr=t2["Desv. Estándar entre Réplicas"],
        capsize=4,
        color=colores_tipo,
        edgecolor="black",
        width=0.55,
    )
    for bar, pct, std_val in zip(
        bars1,
        t2["Porcentaje Empírico (%)"],
        t2["Desv. Estándar entre Réplicas"],
    ):
        h = bar.get_height()
        ax1.annotate(
            f"{h:.1f}\n({pct:.1f}%)",
            xy=(bar.get_x() + bar.get_width() / 2, h + std_val),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8.5,
            fontweight="bold",
        )
    ax1.set_title(
        "Promedio Diario de Usuarios por Tipo\n(Totalidad de Cajeros)",
        fontsize=10.5,
        fontweight="bold",
    )
    ax1.set_ylabel("Usuarios Promedio por Día (Réplica)", fontsize=9.5)
    ax1.set_ylim(0, max(t2["Promedio por Réplica (3 Cajeros)"] + t2["Desv. Estándar entre Réplicas"]) * 1.25)
    ax1.grid(axis="y", linestyle="--", alpha=0.45)

    # Subplot 2: Desglose por Acción (Retiro vs Pago) y Tipo de Usuario
    ret_vals = t2_8[t2_8["Tipo de Acción"] == "Retiro"]["Promedio por Réplica"].values
    pag_vals = t2_8[t2_8["Tipo de Acción"] == "Consignación o pago"][
        "Promedio por Réplica"
    ].values
    x2 = np.arange(len(TIPOS_USUARIO_ORDEN))
    w2 = 0.35

    br = ax2.bar(
        x2 - w2 / 2,
        ret_vals,
        w2,
        label="Retiro (70%)",
        color="#1f4e78",
        edgecolor="black",
    )
    bp = ax2.bar(
        x2 + w2 / 2,
        pag_vals,
        w2,
        label="Consignación o Pago (30%)",
        color="#ed7d31",
        edgecolor="black",
    )
    for bars in [br, bp]:
        for bar in bars:
            h = bar.get_height()
            ax2.annotate(
                f"{h:.1f}",
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )
    ax2.set_title(
        "Promedio Diario por Tipo de Acción y Usuario\n(10 Réplicas de 8 Horas)",
        fontsize=10.5,
        fontweight="bold",
    )
    ax2.set_xticks(x2)
    ax2.set_xticklabels(TIPOS_USUARIO_ORDEN, fontsize=9.5)
    ax2.set_ylabel("Usuarios Promedio por Día", fontsize=9.5)
    ax2.set_ylim(0, max(ret_vals) * 1.25)
    ax2.grid(axis="y", linestyle="--", alpha=0.45)
    ax2.legend(frameon=True, fontsize=8.5)

    plt.tight_layout()
    ruta2 = os.path.join(out_dir, "fig2_promedio_usuarios_tipo.png")
    plt.savefig(ruta2, dpi=300)
    plt.close(fig)
    rutas_generadas.append(ruta2)

    # --------------------------------------------------------------------------
    # GRÁFICA 3: Total de usuarios por tipo en cada una de las 10 réplicas (Punto 3)
    # --------------------------------------------------------------------------
    t3 = tablas["punto3_replicas"]
    fig, ax = plt.subplots(figsize=(9.5, 4.8), dpi=300)
    replicas_labels = [f"R{r}" for r in t3["Réplica"]]
    x3 = np.arange(len(replicas_labels))
    w3 = 0.19

    for idx, (tipo, color) in enumerate(zip(TIPOS_USUARIO_ORDEN, colores_tipo)):
        offset = (idx - 1.5) * w3
        vals = t3[tipo].values
        bars = ax.bar(
            x3 + offset,
            vals,
            w3,
            label=tipo,
            color=color,
            edgecolor="black",
            linewidth=0.6,
        )
        min_idx = int(np.argmin(vals))
        # Destacar el mínimo de cada tipo con un marcador superior
        ax.scatter(
            x3[min_idx] + offset,
            vals[min_idx] + 2.2,
            color="#c00000",
            marker="v",
            s=40,
            zorder=5,
        )

    ax.plot(
        x3,
        t3["Total_Replica"] / 4.0,
        linestyle="--",
        marker="o",
        color="#333333",
        linewidth=1.2,
        label="Promedio General / 4 (Referencia)",
    )

    ax.set_title(
        "Total de Usuarios por Tipo en cada una de las 10 Réplicas (▼ = Mínimo por Tipo)",
        fontsize=11,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Réplica de Simulación (Jornada de 8 Horas = 480 min)", fontsize=10)
    ax.set_ylabel("Cantidad de Usuarios Atendidos", fontsize=10)
    ax.set_xticks(x3)
    ax.set_xticklabels(replicas_labels, fontsize=9.5, fontweight="bold")
    ax.set_ylim(0, 92)
    ax.grid(axis="y", linestyle="--", alpha=0.45)
    ax.legend(frameon=True, ncol=3, fontsize=8.5, loc="upper right")
    plt.tight_layout()
    ruta3 = os.path.join(out_dir, "fig3_usuarios_por_replica.png")
    plt.savefig(ruta3, dpi=300)
    plt.close(fig)
    rutas_generadas.append(ruta3)

    # --------------------------------------------------------------------------
    # GRÁFICA 4: Comparación de tiempos de espera entre configuraciones y nuevo cajero
    # --------------------------------------------------------------------------
    t4 = tablas["punto4_5_escenarios_global"]
    etiquetas_esc = [
        "3 Cajeros Mixtos\n(Actual)",
        "2 Retiros + 1 Pago\n(Exclusiva A)",
        "1 Retiro + 2 Pagos\n(Exclusiva B)",
        "4 Cajeros (2R + 2P)\n(Nuevo Cajero)",
    ]
    fig, ax = plt.subplots(figsize=(9.2, 5.0), dpi=300)
    x4 = np.arange(len(etiquetas_esc))
    w4 = 0.25

    b_glob = ax.bar(
        x4 - w4,
        t4["espera_global_min"],
        w4,
        label="Espera Promedio Global (Wq)",
        color="#1f4e78",
        edgecolor="black",
    )
    b_ret = ax.bar(
        x4,
        t4["espera_retiros_min"],
        w4,
        label="Espera Promedio en Retiros (70%)",
        color="#2e75b6",
        edgecolor="black",
    )
    b_pag = ax.bar(
        x4 + w4,
        t4["espera_pagos_min"],
        w4,
        label="Espera Promedio en Pagos (30%)",
        color="#ed7d31",
        edgecolor="black",
    )

    for bars in [b_glob, b_ret, b_pag]:
        for bar in bars:
            h = bar.get_height()
            ax.annotate(
                f"{h:.2f}",
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8.5,
                fontweight="bold",
            )

    ax.set_title(
        "Comparación de Tiempos Promedio de Espera en Cola (Wq) según Configuración",
        fontsize=11,
        fontweight="bold",
        pad=12,
    )
    ax.set_ylabel("Tiempo Promedio de Espera en Cola (minutos)", fontsize=10)
    ax.set_xticks(x4)
    ax.set_xticklabels(etiquetas_esc, fontsize=9.5, fontweight="bold")
    ax.set_ylim(0, max(t4["espera_pagos_min"]) * 1.25)
    ax.grid(axis="y", linestyle="--", alpha=0.45)
    ax.legend(frameon=True, fontsize=9)
    plt.tight_layout()
    ruta4 = os.path.join(out_dir, "fig4_comparacion_escenarios_espera.png")
    plt.savefig(ruta4, dpi=300)
    plt.close(fig)
    rutas_generadas.append(ruta4)

    return rutas_generadas


def main() -> None:
    """Punto de entrada principal: ejecuta la simulación, exporta CSVs y gráficas."""
    os.makedirs("resultados", exist_ok=True)
    os.makedirs(os.path.join("resultados", "graficas"), exist_ok=True)

    df, tablas = ejecutar_estudio_completo()

    # Guardar tablas en CSV para evidencia en el repositorio de GitHub
    for nombre, tabla in tablas.items():
        tabla.to_csv(os.path.join("resultados", f"{nombre}.csv"), index=False, encoding="utf-8-sig")
    df.to_csv(os.path.join("resultados", "detalle_corridas_mm1.csv"), index=False, encoding="utf-8-sig")

    generar_graficas(df, tablas, os.path.join("resultados", "graficas"))

    print("=== RESUMEN PUNTO 1: ESTADÍSTICAS POR CAJERO (MODELO BASE 3 MIXTOS) ===")
    print(tablas["punto1_cajeros"].to_string(index=False))

    print("\n=== RESUMEN PUNTO 2A: PROMEDIO DE USUARIOS POR TIPO (4 TIPOS) ===")
    print(tablas["punto2_tipo_usuario"].to_string(index=False))

    print("\n=== RESUMEN PUNTO 2B: PROMEDIO DE USUARIOS POR ACCIÓN Y TIPO (8 SUBCATEGORÍAS) ===")
    print(tablas["punto2_8categorias"].to_string(index=False))

    print("\n=== RESUMEN PUNTO 3: TOTAL DE USUARIOS POR TIPO EN CADA RÉPLICA ===")
    print(tablas["punto3_replicas"].to_string(index=False))

    print("\n=== RESUMEN PUNTOS 4 Y 5: COMPARACIÓN DE ESCENARIOS Y EXCLUSIVIDAD ===")
    print(tablas["punto4_5_escenarios_global"].to_string(index=False))

    print("\n=== DETALLE POR CAJERO EN CADA ESCENARIO ===")
    print(tablas["punto4_5_escenarios_cajero"].to_string(index=False))


if __name__ == "__main__":
    main()
