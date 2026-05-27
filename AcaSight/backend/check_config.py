from app.services.ai_service import load_ai_config
config = load_ai_config()
print("Default provider:", config.get("default_provider"))
print("Default model:", config.get("default_model"))
for name, pconf in config.get("providers", {}).items():
    has_key = bool(pconf.get("api_key", ""))
    print(f"  {name}: enabled={pconf.get('enabled')}, has_key={has_key}, base_url={pconf.get('base_url', '')[:50]}")
