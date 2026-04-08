import io
import os
from pathlib import Path

import polars as pl
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
	title="Price Optimizer API",
	description="Analizador masivo de mejores precios por proveedor",
	version="0.1.0",
)


def _parse_cors_origins() -> list[str]:
	raw_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
	return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


CORS_ALLOW_ORIGINS = _parse_cors_origins()
SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
REQUIRED_COLUMNS = {
	"codigo_producto",
	"nombre_producto",
	"nombre_laboratorio",
	"nombre_proveedor",
	"precio_unitario",
}
COLUMN_ALIASES = {
	"descripcion": "nombre_producto",
	"proveedor": "nombre_proveedor",
	"precio": "precio_unitario",
	"laboratorio": "nombre_laboratorio",
	"codigo": "codigo_producto",
}

app.add_middleware(
	CORSMiddleware,
	allow_origins=CORS_ALLOW_ORIGINS,
	allow_credentials=False,
	allow_methods=["*"],
	allow_headers=["*"],
)


def _normalize_columns(df: pl.DataFrame) -> pl.DataFrame:
	renamed_columns = {
		column: COLUMN_ALIASES.get(column.strip().lower(), column.strip().lower())
		for column in df.columns
	}
	return df.rename(renamed_columns)


def _validate_required_columns(df: pl.DataFrame) -> None:
	missing_columns = sorted(REQUIRED_COLUMNS.difference(df.columns))
	if missing_columns:
		raise HTTPException(
			status_code=400,
			detail={
				"error": "Columnas requeridas faltantes",
				"faltantes": missing_columns,
			},
		)


def _read_input_file(filename: str, content: bytes) -> pl.DataFrame:
	extension = Path(filename).suffix.lower()

	if extension == ".csv":
		return pl.read_csv(io.BytesIO(content))

	return pl.read_excel(io.BytesIO(content), engine="openpyxl")


@app.get("/")
async def health_check() -> dict[str, str]:
	return {"status": "ready", "engine": "polars-rust"}


@app.post("/analizar")
async def analizar_precios(file: UploadFile = File(...)) -> list[dict[str, object]]:
	if not file.filename:
		raise HTTPException(status_code=400, detail="El archivo debe tener nombre")

	extension = Path(file.filename).suffix.lower()
	if extension not in SUPPORTED_EXTENSIONS:
		raise HTTPException(
			status_code=400,
			detail="Formato no soportado. Use archivos .csv o .xlsx",
		)

	try:
		content = await file.read()
		if not content:
			raise HTTPException(status_code=400, detail="El archivo esta vacio")

		if len(content) > MAX_UPLOAD_BYTES:
			raise HTTPException(
				status_code=413,
				detail=f"El archivo excede el limite de {MAX_UPLOAD_MB} MB",
			)

		df = _read_input_file(file.filename, content)
		df = _normalize_columns(df)
		_validate_required_columns(df)

		resultado = (
			df.with_columns(
				pl.col("precio_unitario").cast(pl.Float64, strict=False),
				pl.col("codigo_producto").cast(pl.Utf8, strict=False).str.strip_chars(),
				pl.col("nombre_producto").cast(pl.Utf8, strict=False).str.strip_chars(),
				pl.col("nombre_proveedor").cast(pl.Utf8, strict=False).str.strip_chars(),
				pl.col("nombre_laboratorio").cast(pl.Utf8, strict=False).str.strip_chars(),
			)
			.filter(
				pl.col("precio_unitario").is_not_null()
				& (pl.col("precio_unitario") > 0)
				& pl.col("codigo_producto").is_not_null()
				& (pl.col("codigo_producto") != "")
			)
			.sort(["codigo_producto", "precio_unitario", "nombre_proveedor"])
			.unique(subset=["codigo_producto"], keep="first", maintain_order=True)
			.select(
				pl.col("codigo_producto").alias("codigoProducto"),
				pl.col("nombre_producto").alias("nombreProducto"),
				pl.col("nombre_proveedor").alias("nombreProveedor"),
				pl.col("nombre_laboratorio").alias("nombreLaboratorio"),
				pl.col("precio_unitario").alias("precioUnitario"),
			)
		)

		return resultado.to_dicts()
	except HTTPException:
		raise
	except pl.exceptions.PolarsError as exc:
		raise HTTPException(
			status_code=400,
			detail={
				"error": "No se pudo interpretar el archivo de entrada",
				"detalle": str(exc),
			},
		) from exc
	except Exception as exc:
		raise HTTPException(
			status_code=500,
			detail={
				"error": "Fallo en el procesamiento",
				"detalle": str(exc),
			},
		) from exc
