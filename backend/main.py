import asyncio
import json
import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scraper import AmazonScraper
from analyzer import InvoiceAnalyzer

app = FastAPI(title="Amazon Invoice Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_scrapers: dict[str, AmazonScraper] = {}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    scraper = AmazonScraper()
    session_id = str(id(websocket))
    _scrapers[session_id] = scraper

    try:
        raw = await websocket.receive_text()
        msg = json.loads(raw)

        if msg.get("type") == "start":
            await scraper.run(
                email=msg["email"],
                password=msg["password"],
                marketplace=msg.get("marketplace", "amazon.fr"),
                start_date=msg["start_date"],
                end_date=msg["end_date"],
                ws=websocket,
            )

        # Keep alive for OTP
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                msg = json.loads(raw)
                if msg.get("type") == "otp":
                    scraper.set_otp(msg["code"])
            except asyncio.TimeoutError:
                break

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_text(
                json.dumps({"type": "error", "message": str(exc)}))
        except Exception:
            pass
    finally:
        _scrapers.pop(session_id, None)


class AnalyzeOrdersRequest(BaseModel):
    orders: list[dict]


@app.post("/api/analyze-orders")
async def analyze_orders(req: AnalyzeOrdersRequest):
    """Analyze orders already scraped (no PDF needed)."""
    analyzer = InvoiceAnalyzer()
    return analyzer.analyze_orders(req.orders)


# Legacy PDF analysis endpoint kept for manual use
class AnalyzeRequest(BaseModel):
    download_path: str


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    analyzer = InvoiceAnalyzer()
    return analyzer.analyze(req.download_path)


@app.get("/api/browse")
def browse(path: str = Query(default="")):
    target = Path(path) if path else Path.home()
    if not target.exists() or not target.is_dir():
        return {"error": "Dossier introuvable", "path": str(target), "dirs": [], "parent": None}
    try:
        dirs = sorted(
            [{"name": d.name, "path": str(d)} for d in target.iterdir()
             if d.is_dir() and not d.name.startswith('.')],
            key=lambda x: x["name"].lower(),
        )
    except PermissionError:
        dirs = []
    parent = str(target.parent) if target.parent != target else None
    return {"path": str(target), "parent": parent, "dirs": dirs}


class MkdirRequest(BaseModel):
    path: str
    name: str


@app.post("/api/mkdir")
def mkdir(req: MkdirRequest):
    new_dir = Path(req.path) / req.name
    try:
        new_dir.mkdir(parents=True, exist_ok=True)
        return {"path": str(new_dir), "ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@app.get("/api/health")
async def health():
    return {"status": "ok"}
