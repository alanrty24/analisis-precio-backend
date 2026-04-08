from io import BytesIO

from openpyxl import Workbook
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"


def test_analizar_csv_ok() -> None:
    csv_content = (
        "codigo_producto,nombre_producto,nombre_laboratorio,nombre_proveedor,precio_unitario\n"
        "A1,Arroz,Lab 1,Proveedor 1,10\n"
        "A1,Arroz,Lab 2,Proveedor 2,8\n"
        "B1,Azucar,Lab 3,Proveedor 3,0\n"
        "B1,Azucar,Lab 4,Proveedor 4,12\n"
    )

    response = client.post(
        "/analizar",
        files={"file": ("precios.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2

    por_codigo = {item["codigoProducto"]: item for item in data}
    assert por_codigo["A1"]["precioUnitario"] == 8.0
    assert por_codigo["A1"]["nombreProveedor"] == "Proveedor 2"
    assert por_codigo["A1"]["nombreLaboratorio"] == "Lab 2"
    assert por_codigo["B1"]["precioUnitario"] == 12.0
    assert set(por_codigo["A1"].keys()) == {
        "codigoProducto",
        "nombreProducto",
        "nombreLaboratorio",
        "nombreProveedor",
        "precioUnitario",
    }


def test_analizar_csv_con_alias_laboratorio() -> None:
    csv_content = (
        "codigo,descripcion,laboratorio,proveedor,precio\n"
        "A1,Arroz,Lab Alias 1,Proveedor 1,11\n"
        "A1,Arroz,Lab Alias 2,Proveedor 2,7\n"
    )

    response = client.post(
        "/analizar",
        files={"file": ("precios_alias.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()

    assert data == [
        {
            "codigoProducto": "A1",
            "nombreProducto": "Arroz",
            "nombreLaboratorio": "Lab Alias 2",
            "nombreProveedor": "Proveedor 2",
            "precioUnitario": 7.0,
        }
    ]


def test_analizar_xlsx_ok() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(
        [
            "codigo_producto",
            "nombre_producto",
            "nombre_laboratorio",
            "nombre_proveedor",
            "precio_unitario",
        ]
    )
    worksheet.append(["A1", "Arroz", "Lab Excel 1", "Proveedor 1", 9])
    worksheet.append(["A1", "Arroz", "Lab Excel 2", "Proveedor 2", 6])

    file_content = BytesIO()
    workbook.save(file_content)
    file_content.seek(0)

    response = client.post(
        "/analizar",
        files={
            "file": (
                "precios.xlsx",
                file_content.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "codigoProducto": "A1",
            "nombreProducto": "Arroz",
            "nombreLaboratorio": "Lab Excel 2",
            "nombreProveedor": "Proveedor 2",
            "precioUnitario": 6.0,
        }
    ]


def test_analizar_falla_si_falta_nombre_laboratorio() -> None:
    csv_content = (
        "codigo_producto,nombre_producto,nombre_proveedor,precio_unitario\n"
        "A1,Arroz,Proveedor 1,10\n"
    )

    response = client.post(
        "/analizar",
        files={"file": ("precios.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"] == "Columnas requeridas faltantes"
    assert detail["faltantes"] == ["nombre_laboratorio"]


def test_analizar_rechaza_formato_invalido() -> None:
    response = client.post(
        "/analizar",
        files={"file": ("precios.txt", "contenido", "text/plain")},
    )

    assert response.status_code == 400


def test_cors_preflight() -> None:
    response = client.options(
        "/analizar",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
