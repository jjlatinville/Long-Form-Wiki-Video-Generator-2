import requests
from bs4 import BeautifulSoup
import os
import re
import urllib.parse
import time
import random
from PIL import Image
from io import BytesIO

def extract_wiki_title(wiki_url):
    """
    Extract the page title from a Wikipedia URL.
    
    Args:
        wiki_url (str): Full URL to a Wikipedia page
        
    Returns:
        str: The page title
    """
    # Extract the page title from the URL
    if '/wiki/' in wiki_url:
        title = wiki_url.split('/wiki/')[1].split('#')[0].split('?')[0]
        # Replace underscores with spaces and URL decode
        title = urllib.parse.unquote(title).replace('_', ' ')
        return title
    return None

def get_wiki_content_via_api(page_title):
    """
    Fetch text content from a Wikipedia page using the official API.
    
    Args:
        page_title (str): The title of the Wikipedia page
        
    Returns:
        dict: Dictionary containing sections, content, and other metadata
    """
    # Base API URL
    api_url = "https://en.wikipedia.org/w/api.php"
    
    # Parameters for retrieving page content
    params = {
        "action": "parse",
        "page": page_title,
        "format": "json",
        "prop": "text|sections|displaytitle|images|categories|links|templates|externallinks",
        "disabletoc": 1,
        "disableeditsection": 1
    }
    
    # Make the API request
    response = requests.get(api_url, params=params)
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"API request failed with status code: {response.status_code}")
        return None
    
    # Parse the JSON response
    data = response.json()
    
    # Check if the page was found
    if "error" in data:
        print(f"API error: {data['error'].get('info', 'Unknown error')}")
        return None
    
    return data['parse'] if 'parse' in data else None

def process_wiki_content(api_data):
    """
    Process the Wikipedia API content into a readable text format.
    
    Args:
        api_data (dict): API data from the Wikipedia API
        
    Returns:
        tuple: (plain_text, html_text) versions of the content
    """
    if not api_data or 'text' not in api_data or '*' not in api_data['text']:
        return "Failed to retrieve page content", None
    
    # Get the HTML content
    html_content = api_data['text']['*']
    
    # Parse the HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove unwanted elements
    for unwanted in soup.select('.mw-editsection, .reference, .mw-empty-elt, .noprint, .mbox-image'):
        unwanted.decompose()
    
    # Extract the title
    title = api_data.get('displaytitle', api_data.get('title', 'Untitled'))
    title = BeautifulSoup(title, 'html.parser').get_text()
    
    # Start with the title
    plain_text = f"# {title}\n\n"
    
    # Process sections from the API data
    sections = api_data.get('sections', [])
    section_dict = {section['index']: section for section in sections}
    
    # Process the main content
    for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'table']):
        # Skip elements in unwanted sections
        if any(parent.get('class', '') and any(c in ' '.join(parent.get('class', '')) for c in 
              ['toc', 'sidebar', 'navbox', 'vertical-navbox']) 
              for parent in element.parents):
            continue
            
        if element.name.startswith('h'):
            # For headings, add proper formatting
            level = int(element.name[1])
            heading_text = element.get_text().strip()
            # Remove section numbers if present
            heading_text = re.sub(r'^\[\s*edit\s*\]', '', heading_text)
            plain_text += '\n' + '#' * level + ' ' + heading_text + '\n\n'
        elif element.name == 'p':
            # For paragraphs
            paragraph_text = element.get_text().strip()
            if paragraph_text:  # Skip empty paragraphs
                plain_text += paragraph_text + '\n\n'
        elif element.name in ['ul', 'ol']:
            # For lists
            for li in element.find_all('li', recursive=False):
                item_text = li.get_text().strip()
                plain_text += '- ' + item_text + '\n'
            plain_text += '\n'
        elif element.name == 'table':
            # For tables, include a note
            caption = element.find('caption')
            if caption:
                plain_text += f"[Table: {caption.get_text().strip()}]\n\n"
            else:
                plain_text += "[Table content]\n\n"
    
    # Add metadata at the end
    if 'categories' in api_data:
        plain_text += "\n## Categories\n"
        for cat in api_data['categories']:
            cat_name = cat['*'].replace('Category:', '')
            plain_text += f"- {cat_name}\n"
    
    if 'externallinks' in api_data:
        plain_text += "\n## External Links\n"
        for link in api_data['externallinks']:
            plain_text += f"- {link}\n"
    
    return plain_text.strip(), html_content

def get_headers():
    """
    Generate random user agent headers to avoid being blocked.
    """
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36 Edg/98.0.1108.56",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
    ]
    
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://commons.wikimedia.org/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

def get_commons_category_images(page_name, max_images=15):
    """
    Extract images from a Wikimedia Commons category page.
    
    Args:
        page_name (str): The Wikipedia page name to use for the Commons category
        max_images (int): Maximum number of images to fetch
        
    Returns:
        list: List of image info dictionaries with thumbnail and page URLs
    """
    # Form the Commons category URL
    commons_url = f"https://commons.wikimedia.org/wiki/Category:{page_name.replace(' ', '_')}"
    print(f"Fetching images from: {commons_url}")
    
    try:
        response = requests.get(commons_url, headers=get_headers())
        
        # Check if we got redirected to a search page (category doesn't exist)
        if "Special:Search" in response.url:
            print(f"Category does not exist: {commons_url}")
            # Try to fetch from the File: namespace instead
            return get_commons_file_namespace(page_name, max_images)
        
        if response.status_code != 200:
            print(f"Failed to access category {commons_url}, status code: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find gallery or category items
        images = []
        count = 0
        
        # Find all gallery items
        gallery = soup.find('ul', {'class': 'gallery'})
        if gallery:
            for li in gallery.find_all('li', {'class': 'gallerybox'}):
                if count >= max_images:
                    break
                    
                # Extract the thumbnail image and the file page link
                thumb = li.find('img')
                link = li.find('a', {'class': 'image'})
                
                if thumb and link and 'src' in thumb.attrs and 'href' in link.attrs:
                    thumb_url = thumb['src']
                    if not thumb_url.startswith('http'):
                        thumb_url = 'https:' + thumb_url
                        
                    file_page = link['href']
                    if not file_page.startswith('http'):
                        file_page = 'https://commons.wikimedia.org' + file_page
                    
                    # Get the title/filename
                    filename = file_page.split('/')[-1]
                    filename = urllib.parse.unquote(filename)
                    
                    images.append({
                        'filename': filename,
                        'thumbnail_url': thumb_url,
                        'file_page': file_page
                    })
                    
                    count += 1
                    print(f"Found image {count}/{max_images}")
        
        # If we didn't find enough in the gallery, look for thumbnails too
        if count < max_images:
            for thumb_div in soup.find_all('div', {'class': 'thumb'}):
                if count >= max_images:
                    break
                    
                thumb = thumb_div.find('img')
                link = thumb_div.find('a', {'class': 'image'})
                
                if thumb and link and 'src' in thumb.attrs and 'href' in link.attrs:
                    thumb_url = thumb['src']
                    if not thumb_url.startswith('http'):
                        thumb_url = 'https:' + thumb_url
                        
                    file_page = link['href']
                    if not file_page.startswith('http'):
                        file_page = 'https://commons.wikimedia.org' + file_page
                    
                    # Get the title/filename
                    filename = file_page.split('/')[-1]
                    filename = urllib.parse.unquote(filename)
                    
                    images.append({
                        'filename': filename,
                        'thumbnail_url': thumb_url,
                        'file_page': file_page
                    })
                    
                    count += 1
                    print(f"Found image {count}/{max_images}")
        
        if not images:
            print("No images found in the Commons category. Trying the File: namespace.")
            return get_commons_file_namespace(page_name, max_images)
            
        return images
        
    except Exception as e:
        print(f"Error processing Commons category: {e}")
        return []

def get_commons_file_namespace(page_name, max_images=15):
    """
    Try to find images in the File: namespace if the Category doesn't exist.
    
    Args:
        page_name (str): The Wikipedia page name
        max_images (int): Maximum number of images to fetch
        
    Returns:
        list: List of image info dictionaries with thumbnail and page URLs
    """
    # Create a search URL for the file namespace
    search_url = f"https://commons.wikimedia.org/w/index.php?search={urllib.parse.quote(page_name)}&title=Special:MediaSearch&type=image"
    print(f"Trying media search: {search_url}")
    
    try:
        response = requests.get(search_url, headers=get_headers())
        if response.status_code != 200:
            print(f"Failed to search media, status code: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        images = []
        count = 0
        
        # Look for search results
        results = soup.find_all('a', {'class': 'sdms-image-result'})
        for result in results:
            if count >= max_images:
                break
                
            if 'href' in result.attrs:
                file_page = result['href']
                if not file_page.startswith('http'):
                    file_page = 'https://commons.wikimedia.org' + file_page
                
                # Find the thumbnail image
                img = result.find('img')
                if img and 'src' in img.attrs:
                    thumb_url = img['src']
                    if not thumb_url.startswith('http'):
                        thumb_url = 'https:' + thumb_url
                    
                    # Get the title/filename
                    filename = file_page.split('/')[-1]
                    filename = urllib.parse.unquote(filename)
                    
                    images.append({
                        'filename': filename,
                        'thumbnail_url': thumb_url,
                        'file_page': file_page
                    })
                    
                    count += 1
                    print(f"Found image {count}/{max_images}")
        
        # If no results in the modern search, try the older search result format
        if not images:
            results = soup.find_all('div', {'class': 'searchResultImage'})
            for result in results:
                if count >= max_images:
                    break
                    
                link = result.find('a')
                img = result.find('img')
                
                if link and img and 'href' in link.attrs and 'src' in img.attrs:
                    file_page = link['href']
                    if not file_page.startswith('http'):
                        file_page = 'https://commons.wikimedia.org' + file_page
                    
                    thumb_url = img['src']
                    if not thumb_url.startswith('http'):
                        thumb_url = 'https:' + thumb_url
                    
                    # Get the title/filename
                    filename = file_page.split('/')[-1]
                    filename = urllib.parse.unquote(filename)
                    
                    images.append({
                        'filename': filename,
                        'thumbnail_url': thumb_url,
                        'file_page': file_page
                    })
                    
                    count += 1
                    print(f"Found image {count}/{max_images}")
                        
        return images
    
    except Exception as e:
        print(f"Error processing Commons search: {e}")
        return []

def find_larger_thumbnail(file_page, min_width=800):
    """
    Find a larger thumbnail from the file page.
    
    Args:
        file_page (str): URL to the file page
        min_width (int): Minimum width of the image to find
        
    Returns:
        str: URL to a larger thumbnail, or None if not found
    """
    try:
        response = requests.get(file_page, headers=get_headers())
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to find the largest thumbnail that's at least min_width wide
        for size in [1600, 1200, 1000, 800, 600, 400, 300]:
            if size < min_width:
                continue
                
            # Look for size links
            size_links = soup.find_all('a')
            for link in size_links:
                text = link.get_text().strip()
                href = link.get('href', '')
                
                # Match size patterns like "1,600 × 1,200 pixels" or "800 × 600 pixels"
                if re.search(rf'\b{size:,}\b.*pixel', text) and href and '/thumb/' in href:
                    return href if href.startswith('http') else ('https:' + href)
        
        # If we can't find the right size, try to find any image
        img_div = soup.find('div', {'class': 'fullImageLink'})
        if img_div and img_div.find('img'):
            img = img_div.find('img')
            if 'src' in img.attrs:
                return img['src'] if img['src'].startswith('http') else ('https:' + img['src'])
        
        return None
        
    except Exception as e:
        print(f"Error finding larger thumbnail for {file_page}: {e}")
        return None

def download_thumbnail_images(images_list, folder="wiki_images", min_width=800):
    """
    Download thumbnail images (instead of full resolution).
    
    Args:
        images_list (list): List of image info dictionaries
        folder (str): Folder to save images to
        min_width (int): Minimum width to try to get
    
    Returns:
        list: List of saved image filenames
    """
    # Create folder if it doesn't exist
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    saved_images = []
    for img_info in images_list:
        try:
            # Try to get a larger version than the thumbnail
            larger_thumb = find_larger_thumbnail(img_info['file_page'], min_width)
            
            # If we found a larger version, use it, otherwise use the thumbnail
            img_url = larger_thumb if larger_thumb else img_info['thumbnail_url']
            
            filename = img_info['filename']
            
            # Add a small delay between requests
            time.sleep(random.uniform(1.0, 2.0))
            
            # Download the image
            response = requests.get(img_url, headers=get_headers())
            
            if response.status_code == 200:
                # Clean up filename to make it valid for the file system
                safe_filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
                
                # Check if it's a valid image
                try:
                    img = Image.open(BytesIO(response.content))
                    
                    # Save to file
                    file_path = os.path.join(folder, safe_filename)
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    saved_images.append(file_path)
                    print(f"Downloaded: {safe_filename} ({img.width}x{img.height})")
                except Exception as e:
                    print(f"Error processing image {filename}: {e}")
                    
            else:
                print(f"Failed to download {filename}: HTTP {response.status_code}")
        except Exception as e:
            print(f"Error downloading {filename}: {e}")
    
    return saved_images

# Main function
if __name__ == "__main__":
    wiki_url = input("Enter Wikipedia URL: ")
    
    # Extract the page title
    page_title = extract_wiki_title(wiki_url)
    if not page_title:
        print("Could not extract page title from URL.")
        exit(1)
    
    print(f"Page title: {page_title}")
    
    # Get and save text content using the API
    wiki_data = get_wiki_content_via_api(page_title)
    
    if wiki_data:
        text_content, html_content = process_wiki_content(wiki_data)
        
        # Save plain text content
        with open("wiki_content.txt", "w", encoding="utf-8") as f:
            f.write(text_content)
        print("Text content saved to wiki_content.txt")
        
        # Optionally save HTML content
        with open("wiki_content.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("HTML content saved to wiki_content.html")
    else:
        print("Failed to retrieve Wikipedia content")
    
    # Ask if user wants to download images
    download_images = input("Do you want to download images? (y/n): ").lower().strip()
    if download_images != 'y':
        exit(0)
    
    # Get images from Commons
    max_imgs = 15  # Default limit
    try:
        user_max = input("Maximum number of images to download (default 15): ")
        if user_max.strip():
            max_imgs = int(user_max)
    except ValueError:
        print("Invalid number, using default of 15 images")
    
    min_width = 800  # Default minimum width
    try:
        user_width = input("Minimum image width to download (default 800): ")
        if user_width.strip():
            min_width = int(user_width)
    except ValueError:
        print("Invalid width, using default of 800 pixels")
    
    images = get_commons_category_images(page_title, max_images=max_imgs)
    
    # Download the images
    if images:
        saved_imgs = download_thumbnail_images(images, min_width=min_width)
        print(f"Downloaded {len(saved_imgs)} images to the wiki_images folder")
    else:
        print("No images found for this Wikipedia page on Wikimedia Commons")