#!/usr/bin/env python3
# title_cards.py - Generate intro and outro title cards for videos

import os
import argparse
import re
from PIL import Image, ImageDraw, ImageFont
import textwrap
import subprocess

def normalize_path(path):
    """
    Normalize a path for cross-platform compatibility with FFmpeg.
    """
    # Get absolute path
    path = os.path.abspath(path)
    
    # Remove any duplicate directory references
    path = re.sub(r'(/|\\)temp\1temp\1', r'\1temp\1', path)
    
    # Convert backslashes to forward slashes for FFmpeg
    path = path.replace('\\', '/')
    
    return path

def create_title_card(title, output_path, width=1920, height=1080, 
                      bg_color=(5, 5, 30), text_color=(240, 240, 255)):
    """
    Create a simple title card image with the given title.
    
    Args:
        title (str): Title text for the card
        output_path (str): Path to save the image
        width (int): Image width in pixels
        height (int): Image height in pixels
        bg_color (tuple): Background color as RGB tuple
        text_color (tuple): Text color as RGB tuple
    
    Returns:
        str: Path to the created image
    """
    try:
        # Create a blank image with background color
        image = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(image)
        
        # Try to load a font, fall back to default if not available
        try:
            # Try to use a nicer font if available
            title_font = ImageFont.truetype("Arial", 80)
            subtitle_font = ImageFont.truetype("Arial", 40)
        except OSError:
            # Fall back to default font
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
        
        # Wrap the title text to fit the image width
        wrapper = textwrap.TextWrapper(width=30)  # Adjust based on your font size
        wrapped_title = wrapper.fill(title)
        
        # Calculate text position (centered)
        title_bbox = draw.textbbox((0, 0), wrapped_title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_height = title_bbox[3] - title_bbox[1]
        
        x = (width - title_width) // 2
        y = (height - title_height) // 2 - 50  # Shift up slightly
        
        # Draw the title
        draw.text((x, y), wrapped_title, font=title_font, fill=text_color, align="center")
        
        # Draw a subtitle
        subtitle = "An AI-generated documentary"
        subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        
        x = (width - subtitle_width) // 2
        y = y + title_height + 40  # Position below the title
        
        draw.text((x, y), subtitle, font=subtitle_font, fill=text_color)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save the image
        image.save(output_path)
        print(f"Title card created: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error creating title card: {e}")
        return None

def create_outro_card(title, output_path, width=1920, height=1080, 
                     bg_color=(5, 5, 30), text_color=(240, 240, 255)):
    """
    Create an outro card with credits.
    
    Args:
        title (str): Title text for the video
        output_path (str): Path to save the image
        width (int): Image width in pixels
        height (int): Image height in pixels
        bg_color (tuple): Background color as RGB tuple
        text_color (tuple): Text color as RGB tuple
    
    Returns:
        str: Path to the created image
    """
    import time
    try:
        # Create a blank image with background color
        image = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(image)
        
        # Try to load fonts
        try:
            title_font = ImageFont.truetype("Arial", 60)
            credits_font = ImageFont.truetype("Arial", 30)
        except OSError:
            title_font = ImageFont.load_default()
            credits_font = ImageFont.load_default()
        
        # Draw the title
        title_text = f"Thanks for watching\n\"{title}\""
        wrapper = textwrap.TextWrapper(width=40)
        wrapped_title = wrapper.fill(title_text)
        
        title_bbox = draw.textbbox((0, 0), wrapped_title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_height = title_bbox[3] - title_bbox[1]
        
        x = (width - title_width) // 2
        y = 200  # Position from top
        
        draw.text((x, y), wrapped_title, font=title_font, fill=text_color, align="center")
        
        # Draw credits
        credits = [
            "Generated using AI technology",
            "Content sourced from Wikipedia",
            "Narration by ElevenLabs",
            "© " + time.strftime("%Y")
        ]
        
        y = height - 300  # Start position for credits
        for line in credits:
            bbox = draw.textbbox((0, 0), line, font=credits_font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            
            draw.text((x, y), line, font=credits_font, fill=text_color)
            y += 50  # Space between lines
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save the image
        image.save(output_path)
        print(f"Outro card created: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error creating outro card: {e}")
        return None

def add_title_cards_to_video(video_path, title, temp_dir, output_path=None):
    """
    Add intro and outro title cards to a video.
    
    Args:
        video_path (str): Path to the input video
        title (str): Video title
        temp_dir (str): Directory for temporary files
        output_path (str): Path for the output video (default: original filename + _with_titles)
    
    Returns:
        str: Path to the output video
    """
    if not output_path:
        filename, ext = os.path.splitext(video_path)
        output_path = f"{filename}_with_titles{ext}"
    
    # Normalize all paths and ensure they're absolute
    video_path = normalize_path(video_path)
    temp_dir = normalize_path(temp_dir)
    output_path = normalize_path(output_path)
    
    # Create temp directory if it doesn't exist
    os.makedirs(temp_dir, exist_ok=True)
    
    # Create title cards
    intro_path = os.path.join(temp_dir, "intro_card.png")
    outro_path = os.path.join(temp_dir, "outro_card.png")
    
    intro_path = normalize_path(intro_path)
    outro_path = normalize_path(outro_path)
    
    create_title_card(title, intro_path)
    create_outro_card(title, outro_path)
    
    # Create temporary files for the intro and outro videos
    intro_video = os.path.join(temp_dir, "intro.mp4") 
    outro_video = os.path.join(temp_dir, "outro.mp4")
    
    intro_video = normalize_path(intro_video)
    outro_video = normalize_path(outro_video)
    
    # Convert intro image to video (5 seconds)
    try:
        # Print all paths for debugging
        print(f"Creating intro video:")
        print(f"  Source: {intro_path}")
        print(f"  Output: {intro_video}")
        
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", intro_path, "-c:v", "libx264",
            "-t", "5", "-pix_fmt", "yuv420p", "-vf", "scale=1920:1080", intro_video
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error creating intro video: {e}")
        # Create a fallback video without the title cards
        import shutil
        shutil.copy2(video_path, output_path)
        return output_path
    
    # Convert outro image to video (5 seconds)
    try:
        print(f"Creating outro video:")
        print(f"  Source: {outro_path}")
        print(f"  Output: {outro_video}")
        
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", outro_path, "-c:v", "libx264",
            "-t", "5", "-pix_fmt", "yuv420p", "-vf", "scale=1920:1080", outro_video
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error creating outro video: {e}")
        # If intro succeeded but outro failed, try with just the intro
        try:
            # Create a list file with just the intro and main video
            concat_list = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_list, "w") as f:
                f.write(f"file '{intro_video}'\n")
                f.write(f"file '{video_path}'\n")
            
            # Concatenate just the intro and main video
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                "-c", "copy", output_path
            ], check=True)
            
            print(f"Video with intro card only created: {output_path}")
            return output_path
        except Exception:
            # Fall back to the original video if concatenation fails
            import shutil
            shutil.copy2(video_path, output_path)
            return output_path
    
    # Create a list file for concatenation with absolute paths
    concat_list = os.path.join(temp_dir, "concat_list.txt")
    
    # Debug: print paths before writing to concat file
    print(f"\nPaths for concatenation:")
    print(f"  Intro: {intro_video}")
    print(f"  Main: {video_path}")
    print(f"  Outro: {outro_video}")
    print(f"  Concat list: {concat_list}")
    
    with open(concat_list, "w") as f:
        f.write(f"file '{intro_video}'\n")
        f.write(f"file '{video_path}'\n")
        f.write(f"file '{outro_video}'\n")
    
    # Print the content of the concat file for debugging
    print("\nContent of concat file:")
    with open(concat_list, "r") as f:
        print(f.read())
    
    # Concatenate the videos
    try:
        print(f"\nConcatenating videos to: {output_path}")
        
        concat_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
            "-c", "copy", output_path
        ]
        
        print(f"Command: {' '.join(concat_cmd)}")
        
        subprocess.run(concat_cmd, check=True)
        
        print(f"Video with title cards created: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Error during concatenation: {e}")
        
        # Try an alternative concatenation approach
        try:
            print("\nTrying alternative concatenation method...")
            
            # Create a temporary file to hold the merged intro+main
            temp_merged = os.path.join(temp_dir, "intro_main_merged.mp4")
            
            # First merge intro with main video
            subprocess.run([
                "ffmpeg", "-y", "-i", intro_video, "-i", video_path,
                "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", 
                "-map", "[v]", "-c:v", "libx264", temp_merged
            ], check=True)
            
            # Then merge the result with outro
            subprocess.run([
                "ffmpeg", "-y", "-i", temp_merged, "-i", outro_video,
                "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", 
                "-map", "[v]", "-c:v", "libx264", output_path
            ], check=True)
            
            print(f"Video created with alternative method: {output_path}")
            return output_path
        except Exception as fallback_e:
            print(f"Alternative method also failed: {fallback_e}")
            # Provide a fallback
            import shutil
            shutil.copy2(video_path, output_path)
            print(f"Using video without title cards as final output: {output_path}")
            return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create title cards for videos")
    parser.add_argument("--title", required=True, help="Video title")
    parser.add_argument("--video", help="Input video to add title cards to")
    parser.add_argument("--output", help="Output path for the processed video")
    parser.add_argument("--temp_dir", default="temp", help="Directory for temporary files")
    
    args = parser.parse_args()
    
    os.makedirs(args.temp_dir, exist_ok=True)
    
    if args.video:
        # Add title cards to existing video
        add_title_cards_to_video(args.video, args.title, args.temp_dir, args.output)
    else:
        # Just create the title cards
        intro_path = os.path.join(args.temp_dir, "intro_card.png")
        outro_path = os.path.join(args.temp_dir, "outro_card.png")
        
        create_title_card(args.title, intro_path)
        create_outro_card(args.title, outro_path)
        
        print(f"Title cards created at {args.temp_dir}")
