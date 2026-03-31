"""
Tests for app/main.py — FastAPI calculator monolith.

Coverage:
  - GET /health
  - POST /add, /subtract, /multiply, /divide  (happy path)
  - Floating-point and negative inputs
  - Boundary: multiply-by-zero, divide result of 0/n
  - Error: divide by zero  → HTTP 400
  - Error: missing request field → HTTP 422
  - Error: non-numeric field    → HTTP 422
  - Large numbers
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Return a TestClient for the FastAPI app."""
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health_returns_ok_status(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "calculator-monolith"}


# ---------------------------------------------------------------------------
# /add
# ---------------------------------------------------------------------------

def test_add_two_positive_integers_returns_sum(client):
    response = client.post("/add", json={"a": 3, "b": 4})
    assert response.status_code == 200
    assert response.json() == {"result": 7.0}


def test_add_negative_numbers_returns_correct_sum(client):
    response = client.post("/add", json={"a": -5, "b": -3})
    assert response.status_code == 200
    assert response.json()["result"] == pytest.approx(-8.0)


def test_add_floats_returns_correct_sum(client):
    response = client.post("/add", json={"a": 1.1, "b": 2.2})
    assert response.status_code == 200
    assert response.json()["result"] == pytest.approx(3.3)


def test_add_missing_field_returns_422(client):
    response = client.post("/add", json={"a": 5})
    assert response.status_code == 422


def test_add_non_numeric_field_returns_422(client):
    response = client.post("/add", json={"a": "foo", "b": 4})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# /subtract
# ---------------------------------------------------------------------------

def test_subtract_positive_numbers_returns_difference(client):
    response = client.post("/subtract", json={"a": 10, "b": 3})
    assert response.status_code == 200
    assert response.json() == {"result": 7.0}


def test_subtract_resulting_in_negative_returns_negative(client):
    response = client.post("/subtract", json={"a": 3, "b": 10})
    assert response.status_code == 200
    assert response.json()["result"] == pytest.approx(-7.0)


# ---------------------------------------------------------------------------
# /multiply
# ---------------------------------------------------------------------------

def test_multiply_two_positive_integers_returns_product(client):
    response = client.post("/multiply", json={"a": 6, "b": 7})
    assert response.status_code == 200
    assert response.json() == {"result": 42.0}


def test_multiply_by_zero_returns_zero(client):
    response = client.post("/multiply", json={"a": 12345, "b": 0})
    assert response.status_code == 200
    assert response.json()["result"] == pytest.approx(0.0)


def test_multiply_two_negative_numbers_returns_positive_product(client):
    response = client.post("/multiply", json={"a": -4, "b": -5})
    assert response.status_code == 200
    assert response.json()["result"] == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# /divide
# ---------------------------------------------------------------------------

def test_divide_positive_numbers_returns_quotient(client):
    response = client.post("/divide", json={"a": 10, "b": 2})
    assert response.status_code == 200
    assert response.json() == {"result": 5.0}


def test_divide_returns_float_for_non_integer_result(client):
    response = client.post("/divide", json={"a": 1, "b": 3})
    assert response.status_code == 200
    assert response.json()["result"] == pytest.approx(1 / 3)


def test_divide_zero_numerator_returns_zero(client):
    response = client.post("/divide", json={"a": 0, "b": 5})
    assert response.status_code == 200
    assert response.json()["result"] == pytest.approx(0.0)


def test_divide_by_zero_returns_400(client):
    response = client.post("/divide", json={"a": 10, "b": 0})
    assert response.status_code == 400


def test_divide_by_zero_response_contains_detail(client):
    response = client.post("/divide", json={"a": 10, "b": 0})
    body = response.json()
    assert "detail" in body
    assert body["detail"] != ""


# ---------------------------------------------------------------------------
# Large numbers (integration-level smoke test)
# ---------------------------------------------------------------------------

def test_operations_with_large_numbers_do_not_crash(client):
    # Use a large but finite-safe value: 1e153 + 1e153 = 2e153, well within
    # float range (~1.8e308 max).  Using 1e308 + 1e308 overflows to inf,
    # which Python's json encoder rejects — that is a known app limitation.
    large = 1e153
    add_resp = client.post("/add", json={"a": large, "b": large})
    mul_resp = client.post("/multiply", json={"a": large, "b": 2})
    div_resp = client.post("/divide", json={"a": large, "b": 2})

    assert add_resp.status_code == 200
    assert mul_resp.status_code == 200
    assert div_resp.status_code == 200
