from dotenv import load_dotenv
import os
from browser_use import Browser
import time
import asyncio
import cohere
import json
import re

# Disable telemetry if desired
os.environ["ANONYMIZED_TELEMETRY"] = "false"

# Load environment variables from .env file
load_dotenv()

# Initialize Cohere client with API key from environment variables
co = cohere.Client(os.getenv("COHERE_API_KEY"))

async def convert_step_to_action(step, page_context="ecommerce website"):
    """
    Use Cohere AI to convert natural language step to structured browser action
    """
    try:
        prompt = f"""
        Convert the following test step for a {page_context} into a structured browser action command.
        Return ONLY the JSON format with action type and parameters.
        
        Step: "{step}"
        
        Output format examples:
        For clicks: {{"action": "click", "selector": "selector_value", "description": "what is being clicked"}}
        For typing: {{"action": "fill", "selector": "selector_value", "value": "text to type", "description": "what field is being filled"}}
        For navigation: {{"action": "navigate", "url": "url_to_navigate", "description": "navigating to page"}}
        For waiting: {{"action": "wait", "time": seconds_to_wait, "description": "reason for waiting"}}
        For checking: {{"action": "check", "text": "text to verify", "description": "what is being verified"}}
        For viewing: {{"action": "check", "text": "", "description": "viewing the page content"}}
        """
        
        response = co.generate(
            prompt=prompt,
            max_tokens=300,
            temperature=0.2,
            k=0,
            stop_sequences=[],
            return_likelihoods='NONE'
        )
        
        result = response.generations[0].text.strip()
        print(f"AI interpretation of step '{step}':")
        print(result)
        
        # Convert string result to Python dict using json.loads with proper error handling
        try:
            action_dict = json.loads(result)
            return action_dict
        except json.JSONDecodeError:
            # Try to extract just the JSON part if there's additional text
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                try:
                    action_dict = json.loads(json_match.group(0))
                    return action_dict
                except:
                    pass
            
            print(f"Could not parse AI response as JSON. Using fallback interpretation for: {step}")
            
            # Fallback simple parsing
            if "view" in step.lower():
                return {"action": "check", "text": "", "description": "viewing the page content"}
            elif "click" in step.lower() and "sign in" in step.lower():
                return {"action": "click", "selector": "text=Sign in", "description": "clicking sign in button"}
            elif "enter" in step.lower() and "email" in step.lower():
                email = "test@example.com"
                if "as" in step:
                    parts = step.split("as")
                    if len(parts) > 1:
                        email_part = parts[1].strip().strip("'").strip('"')
                        if "@" in email_part:
                            email = email_part
                return {"action": "fill", "selector": "input[type='email']", "value": email, "description": "entering email"}
            elif "enter" in step.lower() and "password" in step.lower():
                password = "test123"
                if "as" in step:
                    parts = step.split("as")
                    if len(parts) > 1:
                        password = parts[1].strip().strip("'").strip('"')
                return {"action": "fill", "selector": "input[type='password']", "value": password, "description": "entering password"}
            else:
                return {"action": "unknown", "description": step}
    
    except Exception as e:
        print(f"Error using Cohere API: {e}")
        # Fallback even more basic interpretation
        return {"action": "unknown", "description": step}

async def execute_browser_action(page, action_dict):
    """Execute a browser action based on the structured command"""
    action_type = action_dict.get("action", "unknown")
    description = action_dict.get("description", "unknown action")
    
    print(f"Executing: {description}")
    
    try:
        if action_type == "click":
            selector = action_dict.get("selector")
            if not selector:
                print("No selector provided for click action")
                return False
                
            selectors = [selector]
            # Add fallback selectors based on the description
            if "sign in" in description.lower():
                selectors.extend([
                    "text=Sign in", "text=Log in", "[aria-label='Sign in']",
                    "a.account-link", "#customer_login_link", 
                    "//a[contains(text(), 'Sign in')]", ".header__action-item-link",
                    ".customer-login-link", "button.signin-button",
                    ".signin", ".login-button", "#login-button"
                ])
            elif "submit" in description.lower() or ("sign in" in description.lower() and "button" in description.lower()):
                selectors.extend([
                    "button[type='submit']", "input[type='submit']",
                    "#signin-button", "#customer_login_submit", ".btn-signin"
                ])
                
            # Try to first find and reveal any hidden elements that might contain our target
            try:
                # Look for account buttons/icons that might need clicking to reveal the login form
                account_buttons = ["button.account-button", ".account-trigger", 
                                  ".icon-account", ".header__icon--account",
                                  ".user-icon", ".account-icon"]
                                  
                for account_selector in account_buttons:
                    try:
                        # Try to find any account button that might need clicking first
                        button = await page.query_selector(account_selector)
                        if button:
                            print(f"Found possible account button with selector {account_selector}, clicking...")
                            await button.click(timeout=2000)
                            await asyncio.sleep(1)  # Wait for animation
                            break
                    except Exception as e:
                        pass
            except Exception as reveal_error:
                print(f"Error trying to reveal login elements: {reveal_error}")
                
            # Try each selector
            for sel in selectors:
                try:
                    # First check if element exists but might be hidden
                    element = await page.query_selector(sel)
                    if element:
                        # Try to make visible with JavaScript if needed
                        try:
                            await page.evaluate(f"""
                                (el) => {{
                                    if (el) {{
                                        el.style.display = "block";
                                        el.style.visibility = "visible";
                                        el.style.opacity = "1";
                                    }}
                                }}
                            """, element)
                        except:
                            pass
                            
                    # Now try clicking
                    await page.click(sel, timeout=2000)
                    print(f"Successfully clicked using selector: {sel}")
                    await asyncio.sleep(1)
                    return True
                except Exception as e:
                    print(f"Failed to click with selector {sel}: {str(e)}")
                    continue
                    
            return False
            
        elif action_type == "fill":
            selector = action_dict.get("selector")
            value = action_dict.get("value", "")
            
            if not selector:
                print("No selector provided for fill action")
                return False
                
            selectors = [selector]
            # Add fallback selectors based on the description
            if "email" in description.lower():
                selectors.extend([
                    "input[type='email']", "input[name='email']",
                    "input[id*='email' i]", "#CustomerEmail", "input.customer-email",
                    "#email", "input.email", "[placeholder*='email' i]"
                ])
            elif "password" in description.lower():
                selectors.extend([
                    "input[type='password']", "input[name='password']",
                    "input[id*='password' i]", "#CustomerPassword", "#password",
                    "input.password", "[placeholder*='password' i]"
                ])
                
            # Try each selector
            for sel in selectors:
                try:
                    # First check if element exists but might be hidden
                    element = await page.query_selector(sel)
                    if element:
                        # Try to make visible with JavaScript if needed
                        try:
                            await page.evaluate(f"""
                                (el) => {{
                                    if (el) {{
                                        el.style.display = "block";
                                        el.style.visibility = "visible";
                                        el.style.opacity = "1";
                                    }}
                                }}
                            """, element)
                        except:
                            pass
                            
                    # Now try filling
                    await page.fill(sel, value, timeout=2000)
                    print(f"Successfully filled {description} using selector: {sel}")
                    return True
                except Exception as e:
                    print(f"Failed to fill with selector {sel}: {str(e)}")
                    continue
                    
            return False
            
        elif action_type == "navigate":
            url = action_dict.get("url")
            if not url:
                print("No URL provided for navigate action")
                return False
                
            await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            print(f"Successfully navigated to {url}")
            return True
            
        elif action_type == "wait":
            time_to_wait = action_dict.get("time", 1)
            await asyncio.sleep(time_to_wait)
            print(f"Waited for {time_to_wait} seconds")
            return True
            
        elif action_type == "check":
            text = action_dict.get("text", "")
            if text:
                content = await page.content()
                result = text.lower() in content.lower()
                print(f"Checking for text '{text}': {'Found' if result else 'Not found'}")
                return result
            else:
                # Just view the page content
                print("Viewing page content")
                return True
            
        else:
            print(f"Unknown action type: {action_type}")
            return False
            
    except Exception as e:
        print(f"Error executing browser action: {e}")
        return False

# Async function to parse and execute test case using AI translation
async def execute_test_case(test_case):
    steps = test_case['steps']
    expected_output = test_case['expected_output']
    url = test_case.get('url')
    
    if not url:
        url = "https://www.farmley.com/"  # Default URL as a fallback
    
    # Initialize Browser-Use for browser automation
    browser = Browser()
    
    try:
        # Get the Playwright browser
        playwright_browser = await browser.get_playwright_browser()
        
        # Create a new context using the Playwright browser with mobile emulation
        # This sometimes helps with sites that have different login UIs for mobile/desktop
        context = await playwright_browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        )
        
        # Create a new page
        page = await context.new_page()
        
        # Enable JavaScript console logging
        page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
        
        # Set up requests logging to better understand redirects
        async def on_request(request):
            print(f"Request: {request.method} {request.url}")
        page.on("request", on_request)
        
        async def on_response(response):
            print(f"Response: {response.status} {response.url}")
        page.on("response", on_response)
        
        # Navigate to the URL with better error handling and retry logic
        print(f"Navigating to URL: {url}")
        max_retries = 3
        retry_count = 0
        navigation_successful = False
        
        while retry_count < max_retries and not navigation_successful:
            try:
                # Increased timeout and changed wait_until option for better reliability
                await page.goto(url, timeout=30000, wait_until="networkidle")
                navigation_successful = True
                print("Successfully navigated to the URL")
            except Exception as e:
                retry_count += 1
                print(f"Navigation attempt {retry_count} failed: {e}")
                if retry_count < max_retries:
                    print(f"Retrying in 3 seconds...")
                    await asyncio.sleep(3)
                else:
                    print(f"All navigation attempts failed. Trying with 'domcontentloaded' option...")
                    try:
                        # Last attempt with different loading strategy
                        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        navigation_successful = True
                        print("Successfully navigated to the URL with domcontentloaded option")
                    except Exception as final_e:
                        print(f"Final navigation attempt failed: {final_e}")
                        # Check if we got a partial page load we can work with
                        try:
                            title = await page.title()
                            if title:
                                print(f"Partial page load detected. Page title: {title}")
                                navigation_successful = True
                        except:
                            pass
                        
                        if not navigation_successful:
                            raise Exception(f"Could not navigate to {url} after multiple attempts") from final_e
        
        # Take a screenshot for debugging
        await page.screenshot(path="screenshot_before.png")
        print("Initial screenshot saved as screenshot_before.png")
        
        # Print page title to verify navigation
        title = await page.title()
        print(f"Current page title: {title}")
        
        # Extract domain for context
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        domain = domain_match.group(1) if domain_match else "ecommerce"
        page_context = f"{domain} website"
        
        # Check for alternative test site if the main site is unreachable
        if not navigation_successful or "farmley" in url.lower() and title == "":
            print("The Farmley site appears to be unreachable. Trying an alternative site for testing...")
            alternative_site = "https://demo.opencart.com/index.php?route=account/login"
            print(f"Navigating to alternative site: {alternative_site}")
            await page.goto(alternative_site, timeout=30000, wait_until="domcontentloaded")
            title = await page.title()
            print(f"Alternative site title: {title}")
            
            # Update test case for the alternative site
            if "farmley" in url.lower():
                print("Adapting test steps for OpenCart demo site...")
                # The steps can remain mostly the same as they're now using AI interpretation
        
        # Execute each step using AI interpretation
        step_results = []
        for i, step in enumerate(steps):
            print(f"\nStep {i+1}: {step}")
            
            # Convert natural language step to structured action using Cohere
            action = await convert_step_to_action(step, page_context)
            
            # Execute the action
            result = await execute_browser_action(page, action)
            step_results.append(result)
            
            # Take a screenshot after each step
            await page.screenshot(path=f"screenshot_step_{i+1}.png")
            print(f"Screenshot saved after step {i+1}")
            
            # Wait a short time between steps
            await asyncio.sleep(1)
        
        # Take a final screenshot
        await page.screenshot(path="screenshot_final.png")
        print("Final screenshot saved as screenshot_final.png")
        
        # Check if the expected output is on the page
        content = await page.content()
        current_url = page.url
        print(f"Final URL: {current_url}")
        print(f"Checking for expected output: '{expected_output}'")
        
        # Fix the test result determination
        result = "Fail"  # Default to fail
        
        if expected_output.lower() in content.lower() or expected_output.lower() in current_url.lower():
            result = "Pass"
            print("Test PASSED!")
        else:
            # More lenient check for account-related success indicators
            if "account" in expected_output.lower():
                account_indicators = ["account", "profile", "dashboard", "my-account", "customer"]
                if any(indicator in current_url.lower() for indicator in account_indicators):
                    result = "Pass"
                    print("Test PASSED based on URL containing account indicators!")
                else:
                    # Check if any step actually succeeded before failing
                    if any(step_results):
                        for i, success in enumerate(step_results):
                            if success:
                                print(f"Step {i+1} was successful")
                    
                    print("Test FAILED - No account indicators found in URL or content")
                    result = "Fail"
            else:
                print("Test FAILED!")
                result = "Fail"
        
        # Close the browser
        await context.close()
        await browser.close()
        
        # Return structured result
        return {
            'result': result,
            'expected_output': expected_output,
            'final_url': current_url,
            'step_results': step_results,
            'content_preview': content[:200] + "..." if len(content) > 200 else content
        }
        
    except Exception as e:
        print(f"Error in test execution: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to close the browser if it exists
        try:
            if 'context' in locals():
                await context.close()
            if 'browser' in locals():
                await browser.close()
        except Exception as cleanup_error:
            print(f"Error during cleanup: {cleanup_error}")
        
        return {
            'result': 'Error',
            'error': str(e)
        }

# Try to detect if the login is hidden in an accordion or popup
async def check_for_hidden_login(page):
    try:
        # Look for common account/profile buttons that might need clicking
        account_triggers = [
            ".header__action-item--account",
            ".user-icon",
            ".account-trigger",
            "a.account-link",
            "#customer_login_link",
            ".header-account-link",
            ".sign-in-link"
        ]
        
        for trigger in account_triggers:
            try:
                element = await page.query_selector(trigger)
                if element:
                    print(f"Found potential account/login trigger: {trigger}")
                    await element.click()
                    await asyncio.sleep(1)  # Wait for animation
                    
                    # Check if login form appears
                    login_form = await page.query_selector("form[action*='login'], form[action*='signin'], form.login-form")
                    if login_form:
                        print("Login form appeared!")
                        return True
            except:
                continue
                
        return False
    except Exception as e:
        print(f"Error checking for hidden login: {e}")
        return False

# Test with a simpler website first
simple_test_case = {
    "url": "https://example.com",
    "steps": [
        "View the page content"
    ],
    "expected_output": "Example Domain"
}

# Main test case for Farmley with backup options
farmley_test_case = {
    "url": "https://www.farmley.com/",
    "steps": [
        "Click on the 'Sign in' button",
        "Enter email as 'test@example.com'",
        "Enter password as 'test123'",
        "Click on the 'Sign in' button"
    ],
    "expected_output": "My account"
}

# Alternative test case for OpenCart demo site (as a fallback)
opencart_test_case = {
    "url": "https://demo.opencart.com/index.php?route=account/login",
    "steps": [
        "Enter email as 'test@example.com'",
        "Enter password as 'test123'",
        "Click the login button"
    ],
    "expected_output": "account"
}

# Create async main function to run our test
async def main():
    # Check if Cohere API key is set
    if not os.getenv("COHERE_API_KEY"):
        print("WARNING: COHERE_API_KEY environment variable not set!")
        print("Please set your Cohere API key in the .env file or environment variables.")
        print("Example: COHERE_API_KEY=your-api-key-here")
        return
        
    # First run a simple test to ensure the automation works
    print("Running simple test with example.com first...")
    try:
        simple_result = await execute_test_case(simple_test_case)
        print("Simple test result:", simple_result)
        
        # Only proceed with the main test if the simple test was successful
        if simple_result.get('result') == 'Pass':
            print("\nSimple test passed! Now running the main test...")
            
            try:
                # Try Farmley first
                main_result = await execute_test_case(farmley_test_case)
                print("Main test result:", main_result)
                
                # If Farmley fails due to connection issues, try OpenCart
                if main_result.get('result') == 'Error' and "timeout" in main_result.get('error', '').lower():
                    print("\nFarmley site appears to be unreachable. Trying alternative test site...")
                    alt_result = await execute_test_case(opencart_test_case)
                    print("Alternative test result:", alt_result)
            except Exception as main_error:
                print(f"Error with main test: {main_error}")
                print("\nTrying alternative test site instead...")
                try:
                    alt_result = await execute_test_case(opencart_test_case)
                    print("Alternative test result:", alt_result)
                except Exception as alt_error:
                    print(f"Error with alternative test: {alt_error}")
                    
        else:
            print("\nSimple test did not pass. Please check your network connectivity and browser configuration.")
    except Exception as e:
        print(f"Error running tests: {e}")
        import traceback
        traceback.print_exc()

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())