import httpx
import lxml.html
import os
import re
import csv
import random
import time
from dotenv import load_dotenv

load_dotenv()


class RateLimiter:
    def __init__(self, min_delay=2, max_delay=15):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = 0

    def wait(self):
        # Calculate how long it's been since the last call
        elapsed = time.time() - self.last_request_time
        # Generate a random target delay (the "jitter")
        target_delay = random.uniform(self.min_delay, self.max_delay)

        if elapsed < target_delay:
            remaining = target_delay - elapsed
            time.sleep(remaining)

        # Update the timestamp for the next call
        self.last_request_time = time.time()


limiter = RateLimiter(min_delay=3, max_delay=7)


def get_html(url, retries=3):
    """
    Fetches HTML with a retry mechanism and custom timeout.
    """
    # Custom timeout
    timeout = httpx.Timeout(20.0, connect=10.0)

    for attempt in range(retries):
        try:
            limiter.wait()

            my_cookie = os.getenv("my_cookie")
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Cookie": my_cookie,
            }

            print(f"Requesting (Attempt {attempt + 1}): {url}...")

            response = httpx.get(
                url, headers=headers, follow_redirects=True, timeout=timeout
            )

            # If we get a rate limit error (429), sleep longer and retry
            if response.status_code == 429:
                print("Rate limited! Sleeping for 30 seconds...")
                time.sleep(30)
                continue

            response.raise_for_status()

            if "sign_in" in response.url.path:
                print("Error: Cookie expired.")
                return None

            return response.text

        except (httpx.ReadTimeout, httpx.ConnectTimeout):
            print(f"Timeout on {url}. Retrying in 5s...")
            time.sleep(5)
        except httpx.HTTPStatusError as e:
            print(f"HTTP Error {e.response.status_code} for {url}. Skipping...")
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None

    print(f"Failed to fetch {url} after {retries} attempts.")
    return None


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
    """
    return: list of dicts
    """
    shelf_elements = tree.xpath(
        '//*[@id="shelves"]//a[contains(@class, "userShowPageShelfListItem")]'
    )
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
                bookshelves.append(
                    {
                        "name": clean_name,
                        "count": int(count),
                        "link": f"https://www.goodreads.com{link}",
                    }
                )
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

        isbn13_raw = safe_extract(
            row, './/td[@class="field isbn13"]//div[@class="value"]/text()'
        )
        isbn13 = "" if isbn13_raw.lower() == "not set" else isbn13_raw

        date_read_raw = safe_extract(
            row, './/td[@class="field date_read"]//span/text()'
        )
        date_read = "" if date_read_raw == "not set" else date_read_raw
        rating = safe_extract(row, './/div[@class="stars"]/@data-rating')
        date_added = safe_extract(row, './/td[@class="field date_added"]//span/text()')

        book_list.append(
            {
                "title": title,
                "author": author,
                "isbn13": isbn13,
                "rating": rating,
                "shelf": shelf["name"],
                "date_read": date_read,
                "date_added": date_added,
            }
        )

    return book_list


def get_next_page_url(tree):
    """
    Takes the URL to a page and returns the URL to the next page if one exists.

    If no next page, return None
    """
    next_page_link = tree.xpath(
        '//div[@id="reviewPagination"]//a[contains(@class, "next_page")]/@href'
    )

    if next_page_link:
        return "https://www.goodreads.com" + next_page_link[0]
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


def populate_csv(books, csv_filename="csv_files/shelves.csv"):
    """
    Get all the list of dictionaries with all bookshelves and create a csv
    """
    HEADERS = [
        "title",
        "author",
        "isbn13",
        "rating",
        "shelf",
        "date_read",
        "date_added",
    ]
    # Writing to CSV
    with open(csv_filename, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=HEADERS)
        writer.writeheader()  # Write header row
        writer.writerows(books)  # Write data rows


def scrape_info_from_user_page(user_id):
    """
    Extract name and list of dict with the user's (populated) bookshelves

    returns:
        - name -> Name of user
        - bookshelves -> List of dict:
            name: str(name of bookshelf)
            count: int(amount of books in given bookshelf)
            link: str(link to the bookshelf)
    """
    # Prepare file and extract + parse html from user's profile page
    filename = f"html_files/user_{user_id}.html"
    url = f"https://www.goodreads.com/user/show/{user_id}"

    html = fetch_or_load(filename, url, refresh=False)
    tree = parse_html(html)

    name = extract_user_name(tree)

    bookshelves = extract_bookshelves(tree)

    return name, bookshelves


def scrape_bookshelf(name, bookshelf):
    counter = 1
    filename = (
        f"html_files/{name}_{bookshelf['name']}_{bookshelf['count']}_{counter}.html"
    )
    url = bookshelf["link"]

    html = fetch_or_load(filename, url)
    tree = parse_html(html)

    books = extract_books(tree, bookshelf)

    while get_next_page_url(tree):
        counter += 1
        filename = (
            f"html_files/{name}_{bookshelf['name']}_{bookshelf['count']}_{counter}.html"
        )
        url = get_next_page_url(tree)

        html = fetch_or_load(filename, url)
        tree = parse_html(html)

        books.extend(extract_books(tree, bookshelf))

    return books


def cleanup_html_files(folder="html_files"):
    """
    Deletes all .html files in the specified folder,
    but keeps the .gitkeep file.
    """
    if not os.path.exists(folder):
        return

    # List all files in the directory
    files = [f for f in os.listdir(folder) if f.endswith(".html")]

    if not files:
        print("No HTML files found to clean up.")
        return

    print(f"Found {len(files)} HTML files in '{folder}'.")
    confirm = input("You want to delete these cache files? (y/n): ").lower()

    if confirm == "y":
        for file in files:
            file_path = os.path.join(folder, file)
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error deleting {file}: {e}")
        print("Done! HTML files have been cleared.")
    else:
        print("Cleanup cancelled. Files kept for caching.")


def main():
    for folder in ["html_files", "csv_files"]:
        os.makedirs(folder, exist_ok=True)

    # Get Profile Data (User Name & Bookshelves)
    user_id = os.getenv("GOODREADS_USER") or input("Enter Goodreads ID: ")
    try:
        name, bookshelves = scrape_info_from_user_page(user_id)

        # Feedback for user:
        print(f"\nExtracting Data for User: {name}")
        print("Extracting books from the list(s): ")
        for item in bookshelves:
            print(f"- {item['name']}")
        print(" -> All other lists are empty")

        all_books = []

        for shelf in bookshelves:
            all_books.extend(scrape_bookshelf(name, shelf))

        populate_csv(all_books)

        cleanup_html_files()

    except KeyboardInterrupt:
        print("\n\nStopping script... progress saved in html_files cache.")
    except Exception as e:
        print(f"\n A critical error occurred: {e}")


if __name__ == "__main__":
    main()
