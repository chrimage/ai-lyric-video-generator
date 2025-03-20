from google import genai

client = genai.Client(api_key="GEMINI_API_KEY")

chat = client.chats.create(model="gemini-2.0-flash")
response = chat.send_message("I have 2 dogs in my house.")
print(response.text)
response = chat.send_message("How many paws are in my house?")
print(response.text)
for message in chat._curated_history:
    print(f'role - {message.role}' end=": ")
    print(message.parts[0].text)