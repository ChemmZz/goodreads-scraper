import httpx
import lxml.html
import os
import re

def get_html(user_id):
    """
    Return the HTML for a given GoodReads user.
    """
    url = f"https://www.goodreads.com/user/show/{user_id}"

    # User-Agent to not get blocked automatically
    headers = {"User-Agent": "Mozilla/5.0"}
    response = httpx.get(url, headers=headers)

    return response.text

def parse_html(html):
    """
    Converts a raw string into a searchable HTML tree.
    """
    return lxml.html.fromstring(html)

def extract_user_name(tree):
    """Extracts the user's name from the tree."""
    name_element = tree.xpath('//*[@id="profileNameTopHeading"]')

    if name_element:
        return name_element[0].text_content().strip()
    else:
        return "User name not found"
    

def extract_bookshelves(tree):
    raw_shelves = tree.xpath('//*[@id="shelves"]//a/text()')
    
    bookshelves = []
    
    for s in raw_shelves:
        # regex to capture the name and the number
        match = re.search(r"(.+)\u200e?\s+\((\d+)\)", s)
        
        if match:
            raw_name = match.group(1)
            clean_name = raw_name.replace("\u200e", "").strip()
            count = int(match.group(2))
            bookshelves.append({"name": clean_name, "count": count})
            
    return bookshelves


def main():
    user_id = os.getenv("GOODREADS_USER") or input("Enter Goodreads ID: ")
    filename = f'files/user_{user_id}.html'

    if os.path.exists(filename):
        print("Loading from local cache...")
        with open(filename, "r", encoding="utf-8") as f:
            html = f.read()
    else:
        print("Fetching from Goodreads...")
        html = get_html(user_id)
        # Save it to not fetch it next time
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)

    tree = parse_html(html)
    name = extract_user_name(tree) 
    
    print(f"\nExtract Data for User: {name}")
    print(extract_bookshelves(tree))


if __name__ == "__main__":
    main()