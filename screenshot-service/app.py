import asyncio
import os
import time
from fastapi import FastAPI
from pydantic import BaseModel
from playwright.async_api import async_playwright, Browser, BrowserContext
from contextlib import asynccontextmanager

# ─── Playwright Globals ───────────────────────────────────────────────────────

_playwright_context = None
_browser: Browser = None
_context: BrowserContext = None
_semaphore = asyncio.Semaphore(5)

SCREENSHOTS_DIR = os.environ.get("SCREENSHOTS_DIR", "/app/screenshots")
SCREENSHOT_CACHE_TTL = max(int(os.environ.get("SCREENSHOT_CACHE_TTL", "21600")), 0)


async def start_playwright():
    global _playwright_context, _browser, _context
    print("DEBUG: Starting Playwright browser...")
    try:
        _playwright_context = await async_playwright().start()
        _browser = await _playwright_context.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        _context = await _browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            ignore_https_errors=True,
        )
        print("DEBUG: Playwright browser ready.")
    except Exception as e:
        print(f"DEBUG: Failed to start Playwright: {e}")


async def stop_playwright():
    global _playwright_context, _browser, _context
    print("DEBUG: Stopping Playwright browser...")
    if _context:
        await _context.close()
    if _browser:
        await _browser.close()
    if _playwright_context:
        await _playwright_context.stop()


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    await start_playwright()
    yield
    await stop_playwright()


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Screenshot Service",
    description="Playwright-based screenshot microservice.",
    version="1.0.0",
    lifespan=lifespan,
)


class ScreenshotRequest(BaseModel):
    domain: str


class ScreenshotResponse(BaseModel):
    url: str | None = None
    error: str | None = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

# @app.get("/health", tags=["Health"])
# async def health():
#     return {"status": "ok"}


@app.post("/screenshot", response_model=ScreenshotResponse, tags=["Screenshot"])
async def take_screenshot(req: ScreenshotRequest):
    """รับ domain แล้วให้ Playwright ถ่ายรูปหน้าเว็บ บันทึกลง shared volume"""
    domain = req.domain.strip()
    if not domain:
        return ScreenshotResponse(error="domain is required")

    result = await _capture_screenshot(domain)
    if result:
        return ScreenshotResponse(url=result)
    return ScreenshotResponse(error=f"Failed to capture screenshot for {domain}")


# ─── Core Capture Logic ───────────────────────────────────────────────────────

async def _capture_screenshot(domain: str) -> str | None:
    global _context
    if not _context:
        print("DEBUG: Playwright context is not initialized.")
        return None

    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    file_path = os.path.join(SCREENSHOTS_DIR, f"{domain}.png")
    public_path = f"/screenshots/{domain}.png"

    # Reuse recent captures when available so repeated scans do not reopen Chromium unnecessarily.
    if os.path.exists(file_path):
        try:
            if SCREENSHOT_CACHE_TTL == 0:
                return public_path
            file_age = max(time.time() - os.path.getmtime(file_path), 0)
            if file_age <= SCREENSHOT_CACHE_TTL:
                return public_path
        except Exception:
            pass

    async with _semaphore:
        page = None
        try:
            page = await _context.new_page()
            page.set_default_timeout(15000)

            url = f"http://{domain}"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            except Exception as e:
                print(
                    f"DEBUG: page.goto exception for {domain}, "
                    f"will attempt screenshot anyway: {str(e)[:100]}"
                )

            # รอ JS redirect / Cloudflare challenge สักครู่
            await page.wait_for_timeout(3000)

            await page.screenshot(path=file_path, type="png")
            return public_path

        except Exception as e:
            print(f"DEBUG: Playwright screenshot failed for {domain} - {str(e)[:100]}")
            return None
        finally:
            if page:
                await page.close()


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
