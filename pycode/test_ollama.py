import urllib.request
from urllib.error import URLError, HTTPError
import os
from dotenv import load_dotenv

# Load your .env file
load_dotenv("src/.env")

url = os.getenv("OLLAMA_BASE_URL")
print(f"Testing connection to: {url}")

if not url:
    print(":x: OLLAMA_BASE_URL is not set in src/.env")
    exit()

# Construct the health endpoint
health_endpoint = f"{url.rstrip('/')}/api/version"
print(f"Probe Endpoint: {health_endpoint}")

req = urllib.request.Request(
    health_endpoint,
    headers={
        "ngrok-skip-browser-warning": "true",
        "User-Agent": "IntelliWrite-Test-Probe"
    }
)

try:
    with urllib.request.urlopen(req, timeout=10) as response:
        print(f":white_check_mark: Success! Status Code: {response.status}")
        print(f"Response: {response.read().decode('utf-8')}")
except HTTPError as e:
    print(f":x: HTTP Error: {e.code} - {e.reason}")
    print(f"Headers: {e.headers}")
except URLError as e:
    print(f":x: Connection Error: {e.reason}")
except Exception as e:
    print(f":x: Unexpected Error: {e}")
