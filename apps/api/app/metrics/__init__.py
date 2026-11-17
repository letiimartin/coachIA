"""Motor de métricas determinista: zonas, carga (TSS) y CTL/ATL/TSB.

Módulo puro: sin base de datos, sin FastAPI y sin red. Recibe primitivas en las mismas unidades
que las columnas de ``activities`` (segundos, W, ppm, m/s, s/km). Ni el coach ni el LLM calculan
métricas: las piden aquí.
"""
