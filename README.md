# Automated Web Testing Framework

A robust and flexible framework that uses AI-powered natural language processing to execute automated tests on web applications, particularly focusing on user authentication flows.

## Overview

This framework bridges the gap between plain English test descriptions and automated web testing by using the Cohere API to interpret test steps and convert them into executable browser actions. It's designed to handle the complexities and variations in e-commerce website layouts and authentication mechanisms.

## Approach to Prompt Design

### Natural Language to Structured Actions

The core of the framework relies on well-crafted prompts to the Cohere AI model that accurately translate natural language test steps into structured browser actions. Our prompt design follows these principles:

1. **Context-Aware Interpretation**: We provide the AI with the website domain context (e.g., "farmley website") to help it understand the specific e-commerce environment.

2. **Structured Output Format**: The prompt explicitly defines the expected JSON output structure for different action types:
   - Clicks: `{"action": "click", "selector": "...", "description": "..."}`
   - Form inputs: `{"action": "fill", "selector": "...", "value": "...", "description": "..."}`
   - Navigation: `{"action": "navigate", "url": "...", "description": "..."}`
   - Waiting: `{"action": "wait", "time": seconds, "description": "..."}`
   - Verification: `{"action": "check", "text": "...", "description": "..."}`

3. **Clear Examples**: The prompt includes clear examples for each action type to guide the AI's response format.

4. **Focused Scope**: We deliberately limit the AI to only return the JSON structure without additional explanations, ensuring the output can be directly parsed.

## Execution and Validation Logic

### Test Execution Flow

1. **Page Initialization**:
   - The framework first creates a browser instance with mobile viewport emulation to handle different UI variations.
   - It sets up console and network logging for better debugging capabilities.

2. **Step-by-Step Execution**:
   - For each natural language step, the AI converts it to a structured action.
   - The framework executes the action with robust error handling.
   - Screenshots are taken after each step for visual verification.

3. **Hidden Element Detection**:
   - The framework actively looks for hidden login elements that might need to be revealed.
   - It uses JavaScript to make hidden elements visible when necessary.

4. **Flexible Selector Strategy**:
   - For each action, multiple selector strategies are tried in order of preference.
   - This includes CSS selectors, XPath, text content, and ARIA attributes.

5. **Results Validation**:
   - Success is determined based on:
     - Presence of expected text in the page content
     - Indicators in the final URL
     - Successful completion of individual steps

### Fallback Mechanisms

1. **Alternative Test Sites**:
   - If the primary test site is unreachable, the framework automatically switches to a fallback site.

2. **Connection Retry Logic**:
   - Multiple navigation attempts with different loading strategies.

3. **Selector Fallbacks**:
   - If the primary selector fails, multiple alternative selectors are tried.

## Challenges and Solutions

### Challenge 1: Hidden Login Forms

**Problem**: Many e-commerce sites hide login forms behind account buttons or in dropdown menus.

**Solution**: 
- Added detection for account triggers that might reveal login forms
- Implemented JavaScript-based visibility forcing for hidden elements
- Added multiple selector strategies to find login elements in different UI architectures

### Challenge 2: Action Type Handling

**Problem**: The original script didn't properly handle "view" action type.

**Solution**:
- Added explicit handling for "view" actions in both the AI interpretation and execution functions
- Mapped "view" to "check" with empty text to handle simple page viewing actions

### Challenge 3: Incorrect Test Results

**Problem**: Tests were incorrectly marked as "PASSED" despite step failures.

**Solution**:
- Redesigned result determination logic to properly account for step success rates
- Added more granular success criteria based on URL indicators and page content
- Improved logging to better understand why tests pass or fail

### Challenge 4: Network Reliability

**Problem**: Inconsistent network connections caused test failures.

**Solution**:
- Implemented retry logic with increased timeouts
- Added multiple navigation strategies (networkidle, domcontentloaded)
- Added partial page load detection for graceful degradation

### Challenge 5: AI Response Parsing

**Problem**: Occasionally the AI would return malformed JSON or include additional text.

**Solution**:
- Added robust JSON parsing with regex-based extraction for imperfect responses
- Implemented a fallback parsing system for common actions when AI interpretation fails

## Getting Started

1. Set up your environment variables in a `.env` file:
   ```
   COHERE_API_KEY=your_api_key_here
   ```

2. Install required dependencies:
   ```bash
   pip install python-dotenv cohere browser-use asyncio playwright
   ```

3. Run the script:
   ```bash
   python main.py
   ```

## Extending the Framework

- **Custom Test Cases**: Add new test cases by following the existing pattern in the `simple_test_case`, `farmley_test_case`, and `opencart_test_case` examples.
- **Additional Actions**: Extend the `convert_step_to_action` and `execute_browser_action` functions to support new types of browser interactions.
- **Enhanced Validation**: Add custom validation logic in the test execution function to verify specific application behavior.