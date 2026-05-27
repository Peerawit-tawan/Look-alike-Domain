# Look-alike Domain Analyzer

ระบบวิเคราะห์โดเมนที่มีลักษณะคล้ายโดเมนต้นทาง เพื่อช่วยตรวจสอบความเสี่ยงจากโดเมนปลอม, phishing, typosquatting และโดเมนที่อาจถูกใช้เลียนแบบแบรนด์หรือบริการจริง

ผู้ใช้สามารถกรอกโดเมนเป้าหมาย เช่น `example.com` แล้วระบบจะสร้างรายการโดเมนที่คล้ายกัน ตรวจสอบว่าโดเมนใด active หรือ inactive และแสดงข้อมูลประกอบ เช่น DNS, HTTP/HTTPS status, SSL, WHOIS, GeoIP, ASN และภาพ screenshot ของหน้าเว็บ

## ฟีเจอร์หลัก

- สร้างโดเมนที่คล้ายกับโดเมนต้นทางด้วยเทคนิค fuzzing หลายรูปแบบ เช่น homoglyph, insertion, omission, replacement, transposition, hyphenation, bitsquatting, dictionary และ TLD swap
- ตรวจสอบสถานะโดเมนด้วย DNS lookup และแยกผลลัพธ์เป็น active / inactive domains
- ดึงข้อมูลเชิงเทคนิคของโดเมน เช่น A record, AAAA, CNAME, NS, MX, HTTP/HTTPS status, SSL certificate และ WHOIS
- วิเคราะห์ IP ด้วย GeoIP และ ASN เพื่อดูประเทศ เมือง ผู้ให้บริการ หรือกลุ่ม infrastructure ที่เกี่ยวข้อง
- ค้นหา subdomain เพิ่มเติมผ่าน DuckDuckGo search
- ถ่าย screenshot เว็บไซต์ด้วย Playwright เพื่อช่วยตรวจสอบหน้าตาเว็บจริง
- มีหน้า dashboard สำหรับค้นหา สแกน ดูผลลัพธ์ และเปิดภาพ preview
- รองรับ progress ผ่าน WebSocket และสามารถ cancel งาน scan ได้
- รันทั้งระบบได้ด้วย Docker Compose

## โครงสร้างโปรเจกต์

```text
.
|-- BE/                    # FastAPI backend สำหรับ scan domain และ expose API
|-- FE/my-app/             # Next.js frontend dashboard
|-- lookalike_fuzzer/      # Python package สำหรับสร้าง look-alike domains
|-- screenshot-service/    # FastAPI + Playwright service สำหรับถ่าย screenshot
|-- docker-compose.yml     # รวม backend, frontend และ screenshot service
`-- README.md
```

## เทคโนโลยีที่ใช้

### Frontend

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4
- Flowbite / Flowbite React
- React Icons

### Backend

- Python 3.11
- FastAPI
- Uvicorn
- Pydantic
- dnspython / aiodns สำหรับ DNS lookup
- requests / httpx สำหรับ HTTP checks
- python-whois สำหรับ WHOIS
- MaxMind GeoIP database สำหรับ IP intelligence
- ddgs / duckduckgo-search สำหรับค้นหา subdomain

### Screenshot Service

- FastAPI
- Playwright
- Chromium headless browser

### DevOps

- Docker
- Docker Compose
- pnpm

## การทำงานโดยรวม

1. ผู้ใช้กรอกโดเมนในหน้าเว็บ
2. Frontend เรียก `POST /api/check-domain` ไปที่ backend
3. Backend ส่งโดเมนเข้า `lookalike_fuzzer` เพื่อสร้างโดเมนที่คล้ายกัน
4. ระบบตรวจ DNS และแยกโดเมนเป็น active / inactive
5. สำหรับโดเมนที่ active ระบบ enrich ข้อมูลเพิ่ม เช่น HTTP, HTTPS, SSL, WHOIS, GeoIP และ ASN
6. Screenshot service ใช้ Playwright ถ่ายภาพหน้าเว็บของโดเมนที่ตรวจพบ
7. Frontend แสดงผลเป็น dashboard พร้อม progress และตัวกรองผลลัพธ์

## วิธีรันด้วย Docker Compose

ต้องมี Docker และ Docker Compose ติดตั้งไว้ก่อน

```bash
docker compose up --build
```

หลังจาก container ทำงานแล้ว เปิดใช้งานได้ที่:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Screenshot service: `http://localhost:8001`

## วิธีรันแบบ Local Development

### Backend

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r BE/requirements.txt
pip install -e lookalike_fuzzer
cd BE
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### Screenshot Service

เปิด terminal อีกหน้าหนึ่ง

```powershell
cd screenshot-service
pip install -r requirements.txt
playwright install chromium
uvicorn app:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend

เปิด terminal อีกหน้าหนึ่ง

```powershell
cd FE/my-app
pnpm install
pnpm dev
```

จากนั้นเปิด `http://localhost:3000`

## API หลัก

### `POST /api/check-domain`

ใช้สำหรับเริ่ม scan โดเมน

```json
{
  "domain": "example.com"
}
```

### `GET /api/progress`

ดูสถานะ progress ล่าสุดของงาน scan

### `WebSocket /ws/progress`

รับ progress แบบ real-time

### `POST /api/cancel`

สั่งยกเลิกงาน scan ที่กำลังทำงานอยู่

## การตั้งค่า

ค่าหลักสามารถปรับผ่าน environment variables ใน `docker-compose.yml` เช่น:

- `DOMAIN_WORKERS` จำนวน worker สำหรับ scan domain
- `DNS_CONCURRENCY` จำนวน DNS query พร้อมกัน
- `ENRICH_WORKERS` จำนวน worker สำหรับ enrich ข้อมูล domain
- `MAX_DOMAINS` จำกัดจำนวนโดเมนที่จะ scan
- `ENABLE_SUBDOMAIN_SEARCH` เปิด/ปิดการค้นหา subdomain
- `ENABLE_WHOIS` เปิด/ปิดการดึง WHOIS
- `CAPTURE_INPUT_SCREENSHOT` เปิด/ปิดการถ่าย screenshot ของโดเมนต้นทาง
- `ACTIVE_SCREENSHOT_LIMIT` จำกัดจำนวน active domains ที่จะถ่าย screenshot
- `SCREENSHOT_SERVICE_URL` URL ของ screenshot service

## GeoIP และข้อมูลลับ

โปรเจกต์นี้รองรับ MaxMind GeoIP database สำหรับแสดงข้อมูล location และ ASN ของ IP address โดยไฟล์ฐานข้อมูลควรอยู่ใน `BE/GeoIP/`

ห้าม commit ค่า secret เช่น MaxMind license key, API key, token หรือ password ขึ้น GitHub ควรเก็บไว้ใน `.env` หรือ config ส่วนตัว และใส่ placeholder ในไฟล์ตัวอย่างแทน

## หมายเหตุ

โปรเจกต์นี้เหมาะสำหรับงาน security awareness, brand monitoring และการตรวจสอบโดเมนที่อาจเลียนแบบระบบจริง ควรใช้งานกับโดเมนที่คุณมีสิทธิ์ตรวจสอบหรือเพื่อวัตถุประสงค์ด้านความปลอดภัยที่ถูกต้องเท่านั้น
