"""
test_live_models.py — Test which Live models support text response

Run: python test_live_models.py
"""

import asyncio
import os
import sys

# Django setup needed for settings
sys.path.insert(0, r'C:\Users\prasa\Desktop\PROJECTS\Agentic_automation\portfolio')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

from dotenv import load_dotenv
load_dotenv(r'C:\Users\prasa\Desktop\PROJECTS\Agentic_automation\portfolio\backend\.env')

from google import genai
from google.genai import types

GEMINI_KEY = os.getenv('GEMINI_API_KEY')

LIVE_MODELS = [
    'gemini-3.1-flash-live-preview',
    # 'gemini-3.5-live-translate-preview',
    'gemini-omni-flash-preview',
    'gemini-2.5-flash-native-audio-latest',
]

TEST_QUESTION = "What is 2 + 2? Reply in one sentence."


async def test_model(model: str) -> None:
    client = genai.Client(api_key=GEMINI_KEY)
    print(f"\n{'='*50}")
    print(f"Testing: {model}")
    print('='*50)

    # Test 1 — no modality specified
    for attempt, config in enumerate([
        None,                                                          # no config at all
        types.LiveConnectConfig(response_modalities=['TEXT']),         # explicit TEXT
        types.LiveConnectConfig(response_modalities=['AUDIO']),        # explicit AUDIO
    ], 1):
        label = ['no config', 'TEXT modality', 'AUDIO modality'][attempt - 1]
        try:
            kwargs = {'model': model}
            if config:
                kwargs['config'] = config

            async with client.aio.live.connect(**kwargs) as session:
                await session.send_client_content(
                    turns=types.Content(
                        role='user',
                        parts=[types.Part(text=TEST_QUESTION)],
                    ),
                    turn_complete=True,
                )

                text_received = ''
                audio_received = False

                async for msg in session.receive():
                    if msg.text:
                        text_received += msg.text
                    if hasattr(msg, 'data') and msg.data:
                        audio_received = True
                    # Stop after first meaningful response
                    if text_received or audio_received:
                        break

                if text_received:
                    print(f"  [{label}] ✅ TEXT works: {text_received[:80]}")
                elif audio_received:
                    print(f"  [{label}] 🔊 AUDIO only (no text)")
                else:
                    print(f"  [{label}] ❓ Connected but no response")

        except Exception as e:
            print(f"  [{label}] ❌ {e}")


async def main():
    for model in LIVE_MODELS:
        await test_model(model)
    print("\nDone.")


if __name__ == '__main__':
    asyncio.run(main())
