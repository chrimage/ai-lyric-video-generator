from google import genai

client = genai.Client(api_key='GEMINI_API_KEY', http_options={'api_version':'v1alpha'})

response = client.models.generate_content(
    model='gemini-2.0-flash-thinking-exp',
    contents='Explain how RLHF works in simple terms.',
)

print(response.text)
