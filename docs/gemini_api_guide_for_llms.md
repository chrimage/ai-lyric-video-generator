# Gemini API Guide for LLMs: Writing Code with Google's Gemini

This guide is specifically designed to help large language models effectively use the Google Gemini API for generating and executing code. It provides a structured approach to understanding the capabilities, features, and best practices of the Gemini API.

## Table of Contents
1. [API Overview](#api-overview)
2. [Installation and Setup](#installation-and-setup)
3. [Core Concepts](#core-concepts)
4. [Models and Capabilities](#models-and-capabilities)
5. [Text Generation](#text-generation)
6. [Code Generation and Execution](#code-generation-and-execution)
7. [Function Calling](#function-calling)
8. [Multimodal Input](#multimodal-input)
9. [Best Practices](#best-practices)
10. [Error Handling](#error-handling)
11. [Example Patterns](#example-patterns)

## API Overview

The Google Gemini API provides access to Google's advanced large language models, with capabilities spanning text generation, code generation, multimodal understanding, and tool integration. The primary use cases include:

- Text generation and chat applications
- Code generation and analysis
- Function calling to connect with external tools and APIs
- Multimodal processing (text, images, video, audio)

## Installation and Setup

### Python Setup

```python
# Install the Gemini API library
pip install -q -U google-genai

# Import and configure the client
from google import genai

# Initialize the client with your API key
client = genai.Client(api_key="YOUR_API_KEY")  # API keys can be obtained from Google AI Studio
```

### Making Your First Request

```python
# Basic text generation
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Explain how to use the Pandas library in Python"
)
print(response.text)
```

## Core Concepts

### Key Components

- **Client**: The main entry point for interacting with the Gemini API
- **Models**: Different model variants optimized for specific use cases
- **Contents**: The input provided to the model (text, images, etc.)
- **Config**: Optional parameters that control model behavior
- **Response**: The output from the model, which can include text and function calls

### Response Structure

Responses from the Gemini API include:
- `text`: The generated text content
- `candidates`: List of alternative responses
- `function_calls`: When using function calling, contains function call information
- Various metadata including token usage information

## Models and Capabilities

The Gemini API offers multiple model variants:

| Model | Capabilities | Best Use Cases |
|-------|--------------|---------------|
| gemini-2.5-pro-exp-03-25 | Most advanced thinking capabilities | Complex reasoning, advanced coding, and multimodal understanding |
| gemini-2.0-flash | Balanced performance, next-gen features | General purpose text generation, code generation, and multimodal tasks |
| gemini-2.0-flash-lite | Cost-effective variant of 2.0 Flash | High-volume, cost-sensitive applications |
| gemini-1.5-flash | Fast multimodal model | Scalable deployments across diverse tasks |
| gemini-1.5-pro | Mid-size model for complex tasks | Complex reasoning with multimodal inputs |

When deciding which model to use, consider:
1. Complexity of the task
2. Performance requirements
3. Cost constraints
4. Input/output token limits

## Text Generation

### Basic Text Generation

```python
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=["How does AI work?"]
)
print(response.text)
```

### Streaming Output

```python
response = client.models.generate_content_stream(
    model="gemini-2.0-flash",
    contents=["Explain how AI works"]
)
for chunk in response:
    print(chunk.text, end="")
```

### Multi-turn Conversations

```python
chat = client.chats.create(model="gemini-2.0-flash")
response = chat.send_message("I have 2 dogs in my house.")
print(response.text)

response = chat.send_message("How many paws are in my house?")
print(response.text)
```

### Configuration Parameters

```python
from google.genai import types

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=["Explain how AI works"],
    config=types.GenerateContentConfig(
        max_output_tokens=500,
        temperature=0.1  # Lower temperature for more deterministic outputs
    )
)
```

### System Instructions

```python
response = client.models.generate_content(
    model="gemini-2.0-flash",
    config=types.GenerateContentConfig(
        system_instruction="You are a programming assistant specialized in Python."),
    contents="How do I use decorators in Python?"
)
```

## Code Generation and Execution

### Code Generation

```python
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Write a Python function to calculate the Fibonacci sequence"
)
print(response.text)
```

### Code Execution

```python
from google.genai import types

response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents='What is the sum of the first 50 prime numbers? Generate and run code for the calculation.',
    config=types.GenerateContentConfig(
        tools=[types.Tool(
            code_execution=types.ToolCodeExecution
        )]
    )
)
```

### Code Execution in Chat

```python
chat = client.chats.create(
    model='gemini-2.0-flash',
    config=types.GenerateContentConfig(
        tools=[types.Tool(
            code_execution=types.ToolCodeExecution
        )]
    )
)

response = chat.send_message("Can you write code to visualize a sine wave using matplotlib?")
```

Important code execution details:
- Includes libraries like `matplotlib`, `numpy`, `pandas`, `sklearn`, etc.
- Maximum runtime: 30 seconds
- Maximum file input size: Limited by model token window (~2MB for text files)
- Supports file input and graph output (applicable to models from Gemini 2.0 Flash onwards)

## Function Calling

Function calling enables the model to invoke external functions and APIs, extending its capabilities beyond text generation.

### Defining Function Declarations

```python
from google.genai import types

# Define a function that the model can call
get_weather_declaration = {
    "name": "get_weather",
    "description": "Get the current weather in a given location",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city and state, e.g., San Francisco, CA",
            },
            "unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "The unit of temperature to use. Infer this from the user's location.",
            },
        },
        "required": ["location"],
    },
}

# Function implementation
def get_weather(location, unit="celsius"):
    """Get the current weather in a given location."""
    # Implementation would call a weather API here
    return {"temperature": 22, "unit": unit, "description": "Sunny"}
```

### Using Function Calling

```python
# Generation Config with Function Declaration
tools = types.Tool(function_declarations=[get_weather_declaration])
config = types.GenerateContentConfig(tools=[tools])

# Define user prompt
contents = [
    types.Content(
        role="user", parts=[types.Part(text="What's the weather like in Paris?")]
    )
]

# Send request with function declarations
response = client.models.generate_content(
    model="gemini-2.0-flash", config=config, contents=contents
)

# Extract function call details
function_call = response.candidates[0].content.parts[0].function_call

if function_call.name == "get_weather":
    result = get_weather(**function_call.args)
    
    # Create a function response part
    function_response_part = types.Part.from_function_response(
        name=function_call.name,
        response={"result": result},
    )
    
    # Append function call and result to contents
    contents.append(types.Content(role="model", parts=[types.Part(function_call=function_call)]))
    contents.append(types.Content(role="user", parts=[function_response_part]))
    
    # Get final response
    final_response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=config,
        contents=contents,
    )
    
    print(final_response.text)
```

### Function Calling Modes

The API supports different function calling modes:
- `AUTO`: Model decides whether to generate text or call a function (default)
- `ANY`: Always predict a function call
- `NONE`: Never predict a function call

```python
tool_config = types.ToolConfig(
    function_calling_config=types.FunctionCallingConfig(
        mode="ANY", allowed_function_names=["get_weather"]
    )
)
```

## Multimodal Input

### Working with Images

```python
from PIL import Image

# Load an image
image = Image.open("/path/to/image.jpg")

# Generate content with text and image
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=["Describe this image in detail", image]
)
print(response.text)
```

### Working with Multiple Images

```python
# Multiple images in a single request
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=["What do these images have in common?", image1, image2, image3]
)
```

### Working with Videos

```python
# Upload a video using the File API
video_file = client.files.upload(file="video.mp4")

# Wait for processing to complete
while video_file.state.name == "PROCESSING":
    time.sleep(1)
    video_file = client.files.get(name=video_file.name)

# Generate content with video
response = client.models.generate_content(
    model="gemini-1.5-pro",
    contents=[
        video_file,
        "Summarize this video"
    ]
)
```

## Best Practices

### Prompt Engineering

1. **Be specific and precise**:
   - Clearly state what you want the model to generate
   - Include relevant context in your prompt

2. **Use system instructions**:
   - Set the tone and behavior of the model
   - Define the role the model should take

3. **Control temperature**:
   - Lower (0.1-0.4) for factual, deterministic responses
   - Higher (0.7-1.0) for creative, diverse outputs

4. **Input/output token management**:
   - Stay within model token limits
   - For long outputs, use streaming

### Function Calling Best Practices

1. **Clear function descriptions**: Be specific about what the function does
2. **Descriptive parameter names**: Make parameter names intuitive
3. **Use enums for fixed value sets**: Define allowed values explicitly
4. **Include examples in descriptions**: Show how parameters should be formatted
5. **Error handling**: Have robust error handling in function implementations

## Error Handling

Common error types and their handling:

```python
from google.genai.types import ResponseBlockedError, StopCandidateError, InvalidArgumentError

try:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="Generate a Python function"
    )
    print(response.text)
except ResponseBlockedError as e:
    print(f"Response was blocked: {e}")
except StopCandidateError as e:
    print(f"Generation stopped early: {e}")
except InvalidArgumentError as e:
    print(f"Invalid argument: {e}")
```

## Example Patterns

### Creating a Code Assistant

```python
def code_assistant(prompt, language="python"):
    """Generate code based on a prompt and execute it if needed."""
    from google.genai import types
    
    system_instruction = f"You are an expert {language} programmer. Generate clean, efficient, and well-documented code."
    
    chat = client.chats.create(
        model='gemini-2.0-flash',
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[types.Tool(
                code_execution=types.ToolCodeExecution
            )],
            temperature=0.2
        )
    )
    
    response = chat.send_message(prompt)
    return response.text
```

### Creating a Custom Function Calling Tool

```python
def create_tool_with_function(function_declaration, function_implementation):
    """Create a reusable tool with function calling."""
    from google.genai import types
    
    tools = types.Tool(function_declarations=[function_declaration])
    config = types.GenerateContentConfig(tools=[tools])
    
    def process_request(prompt):
        contents = [
            types.Content(
                role="user", parts=[types.Part(text=prompt)]
            )
        ]
        
        response = client.models.generate_content(
            model="gemini-2.0-flash", config=config, contents=contents
        )
        
        # Check if function was called
        if hasattr(response.candidates[0].content.parts[0], 'function_call'):
            function_call = response.candidates[0].content.parts[0].function_call
            
            if function_call.name == function_declaration["name"]:
                result = function_implementation(**function_call.args)
                
                # Process function result
                function_response_part = types.Part.from_function_response(
                    name=function_call.name,
                    response={"result": result},
                )
                
                # Update conversation
                contents.append(types.Content(role="model", parts=[types.Part(function_call=function_call)]))
                contents.append(types.Content(role="user", parts=[function_response_part]))
                
                # Get final response
                final_response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    config=config,
                    contents=contents,
                )
                
                return final_response.text
        
        # Return direct response if no function call
        return response.text
    
    return process_request
```

## Final Notes

When using the Gemini API for code generation:

1. **Understand the context**: Analyze the full context of the code problem before generating solutions
2. **Verify outputs**: Always verify generated code for correctness and safety
3. **Iterative refinement**: Use chat interfaces for iterative code improvement
4. **Model selection**: Choose the appropriate model based on the complexity of the coding task
5. **Use multimodal capabilities**: For code involving visual elements or data visualization, leverage the multimodal capabilities

This guide provides a comprehensive overview of using the Google Gemini API for code-related tasks. By following these patterns and best practices, you can effectively leverage the power of Gemini for a wide range of code generation and execution scenarios.