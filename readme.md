# Wikipedia Video Creator

Automatically create educational videos from Wikipedia content with narration, images, and subtitles.

## Features

- Fetch content from multiple Wikipedia articles
- Generate a script using AI (GPT-4)
- Create narration using ElevenLabs text-to-speech
- Add visuals using images from Wikipedia
- Generate subtitles
- Combine everything into a complete video

## Requirements

- Python 3.7+
- FFmpeg installed and in your PATH
- OpenAI API key
- ElevenLabs API key

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Install FFmpeg (if not already installed):
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg` or equivalent for your distribution

## Configuration

1. Set up your OpenAI API key:
   ```
   export OPENAI_API_KEY=your_api_key
   ```
   Or edit the script to include it directly (not recommended for security reasons).

2. Configure your ElevenLabs API key in `narrate.py`.

## Usage

Run the script with the following arguments:

```
python video_creator.py --title "Your Video Title" --links https://en.wikipedia.org/wiki/Example1 https://en.wikipedia.org/wiki/Example2 --length 2000
```

### Arguments

- `--title`: Title of the video
- `--links`: One or more Wikipedia URLs to use as content sources
- `--length`: Target character count for the script (default: 2000)
- `--output`: Output video filename (default: output_video.mp4)
- `--temp_dir`: Directory for temporary files (default: temp)

## Examples

Create a video about interesting animals:

```
python video_creator.py --title "10 Most Interesting Animals in the Jungle" --links https://en.wikipedia.org/wiki/Jungle https://en.wikipedia.org/wiki/Jaguar https://en.wikipedia.org/wiki/Python_(genus) https://en.wikipedia.org/wiki/Toucan --length 3000
```

## Project Structure

- `video_creator.py`: Main script
- `wiki_grabber.py`: Script to fetch content and images from Wikipedia
- `narrate.py`: Script to generate narration using ElevenLabs

## License

MIT
