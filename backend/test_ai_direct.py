import asyncio
from app.services.ai_service import AIService

async def test():
    ai = AIService()
    result = ''
    msgs = [
        {'role': 'system', 'content': 'You are a data visualization expert. Output only JSON.'},
        {'role': 'user', 'content': 'XRD chart: 2theta vs intensity'}
    ]
    async for chunk in ai.chat(msgs, stream=False, temperature=0.3):
        result += chunk
    print('LEN:', len(result))
    print('RESULT:', repr(result[:500]))
    print('IS JSON:', result.strip().startswith('{'))

asyncio.run(test())