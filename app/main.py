from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.calculator import add, subtract, multiply, divide

app = FastAPI()

app.mount("/static", StaticFiles(directory="frontend"), name="static")


class CalcRequest(BaseModel):
    a: float
    b: float


@app.get("/health")
def health():
    return {"status": "ok", "app": "calculator-monolith"}


@app.post("/add")
def route_add(req: CalcRequest):
    return {"result": add(req.a, req.b)}


@app.post("/subtract")
def route_subtract(req: CalcRequest):
    return {"result": subtract(req.a, req.b)}


@app.post("/multiply")
def route_multiply(req: CalcRequest):
    return {"result": multiply(req.a, req.b)}


@app.post("/divide")
def route_divide(req: CalcRequest):
    try:
        return {"result": divide(req.a, req.b)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
