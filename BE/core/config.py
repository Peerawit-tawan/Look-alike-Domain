import os

def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}

# Tuning knobs
DOMAIN_WORKERS = int(os.environ.get("DOMAIN_WORKERS", "40"))
DNS_CONCURRENCY = int(os.environ.get("DNS_CONCURRENCY", "20"))
ENRICH_WORKERS = int(os.environ.get("ENRICH_WORKERS", "5"))
MAX_DOMAINS = int(os.environ.get("MAX_DOMAINS", "0"))
MAX_RESPONSE_ACTIVE = int(os.environ.get("MAX_RESPONSE_ACTIVE", "0"))
MAX_RESPONSE_INACTIVE = int(os.environ.get("MAX_RESPONSE_INACTIVE", "0"))
FULL_ACTIVE_DETAIL_LIMIT = int(os.environ.get("FULL_ACTIVE_DETAIL_LIMIT", "0"))
ACTIVE_SCREENSHOT_LIMIT = int(os.environ.get("ACTIVE_SCREENSHOT_LIMIT", "0"))

# Feature flags
ENABLE_SUBDOMAIN_SEARCH = _env_flag("ENABLE_SUBDOMAIN_SEARCH", False)
CAPTURE_INPUT_SCREENSHOT = _env_flag("CAPTURE_INPUT_SCREENSHOT", False)

# Microservices
SCREENSHOT_SERVICE_URL = os.environ.get("SCREENSHOT_SERVICE_URL", "http://127.0.0.1:8001")
SCREENSHOT_HTTP_CONCURRENCY = int(os.environ.get("SCREENSHOT_HTTP_CONCURRENCY", "10"))

# App Settings
DICTIONARY_WORDS = ["login", "secure", "shop", "bank"]
TLDS = ["net", "org", "info", "co", "io", "co.uk", "com", "co.th"]
