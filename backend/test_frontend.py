import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(base_url="http://frontend:80")
        page = await context.new_page()

        print("Navigating to login...")
        await page.goto("/app")
        # Wait for either onboarding or identifiers page
        await page.wait_for_timeout(2000)
        print("Page URL:", page.url)

        # Assuming no auth required or it uses a guest token for dev?
        # Let's just try to go to /app/identifiers
        print("Navigating to identifiers...")
        await page.goto("/app/identifiers")
        await page.wait_for_timeout(2000)
        
        # Add email
        print("Adding email...")
        await page.fill('input[placeholder="you@example.com"]', 'testfrontend1@example.com')
        await page.click('button:has-text("Add")')
        await page.wait_for_timeout(1000)

        # Click verify
        print("Clicking verify...")
        await page.click('button:has-text("Verify")')
        await page.wait_for_timeout(1000)

        # Check if Dev code is visible
        content = await page.content()
        if "Dev code:" in content:
            print("SUCCESS: Dev code is visible in UI!")
            # Extract code (very naive)
            import re
            m = re.search(r'Dev code:\s*<code>(.*?)</code>', content)
            if m:
                code = m.group(1).strip()
                print("Extracted code:", code)
                # Fill code and confirm
                await page.fill('input[value=""]', code)  # might be tricky to select
                await page.click('button:has-text("Confirm verification")')
                await page.wait_for_timeout(1000)
                print("Confirmed verification!")
        else:
            print("ERROR: Dev code not found in UI")
            print(content[:1000])

        print("Navigating to scans...")
        await page.goto("/app/scans")
        await page.wait_for_timeout(2000)

        # Click start scan
        print("Starting scan...")
        await page.click('button:has-text("Start scan")')
        await page.wait_for_timeout(2000)

        content = await page.content()
        if "An unexpected error occurred" in content:
            print("ERROR: Unexpected error occurred on scan page")
        else:
            print("SUCCESS: Scan started successfully")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
