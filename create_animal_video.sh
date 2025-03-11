#!/bin/bash
# Example script to create a video about interesting jungle animals

# Make sure we have the required packages
pip install -r requirements.txt

# Make the script executable
chmod +x video_creator.py

# Create the video
./video_creator.py \
  --title "10 Most Interesting Animals in the Jungle" \
  --links \
    https://en.wikipedia.org/wiki/Jungle \
    https://en.wikipedia.org/wiki/Jaguar \
    https://en.wikipedia.org/wiki/Toucan \
    https://en.wikipedia.org/wiki/Anaconda \
    https://en.wikipedia.org/wiki/Okapi \
    https://en.wikipedia.org/wiki/Orangutan \
    https://en.wikipedia.org/wiki/Poison_dart_frog \
    https://en.wikipedia.org/wiki/Chameleon \
  --length 3000 \
  --output "jungle_animals_video.mp4"

echo "Video creation process completed!"
