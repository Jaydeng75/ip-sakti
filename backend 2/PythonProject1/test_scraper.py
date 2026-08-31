import asyncio
from playwright.async_api import async_playwright
import sqlite3

# Testing Section 3 of Patents Act 1970
TEST_URL = "https://www.indiacode.nic.in/show-data?actid=AC_CEN_11_61_00002_197039_1517807321764&orderno=3"


async def test_single_scrape():
    print("Starting test...")
    async with async_playwright() as p:
        # Opens a visible browser window so you can watch it load
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print(f"Navigating to {TEST_URL}...")
        await page.goto(TEST_URL, wait_until="networkidle")

        # Pull text content from the page
        title = await page.inner_text("h4") if await page.query_selector("h4") else "Title Not Found"
        content = await page.inner_text("body")

        print("\n--- EXTRACTED TITLE ---")
        print(title.strip())
        print("\n--- CONTENT PREVIEW (First 200 chars) ---")
        print(content.strip()[:200])
        print("------------------------------------------\n")

        # Test DB Insertion using built-in sqlite3
        conn = sqlite3.connect("test_patents.db")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS test (title TEXT, content TEXT)")
        cursor.execute("INSERT INTO test VALUES (?, ?)", (title.strip(), content.strip()))
        conn.commit()
        conn.close()

        print("Inserted successfully into test_patents.db!")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_single_scrape())