# Comprehensive Guide to Google GenAI Library

This guide provides information-dense documentation to help LLMs effectively write code using the `google-genai` Python library for accessing Google's Gemini models via the Gemini Developer API.

## Table of Contents
- [Library Overview](#library-overview)
- [Installation & Setup](#installation--setup)
- [Client Configuration](#client-configuration)
- [Core Functionality](#core-functionality)
- [Function Calling](#function-calling)
- [Multimodal Capabilities](#multimodal-capabilities)
  - [Image Analysis](#image-analysis)
  - [Mixed Content](#mixed-content)
  - [Loading Images - Different Methods](#loading-images---different-methods)
  - [Image Generation & Editing with Gemini 2.0 Flash Experimental](#image-generation--editing-with-gemini-20-flash-experimental)
- [Advanced Features](#advanced-features)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Common Patterns](#common-patterns)
- [Limitations](#limitations)

## Library Overview

The `google-genai` library is Google's official Python SDK for accessing Gemini models through the Gemini Developer API (simpler setup, focused on developer experience). While the library also supports Vertex AI for enterprise use cases in Google Cloud, this guide focuses exclusively on the Gemini Developer API approach.

This library replaces the deprecated `google.generativeai` package, providing a more consistent interface with enhanced capabilities. Core abstractions include:

- `Client`: Main entry point for all operations
- `models`: Access to model configurations and generation
- `files`: File management for document processing
- `types`: Structured data types for configuration

## Installation & Setup

```bash
pip install google-genai
# Optional: For local environment variable management
pip install python-dotenv
```

**Requirements**:
- Python ≥3.9
- API key from Google AI Studio (https://makersuite.google.com/app/apikey)

## Client Configuration

### Basic Setup

```python
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

# Load API key from environment (recommended)
load_dotenv()  # Load from .env file
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Alternative: Direct API key configuration
client = genai.Client(api_key="YOUR_API_KEY")
```

### API Version Control

The SDK supports two API versions:
- `v1`: Stable API with production-ready features
- `v1alpha`: Preview API with experimental features

```python
from google import genai
from google.genai import types

client = genai.Client(
    api_key="YOUR_API_KEY",
    http_options=types.HttpOptions(
        api_version="v1"  # "v1" (stable) or "v1alpha" (preview)
    )
)
```

### Environment Variables

You can also configure the client using environment variables:

```bash
# Set in your .env file or shell environment
export GOOGLE_API_KEY='your-api-key'
```

```python
# Creates client using environment variables
client = genai.Client()  # Automatically uses GOOGLE_API_KEY
```

## Core Functionality

### Text Generation

```python
# Basic generation - using gemini-2.0-flash-001 as the default model
response = client.models.generate_content(
    model="gemini-2.0-flash-001",  # Default recommended model
    contents="Explain cloud computing in 3 paragraphs"
)
print(response.text)

# With generation parameters
response = client.models.generate_content(
    model="gemini-2.0-flash-001", 
    contents="Write a Python function that checks if a number is prime",
    config=types.GenerateContentConfig(
        temperature=0.2,  # Lower = more deterministic
        top_p=0.8,        # Controls diversity
        top_k=40,         # Controls randomness
        max_output_tokens=1024,  # Limit response length
        safety_settings={
            types.SafetyCategory.HARASSMENT: types.SafetySetting.BLOCK_MEDIUM_AND_ABOVE,
            types.SafetyCategory.HATE_SPEECH: types.SafetySetting.BLOCK_MEDIUM_AND_ABOVE
        }
    )
)
```

### Streaming Responses

```python
# Stream responses for a better user experience with long outputs
stream = client.models.generate_content_stream(
    model="gemini-2.0-flash-001",
    contents="Write a 500 word essay on sustainable energy",
)

for chunk in stream:
    if chunk.text:
        print(chunk.text, end="")
```

### Chat Conversations

```python
# Multi-turn conversations with memory
chat = client.models.start_chat(
    model="gemini-2.0-flash-001",
)

# First message
response = chat.send_message("Hello, can you help me understand JavaScript promises?")
print(response.text)

# Follow-up in the same conversation
response = chat.send_message("Show me a practical example with error handling")
print(response.text)
```

### Token Counting

```python
# Count tokens for cost estimation or context window management
tokens = client.models.count_tokens(
    model="gemini-2.0-flash-001",
    contents="How many tokens is this sentence?"
)
print(f"Token count: {tokens.token_count}")
```

## Function Calling

The `gemini-2.0-flash-001` model has excellent function calling capabilities, allowing your applications to integrate with external APIs and services.

### Automatic Function Execution (Simplest)

```python
def get_stock_price(ticker: str) -> float:
    """Get the current stock price for a given ticker symbol
    
    Args:
        ticker: Stock ticker symbol (e.g., GOOG, AAPL)
        
    Returns:
        Current stock price in USD
    """
    # Implementation would call a stock API
    prices = {"GOOG": 186.12, "AAPL": 174.26, "MSFT": 425.74}
    return prices.get(ticker.upper(), 0.0)

# Pass the Python function directly - automatic schema creation
response = client.models.generate_content(
    model="gemini-2.0-flash-001",
    contents="What's the current price of Google stock?",
    config=types.GenerateContentConfig(
        tools=[get_stock_price],  # Direct function passing
    )
)
print(response.text)  # Result includes function call results
```

### Manual Function Declaration (More Control)

```python
from google.genai import types

# Define function schema manually
weather_function = types.FunctionDeclaration(
    name="get_weather",
    description="Gets current weather for a location",
    parameters={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city and state or country"
            },
            "unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "Temperature unit"
            }
        },
        "required": ["location"]
    }
)

# Using with content generation
response = client.models.generate_content(
    model="gemini-2.0-flash-001",
    contents="What's the weather like in Tokyo right now?",
    config=types.GenerateContentConfig(
        tools=[types.Tool(function_declarations=[weather_function])]
    )
)

# Extract function call
if response.function_calls:
    function_call = response.function_calls[0]
    print(f"Function name: {function_call.name}")
    print(f"Arguments: {function_call.args}")
```

### Multiple Function Declarations

```python
def get_weather(location: str, unit: str = "celsius") -> dict:
    """Get current weather conditions for a location"""
    # Implementation would call a weather API
    return {"temp": 22, "conditions": "sunny", "unit": unit}

def get_population(city: str, country: str) -> int:
    """Get population of a city"""
    # Implementation would look up population data
    populations = {"tokyo,japan": 37_468_000, "delhi,india": 32_941_000}
    return populations.get(f"{city.lower()},{country.lower()}", 0)

# Simple multi-function setup - just pass the functions directly
response = client.models.generate_content(
    model="gemini-2.0-flash-001",
    contents="What's the population of Tokyo and what's the weather there?",
    config=types.GenerateContentConfig(
        tools=[get_weather, get_population],  # Multiple functions
    )
)
print(response.text)  # Results include both function calls
```

### Controlling Function Calling Behavior

```python
# Disable automatic function calling
response = client.models.generate_content(
    model="gemini-2.0-flash-001",
    contents="What's the weather in New York?",
    config=types.GenerateContentConfig(
        tools=[get_weather],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True  # Don't automatically execute
        )
    )
)

# Get function call information
if response.function_calls:
    call = response.function_calls[0]
    print(f"Function: {call.name}")
    print(f"Arguments: {call.args}")
    
    # Manual execution
    result = get_weather(**call.args)
    
    # Send result back to model
    function_response = types.Part.from_function_response(
        name=call.name,
        response={"result": result}
    )
    
    # Continue conversation with function result
    final_response = client.models.generate_content(
        model="gemini-2.0-flash-001",
        contents=[
            "What's the weather in New York?",
            function_response
        ]
    )
    print(final_response.text)
```

## Multimodal Capabilities

### Image Analysis

For vision tasks, use the vision-enabled version of the model:

```python
from PIL import Image
import io

# Load image from file
image = Image.open("diagram.jpg")

# Process image with text prompt
response = client.models.generate_content(
    model="gemini-2.0-flash-001-vision",  # Vision-specific model
    contents=[
        "Explain what this diagram shows in detail",
        types.ImagePart.from_image(image),
    ]
)
print(response.text)
```

### Mixed Content

```python
# Process multiple images and text
response = client.models.generate_content(
    model="gemini-2.0-flash-001-vision",
    contents=[
        "Compare and contrast these two products based on their images:",
        types.ImagePart.from_file("product1.jpg"),
        "Product 1 above, Product 2 below:",
        types.ImagePart.from_file("product2.jpg")
    ]
)
print(response.text)
```

### Loading Images - Different Methods

```python
# Method 1: From file path
response = client.models.generate_content(
    model="gemini-2.0-flash-001-vision",
    contents=[
        "What's in this image?",
        types.ImagePart.from_file("image.jpg")
    ]
)

# Method 2: From PIL Image object
from PIL import Image
img = Image.open("image.jpg")
response = client.models.generate_content(
    model="gemini-2.0-flash-001-vision",
    contents=[
        "What's in this image?",
        types.ImagePart.from_image(img)
    ]
)

# Method 3: From bytes
with open("image.jpg", "rb") as f:
    image_bytes = f.read()
response = client.models.generate_content(
    model="gemini-2.0-flash-001-vision",
    contents=[
        "What's in this image?",
        types.ImagePart.from_bytes(image_bytes, mime_type="image/jpeg")
    ]
)
```

### Image Generation & Editing with Gemini 2.0 Flash Experimental

The `gemini-2.0-flash-exp-image-generation` model supports generating text and inline images conversationally. This allows for tasks like generating blog posts with interwoven text and images or editing images based on textual instructions within a chat context.

**Note:** This is an experimental model. All generated images include a [SynthID watermark](https://ai.google.dev/responsible/docs/safeguards/synthid).

**Generating Text and Image Output:**

```python
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import base64
import os

# Assumes client is already configured with API key
# client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY")) 

contents = ('Hi, can you create a 3d rendered image of a pig '
            'with wings and a top hat flying over a happy '
            'futuristic scifi city with lots of greenery?')

response = client.models.generate_content(
    model="gemini-2.0-flash-exp-image-generation",
    contents=contents,
    config=types.GenerateContentConfig(
      # Specify that the response can include both Text and Image modalities
      response_modalities=[types.ResponseModality.TEXT, types.ResponseModality.IMAGE] 
    )
)

# Process the response parts
generated_text = ""
generated_image = None

for part in response.candidates[0].content.parts:
  if part.text is not None:
    generated_text += part.text
    print(f"Generated Text: {part.text}")
  elif part.inline_data is not None:
    # Handle image data (assuming one image for simplicity)
    if part.inline_data.mime_type.startswith('image/'):
        image_bytes = part.inline_data.data
        generated_image = Image.open(BytesIO(image_bytes))
        print(f"Generated Image received (MIME type: {part.inline_data.mime_type})")
        # Optionally save or display
        generated_image.save('gemini_generated_image.png')
        # generated_image.show() # Uncomment to display locally if environment supports it
```

**Image Editing with Gemini 2.0 Flash Experimental:**

You can provide an existing image along with text instructions to edit it.

```python
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import os

# Assumes client is already configured
# client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY")) 

# Load your image (replace with your image path)
try:
    input_image = Image.open("path/to/your/image.png") 
except FileNotFoundError:
    print("Error: Input image not found. Please provide a valid path.")
    # Handle error appropriately, maybe exit or use a placeholder
    input_image = None 

if input_image:
    text_input = 'Hi, This is a picture of me. Can you add a llama next to me?'

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp-image-generation",
        # Provide both text and image as input parts
        contents=[text_input, input_image], 
        config=types.GenerateContentConfig(
          response_modalities=[types.ResponseModality.TEXT, types.ResponseModality.IMAGE]
        )
    )

    # Process response (similar to generation example)
    edited_text = ""
    edited_image = None
    for part in response.candidates[0].content.parts:
      if part.text is not None:
        edited_text += part.text
        print(f"Response Text: {part.text}")
      elif part.inline_data is not None and part.inline_data.mime_type.startswith('image/'):
        image_bytes = part.inline_data.data
        edited_image = Image.open(BytesIO(image_bytes))
        print(f"Edited Image received (MIME type: {part.inline_data.mime_type})")
        edited_image.save('gemini_edited_image.png')
        # edited_image.show()
```

**Limitations:**
- Best performance with English, Spanish (Mexico), Japanese, Chinese (Simplified), Hindi.
- Does not support audio or video inputs.
- Image generation might not always trigger; explicit prompts ("generate an image") can help.
- The model might stop generating mid-way; retrying or rephrasing the prompt might be necessary.
- For adding text to images, generating text first and then asking for an image with that text often works best.

## Document Processing

The Gemini Developer API allows you to process various document formats including PDFs, Word documents, and text files.

```python
# Process PDF with text prompt
with open("report.pdf", "rb") as f:
    pdf_data = f.read()

# Upload file first (required for document processing)
pdf_file = client.files.upload(
    file=pdf_data,
    mime_type="application/pdf"
)

# Analyze PDF
response = client.models.generate_content(
    model="gemini-2.0-flash-001",
    contents=[
        "Extract the executive summary and key financial figures from this report",
        pdf_file,
    ]
)
print(response.text)

# Clean up file when done
client.files.delete(pdf_file.name)
```

For multi-document processing:

```python
# Upload multiple files
file1 = client.files.upload(file="document1.pdf")
file2 = client.files.upload(file="document2.pdf")

# Compare documents
response = client.models.generate_content(
    model="gemini-2.0-flash-001",
    contents=[
        "Compare these two documents and identify key differences",
        file1,
        file2
    ]
)
print(response.text)

# Clean up
client.files.delete(file1.name)
client.files.delete(file2.name)
```

## Structured Output

### JSON Response

`gemini-2.0-flash-001` excels at structured outputs like JSON:

```python
from pydantic import BaseModel, Field

class MovieReview(BaseModel):
    title: str
    year: int
    director: str
    rating: float = Field(ge=0, le=10)
    pros: list[str] 
    cons: list[str]

response = client.models.generate_content(
    model="gemini-2.0-flash-001",
    contents="Review the movie 'The Shawshank Redemption'",
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=MovieReview,
    )
)

# Parse JSON response
import json
review = json.loads(response.text)
print(f"Rating: {review['rating']}/10")
print(f"Director: {review['director']}")
for pro in review['pros']:
    print(f"- {pro}")
```

### Enum Responses for Classification

```python
from enum import Enum

class Sentiment(Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

response = client.models.generate_content(
    model="gemini-2.0-flash-001",
    contents="Classify the sentiment: 'I absolutely loved this product!'",
    config=types.GenerateContentConfig(
        response_mime_type="text/x.enum",
        response_schema=Sentiment,
    )
)
print(f"Sentiment: {response.text}")  # Output: "positive"
```

## Advanced Features

### Embedding Generation

```python
# Generate embeddings for text
embedding_response = client.models.get_model("text-embedding-004").embed_content(
    content="This is a sample text for embedding"
)
print(f"Embedding dimension: {len(embedding_response.embedding)}")

# Generate embeddings for multiple texts
embedding_responses = client.models.get_model("text-embedding-004").embed_content(
    content=[
        "First text to embed",
        "Second text to embed",
        "Third text to embed"
    ]
)
# Access individual embeddings
for i, embedding in enumerate(embedding_responses.embeddings):
    print(f"Embedding {i+1} dimension: {len(embedding.values)}")
```

### Batch Processing

```python
# Process multiple text prompts in parallel
batch_responses = client.models.batch_generate_content(
    model="gemini-2.0-flash-001",
    contents=[
        "Write a short poem about the ocean",
        "Explain quantum computing in simple terms",
        "List 5 healthy breakfast ideas"
    ]
)

for i, response in enumerate(batch_responses, 1):
    print(f"Response {i}:\n{response.text}\n")
```

### Content Caching

For frequently used document processing or content that doesn't change often:

```python
# Upload files first
file1 = client.files.upload(file="large_document.pdf")
file2 = client.files.upload(file="product_catalog.pdf")

# Create cached content
cached_content = client.caches.create(
    model="gemini-2.0-flash-001",
    config=types.CreateCachedContentConfig(
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=file1.uri, mime_type="application/pdf"
                    ),
                    types.Part.from_uri(
                        file_uri=file2.uri, mime_type="application/pdf"
                    ),
                ],
            )
        ],
        system_instruction="You are a product expert helping users find information.",
        display_name="product_knowledge_base",
        ttl="86400s",  # Cache for 24 hours
    ),
)

# Use cached content
response = client.models.generate_content(
    model="gemini-2.0-flash-001",
    contents="What products are available?",
    config=types.GenerateContentConfig(
        cached_content=cached_content.name,
    ),
)
print(response.text)
```

### Image Generation with Imagen 3

While Gemini 2.0 Flash Experimental offers conversational image generation/editing, the **Imagen 3** models (`imagen-3.0-generate-*`) are recommended when **image quality** is the top priority. They excel at photorealism, artistic detail, and specific styles.

```python
# Generate an image using Imagen 3
image_response = client.models.generate_images(
    model="imagen-3.0-generate-002",  # Example Imagen 3 model
    prompt="A photorealistic image of two fuzzy bunnies collaborating on cooking pasta in a sunlit kitchen.",
    config=types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio="16:9",
        output_mime_type="image/jpeg",
    )
)

# Show and save generated images
for i, generated_image_obj in enumerate(image_response.generated_images):
    # Access the image data directly from the nested structure
    image_data_bytes = generated_image_obj.image.image_bytes 
    image = Image.open(BytesIO(image_data_bytes))
    
    print(f"Displaying generated image {i+1}...")
    # image.show() # Uncomment to display locally if environment supports it
    
    save_path = f"imagen3_generated_image_{i+1}.png" # Save as PNG by default
    image.save(save_path) 
    print(f"Saved image {i+1} to {save_path}")

```

**Imagen 3 Parameters:**
- `numberOfImages`: 1 to 4 (default 4).
- `aspectRatio`: `"1:1"` (default), `"3:4"`, `"4:3"`, `"9:16"`, `"16:9"`.
- `personGeneration`: `"DONT_ALLOW"`, `"ALLOW_ADULT"` (default). Blocks children generation.

> Note: Using image generation models (Gemini 2.0 Flash Experimental or Imagen 3) may require specific API key permissions or project settings. Refer to the official Google AI documentation for details.

## Best Practices

### Effective Prompting for gemini-2.0-flash-001

```python
# Bad prompt (too vague)
bad_prompt = "Generate some Python code"

# Good prompt (specific, structured)
good_prompt = """
Generate a Python function that:
1. Takes a list of integers as input
2. Returns the sum of even numbers in the list
3. Includes error handling for non-integer inputs
4. Has clear docstrings and type hints
"""

# Using system instructions for consistent behavior
response = client.models.generate_content(
    model="gemini-2.0-flash-001",
    contents="Implement a function to find the nth Fibonacci number using memoization.",
    config=types.GenerateContentConfig(
        system_instruction="You are a Python coding assistant focused on efficient algorithms.",
    )
)
```

### Resource Management

```python
# Always use try/finally for file cleanup
try:
    # Upload file 
    file = client.files.upload(file="document.pdf")
    
    # Use file in multiple operations
    for prompt in ["Summarize this", "Extract key points", "Identify main themes"]:
        response = client.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=[prompt, file]
        )
        print(f"{prompt}: {response.text}\n")
        
finally:
    # Always clean up uploaded files to avoid storage charges
    if 'file' in locals() and file:
        client.files.delete(file.name)
```

### Error Handling and Retries

```python
import time
from google.genai import exceptions

# Production-ready request handling with retry logic
def generate_with_retry(prompt, max_attempts=3):
    attempt = 0
    while attempt < max_attempts:
        try:
            # Count tokens first to estimate cost and check limits
            token_count = client.models.count_tokens(
                model="gemini-2.0-flash-001", 
                contents=prompt
            ).token_count
            
            # Verify token count is within model limits
            if token_count > 30000:  
                return "Prompt too long - please reduce input size"
                
            # Generate with optimized parameters for gemini-2.0-flash-001
            return client.models.generate_content(
                model="gemini-2.0-flash-001",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,  # Lower temperature for consistency
                    max_output_tokens=2048  # Limit output size
                )
            ).text
            
        except exceptions.BlockedPromptException as e:
            return f"Content blocked: {e.message}"
        except exceptions.ApiConnectionError:
            # Network errors - use exponential backoff
            attempt += 1
            backoff = 2 ** attempt  # 2, 4, 8 seconds
            print(f"Connection error, retrying in {backoff} seconds...")
            time.sleep(backoff)  
        except exceptions.RateLimitError:
            # Rate limit reached - wait longer
            attempt += 1
            backoff = 5 ** attempt  # 5, 25, 125 seconds
            print(f"Rate limit reached, retrying in {backoff} seconds...")
            time.sleep(backoff)
            
    return "Failed after multiple attempts"
```

## Common Application Patterns

### RAG (Retrieval-Augmented Generation)

Use `gemini-2.0-flash-001` with embeddings for knowledge-based applications:

```python
def rag_with_gemini(query, documents):
    # Step 1: Generate embeddings for query
    query_embedding = client.models.get_model("text-embedding-004").embed_content(
        content=query
    ).embedding
    
    # Step 2: Find relevant documents (simplified)
    # In practice, use a vector database like Pinecone, Weaviate, etc.
    relevant_docs = find_relevant_documents(query_embedding, documents)
    
    # Step 3: Create context from relevant documents
    context = "\n\n".join(relevant_docs)
    
    # Step 4: Generate answer with context using gemini-2.0-flash-001
    response = client.models.generate_content(
        model="gemini-2.0-flash-001",
        contents="Answer this question based on the provided context only.",
        config=types.GenerateContentConfig(
            system_instruction=f"Context: {context}\nQuestion: {query}"
        )
    )
    
    return response.text
```

### Document Q&A Application

```python
def document_qa(file_path, question):
    # Upload document to Gemini API
    with open(file_path, "rb") as f:
        file_data = f.read()
    
    try:
        # Upload file
        file = client.files.upload(file=file_data)
        
        # Ask question about the document
        response = client.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=[
                f"Based on the document, {question}",
                file
            ]
        )
        
        return response.text
    finally:
        # Always clean up the file
        if 'file' in locals():
            client.files.delete(file.name)
```

### Conversational Agent with Tool Use

```python
def weather_and_calendar_assistant():
    def get_weather(location):
        # Stub implementation - would call a real weather API
        return {"temp": 75, "conditions": "sunny"}
    
    def check_calendar(date):
        # Stub implementation - would query user's calendar
        events = [
            {"time": "9:00 AM", "title": "Team meeting"},
            {"time": "2:00 PM", "title": "Client call"}
        ]
        return events
    
    # Start a chat session with the model
    chat = client.chats.create(model="gemini-2.0-flash-001")
    
    # Configure tools
    tools = [get_weather, check_calendar]
    
    # Chat loop
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit", "bye"]:
            break
            
        # Send message with tools available
        response = chat.send_message(
            user_input,
            config=types.GenerateContentConfig(
                tools=tools
            )
        )
        
        print(f"Assistant: {response.text}")
```

## Performance Tips for gemini-2.0-flash-001

### Optimal Generation Settings

```python
# Production-ready settings for gemini-2.0-flash-001
optimal_config = types.GenerateContentConfig(
    temperature=0.2,            # Lower for factual responses
    top_p=0.85,                 # Good balance of creativity vs determinism
    top_k=40,                   # Default is often good
    max_output_tokens=1024,     # Limit for cost efficiency
    candidate_count=1,          # Only need one response for most cases
    stop_sequences=[],          # Add custom stop sequences if needed
    safety_settings={
        types.SafetyCategory.HARASSMENT: types.SafetySetting.BLOCK_ONLY_HIGH,
        types.SafetyCategory.HATE_SPEECH: types.SafetySetting.BLOCK_ONLY_HIGH,
        types.SafetyCategory.SEXUALLY_EXPLICIT: types.SafetySetting.BLOCK_ONLY_HIGH,
        types.SafetyCategory.DANGEROUS_CONTENT: types.SafetySetting.BLOCK_ONLY_HIGH
    }
)

response = client.models.generate_content(
    model="gemini-2.0-flash-001",
    contents=prompt,
    config=optimal_config
)
```

### Cost Estimation

```python
def estimate_cost(prompt, expected_response_tokens=500):
    # Current pricing (as of 2025)
    input_rate = 0.00025  # $ per 1K tokens for gemini-2.0-flash
    output_rate = 0.0005  # $ per 1K tokens for gemini-2.0-flash
    
    # Count tokens
    token_count = client.models.count_tokens(
        model="gemini-2.0-flash-001",
        contents=prompt
    ).token_count
    
    # Calculate costs
    input_cost = (token_count / 1000) * input_rate
    output_cost = (expected_response_tokens / 1000) * output_rate
    total_cost = input_cost + output_cost
    
    return {
        "input_tokens": token_count,
        "output_tokens_estimate": expected_response_tokens,
        "input_cost": f"${input_cost:.6f}",
        "output_cost": f"${output_cost:.6f}",
        "total_cost": f"${total_cost:.6f}"
    }
```

## Security and Content Moderation

### Content Safety Filtering

Gemini models include built-in safety filtering, which can be adjusted:

```python
# Default safety settings block harmful content
response = client.models.generate_content(
    model="gemini-2.0-flash-001",
    contents="Write a story about a detective",
    config=types.GenerateContentConfig(
        safety_settings={
            # Available categories:
            types.SafetyCategory.HARM_CATEGORY_HARASSMENT: types.SafetySetting.BLOCK_MEDIUM_AND_ABOVE,
            types.SafetyCategory.HARM_CATEGORY_HATE_SPEECH: types.SafetySetting.BLOCK_MEDIUM_AND_ABOVE,
            types.SafetyCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: types.SafetySetting.BLOCK_MEDIUM_AND_ABOVE,
            types.SafetyCategory.HARM_CATEGORY_DANGEROUS_CONTENT: types.SafetySetting.BLOCK_MEDIUM_AND_ABOVE,
        }
    )
)
```

### Custom Content Moderation Function

```python
def moderate_user_input(text):
    """Pre-screen user inputs before sending to Gemini"""
    try:
        # Use a separate call to check content
        check = client.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=text,
            config=types.GenerateContentConfig(
                # Most restrictive settings
                safety_settings={
                    safety_cat: types.SafetySetting.BLOCK_LOW_AND_ABOVE
                    for safety_cat in types.SafetyCategory
                }
            )
        )
        # If we get here, content passed the strict filter
        return {"safe": True, "text": text}
    except exceptions.BlockedPromptException as e:
        # Content was blocked
        return {"safe": False, "reason": str(e)}
```

## Conclusion

This guide has covered the essential functionality of the `google-genai` library for working with the Gemini Developer API, using `gemini-2.0-flash-001` as the primary model. By following these best practices and examples, you'll be able to create robust applications that leverage Google's state-of-the-art generative AI models.

For the latest information, refer to the [official documentation](https://ai.google.dev/gemini-api/docs/models/gemini).
