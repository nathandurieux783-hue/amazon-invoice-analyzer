import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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

# One active scraper per WebSocket session
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
                download_path=msg["download_path"],
                ws=websocket,
            )

        elif msg.get("type") == "otp":
            scraper.set_otp(msg["code"])

        # Keep connection alive to receive OTP if needed
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


class AnalyzeRequest(BaseModel):
    download_path: str


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    analyzer = InvoiceAnalyzer()
    result = analyzer.analyze(req.download_path)
    return result


@app.get("/api/health")
async def health():
    return {"status": "ok"}
