import httpx
import lxml.html
import os
import re
from dotenv import load_dotenv

load_dotenv()

def get_html(url):
    # Paste your cookie string here
    my_cookie = os.getenv("my_cookie")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Cookie": my_cookie
    }
    
    response = httpx.get(url, headers=headers, follow_redirects=True)
    
    # Safety Check: If we still get redirected to a login page, stop!
    if "sign_in" in response.url.path:
        print("Error: Cookie expired or invalid.")
        return None

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
    '''
    return: dict of lists
    '''
    shelf_elements = tree.xpath('//*[@id="shelves"]//a[contains(@class, "userShowPageShelfListItem")]')
    bookshelves = []
    
    for shelf in shelf_elements:
        text = shelf.text_content()
        link = shelf.get("href")

        match = re.search(r"(.+)\u200e?\s+\((\d+)\)", text)

        if match:
            count = int(match.group(2))
            if count > 0:
                raw_name = match.group(1)
                clean_name = raw_name.replace("\u200e", "").strip()
                bookshelves.append({
                    "name": clean_name, 
                    "count": int(count),
                    "link": f"https://www.goodreads.com{link}"
                })
            else:
                continue

    return bookshelves


def fetch_or_load(filename, url, refresh=False):
    # Only fetch if the file doesn't exist OR if we explicitly ask for a refresh
    if not os.path.exists(filename) or refresh:
        print("Fetching fresh data from Goodreads...")
        html = get_html(url)
        with open(filename, "w", encoding="utf-8") as f: 
            f.write(html)
    else:
        print("Loading from cache...")
        with open(filename, "r", encoding="utf-8") as f: 
            html = f.read()
    
    return html

def extract_books(tree, shelf):
    # Find all the rows first
    rows = tree.xpath('//tr[contains(@class, "bookalike review")]')
    book_list = []

    for row in rows:
        title = safe_extract(row, './/td[@class="field title"]//a/text()')
        author = safe_extract(row, './/td[@class="field author"]//a/text()')
        date_read_raw = safe_extract(row, './/td[@class="field date_read"]//span/text()')
        date_read = "" if date_read_raw == "not set" else date_read_raw
        rating = safe_extract(row, './/div[@class="stars"]/@data-rating')
        date_added = safe_extract(row, './/td[@class="field date_added"]//span/text()')

        book_list.append({
            "title": title,
            "author": author,
            "rating": rating,
            "shelf": shelf,
            "date_read": date_read,
            "date_added": date_added

        })

    return book_list

def get_next_page_url(tree):
    '''
    Takes the URL to a page and returns the URL to the next page if one exists.

    If no next page, return None
    '''
    next_page_link = tree.xpath('//div[@id="reviewPagination"]//a[contains(@class, "next_page")]/@href')

    if next_page_link: 
        return "https://www.goodreads.com/" + next_page_link[0]
    else:
        return None


def safe_extract(element, xpath_query):
    """
    Safely extracts text or attributes. 
    Returns the string if found, otherwise an empty string or None.
    """
    result = element.xpath(xpath_query)
    
    if result:
        # We found at least one match, return the first one cleaned up
        return result[0].strip()
    
    # If the list is empty, return a default value
    return "N/A"

def populate_csv(books):
    pass


def main():
    # Get Profile Data
    user_id = os.getenv("GOODREADS_USER") or input("Enter Goodreads ID: ")
    filename = f'html_files/user_{user_id}.html'
    url = f"https://www.goodreads.com/user/show/{user_id}"
    html = fetch_or_load(filename, url, refresh=False)
    tree = parse_html(html)
    name = extract_user_name(tree) 

    # Get Lists (Bookshelves)
    bookshelves = extract_bookshelves(tree)
    ## Change this to a for loop ATTENTION HERE HREHREHREHREHRHEHREH
    url = bookshelves[0]["link"]
    filename = f'html_files/{name}_{bookshelves[0]["name"]}_{bookshelves[0]["count"]}.html'
    html = fetch_or_load(filename, url)
    tree = parse_html(html)
    ## --
    print(extract_books(tree, bookshelves[0]["name"]))
    get_next_page_url(tree)


    # print(f"\nExtracting Data for User: {name}")
    # print("Extracting books from the list(s): ")
    # for item in bookshelves:
    #     print(f'- {item["name"]}')
    # print(" -> All other lists are empty")
    #print(f'{bookshelves}')




if __name__ == "__main__":
    main()