# analisis-precio

API en FastAPI + Polars para optimizar cotizaciones y seleccionar el menor precio por codigo de producto.

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

## Endpoint principal

- POST /analizar
- Form-data: file (csv o xlsx)

Respuesta JSON por item:

- codigoProducto
- nombreProducto
- nombreProveedor
- precioUnitario

Columnas esperadas:

- codigo_producto
- nombre_producto
- nombre_proveedor
- precio_unitario

Alias soportados:

- codigo -> codigo_producto
- descripcion -> nombre_producto
- proveedor -> nombre_proveedor
- precio -> precio_unitario

## Regla de optimizacion

1. Filtra filas con precio_unitario <= 0 o codigo_producto nulo/vacio.
2. Agrupa implicitamente por codigo_producto.
3. Selecciona la fila con menor precio_unitario por codigo.
4. Preserva nombre_producto y nombre_proveedor de la fila minima.

## Deploy en Render

- Archivo de infraestructura: render.yaml
- Build command: pip install -r requirements.txt
- Start command: uvicorn src.main:app --host 0.0.0.0 --port $PORT

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```
