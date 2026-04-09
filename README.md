# analisis-precio

API en FastAPI + Polars para consolidar inventarios y precios de multiples proveedores y generar una maestra de precios minimos por codigo_barra.

## Requisitos

- Python 3.11
- Dependencias en requirements.txt

## Ejecutar local

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
uvicorn src.main:app --reload
```

Variables utiles para frontend local:

- CORS_ALLOW_ORIGINS=* para permitir pruebas desde cualquier origen
- CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:5173 para restringir a orígenes concretos
- MAX_UPLOAD_MB=10 para limitar el tamano del archivo en memoria

## Endpoint principal

- POST /analizar
- Form-data: file (csv o xlsx, un solo archivo)
- Form-data: files (csv o xlsx, multiples archivos)

Respuesta JSON por item:

- codigo_barra
- codigo_interno_proveedor
- nombre_producto
- mejor_precio
- proveedor_ganador
- unidades_disponibles
- analisis_timestamp

Columnas esperadas:

- codigo_barra
- codigo_producto
- nombre_producto
- nombre_laboratorio
- unidades_existentes
- precio_unitario

Formato esperado por archivo:

- Fila 1, columna A: nombre del proveedor, drogueria o laboratorio (obligatorio)
- Fila 2: encabezados reales
- Fila 3 en adelante: datos del archivo

Con este formato, no necesitas la columna `nombre_proveedor`; la API la inyecta automaticamente desde la primera celda del archivo.

Alias soportados:

- barra -> codigo_barra
- barcode -> codigo_barra
- codigo_de_barra -> codigo_barra
- codigo -> codigo_producto
- descripcion -> nombre_producto
- laboratorio -> nombre_laboratorio
- stock -> unidades_existentes
- existencia -> unidades_existentes
- unidades -> unidades_existentes
- disponible -> unidades_existentes
- precio -> precio_unitario

## Regla de optimizacion

1. Normaliza codigo_barra removiendo espacios y ceros a la izquierda.
2. Filtra filas con codigo_barra nulo/vacio o precio_unitario <= 0.
3. Agrupa implicitamente por codigo_barra.
4. Selecciona la fila con menor precio_unitario por codigo_barra.
5. Preserva codigo_producto, nombre_producto, nombre_proveedor y unidades_existentes de la fila ganadora.

## Ejemplo de respuesta

```json
[
	{
		"codigo_barra": "7701234567890",
		"codigo_interno_proveedor": "ABC-001",
		"nombre_producto": "Acetaminofen 500mg",
		"mejor_precio": 12.5,
		"proveedor_ganador": "Drogueria Central",
		"unidades_disponibles": 48,
		"analisis_timestamp": "2026-04-09T15:30:00+00:00"
	}
]
```

## Como usar la API

1. Inicia el servidor con `uvicorn src.main:app --reload`.
2. Abre `http://127.0.0.1:8000/docs`.
3. En `POST /analizar`, pulsa `Try it out`.
4. Carga uno o varios archivos `.csv` o `.xlsx` con las columnas requeridas.
5. Ejecuta la solicitud y revisa el JSON consolidado por codigo_barra.

Ejemplo de archivo con proveedor en la primera fila:

```text
Drogueria Central
codigo_barra,codigo_producto,nombre_producto,nombre_laboratorio,unidades_existentes,precio_unitario
00012345,P1,Acetaminofen,Lab Norte,40,12
12345,P2,Acetaminofen,Lab Norte,18,9
```

## Deploy en Render

- Archivo de infraestructura: render.yaml
- Build command: pip install -r requirements.txt
- Start command: uvicorn src.main:app --host 0.0.0.0 --port $PORT
- Configura CORS_ALLOW_ORIGINS con los dominios reales del frontend separados por coma

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```
