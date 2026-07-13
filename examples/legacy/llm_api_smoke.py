import os
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

response = requests.post(
    os.environ["BASE_URL"],
    headers={"Authorization": os.environ["API_KEY"], "Content-Type": "application/json"},
    json={
        "model": os.getenv("LLM_MODEL", "ep-20260630143153-fglld"),
        "messages": [{"role": "user", "content": "你好"}],
        "max_tokens": 50,
    },
    timeout=15,
)
print("status:", response.status_code)
if response.status_code == 200:
    print("reply:", response.json()["choices"][0]["message"]["content"][:50])
else:
    print("error:", response.text[:500])
