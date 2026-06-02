import httpx
import json
import sys

url = "http://localhost:18000/api/agent/task"
payload = {"task": "hello, please respond briefly"}

print(f"POST {url}")
print(f"Payload: {json.dumps(payload)}")
print("-" * 60)

with httpx.stream("POST", url, json=payload, timeout=120.0) as response:
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    print("-" * 60)
    
    for line in response.iter_lines():
        if not line.strip():
            continue
        if line.startswith("event: "):
            event_type = line[7:]
            print(f"[EVENT] {event_type}", end=" ")
        elif line.startswith("data: "):
            data_str = line[6:]
            try:
                data = json.loads(data_str)
                if data.get("type") == "thinking":
                    print(f"=> {data.get('content', '')[:60]}")
                elif data.get("type") == "answer":
                    print(f"=> {data.get('content', '')[:80]}")
                elif data.get("type") == "error":
                    print(f"=> ERROR: {data.get('content', '')[:80]}")
                elif data.get("type") == "meta":
                    print(f"=> conversation_id={data.get('conversation_id', '')}")
                else:
                    print(f"=> {json.dumps(data, ensure_ascii=False)[:80]}")
            except json.JSONDecodeError:
                print(f"=> raw: {data_str[:60]}")
        else:
            print(f"[LINE] {line[:80]}")

print("-" * 60)
print("SSE stream ended")
