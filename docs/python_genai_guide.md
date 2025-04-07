# Guide to Using the Google AI Python SDK (`google-genai`) for LLMs

This guide provides essential information for generating Python code using the Google AI Python SDK (installed via the `google-genai` package). It focuses on core concepts, common patterns, and key components for the **Gemini Developer API**, based on official documentation like [https://googleapis.github.io/python-genai/](https://googleapis.github.io/python-genai/) and the [Python Quickstart](https://ai.google.dev/gemini-api/docs/quickstart?lang=python).

**Note:** This guide aims to reflect current best practices for the Gemini Developer API. Vertex AI usage involves different initialization and features not covered here. Always refer to the official documentation for the latest features and API details.

---

## **IMPORTANT NOTE: Installation (`google-genai`) vs. Import (`google.genai`)**

*   **Installation:** You install the SDK using pip with the package name `google-genai`.
    ```bash
    pip install -q -U google-genai
    ```
*   **Import:** In your Python code, you import the library using `google.genai`.
    ```python
    from google import genai
    from google.genai import types # Often needed for configuration
    ```
*   **Legacy Confusion:** There was an older library sometimes referred to as `google-generativeai`. The current, recommended SDK is installed via `google-genai` and imported as `google.genai`.
*   **Why Referencing Documentation is CRUCIAL:** Your training data might contain examples using older patterns or incorrect import statements. **Always prioritize patterns and examples shown in the official Google AI documentation** over patterns recalled from training data.

---

## Installation

Using Python 3.9+, install the SDK package using pip:

```bash
pip install -q -U google-genai
```

---

## Core Concepts

### 1. Client Initialization (Gemini Developer API)

The primary entry point is `genai.Client`. For the Gemini Developer API, initialization requires an API key obtained from [Google AI Studio](https://aistudio.google.com/app/apikey).

*   **Direct API Key:**
    ```python
    from google import genai

    # Replace with your actual API key
    client = genai.Client(api_key="YOUR_API_KEY")
    ```
*   **Using Environment Variable (Recommended):** Set the `GOOGLE_API_KEY` environment variable. The client will automatically pick it up.
    ```bash
    # In your terminal or environment configuration
    export GOOGLE_API_KEY='YOUR_API_KEY'
    ```
    ```python
    # Python code
    from google import genai
    import os
    # Ensure the variable is set before initializing
    # Consider using a library like python-dotenv to load from a .env file
    # from dotenv import load_dotenv
    # load_dotenv()
    client = genai.Client()
    ```
    *(**Best Practice:** Use environment variables, potentially loaded from a `.env` file using libraries like `python-dotenv`, to avoid hardcoding keys in your source code.)*

### 2. Asynchronous Client

For non-blocking operations (using `async`/`await`), access the async client via the `.aio` property:
```python
async_client = client.aio
# Now use async methods, e.g., await async_client.models.generate_content(...)
```

### 3. API Version Selection (Optional)

By default, the SDK uses the beta API endpoints. You can explicitly select a different version (e.g., `v1beta` or `v1alpha` if available) using `http_options`:
```python
from google.genai import types

client = genai.Client(
    api_key='YOUR_API_KEY',
    http_options=types.HttpOptions(api_version='v1beta') # Or 'v1alpha' etc.
)
```

### 4. Service Modules

Functionality is organized into modules accessible via the client instance (e.g., `client.models`, `client.chats`). Key modules for the Gemini API include:

*   `client.models`: Core interactions like text/image/video generation, embedding, token counting.
*   `client.chats`: Managing conversational interactions.
*   `client.files`: Uploading, downloading, and managing files for use with models.
*   `client.operations`: Managing long-running operations.
*   `client.live`: (Experimental) Real-time interaction sessions.

### 5. Input/Output Structure (`Content` and `Part`)

Input (`contents`) and output (`candidates[].content`) use a structured format defined in `google.genai.types`.

*   `Content`: Represents a single message turn (e.g., a user prompt or a model response). Contains a `role` (`'user'`, `'model'`, or `'tool'`) and a list of `parts`.
    *   Helper classes `types.UserContent` and `types.ModelContent` set the role automatically.
*   `Part`: Represents a piece of data within a `Content` object. Can be text, inline data (bytes + mime_type), file data (URI + mime_type from `client.files`), function calls/responses, etc.
    *   Use helper methods like `Part.from_text()`, `Part.from_uri()`, `Part.from_data()`, `Part.from_function_call()`, `Part.from_function_response()`.
    *   Multimodal input involves multiple `Part` objects within a single `Content`.

**Structuring the `contents` Argument:**

The SDK intelligently converts various input formats for the `contents` argument into the canonical `list[types.Content]` format.

*   **`str`:** Assumes a single text part from the 'user'.
    ```python
    contents = "Why is the sky blue?"
    # Becomes: [types.UserContent(parts=[Part.from_text("Why is the sky blue?")])]
    ```
*   **`list[str]`:** Assumes multiple text parts within a single 'user' `Content`.
    ```python
    contents = ["Why is the sky blue?", "Why is the cloud white?"]
    # Becomes: [types.UserContent(parts=[Part.from_text("..."), Part.from_text("...")])]
    ```
*   **`types.Part` (non-function call):** Assumes a single part in a 'user' `Content`.
    ```python
    # Assuming 'image_part' is Part.from_data(...) or Part.from_uri(...)
    contents = image_part
    # Becomes: [types.UserContent(parts=[image_part])]
    ```
*   **`list[types.Part]` (non-function call):** Assumes multiple parts within a single 'user' `Content`.
    ```python
    contents = [Part.from_text("Describe this:"), image_part]
    # Becomes: [types.UserContent(parts=[Part.from_text("..."), image_part])]
    ```
*   **`types.Part` (function call/response):** Assumes a single part in a 'model' or 'tool' `Content`.
    ```python
    contents = Part.from_function_call(...)
    # Becomes: [types.ModelContent(parts=[Part.from_function_call(...)])]

    contents = Part.from_function_response(...)
    # Becomes: [types.Content(role='tool', parts=[Part.from_function_response(...)])]
    ```
*   **`types.Content`:** Wrapped in a list if a single instance is provided.
    ```python
    contents = types.UserContent(parts=[...])
    # Becomes: [types.UserContent(parts=[...])]
    ```
*   **`list[types.Content]`:** Used directly (canonical format). This is required for multi-turn history.
    ```python
    contents = [
        types.UserContent(parts=[Part.from_text("Hello")]),
        types.ModelContent(parts=[Part.from_text("Hi there!")]),
        types.UserContent(parts=[Part.from_text("How are you?")])
    ]
    ```
*   **Mixed List:** Can contain `str`, `Part`, `Content`. The SDK groups consecutive compatible parts into appropriate `Content` objects.

### 6. Configuration Objects (`types` module)

Behavior is controlled via configuration objects passed to methods (often in a `config` dictionary or object parameter). Key examples:

*   `types.GenerationConfig`: Controls generation parameters (temperature, top_k, top_p, max_output_tokens, stop_sequences, safety_settings, tools, tool_config, response_mime_type, response_schema, etc.).
*   `types.SafetySetting`: Defines thresholds for blocking harmful content (`category`, `threshold`).
*   `types.Tool`: Defines tools the model can use (Function Declarations, Google Search Retrieval).
*   `types.FunctionDeclaration`: Defines a function the model can call (name, description, parameters schema). Can be generated from Python functions.
*   `types.EmbedContentConfig`: Configures embedding requests (task_type, title, output_dimensionality).
*   `types.HttpOptions`: Overrides HTTP client settings (timeout, headers, api_version).

---

## Choosing the Right Gemini Model

While Google offers several Gemini models, choosing the right one can significantly impact performance and cost. Here's a guide based on current offerings (as of early 2025):

*   **`gemini-2.0-flash` (Recommended Default):**
    *   **Use Case:** The best starting point for most common tasks. Offers a great balance of speed, capability, and cost-efficiency.
    *   **Strengths:** Strong performance across various tasks, significantly cheaper than Pro models, 1 million token context window. Generally outperforms the older `gemini-1.5-flash`.
    *   **Consider if:** You need a reliable and affordable model for general-purpose generation, summarization, chat, etc.

*   **`gemini-2.5-pro-exp` (Highest Capability):**
    *   **Use Case:** Tasks requiring maximum intelligence, complex reasoning, advanced coding, or nuanced understanding.
    *   **Strengths:** State-of-the-art performance, excels at difficult benchmarks. Currently has a 1 million token context window (expected to increase to 2 million).
    *   **Consider if:** Performance is paramount and budget allows. Be aware it's experimental and likely more expensive.

*   **`gemini-1.5-pro` (Largest Context Window):**
    *   **Use Case:** *Specifically* when you need to process extremely long inputs (documents, conversations, codebases).
    *   **Strengths:** Massive **2 million token context window**. Solid performance, though potentially slower and less capable than 2.5 Pro for tasks *within* a 1M token limit.
    *   **Consider if:** Your primary bottleneck is the context window size. For tasks fitting within 1M tokens, `gemini-2.0-flash` or `gemini-2.5-pro-exp` are often better choices.

*   **`gemini-1.5-flash` (Generally Avoid):**
    *   **Use Case:** Largely superseded by `gemini-2.0-flash`.
    *   **Reasoning:** `gemini-2.0-flash` offers better performance and similar (or better) pricing with the same 1M token context window. There's little reason to choose 1.5 Flash now.
```

**2. Stream Text:**
```python
from google import genai

stream = client.models.generate_content_stream(
    model="gemini-2.0-flash", # Recommended default
    contents="Tell me a long story about a brave knight."
)
for chunk in stream:
    print(chunk.text, end="")
print()
```

**3. Start a Chat:**
```python
from google import genai

chat = client.chats.create(model="gemini-2.0-flash") # Recommended default
response = chat.send_message("Hello! What can you do?")
print(response.text)

response2 = chat.send_message("What was the first thing I said?")
print(response2.text)
# `chat.history` contains the conversation turns (list[types.Content])
print(chat.history)
```

**4. Embed Content:**
```python
from google import genai
from google.genai import types

response = client.models.embed_content(
    model="text-embedding-004", # Specific embedding model
    contents=["What is the meaning of life?", "How does photosynthesis work?"],
    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
)
# response.embeddings is a list of ContentEmbedding objects
print(f"Number of embeddings: {len(response.embeddings)}")
print(f"Dimension of first embedding: {len(response.embeddings[0].values)}")
```

**5. Count Tokens:**
```python
from google import genai

response = client.models.count_tokens(
    model="gemini-2.0-flash", # Recommended default
    contents="How many tokens are in this sentence?"
)
print(f"Total tokens: {response.total_tokens}")

# Can also count tokens for multi-turn history
chat_history = [
    types.UserContent(parts=[types.Part.from_text("Hello")]),
    types.ModelContent(parts=[types.Part.from_text("Hi there!")]),
]
response_hist = client.models.count_tokens(
    model="gemini-2.0-flash", # Recommended default
    contents=chat_history
)
print(f"History tokens: {response_hist.total_tokens}")

```

**6. Upload & Use Local Files (Gemini API):**

The `client.files` API allows uploading files for temporary use (they expire).

```python
import pathlib
from google import genai
from google.genai import types

# --- Method 1: Upload via client.files ---
# Create a dummy file for example
file_path = pathlib.Path("my_document.txt")
file_path.write_text("This is the content of my local file.")

print(f"Uploading file: {file_path.name}")
# Upload the file
uploaded_file = client.files.upload(
    file=file_path, # Can be str path, Path object, or file-like object
    config=types.UploadFileConfig(display_name="My Text Document")
)
print(f"Uploaded file: {uploaded_file.name}, URI: {uploaded_file.uri}")

# Use the uploaded file URI in a prompt
prompt_with_file_uri = [
    "Summarize this document:",
    # Use the File object directly or its URI
    uploaded_file
    # Or: types.Part.from_uri(uploaded_file.uri, mime_type=uploaded_file.mime_type)
]
gen_response_uri = client.models.generate_content(
    model="gemini-2.0-flash", # Recommended default
    contents=prompt_with_file_uri
)
print("\nSummary (using uploaded file URI):")
print(gen_response_uri.text)

# Clean up the uploaded file (optional)
print(f"Deleting file: {uploaded_file.name}")
client.files.delete(name=uploaded_file.name)
file_path.unlink() # Delete local dummy file

# --- Method 2: Inline Data using Part.from_data ---
image_path = pathlib.Path("path/to/your/local_image.jpg") # Replace with actual path
if image_path.exists():
    print(f"\nUsing inline data for: {image_path.name}")
    image_part = types.Part.from_data(
        data=image_path.read_bytes(),
        mime_type="image/jpeg" # Adjust mime type as needed
    )
    prompt_with_inline_data = [
        "Describe this image:",
        image_part
    ]
    gen_response_inline = client.models.generate_content(
        model="gemini-2.0-flash", # Recommended default (handles vision)
        contents=prompt_with_inline_data
    )
    print("\nDescription (using inline data):")
    print(gen_response_inline.text)
else:
    print(f"\nSkipping inline image example: {image_path} not found.")

```
*(Note: `client.files` is suitable for larger files or when you need to reference the same file multiple times. Inline data (`Part.from_data`) is simpler for smaller, single-use files.)*

**7. Using Function Calling:**

Define functions the model can call to interact with external tools or APIs.

```python
from google import genai
from google.genai import types
import json

# Define a Python function
def find_theaters(location: str, movie: str | None = None) -> str:
    """Find theaters showing movies based on location and optionally movie title.

    Args:
        location: The city and state, e.g. San Francisco, CA
        movie: Optional. The name of the movie.
    """
    # In a real scenario, this would call an external API
    theaters = [f"Theater A in {location}", f"Theater B in {location}"]
    if movie:
        return json.dumps({"theaters": theaters, "showing": movie})
    else:
        return json.dumps({"theaters": theaters})

# --- Method 1: Automatic Function Calling (Recommended) ---
# Pass the Python function directly in the tools list
response_auto = client.models.generate_content(
    model="gemini-2.0-flash", # Recommended default, supports function calling
    contents="Find me movie theaters in Mountain View, CA.",
    config=types.GenerateContentConfig(tools=[find_theaters])
)
print("\n--- Automatic Function Calling ---")
print(response_auto.text) # Model summarizes the function result

# --- Method 2: Manual Function Calling ---
# 1. Declare the function schema
find_theaters_declaration = types.FunctionDeclaration.from_callable(find_theaters)
tools_manual = types.Tool(function_declarations=[find_theaters_declaration])

# 2. Send the prompt and tools to the model
print("\n--- Manual Function Calling ---")
user_prompt = "Find me movie theaters in Mountain View, CA showing 'Action Movie'."
response_manual_1 = client.models.generate_content(
    model="gemini-2.0-flash", # Recommended default, supports function calling
    contents=user_prompt,
    config=types.GenerateContentConfig(tools=tools_manual)
)

# 3. Check if the model requested a function call
if not response_manual_1.function_calls:
    print("Model did not request function call.")
else:
    fc = response_manual_1.function_calls[0]
    print(f"Function Call Requested: {fc.name}")
    print(f"Args: {fc.args}")

    # 4. Execute the function with the provided arguments
    try:
        api_result = find_theaters(**fc.args)
        function_response_part = types.Part.from_function_response(
            name=fc.name,
            response={"result": json.loads(api_result)} # Send structured data back
        )
    except Exception as e:
        print(f"Error executing function: {e}")
        function_response_part = types.Part.from_function_response(
            name=fc.name,
            response={"error": str(e)}
        )

    # 5. Send the function response back to the model
    response_manual_2 = client.models.generate_content(
        model="gemini-2.0-flash", # Recommended default
        contents=[
            response_manual_1.candidates[0].content, # Include previous model turn (with the call)
            function_response_part # Add the function result part
        ],
        config=types.GenerateContentConfig(tools=tools_manual) # Include tools again
    )
    print("\nModel Response after Function Execution:")
    print(response_manual_2.text)

# --- Disabling Automatic Function Calling ---
# Useful if you *always* want to handle the call manually, even if passing the function
response_disable_auto = client.models.generate_content(
    model="gemini-2.0-flash", # Recommended default
    contents="Find me movie theaters in Mountain View, CA.",
    config=types.GenerateContentConfig(
        tools=[find_theaters], # Still pass the function for schema generation
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
    )
)
print("\n--- Disabled Automatic Function Calling ---")
if response_disable_auto.function_calls:
    print(f"Function Call Requested: {response_disable_auto.function_calls[0].name}")
    # Proceed with manual execution as above
else:
    print("Model generated text directly.")
    print(response_disable_auto.text)

```

**8. Requesting JSON Output:**

Use `response_mime_type` and `response_schema`.

```python
from google import genai
from google.genai import types
from pydantic import BaseModel
import json

# Define schema using Pydantic (or as a dictionary)
class CountryInfo(BaseModel):
    name: str
    population: int
    capital: str
    continent: str

response = client.models.generate_content(
    model="gemini-2.0-flash", # Recommended default
    contents="Give me information for the United States.",
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=CountryInfo, # Pass Pydantic model directly
    )
)

# The response.text will be a JSON string
print("\n--- JSON Output ---")
print(response.text)
try:
    # Use response.parsed for automatic Pydantic parsing
    parsed_info = response.parsed
    if parsed_info:
         print(f"Parsed Capital (Pydantic): {parsed_info.capital}")
    else: # Fallback if parsing fails or response is blocked
         print("Could not parse response automatically.")
         # Manual parsing
         country_data = json.loads(response.text)
         print(f"Parsed Capital (Manual): {country_data.get('capital')}")

except json.JSONDecodeError:
    print("Failed to decode JSON response.")
except Exception as e:
     print(f"An error occurred: {e}")

```

**9. Requesting Enum Output:**

Force the model to choose from a predefined set of values.

```python
from google import genai
from google.genai import types
from enum import Enum

class InstrumentEnum(Enum):
    PERCUSSION = 'Percussion'
    STRING = 'String'
    WOODWIND = 'Woodwind'
    BRASS = 'Brass'
    KEYBOARD = 'Keyboard'

response = client.models.generate_content(
    model='gemini-2.0-flash', # Recommended default
    contents='What instrument family is a piano in?',
    config=types.GenerateContentConfig(
        # Use 'text/x.enum' or 'application/json'
        response_mime_type='text/x.enum',
        response_schema=InstrumentEnum, # Pass Enum class directly
    ),
)
print("\n--- Enum Output ---")
print(f"Selected Enum: {response.text}")
# You can compare response.text to InstrumentEnum members
if response.text == InstrumentEnum.KEYBOARD.value:
    print("Correctly identified as Keyboard.")

```

---
## Asynchronous Operations (`client.aio`)

All synchronous methods have asynchronous counterparts available via `client.aio`.

**Async Generate Text:**
```python
import asyncio
from google import genai

async def async_generate():
    client = genai.Client() # Assumes GOOGLE_API_KEY is set
    async_client = client.aio
    response = await async_client.models.generate_content(
        model="gemini-2.0-flash", # Recommended default
        contents="Write an async poem."
    )
    print("\n--- Async Generate ---")
    print(response.text)

# asyncio.run(async_generate()) # Uncomment to run
```

**Async Stream Text:**
```python
import asyncio
from google import genai

async def async_stream():
    client = genai.Client()
    async_client = client.aio
    stream = await async_client.models.generate_content_stream(
        model="gemini-2.0-flash", # Recommended default
        contents="Tell an async story."
    )
    print("\n--- Async Stream ---")
    async for chunk in stream:
        print(chunk.text, end="")
    print()

# asyncio.run(async_stream()) # Uncomment to run
```

**Async Chat:**
```python
import asyncio
from google import genai

async def async_chat_example():
    client = genai.Client()
    async_client = client.aio
    chat = async_client.chats.create(model="gemini-2.0-flash") # Recommended default
    print("\n--- Async Chat ---")
    response = await chat.send_message("Async hello!")
    print(f"Model: {response.text}")
    response2 = await chat.send_message("What did I say first?")
    print(f"Model: {response2.text}")

# asyncio.run(async_chat_example()) # Uncomment to run
```

---

## Error Handling

Use a `try...except` block with `errors.APIError` to catch SDK-specific issues.

```python
from google.genai import errors

try:
    response = client.models.generate_content(
        model="invalid-model-name", # Intentionally invalid
        contents="This will fail."
    )
except errors.APIError as e:
    print("\n--- Error Handling ---")
    print(f"API Error Code: {e.code}")
    print(f"API Error Message: {e.message}")
    # Specific error types like NotFoundError, PermissionDeniedError also exist
    if isinstance(e, errors.NotFoundError):
        print("Caught a NotFoundError specifically.")
except Exception as e:
    print(f"A general error occurred: {e}")

```

---

## Key Types (`google.genai.types`)

The `types` module is crucial. It contains Pydantic models and Enums for configuring requests and parsing responses. Explore this module in the documentation or using `help(types)` or `dir(types)` for detailed structures like:

*   **Core:** `Content`, `Part`, `Blob`, `FileData`, `UserContent`, `ModelContent`
*   **Configs:** `GenerateContentConfig`, `SafetySetting`, `EmbedContentConfig`, `ToolConfig`, `HttpOptions`, `UploadFileConfig`
*   **Safety:** `HarmCategory`, `HarmBlockThreshold`, `HarmProbability`, `HarmSeverity`
*   **Tools:** `Tool`, `FunctionDeclaration`, `FunctionCall`, `FunctionResponse`, `Schema`, `Type`, `GoogleSearchRetrieval`
*   **Responses:** `GenerateContentResponse`, `EmbedContentResponse`, `CountTokensResponse`, `File`, `Model`, `Operation`
*   **Response Components:** `Candidate`, `SafetyRating`, `CitationMetadata`, `PromptFeedback`, `ContentEmbedding`

---

## What's Next

Now that you understand the basics for the Gemini Developer API, explore the official guides for more specific use cases:

*   [Gemini API Overview](https://ai.google.dev/gemini-api/docs)
*   [Text generation](https://ai.google.dev/gemini-api/docs/text-generation)
*   [Vision (Multimodal Input)](https://ai.google.dev/gemini-api/docs/vision)
*   [Function calling](https://ai.google.dev/gemini-api/docs/function-calling)
*   [Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)
*   [File API Guide](https://ai.google.dev/gemini-api/docs/file-api)

---

**Reminder:** Always consult the official Google AI documentation ([https://ai.google.dev/gemini-api/docs](https://ai.google.dev/gemini-api/docs)) for the most up-to-date information, detailed parameter descriptions, and advanced usage patterns specific to the Gemini Developer API.
