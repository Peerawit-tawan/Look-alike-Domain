import os
import re
import idna
import socket
import ssl
import requests
import concurrent.futures
import urllib3
import whois
import dns.resolver
import time
import maxminddb
from dataclasses import dataclass
import urllib.parse
from ddgs import DDGS

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
LOG_ENRICH_TIMING = os.environ.get("LOG_ENRICH_TIMING", "0") == "1"
ENABLE_WHOIS = os.environ.get("ENABLE_WHOIS", "0").strip().lower() in {"1", "true", "yes", "on"}
DDG_QUERY_DELAY = max(float(os.environ.get("DDG_QUERY_DELAY", "0.1")), 0.0)

def make_base_result(domain: str):
    return {
        "domain": domain,
        "page_title": None,
        "dns_a": [],
        "dns_aaaa": [],
        "dns_cname": [],
        "dns_ns": [],
        "dns_mx": [],
        "ip_info": [],
        "http_status": None,
        "https_status": None,
        "ssl_info": None,
        "whois_info": None
    }


def to_request_domain(domain: str) -> str:
    try:
        return idna.encode(domain).decode()
    except Exception:
        return domain


def build_resolver():
    resolver = dns.resolver.Resolver()
    resolver.timeout = 2.0
    resolver.lifetime = 2.0
    resolver.nameservers = ['8.8.8.8', '1.1.1.1']
    return resolver


def check_domain_dns_only(domain: str):
    result = make_base_result(domain)
    request_domain = to_request_domain(domain)
    resolver = build_resolver()

    try:
        answers = resolver.resolve(request_domain, "A")
        result["dns_a"] = [rdata.to_text() for rdata in answers]
    except Exception:
        return result

    return result


GLOBAL_GEOIP_CITY = None
GLOBAL_GEOIP_ASN = None

def reload_geoip_dbs():
    global GLOBAL_GEOIP_CITY, GLOBAL_GEOIP_ASN
    if GLOBAL_GEOIP_CITY is not None:
        try:
            GLOBAL_GEOIP_CITY.close()
        except:
            pass
        GLOBAL_GEOIP_CITY = None
    if GLOBAL_GEOIP_ASN is not None:
        try:
            GLOBAL_GEOIP_ASN.close()
        except:
            pass
        GLOBAL_GEOIP_ASN = None

def get_global_geoip_db():
    global GLOBAL_GEOIP_CITY, GLOBAL_GEOIP_ASN
    if GLOBAL_GEOIP_CITY is None or GLOBAL_GEOIP_ASN is None:
        geoip_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "GeoIP")
        city_db_path = os.path.join(geoip_dir, "GeoLite2-City.mmdb")
        asn_db_path = os.path.join(geoip_dir, "GeoLite2-ASN.mmdb")
        
        if os.path.exists(city_db_path):
            GLOBAL_GEOIP_CITY = maxminddb.open_database(city_db_path)
        if os.path.exists(asn_db_path):
            GLOBAL_GEOIP_ASN = maxminddb.open_database(asn_db_path)
            
    return GLOBAL_GEOIP_CITY, GLOBAL_GEOIP_ASN


def classify_asn(org_name: str) -> str:
    org_lower = org_name.lower()
    datacenter_keywords = [
        "cloud", "hosting", "host", "datacenter", "data center", "digitalocean",
        "amazon", "google", "microsoft", "hetzner", "ovh", "linode", "alibaba",
        "tencent", "fastly", "cloudflare", "akamai", "incapsula", "sucuri", "vps", "compute", "azure", "ocean"
    ]
    for kw in datacenter_keywords:
        if kw in org_lower:
            return "company"
    return "isp"


def query_geoip_offline(ip: str) -> dict:
    city_db, asn_db = get_global_geoip_db()
    
    country = "Unknown"
    state = ""
    city = ""
    org_name = "Unknown ISP"
    asn_num = ""
    
    try:
        if city_db:
            city_data = city_db.get(ip)
            if city_data:
                if 'country' in city_data and 'names' in city_data['country']:
                    country = city_data['country']['names'].get('en', 'Unknown')
                if country == "Unknown" and 'registered_country' in city_data and 'names' in city_data['registered_country']:
                    country = city_data['registered_country']['names'].get('en', 'Unknown')
                
                if 'subdivisions' in city_data and len(city_data['subdivisions']) > 0:
                    state_name = city_data['subdivisions'][0].get('names', {}).get('en')
                    if state_name:
                        state = f" - {state_name}"
                        
                if 'city' in city_data and 'names' in city_data['city']:
                    city_name = city_data['city']['names'].get('en')
                    if city_name:
                        city = f" - {city_name}"
                
        if asn_db:
            asn_data = asn_db.get(ip)
            if asn_data:
                org_name = asn_data.get('autonomous_system_organization', 'Unknown ISP')
                asn_num = asn_data.get('autonomous_system_number', '')
                
        asn_str = f"AS{asn_num}"
                
        return {
            "ip": ip,
            "location": f"{country}{state}{city} - {org_name}",
            "asn": asn_str,
            "asn_type": classify_asn(org_name)
        }
    except Exception:
        return {
            "ip": ip,
            "location": "No GeoIP data",
            "asn": "",
            "asn_type": "unknown"
        }


def fetch_page_title(url: str) -> str | None:
    try:
        resp = requests.get(url, timeout=3, allow_redirects=True, verify=False)
        if resp.status_code == 200:
            match = re.search(r'(?i)<title[^>]*>(.*?)</title>', resp.text, re.DOTALL)
            if match:
                t = re.sub(r'\s+', ' ', match.group(1)).strip()
                return t[:100] + '...' if len(t) > 100 else t
    except Exception:
        pass
    return None

def enrich_domain_details(result: dict):
    domain = result["domain"]
    # ตัด path ทิ้งเฉพาะตอนสแกน DNS, SSL, และ Whois
    host_only = domain.split('/')[0].split('?')[0]
    request_domain = to_request_domain(host_only)
    
    t_start = time.time()
    
    def fetch_dns():
        resolver = build_resolver()
        dns_res = {"dns_aaaa": [], "dns_cname": [], "dns_ns": [], "dns_mx": []}
        try:
            answers_aaaa = resolver.resolve(request_domain, "AAAA")
            dns_res["dns_aaaa"] = [rdata.to_text() for rdata in answers_aaaa]
        except Exception: pass

        try:
            answers_cname = resolver.resolve(request_domain, "CNAME")
            dns_res["dns_cname"] = [rdata.target.to_text().rstrip(".") for rdata in answers_cname]
        except Exception: pass

        try:
            answers_ns = resolver.resolve(request_domain, "NS")
            dns_res["dns_ns"] = [rdata.target.to_text().rstrip(".") for rdata in answers_ns]
        except Exception: pass

        try:
            answers_mx = resolver.resolve(request_domain, "MX")
            dns_res["dns_mx"] = [f"{rdata.preference} {rdata.exchange.to_text().rstrip('.')}" for rdata in answers_mx]
        except Exception: pass
        return dns_res

    def fetch_http():
        try:
            resp = requests.get(f"http://{domain}", timeout=3, allow_redirects=True)
            title = None
            status = resp.status_code
            use_www = False
            if status == 200:
                match = re.search(r'(?i)<title[^>]*>(.*?)</title>', resp.text, re.DOTALL)
                if match:
                    t = re.sub(r'\s+', ' ', match.group(1)).strip()
                    title = t[:100] + '...' if len(t) > 100 else t
            
            if status != 200 and not domain.startswith("www."):
                try:
                    resp_www = requests.get(f"http://www.{domain}", timeout=3, allow_redirects=True)
                    if resp_www.status_code == 200:
                        status = resp_www.status_code
                        use_www = True
                        match = re.search(r'(?i)<title[^>]*>(.*?)</title>', resp_www.text, re.DOTALL)
                        if match:
                            t = re.sub(r'\s+', ' ', match.group(1)).strip()
                            title = t[:100] + '...' if len(t) > 100 else t
                except Exception:
                    pass
                    
            return {"status": status, "title": title, "use_www": use_www}
        except Exception: return {"status": None, "title": None, "use_www": False}

    def fetch_https():
        try:
            resp = requests.get(f"https://{domain}", timeout=3, allow_redirects=True, verify=False)
            title = None
            status = resp.status_code
            use_www = False
            if status == 200:
                match = re.search(r'(?i)<title[^>]*>(.*?)</title>', resp.text, re.DOTALL)
                if match:
                    t = re.sub(r'\s+', ' ', match.group(1)).strip()
                    title = t[:100] + '...' if len(t) > 100 else t
                    
            if status != 200 and not domain.startswith("www."):
                try:
                    resp_www = requests.get(f"https://www.{domain}", timeout=3, allow_redirects=True, verify=False)
                    if resp_www.status_code == 200:
                        status = resp_www.status_code
                        use_www = True
                        match = re.search(r'(?i)<title[^>]*>(.*?)</title>', resp_www.text, re.DOTALL)
                        if match:
                            t = re.sub(r'\s+', ' ', match.group(1)).strip()
                            title = t[:100] + '...' if len(t) > 100 else t
                except Exception:
                    pass
                    
            return {"status": status, "title": title, "use_www": use_www}
        except Exception: return {"status": None, "title": None, "use_www": False}

    def fetch_ssl():
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((request_domain, 443), timeout=3) as sock:
                with ctx.wrap_socket(sock, server_hostname=request_domain) as ssock:
                    cert = ssock.getpeercert(binary_form=False)
                    if cert:
                        issuer_info = dict(x[0] for x in cert.get('issuer', []))
                        subject_info = dict(x[0] for x in cert.get('subject', []))
                        issuer_name = issuer_info.get('organizationName', issuer_info.get('commonName', 'Unknown'))
                        subj_name = subject_info.get('commonName', 'Unknown')
                        return f"Issuer: {issuer_name} | Subject: {subj_name}"
            return None
        except ssl.SSLCertVerificationError:
            return "Invalid, Expired, or Untrusted Certificate"
        except Exception: return None

    def fetch_whois():
        try:
            from dateutil import parser as dateutil_parser
            w = whois.whois(request_domain)
            registrar = w.registrar if w.registrar else "Unknown"

            def normalize_date(val):
                """แปลงวันที่ให้เป็น YYYY-MM-DD ไม่ว่าจะรูปแบบไหน"""
                if not val or val == "None":
                    return "None"
                # ถ้าเป็น datetime object อยู่แล้ว
                if hasattr(val, 'strftime'):
                    return val.strftime("%Y-%m-%d")
                # ถ้าเป็น string ให้ลอง parse ด้วย dateutil
                try:
                    return dateutil_parser.parse(str(val), dayfirst=True).strftime("%Y-%m-%d")
                except Exception:
                    return str(val).strip()

            def extract_date(field):
                """ดึงวันที่จาก whois object"""
                if field:
                    d = field[0] if isinstance(field, list) else field
                    return normalize_date(d)
                return "None"

            def regex_date(pattern):
                """fallback ดึงวันที่จากข้อความดิบ แล้ว normalize ให้ด้วย"""
                if hasattr(w, 'text') and w.text:
                    match = re.search(rf'(?i){pattern}\s*:\s*([^\n\r]+)', w.text)
                    if match:
                        raw = match.group(1).strip()
                        return normalize_date(raw)
                return "None"

            creation_str = extract_date(w.creation_date)
            if creation_str == "None":
                creation_str = regex_date(r'(?:created|creation)\s*date')

            updated_str = extract_date(w.updated_date)
            if updated_str == "None":
                updated_str = regex_date(r'(?:updated|last\s*updated)\s*date')

            # รองรับทั้ง "Exp date:", "Expiry date:", "Expiration date:"
            expiry_str = extract_date(w.expiration_date)
            if expiry_str == "None":
                expiry_str = regex_date(r'(?:exp|expir(?:y|ation|es))\s*date')

            if registrar == "Unknown" and hasattr(w, 'text') and w.text:
                match_reg = re.search(r'(?i)registrar\s*:\s*([^\n\r]+)', w.text)
                if match_reg:
                    registrar = match_reg.group(1).strip()

            return f"Registrar: {registrar} | Created: {creation_str} | Updated: {updated_str} | Expires: {expiry_str}"
        except Exception: return None

    # ยิง 5 งานนี้พร้อมกันหมดเลย
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
    f_dns = executor.submit(fetch_dns)
    f_http = executor.submit(fetch_http)
    f_https = executor.submit(fetch_https)
    f_ssl = executor.submit(fetch_ssl)
    f_whois = executor.submit(fetch_whois) if ENABLE_WHOIS else None

    # กั้นเวลาตายตัวให้ทั้งหมดเสร็จภายใน 4 วินาที (ไม่บวกทบกัน)
    futures = [f_dns, f_http, f_https, f_ssl]
    if f_whois is not None:
        futures.append(f_whois)
    concurrent.futures.wait(
        futures,
        timeout=10.0,
        return_when=concurrent.futures.ALL_COMPLETED
    )

    # ดึงค่าเฉพาะ Thread ที่ทำงานเสร็จทันเวลา
    if f_dns.done() and not f_dns.exception():
        result.update(f_dns.result())
    
    if f_http.done() and not f_http.exception():
        http_res = f_http.result()
        if http_res:
            result["http_status"] = http_res["status"]
            if http_res.get("use_www"):
                result["screenshot_domain"] = "www." + domain
            if http_res["title"] and not result.get("page_title"):
                result["page_title"] = http_res["title"]
        
    if f_https.done() and not f_https.exception():
        https_res = f_https.result()
        if https_res:
            result["https_status"] = https_res["status"]
            if https_res.get("use_www"):
                result["screenshot_domain"] = "www." + domain
            if https_res["title"]:
                result["page_title"] = https_res["title"]
        
    if f_ssl.done() and not f_ssl.exception():
        result["ssl_info"] = f_ssl.result()
        
    if f_whois is not None and f_whois.done() and not f_whois.exception():
        whois_res = f_whois.result()
        if whois_res: 
            result["whois_info"] = whois_res
            
    # สั่งปิด ThreadPool โดยไม่รอ
    executor.shutdown(wait=False, cancel_futures=True)

    t_end = time.time()
    if LOG_ENRICH_TIMING:
        print(f"   [Enrich-Parallel] {domain} -> Time taken: {t_end-t_start:.2f}s")
    
    return result


def check_domain_status(domain: str) -> dict:
    """
    ฟังก์ชันหลักสำหรับเช็คสถานะ domain ครบทุกด้าน:
    DNS (A, AAAA, CNAME, NS, MX), IP info, HTTP/HTTPS status, SSL, WHOIS
    """
    t_start = time.time()
    result = check_domain_dns_only(domain)
    t_dns_a = time.time()

    if result["dns_a"]:
        result["ip_info"] = [query_geoip_offline(ip) for ip in result["dns_a"]]
        result = enrich_domain_details(result)
        
    t_end = time.time()
    
    # พิมพ์เวลาที่ใช้ของแต่ละโดเมน
    if result["dns_a"]:
        print(f"[Timer] {domain} -> DNS_A: {t_dns_a - t_start:.2f}s | Enrich: {t_end - t_dns_a:.2f}s | Total: {t_end - t_start:.2f}s")
    else:
        # ถ้าไม่มี dns_a แปลว่าโดเมนไม่พบบนโลก จะมีแค่การเช็ค DNS A
        pass

    return result


def get_hostname_from_url(url: str, domain: str, allowed_hosts: set = None) -> str | None:
    """
    ดึง Hostname จาก URL และตรวจสอบว่าเป็น Subdomain ของ Domain ที่ระบุหรือไม่
    หรือถ้าตรงกับรายการ fuzzer domains (allowed_hosts) ก็ดึงมาด้วย
    """
    if allowed_hosts is None:
        allowed_hosts = set()
        
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname
        if not host:
            return None
            
        host = host.lower()
        if host.endswith("."):
            host = host[:-1]
            
        if host == domain or host.endswith(f".{domain}") or host in allowed_hosts:
            return host
            
    except Exception as e:
        return None
        
    return None


def find_subdomains_duckduckgo(domain: str, allowed_hosts: set = None) -> list[str]:
    domain = domain.lower().strip()
    found_subdomains = set()

    # ❗ ตัด query ที่ useless ออก
    queries = [
        f"site:{domain}",
        f'"{domain}" -www',
    ]

    # ✅ เพิ่ม keyword ช่วย
    keywords = ["api", "login"]

    try:
        with DDGS() as ddgs:
            for query in queries:
                for kw in keywords:
                    full_query = f"{query} {kw}"

                    try:
                        results = None
                        for bld in ["lite", "html"]:  # ❗ ตัด api ออก (พังบ่อย)
                            try:
                                results = ddgs.text(full_query, max_results=20, backend=bld)
                                if results:
                                    break
                            except:
                                continue

                        if not results:
                            continue

                        for r in results:
                            url = (
                                r.get("href")
                                or r.get("url")
                                or r.get("link")  # ✅ รองรับ field เพิ่ม
                            )

                            if not url:
                                continue

                            host = get_hostname_from_url(url, domain, allowed_hosts)
                            if host:
                                found_subdomains.add(host)

                    except Exception as e:
                        continue

                    if DDG_QUERY_DELAY:
                        time.sleep(DDG_QUERY_DELAY)

    except Exception as e:
        print(f"[!] DuckDuckGo error: {e}")

    return list(found_subdomains)


def find_subdomains_crtsh(domain: str) -> list[str]:
    """
    ค้นหา Subdomain ที่มีอยู่จริงจากฐานข้อมูล Certificate Transparency (crt.sh) แบบเจาะลึกสุดๆ
    """
    domain = domain.lower().strip()
    found_subdomains = set()
    try:
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        # เพิ่ม headers เลียนแบบ Browser เพื่อป้องกันการถูกบล็อก
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, timeout=10, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            for entry in data:
                name_value = entry.get('name_value', '')
                for name in name_value.split('\n'):
                    name = name.strip().lower()
                    if name.endswith(f".{domain}") and '*' not in name:
                        found_subdomains.add(name)
    except Exception as e:
        print(f"[!] crt.sh search error: {e}")
        
    return list(found_subdomains)


if __name__ == "__main__":

    user_input = input("Enter domain: ").strip()

    dictionary_words = ["login", "secure", "shop", "bank"]
    tlds = ["net", "org", "info", "co", "io", "co.uk", "com"]

    try:
        results = generate_similar_domains(
            input_domain=user_input,
            dictionary=dictionary_words,
            tld_dictionary=tlds
        )

        print(f"\nDomain: {user_input}")
        print(f"Total domain generate: {len(results)} items\n")
        print("Check DNS / HTTP / SSL...\n")

        domains_to_check = [item["domain"] for item in results]

        # STEP 1: เช็ค DNS A ก่อนทั้งหมด
        active_results = []
        inactive_domains = []
        all_unique_ips = set()

        dns_workers = 20
        with concurrent.futures.ThreadPoolExecutor(max_workers=dns_workers) as executor:
            dns_results = list(executor.map(check_domain_dns_only, domains_to_check))

        for res in dns_results:
            if res["dns_a"]:
                active_results.append(res)
                all_unique_ips.update(res["dns_a"])
            else:
                inactive_domains.append(res)

        # STEP 2: โหลดข้อมูล GeoIP และค้นหาข้อมูล IP
        print("Loading GeoIP database for local lookup...")

        ip_cache = {}
        unique_ips = list(all_unique_ips)

        for ip in unique_ips:
            ip_cache[ip] = query_geoip_offline(ip)

        # STEP 3: ใส่ ip_info กลับเข้าแต่ละโดเมน
        for res in active_results:
            res["ip_info"] = [
                ip_cache.get(ip, {"ip": ip, "location": "No GeoIP data", "asn": ""})
                for ip in res["dns_a"]
            ]

        # STEP 4: enrich รายละเอียดของ active domains
        enriched_active_domains = []
        detail_workers = 20

        with concurrent.futures.ThreadPoolExecutor(max_workers=detail_workers) as executor:
            future_to_domain = {
                executor.submit(enrich_domain_details, res): res["domain"]
                for res in active_results
            }

            for future in concurrent.futures.as_completed(future_to_domain):
                res = future.result()
                enriched_active_domains.append(res)

                print(f"[ACTIVE] {res['domain']}")
                if res["ip_info"]:
                    for info in res["ip_info"]:
                        print(f"   IP Address: {info['ip']}")
                        print(f"   IP Location: {info['location']}")
                        if info['asn']:
                            print(f"   ASN: {info['asn']}")
                        print("   ---")
                else:
                    print(f"   IPs: {', '.join(res['dns_a'])}")

                print(f"   HTTP: {res['http_status']}")
                print(f"   HTTPS: {res['https_status']}")

                if res["ssl_info"]:
                    print(f"   SSL: {res['ssl_info']}")
                if res["whois_info"]:
                    print(f"   WHOIS: {res['whois_info']}")
                if res["dns_ns"]:
                    print(f"   NS: {', '.join(res['dns_ns'])}")
                if res["dns_mx"]:
                    print(f"   MX: {', '.join(res['dns_mx'])}")

                print("-" * 50)

        for res in inactive_domains:
            print(f"[INACTIVE] {res['domain']}")
            print("-" * 50)

        print(f"\nActive Domain: {len(enriched_active_domains)} items")
        print(f"Inactive Domain: {len(inactive_domains)} items")
        print(f"Unique IP checked: {len(unique_ips)} items")

    except Exception as e:
        print("error:", e)
