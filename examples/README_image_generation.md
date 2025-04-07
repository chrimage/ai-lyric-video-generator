# Gemini Image Generation Examples

This directory contains examples of using the Google Gemini API for image generation. These scripts demonstrate how to use the `gemini-2.0-flash-exp-image-generation` model to create images from text prompts.

## Prerequisites

1. Install the required package:
   ```bash
   pip install -q -U google-genai
   ```

2. Set your Google API key as an environment variable:
   ```bash
   # You can use either of these names for the environment variable:
   export GEMINI_API_KEY="your-api-key-here"
   # or
   export GOOGLE_API_KEY="your-api-key-here"
   ```
   
   Or add it to a `.env` file in the project root:
   ```
   GOOGLE_API_KEY=your-api-key-here
   ```

## Available Scripts

### 1. Basic Image Generation (`test_image_generation.py`)

A simple script that generates an image of a purple fairy unicorn.

```bash
python examples/test_image_generation.py
```

### 2. Command-line Image Generator (`gemini_image_generator.py`)

A more flexible script that accepts a prompt from the command line.

```bash
python examples/gemini_image_generator.py "A futuristic cityscape with flying cars and neon lights"
```

To specify an output filename:
```bash
python examples/gemini_image_generator.py "A cat in a space suit" --output space_cat
```

### 3. Advanced Image Generator (`advanced_image_generator.py`)

A comprehensive script with advanced features like batch processing, styling options, and error handling.

Generate a single image:
```bash
python examples/advanced_image_generator.py --prompt "A cat wearing a space suit on Mars"
```

Generate multiple variations of the same prompt:
```bash
python examples/advanced_image_generator.py --prompt "A serene mountain landscape" --count 3
```

Apply a specific style:
```bash
python examples/advanced_image_generator.py --prompt "A portrait of a robot" --style "oil painting"
```

Use a negative prompt to exclude certain elements:
```bash
python examples/advanced_image_generator.py --prompt "A fantasy castle" --negative-prompt "dark, gloomy"
```

Batch process multiple prompts from a file:
```bash
python examples/advanced_image_generator.py --batch prompts.txt --output-dir custom_images
```

Example `prompts.txt` file:
```
A cat playing piano
A dog riding a skateboard
A mountain landscape at sunset
```

## Output

All generated images are saved to the `output/generated_images` directory by default, or to the directory specified with the `--output-dir` option.

## Notes on the Model

The `gemini-2.0-flash-exp-image-generation` model is specialized for converting text descriptions into images. Some tips for getting good results:

1. Be specific and detailed in your prompts
2. Include style information (e.g., "digital art", "photorealistic", "oil painting")
3. Mention lighting, perspective, and mood for more control
4. Use the negative prompt parameter to exclude unwanted elements

## Error Handling

If you encounter errors:

1. Verify your API key is correct and has permissions for image generation
2. Check your internet connection
3. The model might be busy - the scripts include retry logic for transient errors
4. Some prompts may be rejected if they violate content policies
