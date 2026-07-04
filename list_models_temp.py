from google import genai

client = genai.Client(api_key="AQ.Ab8RN6Kj1rwIkpJpP3bjnCIVdOPb2Hv4_yaOX9k-79N8LbB4cw")

for m in client.models.list():
    print(m.name)
