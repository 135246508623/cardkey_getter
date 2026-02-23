import re
import random
import base64
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from .config import BASE_TELEMETRY

def generate_telemetry(variation=0.1):
    telemetry = {}
    for key, value in BASE_TELEMETRY.items():
        factor = 1 + random.uniform(-variation, variation)
        telemetry[key] = value * factor
    telemetry["dwellMs"] = int(telemetry["dwellMs"])
    telemetry["moves"] = int(telemetry["moves"])
    telemetry["directionChanges"] = int(telemetry["directionChanges"])
    telemetry["keypresses"] = 0
    telemetry["speedSamples"] = telemetry["moves"]
    return telemetry

def generate_fingerprint():
    return "-" + ''.join(random.choices("0123456789abcdef", k=8))

def decode_base64_url(raw_url):
    parsed = urlparse(raw_url)
    if parsed.path.endswith('/a') or 'a?' in raw_url:
        query = parse_qs(parsed.query)
        if 'd' in query:
            d_param = query['d'][0]
            try:
                decoded = base64.b64decode(d_param).decode('utf-8')
                if decoded.startswith('http'):
                    return decoded
                else:
                    return f"{parsed.scheme}://{parsed.netloc}{decoded}"
            except Exception:
                pass
    return raw_url

def extract_card_key(html):
    soup = BeautifulSoup(html, 'html.parser')
    selectors = [
        '#card-key', '.voucher-code', 'pre', 'code',
        'div[class*="card"]', 'p[class*="key"]', 'span[class*="code"]'
    ]
    for selector in selectors:
        elem = soup.select_one(selector)
        if elem:
            return elem.get_text(strip=True)
    match = re.search(r'[A-Z0-9]{16}', html)
    if match:
        return match.group()
    return None
