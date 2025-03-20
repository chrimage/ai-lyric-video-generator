from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

client = genai.Client()

contents = ('Hi, can you create a 3d rendered image of a pig '
            'with wings and a top hat flying over a happy ' 
            'futuristic scifi city with lots of greenery?')

response = client.models.generate_content(
    model="models/gemini-2.0-flash-exp",
    contents=contents,
    config=types.GenerateContentConfig(response_modalities=['Text', 'Image'])
)

for part in response.candidates[0].content.parts:
  if part.text is not None:
    print(part.text)
  elif part.inline_data is not None:
    image = Image.open(BytesIO(part.inline_data.data))
    image.show()