#!/usr/bin/env python3
# pixabay_image_fetcher.py - Fixed version with filename sanitization

import os
import re
import json
import requests
import argparse
from dotenv import load_dotenv
import openai
import time

# Load environment variables
load_dotenv()

# Configure OpenAI API
openai.api_key = os.environ.get("OPENAI_API_KEY")

def parse_srt_file(srt_file):
    """
    Parse an SRT subtitle file and extract the text with timestamps.
    
    Args:
        srt_file (str): Path to the SRT subtitle file
        
    Returns:
        list: List of dictionaries with start time, end time, and text
    """
    with open(srt_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by subtitle entries (blank line)
    subtitle_blocks = re.split('\r?\n\r?\n', content.strip())
    subtitles = []
    
    for block in subtitle_blocks:
        lines = block.split('\n')
        if len(lines) < 3:
            continue
        
        # Parse the timing line
        timing = lines[1]
        timestamps = re.match(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', timing)
        
        if not timestamps:
            continue
            
        start_time = timestamps.group(1)
        end_time = timestamps.group(2)
        
        # Convert timestamp to seconds for easier comparison
        start_seconds = timestamp_to_seconds(start_time)
        end_seconds = timestamp_to_seconds(end_time)
        
        # Get the text content (may be multiple lines)
        text = '\n'.join(lines[2:])
        
        subtitles.append({
            'start_time': start_time,
            'end_time': end_time,
            'start_seconds': start_seconds,
            'end_seconds': end_seconds,
            'text': text
        })
    
    return subtitles

def timestamp_to_seconds(timestamp):
    """
    Convert an SRT timestamp to seconds.
    
    Args:
        timestamp (str): SRT timestamp in format HH:MM:SS,mmm
        
    Returns:
        float: Time in seconds
    """
    hours, minutes, seconds = timestamp.replace(',', '.').split(':')
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)

def seconds_to_timestamp(seconds):
    """
    Convert seconds to an SRT timestamp.
    
    Args:
        seconds (float): Time in seconds
        
    Returns:
        str: SRT timestamp in format HH:MM:SS,mmm
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace('.', ',')

def group_subtitles_by_segments(subtitles, segment_duration=30):
    """
    Group subtitles into logical segments for image searches.
    
    Args:
        subtitles (list): List of subtitle dictionaries
        segment_duration (int): Target duration for each segment in seconds
        
    Returns:
        list: List of segment dictionaries with start, end, and text
    """
    if not subtitles:
        return []
    
    segments = []
    current_segment = {
        'start_seconds': subtitles[0]['start_seconds'],
        'text': subtitles[0]['text'],
        'subtitles': [subtitles[0]]
    }
    
    for i in range(1, len(subtitles)):
        subtitle = subtitles[i]
        segment_duration_so_far = subtitle['start_seconds'] - current_segment['start_seconds']
        
        # If the segment is long enough, start a new one
        if segment_duration_so_far >= segment_duration:
            # Finalize current segment
            last_subtitle = current_segment['subtitles'][-1]
            current_segment['end_seconds'] = last_subtitle['end_seconds']
            segments.append(current_segment)
            
            # Start a new segment
            current_segment = {
                'start_seconds': subtitle['start_seconds'],
                'text': subtitle['text'],
                'subtitles': [subtitle]
            }
        else:
            # Add to current segment
            current_segment['text'] += ' ' + subtitle['text']
            current_segment['subtitles'].append(subtitle)
    
    # Add the last segment
    if current_segment['subtitles']:
        last_subtitle = current_segment['subtitles'][-1]
        current_segment['end_seconds'] = last_subtitle['end_seconds']
        segments.append(current_segment)
    
    return segments

def determine_image_search_terms(segments, script_text):
    """
    Use OpenAI to determine image search terms for each segment.
    
    Args:
        segments (list): List of segment dictionaries
        script_text (str): The full script text for context
        
    Returns:
        list: Updated segments with search terms
    """
    system_prompt = (
        "You are an AI assistant helping to find relevant images for a video narration. "
        "Given segments of the narration text, suggest one specific search term for each segment "
        "that would find an image relevant to that part of the narration. "
        "Your search terms should be specific enough to find images that match the narration content exactly. "
        "For example, if the text talks about jaguars in the jungle, suggest 'jaguar in jungle'."
    )
    
    # Process segments in smaller batches to avoid token limits
    batch_size = 5
    for i in range(0, len(segments), batch_size):
        batch = segments[i:i+batch_size]
        
        # Prepare the segments as a numbered list
        segment_text = "\n\n".join([
            f"Segment {j+1}:\n{segment['text']}"
            for j, segment in enumerate(batch)
        ])
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Here's the full script for context:\n\n{script_text[:1000]}...\n\nNow analyze these segments and suggest one specific image search term for each:\n\n{segment_text}"}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            result = response.choices[0].message.content
            
            # Parse the results to extract the search terms
            for j, segment in enumerate(batch):
                # Look for segment number followed by a search term
                match = re.search(rf"Segment {j+1}:?\s*(.+?)(?=Segment|\Z)", result, re.DOTALL)
                if match:
                    search_term = match.group(1).strip()
                    # Clean up any formatting or explanations
                    search_term = re.sub(r'^[^a-zA-Z0-9]+', '', search_term)  # Remove leading non-alphanumeric
                    search_term = re.sub(r'["\':]', '', search_term)  # Remove quotes and colons
                    search_term = search_term.split('\n')[0].strip()  # Take only the first line
                    
                    segment['search_term'] = search_term
                else:
                    # Fallback search term if parsing fails
                    segment['search_term'] = "educational video content"
            
            # Add a small delay to avoid API rate limits
            time.sleep(1)
                
        except Exception as e:
            print(f"Error determining image search terms: {e}")
            # Assign a generic search term as fallback
            for segment in batch:
                segment['search_term'] = "educational video content"
    
    return segments

def fetch_pixabay_images(search_term, api_key, min_width=1280, max_results=3):
    """
    Fetch images from Pixabay API.
    
    Args:
        search_term (str): The search term for Pixabay
        api_key (str): Pixabay API key
        min_width (int): Minimum width for images
        max_results (int): Maximum number of results to return
        
    Returns:
        list: List of image URLs that match the criteria
    """
    base_url = "https://pixabay.com/api/"
    
    params = {
        'key': api_key,
        'q': search_term,
        'image_type': 'photo',
        'orientation': 'horizontal',
        'safesearch': 'true',
        'per_page': 30,  # Request more than we need to filter by size
        'min_width': min_width
    }
    
    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        
        if 'hits' not in data or not data['hits']:
            print(f"No results found for '{search_term}'")
            return []
        
        # Filter and sort by size and relevance
        filtered_hits = [hit for hit in data['hits'] if hit['imageWidth'] >= min_width]
        sorted_hits = sorted(filtered_hits, key=lambda x: x['imageWidth'] * x['imageHeight'], reverse=True)
        
        # Take the best matches
        best_matches = sorted_hits[:max_results]
        
        # Extract the image URLs
        image_urls = [hit['largeImageURL'] for hit in best_matches]
        return image_urls
        
    except Exception as e:
        print(f"Error fetching Pixabay images for '{search_term}': {e}")
        return []

def sanitize_filename(filename):
    """
    Sanitize a filename to make it valid for all operating systems.
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Sanitized filename
    """
    # Remove invalid characters for Windows filenames (most restrictive)
    invalid_chars = r'[<>:"/\\|?*\x00-\x1F]'
    sanitized = re.sub(invalid_chars, '', filename)
    
    # Ensure it doesn't end with a space or period (Windows restriction)
    sanitized = sanitized.rstrip('. ')
    
    # If the filename is empty after sanitizing, provide a default
    if not sanitized:
        sanitized = "image"
        
    return sanitized

def download_image(url, folder, filename):
    """
    Download an image from a URL.
    
    Args:
        url (str): Image URL
        folder (str): Folder to save the image
        filename (str): Filename to save as
        
    Returns:
        str: Path to the downloaded image or None if failed
    """
    os.makedirs(folder, exist_ok=True)
    
    # Sanitize the filename to avoid errors
    sanitized_filename = sanitize_filename(filename)
    
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            file_path = os.path.join(folder, sanitized_filename)
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            return file_path
        else:
            print(f"Failed to download image: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

def get_images_for_segments(segments, pixabay_api_key, images_dir):
    """
    Download images for each segment.
    
    Args:
        segments (list): List of segment dictionaries with search terms
        pixabay_api_key (str): Pixabay API key
        images_dir (str): Directory to save images
        
    Returns:
        list: Updated segments with image paths
    """
    for i, segment in enumerate(segments):
        search_term = segment.get('search_term', 'educational content')
        
        print(f"Searching Pixabay for: '{search_term}'")
        image_urls = fetch_pixabay_images(search_term, pixabay_api_key)
        
        if image_urls:
            # Use the first image (best match)
            image_url = image_urls[0]
            
            # Generate a filename - sanitize the search term to avoid issues
            filename = f"segment_{i+1}_{search_term.replace(' ', '_')[:30]}.jpg"
            
            # Download the image
            image_path = download_image(image_url, images_dir, filename)
            
            if image_path:
                segment['image_path'] = image_path
        
        # Add a small delay to avoid hammering the API
        time.sleep(0.5)
    
    return segments

def create_image_timing_data(segments):
    """
    Create image timing data for video creation.
    
    Args:
        segments (list): List of segment dictionaries with images
        
    Returns:
        tuple: (image_paths, image_durations) for video creation
    """
    image_paths = []
    image_durations = []
    
    for segment in segments:
        if 'image_path' in segment:
            image_paths.append(segment['image_path'])
            duration = segment['end_seconds'] - segment['start_seconds']
            image_durations.append(duration)
    
    return image_paths, image_durations

def get_relevant_images_for_script(script_file, subtitle_file, images_dir, pixabay_api_key=None):
    """
    Main function to get relevant images for a script.
    
    Args:
        script_file (str): Path to the script text file
        subtitle_file (str): Path to the SRT subtitle file
        images_dir (str): Directory to save images
        pixabay_api_key (str): Pixabay API key (if None, will use environment variable)
        
    Returns:
        tuple: (image_paths, image_durations) for video creation
    """
    # Use environment variable if API key not provided
    if not pixabay_api_key:
        pixabay_api_key = os.environ.get("PIXABAY_API_KEY")
        if not pixabay_api_key:
            raise ValueError("Pixabay API key not found. Set PIXABAY_API_KEY in environment or .env file.")
    
    # Create images directory
    os.makedirs(images_dir, exist_ok=True)
    
    # Read the script
    with open(script_file, 'r', encoding='utf-8') as f:
        script_text = f.read()
    
    # Parse the subtitles
    subtitles = parse_srt_file(subtitle_file)
    
    # Group subtitles into segments
    segments = group_subtitles_by_segments(subtitles)
    
    # Determine image search terms
    segments = determine_image_search_terms(segments, script_text)
    
    # Get images for each segment
    segments = get_images_for_segments(segments, pixabay_api_key, images_dir)
    
    # Create image timing data
    image_paths, image_durations = create_image_timing_data(segments)
    
    return image_paths, image_durations, segments

if __name__ == "__main__":
    # Example usage when run directly
    parser = argparse.ArgumentParser(description="Fetch relevant images from Pixabay for a narrated script.")
    parser.add_argument("--script", required=True, help="Path to the script text file")
    parser.add_argument("--subtitles", required=True, help="Path to the SRT subtitle file")
    parser.add_argument("--output_dir", default="pixabay_images", help="Directory to save images")
    parser.add_argument("--api_key", help="Pixabay API key (optional, can use .env file)")
    
    args = parser.parse_args()
    
    try:
        image_paths, image_durations, segments = get_relevant_images_for_script(
            args.script, args.subtitles, args.output_dir, args.api_key
        )
        
        # Output results
        print(f"\nProcessed {len(segments)} segments and found {len(image_paths)} images.")
        
        # Save segments data to JSON for reference
        with open(os.path.join(args.output_dir, "segments.json"), "w", encoding="utf-8") as f:
            json.dump(segments, f, indent=2)
            
        print(f"Segment data saved to {os.path.join(args.output_dir, 'segments.json')}")
        
    except Exception as e:
        print(f"Error: {e}")
