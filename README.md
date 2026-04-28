# Scrape Your Goodreads Shelves

**Status:** This README is valid and was last updated on April 28, 2026.

A small Python scraper for exporting your Goodreads shelves to CSV. It logs in with your Goodreads browser cookie, gets every non-empty shelf on your profile, and writes all the books metadata to `csv_files/shelves.csv`.

## What it exports

The CSV includes one row per book/shelf entry with these columns:

| Column | Description |
| --- | --- |
| `title` | Book title |
| `author` | Primary author shown by Goodreads |
| `isbn13` | ISBN-13, when Goodreads provides it |
| `rating` | Your Goodreads rating |
| `shelf` | Shelf name |
| `date_read` | Date read, when set |
| `date_added` | Date added to Goodreads |

## Requirements

- Git
- Python 3.13
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- A Goodreads account session cookie

## Setup from scratch

Run these commands from your terminal. Do one step at a time.

### 1. Clone the repository

```bash
git clone https://github.com/ChemmZz/goodreads-scraper.git
```

### 2. Move into the project folder

```bash
cd goodreads-scraper
```

### 3. Install `uv`

This project uses `uv` to install and run Python dependencies.

On macOS or Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installing `uv`, close and reopen your terminal if the `uv` command is not found.

### 4. Install the project dependencies

```bash
uv sync
```

This creates a local virtual environment and installs the packages listed in `pyproject.toml`.

### 5. Run the scraper

```bash
uv run python main.py
```

The first time you run the script, it asks for your Goodreads ID and cookie in the terminal. After you paste them once, the script saves them in a `.env` file so future runs can skip those prompts.

Your Goodreads ID is the value used in your Goodreads profile URL:

```text
https://www.goodreads.com/user/show/YOUR_GOODREADS_ID
```

For example, if your profile URL is `https://www.goodreads.com/user/show/12345678-name`, use:

```text
12345678-name
```

When the script asks for your Goodreads cookie, paste the full `Cookie` request header value.

To find your cookie:

1. Log in to Goodreads in your browser.
2. Open your browser's developer tools (right-click -> Inspect).
3. Go to the **Network** tab.
4. Refresh a Goodreads page.
5. Click a request to `goodreads.com`.
6. In the request headers, find `Cookie`.
7. Paste the full cookie value into the terminal prompt.

Keep this value private. It may start with something like `ccsid=`.

### How saved values work

After you answer the prompts, the script automatically creates a `.env` file in the project folder. It looks like this:

```bash
GOODREADS_USER="your-goodreads-user-id"
my_cookie="your Goodreads Cookie header value"
```

If `.env` exists, the script uses those values and skips the prompts. The `.env` file is ignored by git, so your cookie is not committed to the repository.

To change accounts or replace an expired cookie, edit `.env` or delete it and run the script again.

### 6. Find the output

The scraper writes:

```text
csv_files/shelves.csv
```

It also caches downloaded Goodreads pages in:

```text
html_files/
```

At the end of a successful run, the script asks whether to delete cached HTML files. Keeping the cache makes reruns faster and lets an interrupted run reuse previous downloads. Deleting it forces fresh data to be fetched next time.

## Behavior

- Fetches the profile page and extracts all non-empty shelves.
- Scrapes each shelf page and follows pagination until no next page exists.
- Uses a random delay between requests to reduce rate-limit errors.
- Retries transient timeouts and waits longer after HTTP 429 responses.
- Stops cleanly on `Ctrl+C`; already-downloaded HTML remains in `html_files/`.

## Troubleshooting

**`Error: Cookie expired.`**  
Your Goodreads session cookie is no longer valid. Log in again, copy a fresh `Cookie` header, and update `my_cookie` in `.env`. You can also delete `.env` and run the script again so it asks for fresh values.

**The output looks stale.**  
Delete cached `.html` files in `html_files/`, or choose `y` when the script asks whether to clear the cache after a run.

**Goodreads fields are missing or set to `N/A`.**  
Goodreads pages can differ by account, privacy setting, locale, or layout changes. The scraper depends on Goodreads HTML structure, so selectors may need updates if Goodreads changes the page.

## License and responsible use

This project is intended for personal use only. Its purpose is to help you export and reclaim your own Goodreads reading data.

You are responsible for how you use this scraper. Do not use it to collect data from other people, abuse Goodreads, bypass access controls, or violate any applicable terms, rules, or laws.

The author is not responsible for misuse of this project, account issues, data loss, rate limits, blocked requests, or any other consequences caused by running or modifying this code.

Keep your Goodreads cookie private, and do not commit your `.env`, cached HTML files, or generated CSV files.
