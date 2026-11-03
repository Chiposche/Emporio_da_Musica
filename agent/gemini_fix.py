from google import genai
client = genai.Client()
resp = client.interactions.create(model="gemini-3.8-flash", input="Quais violões?")
print(resp.output_text)
