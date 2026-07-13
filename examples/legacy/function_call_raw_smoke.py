import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

tools = [
    {
        "type": "function",
        "function": {
            "name": "Query_Weather",
            "description": "查询指定城市的天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"},
                    "date": {"type": "string", "description": "日期"},
                },
                "required": ["city"],
            },
        },
    }
]

# Legacy NLU service used raw JSON payloads in this path.
response = requests.post(
    os.environ["BASE_URL"],
    headers={"Authorization": os.environ["API_KEY"], "Content-Type": "application/json"},
    data=json.dumps(
        {
            "model": os.getenv("LLM_MODEL", "ep-20260630143153-fglld"),
            "messages": [{"role": "user", "content": "北京明天天气怎么样"}],
            "tools": tools,
            "temperature": 1e-6,
            "top_p": 0,
        },
        ensure_ascii=False,
    ),
    timeout=15,
)
print("status:", response.status_code)
body = json.loads(response.content.decode("utf-8"))
print("keys:", list(body.keys()))
if "choices" in body:
    message = body["choices"][0]["message"]
    print("tool_calls:", message.get("tool_calls"))
else:
    print("ERROR:", json.dumps(body, ensure_ascii=False)[:300])
