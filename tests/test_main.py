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
        "codigo_producto,nombre_producto,nombre_proveedor,precio_unitario\n"
        "A1,Arroz,Proveedor 1,10\n"
        "A1,Arroz,Proveedor 2,8\n"
        "B1,Azucar,Proveedor 3,0\n"
        "B1,Azucar,Proveedor 4,12\n"
    )

    response = client.post(
        "/analizar",
        files={"file": ("precios.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2

    por_codigo = {item["codigo_producto"]: item for item in data}
    assert por_codigo["A1"]["precio_unitario"] == 8.0
    assert por_codigo["A1"]["nombre_proveedor"] == "Proveedor 2"
    assert por_codigo["B1"]["precio_unitario"] == 12.0
    assert "analisis_timestamp" in por_codigo["A1"]


def test_analizar_rechaza_formato_invalido() -> None:
    response = client.post(
        "/analizar",
        files={"file": ("precios.txt", "contenido", "text/plain")},
    )

    assert response.status_code == 400
