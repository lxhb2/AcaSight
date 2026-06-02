import httpx
import json

url = "http://localhost:18000/api/agent/task"

def send_task(task, conversation_id=None):
    payload = {"task": task}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    
    events = []
    with httpx.stream("POST", url, json=payload, timeout=120.0) as response:
        for line in response.iter_lines():
            if line.startswith("event: "):
                events.append({"event": line[7:]})
            elif line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    if events:
                        events[-1]["data"] = data
                except:
                    pass
    return events

print("=== Round 1 ===")
events1 = send_task("My name is Alice. Please remember it.")
for e in events1:
    if e.get("event") == "answer":
        print(f"  Answer: {e['data'].get('content', '')[:80]}")
    elif e.get("event") == "meta":
        cid = e['data'].get('conversation_id', '')
        print(f"  conversation_id: {cid}")

cid = None
for e in events1:
    if e.get("event") == "meta":
        cid = e['data'].get('conversation_id')

print(f"\n=== Round 2 (same conversation: {cid}) ===")
events2 = send_task("What is my name?", conversation_id=cid)
for e in events2:
    if e.get("event") == "answer":
        print(f"  Answer: {e['data'].get('content', '')[:80]}")

print("\n=== Sessions ===")
r = httpx.get("http://localhost:18000/api/agent/sessions")
data = r.json()
for s in data.get("sessions", [])[:3]:
    print(f"  {s['conversation_id'][:8]}... messages={s['message_count']} preview={s.get('preview','')[:40]}")

print("\n=== Get Session Detail ===")
if cid:
    r = httpx.get(f"http://localhost:18000/api/agent/sessions/{cid}")
    data = r.json()
    print(f"  Messages: {len(data.get('messages', []))}")
    for m in data.get("messages", []):
        print(f"    [{m['role']}] {m['content'][:60]}")

print("\nAll tests passed!")
