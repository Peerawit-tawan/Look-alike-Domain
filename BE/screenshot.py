"""
screenshot.py — HTTP client wrapper สำหรับเรียก screenshot-service
แทนที่ Playwright ที่เคยรันอยู่ใน process เดียวกับ Backend
"""
import os
import httpx
import asyncio

SCREENSHOT_SERVICE_URL = os.environ.get(
    # Default to localhost for local dev runs.
    # In Docker, docker-compose overrides this to http://screenshot-service:8001
    "SCREENSHOT_SERVICE_URL",
    "http://127.0.0.1:8001",
)

# Limit concurrent HTTP calls to screenshot-service to avoid overload bursts.
_SCREENSHOT_HTTP_SEM = asyncio.Semaphore(
    int(os.environ.get("SCREENSHOT_HTTP_CONCURRENCY", "10"))
)

# ─── No-op lifecycle functions (kept for API compatibility) ──────────────────

async def start_playwright():
    """No-op: Playwright ย้ายไปอยู่ใน screenshot-service แล้ว"""
    print("DEBUG: screenshot.py → using screenshot-service (no local Playwright)")


async def stop_playwright():
    """No-op: Playwright ย้ายไปอยู่ใน screenshot-service แล้ว"""
    pass


# ─── Capture via HTTP ────────────────────────────────────────────────────────

async def capture_screenshot(domain: str, output_dir: str = "screenshots") -> str | None:
    """
    ส่งคำขอ POST ไปหา screenshot-service แล้วรับ URL ของรูปภาพกลับมา
    `output_dir` ยังรับพารามิเตอร์เดิมไว้เพื่อความ compatible แต่ไม่ได้ใช้ที่นี่
    """
    url = f"{SCREENSHOT_SERVICE_URL}/screenshot"
    try:
        timeout = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0)
        async with _SCREENSHOT_HTTP_SEM:
            async with httpx.AsyncClient(timeout=timeout) as client:
                # One light retry helps with transient connect resets/timeouts.
                for attempt in (1, 2):
                    try:
                        resp = await client.post(url, json={"domain": domain})
                        resp.raise_for_status()
                        data = resp.json()
                        result = data.get("url")
                        if result:
                            return result
                        print(
                            f"DEBUG: screenshot-service error for {domain} "
                            f"(url={url}): {data.get('error')}"
                        )
                        return None
                    except Exception:
                        if attempt == 2:
                            raise
                        await asyncio.sleep(0.25)
    except httpx.HTTPStatusError as e:
        print(f"DEBUG: screenshot-service HTTP error for {domain}: {e}")
        return None
    except Exception as e:
        msg = str(e).strip() or repr(e)
        print(
            f"DEBUG: screenshot-service unreachable for {domain} "
            f"(url={url}): {msg[:160]}"
        )
        return None
