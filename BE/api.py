from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import json

from schema.api_schema import DomainRequest, ApiResponse
from services.scanner import run_domain_scan
from services.progress_manager import progress_manager
from core import config
import screenshot
from lookalike import reload_geoip_dbs
from services.geoip_service import geoip_updater_task

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("DEBUG: API Lifespan started")
    import asyncio
    updater = asyncio.create_task(geoip_updater_task())
    await screenshot.start_playwright()
    yield
    updater.cancel()
    await screenshot.stop_playwright()
    print("DEBUG: API Lifespan stopping")

app = FastAPI(
    title="Look-alike Domain Analyzer API",
    lifespan=lifespan
)

os.makedirs("screenshots", exist_ok=True)
app.mount("/screenshots", StaticFiles(directory="screenshots"), name="screenshots")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/progress")
async def ws_progress(ws: WebSocket):
    await progress_manager.websocket_handler(ws)

@app.get("/api/progress")
def get_progress():
    return progress_manager.get_snapshot()

@app.post("/api/cancel")
def cancel_check():
    progress_manager.cancel_flag = True
    return {"status": "cancelled"}

@app.post("/api/check-domain", response_model=ApiResponse)
async def check_domain(req: DomainRequest):
    if not req.domain.strip():
        raise HTTPException(status_code=400, detail="Domain is required")

    progress_manager.reset(status="Initializing scan...")
    try:
        results = await run_domain_scan(req.domain)
        
        # Log to file
        with open("check_domain_log.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)
            
        progress_manager.stop()
        return ApiResponse(**results)
    except Exception as e:
        progress_manager.stop()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
