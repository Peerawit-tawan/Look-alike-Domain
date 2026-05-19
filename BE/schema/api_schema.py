from pydantic import BaseModel
from typing import List, Optional

class TextRequest(BaseModel):
    text: str
    fuzzers: Optional[List[str]] = None

class DomainRequest(BaseModel):
    domain: str

class DomainResult(BaseModel):
    domain: str
    page_title: Optional[str] = None
    dns_a: List[str]
    dns_aaaa: List[str] = []
    dns_cname: List[str] = []
    dns_ns: List[str] = []
    dns_mx: List[str] = []
    ip_info: List[dict]
    http_status: Optional[int]
    https_status: Optional[int]
    ssl_info: Optional[str]
    whois_info: Optional[str]
    screenshot_url: Optional[str] = None
    # Optional fields to make debugging at scale easier.
    # Frontend can ignore these safely.
    error_type: Optional[str] = None
    error_detail: Optional[str] = None
    dns_error: Optional[str] = None
    screenshot_error: Optional[str] = None

class ApiResponse(BaseModel):
    input_domain: str
    input_domain_title: Optional[str] = None
    input_domain_screenshot: Optional[str] = None
    total_generated: int
    active_count: int
    inactive_count: int
    active_domains: List[DomainResult]
    inactive_domains: List[DomainResult]
