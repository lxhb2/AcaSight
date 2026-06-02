import httpx, json, uuid, asyncio, base64

async def main():
    async with httpx.AsyncClient(timeout=15) as c:
        # List tools
        payload = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": "tools/list"}
        r = await c.post("http://127.0.0.1:23120/mcp", json=payload)
        data = r.json()
        tools = data.get("result", {}).get("tools", [])
        print("=== TOOLS ===")
        for t in tools:
            name = t.get("name", "")
            desc = (t.get("description", "") or "")[:100]
            print(f"  {name}: {desc}")
        print()

        # Get collections to find items
        payload = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": "tools/call", "params": {"name": "get_collections", "arguments": {"mode": "standard"}}}
        r = await c.post("http://127.0.0.1:23120/mcp", json=payload)
        data = r.json()
        result = data.get("result", {})
        content = result.get("content", [{}])
        text = ""
        for ci in content:
            if ci.get("type") == "text":
                text = ci.get("text", "")
        collections = json.loads(text) if text else []
        if collections and len(collections) > 0:
            first_col = collections[0]
            col_key = first_col.get("key") or first_col.get("collectionKey") or first_col.get("data", {}).get("key")
            print(f"Collection: {first_col.get('name', '?')} key={col_key}")

            # Get items from this collection
            payload = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": "tools/call", "params": {"name": "get_collection_items", "arguments": {"collectionKey": col_key, "limit": 5}}}
            r = await c.post("http://127.0.0.1:23120/mcp", json=payload)
            data = r.json()
            result = data.get("result", {})
            content = result.get("content", [{}])
            text = ""
            for ci in content:
                if ci.get("type") == "text":
                    text = ci.get("text", "")
            items = json.loads(text) if text else []
            if isinstance(items, dict):
                items = items.get("results", items.get("items", []))
            print(f"  Items found: {len(items) if isinstance(items, list) else 'not a list'}")
            if isinstance(items, list) and len(items) > 0:
                for item in items[:3]:
                    if isinstance(item, dic