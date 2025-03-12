import requests
from bs4 import BeautifulSoup
import os
import re
import urllib.parse

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
        "prop": "text|sections|displaytitle|categories|links|templates|externallinks",
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
