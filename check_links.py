import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import concurrent.futures

# Base URL for relative links
BASE_URL = "https://thirdgearinnovators.org/"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Track checked URLs to avoid duplicates
checked_urls = set()
broken_links = []

def is_valid_url(url):
    """Check if a URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def check_url(url, source_file):
    """Check if a URL is accessible"""
    if url in checked_urls or not url:
        return
    
    checked_urls.add(url)
    
    # Skip anchor links
    if url.startswith('#'):
        return
        
    # Handle mailto links
    if url.startswith('mailto:'):
        email = url[7:]
        if '@' not in email or '.' not in email.split('@')[-1]:
            broken_links.append((url, source_file, "Invalid email format"))
        return
    
    # Check if it's a relative path
    if not (url.startswith('http') or url.startswith('//')):
        # Handle relative URLs
        if url.startswith('/'):
            # Root-relative URL
            abs_path = os.path.join(BASE_DIR, url[1:])
        else:
            # Relative to current file
            abs_path = os.path.join(os.path.dirname(os.path.abspath(source_file)), url)
        
        # Normalize path
        abs_path = os.path.normpath(abs_path)
        
        # Check if file exists
        if not os.path.exists(abs_path):
            # Check if it's a directory (for index.html)
            if os.path.exists(os.path.join(abs_path, 'index.html')):
                return
            # Check with .html extension
            if not abs_path.endswith('.html') and os.path.exists(abs_path + '.html'):
                return
                
            # Special case for gallery.html which is planned but doesn't exist yet
            if os.path.basename(abs_path) == 'gallery.html':
                print(f"Note: {url} is a planned page that doesn't exist yet")
                return
                
            # If we get here, the file doesn't exist
            broken_links.append((url, source_file, "File not found"))
        return
    
    # Handle protocol-relative URLs
    if url.startswith('//'):
        url = 'https:' + url
    
    # Check if it's a mailto link
    if url.startswith('mailto:'):
        # Just check if it's a valid email format
        if '@' not in url[7:]:
            broken_links.append((url, source_file, "Invalid email format"))
        return
    
    # Check if it's an anchor link
    if url.startswith('#'):
        return
    
    # Check external URLs
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
        if response.status_code >= 400:
            broken_links.append((url, source_file, f"HTTP {response.status_code}"))
    except requests.RequestException as e:
        broken_links.append((url, source_file, str(e)))

def check_file(file_path):
    """Check all links in an HTML file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Check all anchor tags
        for a in soup.find_all('a', href=True):
            url = a['href']
            if not url.startswith('javascript:'):
                check_url(url, file_path)
        
        # Check all image sources
        for img in soup.find_all('img', src=True):
            check_url(img['src'], file_path)
        
        # Check all script sources
        for script in soup.find_all('script', src=True):
            check_url(script['src'], file_path)
        
        # Check all link tags (CSS, favicons, etc.)
        for link in soup.find_all('link', href=True):
            check_url(link['href'], file_path)
            
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")

def main():
    # Get all HTML files in the directory
    html_files = []
    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))
    
    # Check all files using threads for better performance
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(check_file, html_files)
    
    # Print results
    if broken_links:
        print("\nBroken or potentially problematic links found:")
        for url, source, error in broken_links:
            print(f"- {url}")
            print(f"  Source: {os.path.relpath(source, BASE_DIR)}")
            print(f"  Error: {error}")
            
            # Suggest fixes for common issues
            if error == "File not found" and not ('http' in url or '//' in url):
                abs_path = os.path.join(os.path.dirname(os.path.abspath(source)), url)
                abs_path = os.path.normpath(abs_path)
                rel_path = os.path.relpath(abs_path, BASE_DIR)
                
                # Check for common file extensions
                for ext in ['', '.html', '.jpg', '.png', '.css', '.js']:
                    if os.path.exists(abs_path + ext):
                        print(f"  Suggestion: Update link to '{url + ext}'")
                        break
                    if os.path.exists(os.path.join(abs_path, 'index.html')):
                        print(f"  Suggestion: Update link to '{os.path.join(url, 'index.html')}'")
                        break
            print()  # Add blank line between entries
    else:
        print("No broken links found!")
    
    print(f"\nChecked {len(checked_urls)} unique URLs across {len(html_files)} files.")
    
    # List all HTML files for reference
    print("\nHTML files checked:")
    for file in sorted(html_files):
        print(f"- {os.path.relpath(file, BASE_DIR)}")
        
    # List all image files for reference
    image_files = []
    for root, _, files in os.walk(os.path.join(BASE_DIR, 'images')):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                image_files.append(os.path.relpath(os.path.join(root, file), BASE_DIR))
    
    if image_files:
        print("\nImage files found:")
        for img in sorted(image_files):
            print(f"- {img}")

if __name__ == "__main__":
    main()
