# MoviePy API Reference Guide

This document provides a comprehensive guide to the MoviePy library API, focusing on its core components, classes, and methods. MoviePy is a Python library for video editing including cuts, concatenations, title insertions, video compositing, video processing, and creation of custom effects.

## Important Note

MoviePy v2.0 introduced breaking changes. For migration information, see the [Updating from v1.X to v2.X](https://zulko.github.io/moviepy/getting_started/updating_to_v2.html) guide.

## Core Structure

MoviePy's API is organized into several key modules:

```
moviepy
├── Clip (Base class)
├── Effect (Base class for effects)
├── audio (Audio manipulation)
├── video (Video manipulation)
├── config (Third-party program configuration)
├── decorators (Decorators used by MoviePy)
└── tools (Miscellaneous utilities)
```

## Main Import

MoviePy provides a convenient way to import all necessary components:

```python
from moviepy import *
```

## Core Classes

### `Clip`

`Clip` is the base class for all clips (VideoClips and AudioClips).

#### Properties:
- `start` (float): When the clip starts playing in a composition (in seconds)
- `end` (float): When the clip stops playing in a composition (in seconds)
- `duration` (float): Duration of the clip in seconds. Some clips are infinite (`duration=None`)

#### Methods:
- `close()`: Release any resources in use
- `copy()`: Create a copy of the clip
- `get_frame(t)`: Get a frame at time `t`
- `is_playing(t)`: Check if the clip is playing at time `t`
- `iter_frames(fps=None, with_times=False, logger=None, dtype=None)`: Iterate over all frames of the clip
- `subclipped(start_time=0, end_time=None)`: Create a subclip from the original clip
- `time_transform(time_func, apply_to=None, keep_duration=False)`: Apply a time transformation
- `transform(func, apply_to=None, keep_duration=True)`: Apply a general transformation
- `with_duration(duration, change_end=True)`: Set the clip duration
- `with_effects(effects)`: Apply effects to the clip
- `with_end(t)`: Set the end time
- `with_fps(fps, change_duration=False)`: Set the frames per second
- `with_is_mask(is_mask)`: Set whether the clip is a mask
- `with_memoize(memoize)`: Set whether to cache frames
- `with_section_cut_out(start_time, end_time)`: Create a clip with a section removed
- `with_speed_scaled(factor=None, final_duration=None)`: Scale the speed of the clip
- `with_start(t, change_end=True)`: Set the start time
- `with_updated_frame_function(frame_function)`: Update the frame generation function
- `with_volume_scaled(factor, start_time=None, end_time=None)`: Scale the volume

## Video Module

The `video` module contains components for video manipulation.

### `VideoClip`

Base class for all video clips.

#### Main VideoClip Types:
- **Animated clips**: 
  - `VideoFileClip`: Load a video file
  - `ImageSequenceClip`: Create video from a sequence of images 
  - `BitmapClip`: Create video from bitmap frames

- **Static image clips**:
  - `ImageClip`: Create a non-moving clip from an image
  - `ColorClip`: Create a clip showing a single color
  - `TextClip`: Create a clip with text

### Video Effects (`video.fx`)

MoviePy provides many video effects, including:

- `AccelDecel`: Accelerate and decelerate a clip
- `BlackAndWhite`: Convert to black and white
- `Blink`: Make the clip blink
- `Crop`: Crop a region of the clip
- `CrossFadeIn`/`CrossFadeOut`: Fade in/out with transparency
- `FadeIn`/`FadeOut`: Fade in/out to a color
- `Freeze`: Freeze the clip at a specific time
- `GammaCorrection`: Apply gamma correction
- `InvertColors`: Invert the colors
- `Loop`: Loop the clip
- `MakeLoopable`: Make a clip that can be looped seamlessly
- `Margin`: Add a margin around the clip
- `MirrorX`/`MirrorY`: Flip horizontally/vertically
- `MultiplySpeed`: Change the speed of the clip
- `Resize`: Resize the clip
- `Rotate`: Rotate the clip
- `SlideIn`/`SlideOut`: Make the clip slide in/out

## Audio Module

The `audio` module contains components for audio manipulation.

### `AudioClip`

Base class for all audio clips.

#### Main AudioClip Types:
- `AudioFileClip`: Load an audio file
- `CompositeAudioClip`: Combine multiple audio clips
- `AudioArrayClip`: Create audio from a numpy array

### Audio Effects (`audio.fx`)

MoviePy includes audio effects such as:
- Volume adjustment
- Fading in/out
- Audio mixing

## Compositing

MoviePy allows composition of multiple clips:

- `CompositeVideoClip`: Overlay multiple video clips
- `concatenate_videoclips`: Join clips end-to-end
- `clips_array`: Arrange clips in a grid pattern

## Input/Output Operations

MoviePy supports various I/O operations:

- Reading video and audio files
- Writing to various formats
- Previewing clips

## Examples

### Basic Video Editing
```python
from moviepy import *

# Load a video file
clip = VideoFileClip("video.mp4")

# Trim the clip
clip = clip.subclipped(10, 20)  # 10 seconds to 20 seconds

# Apply effects
clip = clip.resize(0.5)  # Resize to 50%
clip = clip.fx(vfx.BlackAndWhite)  # Apply black and white effect

# Write the result
clip.write_videofile("output.mp4")
```

### Creating a Text Animation
```python
from moviepy import *

# Create a text clip
txt = TextClip("Hello World", fontsize=70, color='white')
txt = txt.set_position('center').set_duration(10)

# Add animation
txt = txt.fx(vfx.FadeIn, duration=1)
txt = txt.fx(vfx.FadeOut, duration=1)

# Write to file
txt.write_videofile("text_animation.mp4", fps=24)
```

### Compositing Videos
```python
from moviepy import *

video1 = VideoFileClip("clip1.mp4")
video2 = VideoFileClip("clip2.mp4").resize(0.6)

# Position video2 in the top right corner of video1
video2 = video2.set_position(("right", "top"))

# Overlay videos
final_clip = CompositeVideoClip([video1, video2])
final_clip.write_videofile("composite.mp4")
```

## Additional Resources

- [Official Documentation](https://zulko.github.io/moviepy/)
- [GitHub Repository](https://github.com/Zulko/moviepy/)
- [User Guide](https://zulko.github.io/moviepy/user_guide/index.html)
- [Getting Started](https://zulko.github.io/moviepy/getting_started/index.html)
