import re

_DOMAIN_RE = re.compile(r"^[a-z0-9.-]+$", re.IGNORECASE)

def is_valid_hostname(host: str) -> bool:
    host = (host or "").strip().lower()
    if not host or len(host) > 253:
        return False
    if host.startswith(".") or host.endswith(".") or ".." in host:
        return False
    if not _DOMAIN_RE.match(host):
        return False
    labels = host.split(".")
    if len(labels) < 2:
        return False
    for lbl in labels:
        if not (1 <= len(lbl) <= 63):
            return False
        if lbl.startswith("-") or lbl.endswith("-"):
            return False
    return True
