"""
test_gemma.py — Quick test of gemma-4-31b-it for document Q&A
Run: python test_gemma.py
"""

import os
from dotenv import load_dotenv

load_dotenv(r'C:\Users\prasa\Desktop\PROJECTS\Agentic_automation\portfolio\backend\.env')

from google import genai

GEMINI_KEY = os.getenv('GEMINI_API_KEY')
client     = genai.Client(api_key=GEMINI_KEY)

CONTEXT = """
Document: Sample Resume
Sections:
  - Personal Info: Satya Vani, Technical Recruiter at KYNEA Solutions
  - Experience: 5 years recruiting for tech roles
  - Skills: Talent acquisition, ATS systems, technical screening
"""

QUESTION = "Who is the technical recruiter at KYNEA Solutions?"

prompt = f"""You are a document assistant. Answer based only on the context below.

CONTEXT:
{CONTEXT}

QUESTION: {QUESTION}"""

print(f"Testing: gemma-4-31b-it")
print(f"Question: {QUESTION}\n")

try:
    response = client.models.generate_content_stream(
        model='gemma-4-31b-it',
        contents=prompt,
    )
    print("Response: ", end='', flush=True)
    for chunk in response:
        if chunk.text:
            print(chunk.text, end='', flush=True)
    print("\n\nStreaming works ✅")
except Exception as e:
    print(f"❌ Error: {e}")
