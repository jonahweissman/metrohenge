#!/usr/bin/env python3
"""
Browser automation test for Observable Framework DuckDB queries
Uses Playwright (Python equivalent of Puppeteer) to test the application
"""

import asyncio
import sys
import time
from playwright.async_api import async_playwright


async def test_query_execution():
    """Test the Observable Framework application with browser automation."""
    
    async with async_playwright() as p:
        print("🚀 Starting browser automation test...")
        
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"🖥️  Console: {msg.text}"))
        page.on("pageerror", lambda err: print(f"❌ Page Error: {err}"))
        
        try:
            print("📂 Loading application...")
            await page.goto("http://127.0.0.1:3000/", wait_until="networkidle", timeout=30000)
            
            # Wait for the page to fully load
            print("⏳ Waiting for page to load...")
            await page.wait_for_timeout(3000)
            
            # Check if DuckDB initialization completed
            print("🔍 Checking for DuckDB initialization...")
            
            # Look for the SQL textarea
            textarea_selector = 'textarea[placeholder*="Enter your SQL query"]'
            await page.wait_for_selector(textarea_selector, timeout=10000)
            print("✅ Found SQL textarea")
            
            # Look for the Run Query button
            button_selector = 'button:has-text("Run Query")'
            await page.wait_for_selector(button_selector, timeout=10000)
            print("✅ Found Run Query button")
            
            # Check if there are any error messages
            error_elements = await page.query_selector_all('[style*="color: red"]')
            if error_elements:
                print(f"⚠️  Found {len(error_elements)} error messages on page")
                for i, error in enumerate(error_elements):
                    error_text = await error.inner_text()
                    print(f"   Error {i+1}: {error_text[:100]}...")
            
            # Test 1: Click the button with default query
            print("\n🧪 Test 1: Running default query...")
            await page.click(button_selector)
            await page.wait_for_timeout(2000)
            
            # Check for results
            results_text = await page.inner_text('body')
            if "Query Results" in results_text:
                print("✅ Default query executed successfully")
                
                # Look for table rows
                table_rows = await page.query_selector_all('table tr')
                if table_rows:
                    print(f"✅ Found table with {len(table_rows)} rows (including header)")
                else:
                    print("⚠️  Query ran but no table found")
            else:
                print("❌ Default query did not show results")
            
            # Test 2: Try a custom query
            print("\n🧪 Test 2: Running custom query...")
            custom_query = "SELECT count(*) as total_escalators FROM escalators;"
            
            await page.fill(textarea_selector, custom_query)
            await page.click(button_selector)
            await page.wait_for_timeout(2000)
            
            # Check results
            page_content = await page.inner_text('body')
            if "total_escalators" in page_content:
                print("✅ Custom count query executed successfully")
            else:
                print("❌ Custom query failed")
            
            # Test 3: Try a query that should show escalator types
            print("\n🧪 Test 3: Running escalator types query...")
            types_query = "SELECT conveying, count(*) as count FROM escalators GROUP BY 1 ORDER BY 2 DESC;"
            
            await page.fill(textarea_selector, types_query)
            await page.click(button_selector)
            await page.wait_for_timeout(3000)
            
            # Check results
            page_content = await page.inner_text('body')
            if "conveying" in page_content and ("yes" in page_content or "forward" in page_content):
                print("✅ Escalator types query executed successfully")
                print("✅ Found expected escalator conveying types in results")
            else:
                print("❌ Escalator types query failed or missing expected data")
            
            # Final page state check
            print("\n📊 Final page analysis...")
            final_content = await page.inner_text('body')
            
            if "72 escalators" in final_content:
                print("✅ Page shows expected escalator count")
            else:
                print("⚠️  Page doesn't show expected '72 escalators' text")
            
            if "Query Results" in final_content:
                print("✅ Query results are displayed")
            else:
                print("❌ No query results visible")
            
            # Check for any JavaScript errors
            js_errors = []
            page.on("pageerror", lambda err: js_errors.append(str(err)))
            
            if js_errors:
                print(f"❌ Found {len(js_errors)} JavaScript errors:")
                for error in js_errors:
                    print(f"   {error}")
            else:
                print("✅ No JavaScript errors detected")
                
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            return False
            
        finally:
            await browser.close()
    
    print("\n🎉 Browser automation test completed!")
    return True


def check_server_running():
    """Check if the development server is running."""
    import requests
    try:
        response = requests.get("http://127.0.0.1:3000/", timeout=5)
        return response.status_code == 200
    except:
        return False


async def main():
    print("🔧 Observable Framework Browser Test")
    print("=" * 50)
    
    # Check if server is running
    if not check_server_running():
        print("❌ Development server not running at http://127.0.0.1:3000/")
        print("   Run 'npm run dev' first!")
        sys.exit(1)
    
    print("✅ Development server is running")
    
    # Run the test
    success = await test_query_execution()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())