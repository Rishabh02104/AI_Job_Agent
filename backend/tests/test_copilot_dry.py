import os
import sys
import asyncio
from playwright.async_api import async_playwright

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.playwright_bot import auto_fill_simplify_copilot_fields

# Mock settings dictionary
mock_settings = {
    "github_url": "https://github.com/testcandidate",
    "linkedin_url": "https://linkedin.com/in/testcandidate",
    "portfolio_url": "https://testcandidate.com",
    "authorized_to_work": True,
    "requires_sponsorship": False,
    "gender": "Male",
    "race": "Asian",
    "disability_status": "No, I do not have a disability",
    "veteran_status": "I am not a protected veteran"
}

# Create a simple mock HTML file for testing
mock_html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Mock Job Form</title>
</head>
<body>
    <form>
        <!-- Socials -->
        <div>
            <label for="github">GitHub Profile</label>
            <input type="text" id="github" name="github_url" />
        </div>
        <div>
            <label for="linkedin_field">LinkedIn Profile</label>
            <input type="text" id="linkedin_field" name="linkedin" />
        </div>
        <div>
            <label for="website">Portfolio Website</label>
            <input type="text" id="website" name="website" />
        </div>

        <!-- Work Auth -->
        <div>
            <label for="authorized">Are you legally authorized to work in the US?</label>
            <select id="authorized" name="authorized_status">
                <option value="">Select option</option>
                <option value="yes_auth">Yes</option>
                <option value="no_auth">No</option>
            </select>
        </div>
        <div>
            <label for="sponsorship">Will you require sponsorship now or in the future?</label>
            <select id="sponsorship" name="visa_sponsorship">
                <option value="">Select option</option>
                <option value="yes_spons">Yes</option>
                <option value="no_spons">No</option>
            </select>
        </div>

        <!-- Demographics -->
        <div>
            <label for="gender_field">Please select your gender identity:</label>
            <select id="gender_field" name="gender">
                <option value="">Select...</option>
                <option value="m">Male</option>
                <option value="f">Female</option>
                <option value="nb">Non-binary</option>
                <option value="decline">I prefer not to say</option>
            </select>
        </div>
        <div>
            <label for="race_field">Race/Ethnicity:</label>
            <select id="race_field" name="race">
                <option value="">Select...</option>
                <option value="white">White</option>
                <option value="asian">Asian</option>
                <option value="black">Black / African American</option>
                <option value="decline">Decline to self-identify</option>
            </select>
        </div>
        <div>
            <label for="disability">Disability Status:</label>
            <select id="disability" name="disability_status">
                <option value="">Select...</option>
                <option value="has_disability">Yes, I have a disability</option>
                <option value="no_disability">No, I do not have a disability</option>
                <option value="decline">Decline</option>
            </select>
        </div>
        <div>
            <label for="veteran">Veteran Status:</label>
            <select id="veteran" name="military_status">
                <option value="">Select...</option>
                <option value="vet">I am a protected veteran</option>
                <option value="not_vet">I am not a protected veteran</option>
                <option value="decline">Decline to self-identify</option>
            </select>
        </div>
    </form>
</body>
</html>
"""

async def run_copilot_test():
    # Save mock html
    mock_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_form.html")
    with open(mock_file_path, "w") as f:
        f.write(mock_html_content)
        
    file_url = f"file:///{mock_file_path.replace(os.sep, '/')}"
    
    print(f"Launching Playwright to test Simplify Copilot auto-filling on: {file_url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(file_url)
        
        # Run auto-fill
        await auto_fill_simplify_copilot_fields(page, mock_settings)
        
        # Verify values
        github_val = await page.input_value("#github")
        linkedin_val = await page.input_value("#linkedin_field")
        website_val = await page.input_value("#website")
        
        auth_val = await page.eval_on_selector("#authorized", "el => el.value")
        spons_val = await page.eval_on_selector("#sponsorship", "el => el.value")
        
        gender_val = await page.eval_on_selector("#gender_field", "el => el.value")
        race_val = await page.eval_on_selector("#race_field", "el => el.value")
        disability_val = await page.eval_on_selector("#disability", "el => el.value")
        veteran_val = await page.eval_on_selector("#veteran", "el => el.value")
        
        print("\n--- Test Verification Results ---")
        print(f"GitHub filled: {github_val} (Expected: {mock_settings['github_url']})")
        print(f"LinkedIn filled: {linkedin_val} (Expected: {mock_settings['linkedin_url']})")
        print(f"Website filled: {website_val} (Expected: {mock_settings['portfolio_url']})")
        
        print(f"Authorized work selected: {auth_val} (Expected: yes_auth)")
        print(f"Sponsorship selected: {spons_val} (Expected: no_spons)")
        
        print(f"Gender selected: {gender_val} (Expected: m)")
        print(f"Race selected: {race_val} (Expected: asian)")
        print(f"Disability selected: {disability_val} (Expected: no_disability)")
        print(f"Veteran selected: {veteran_val} (Expected: not_vet)")
        
        assert github_val == mock_settings["github_url"]
        assert linkedin_val == mock_settings["linkedin_url"]
        assert website_val == mock_settings["portfolio_url"]
        assert auth_val == "yes_auth"
        assert spons_val == "no_spons"
        assert gender_val == "m"
        assert race_val == "asian"
        assert disability_val == "no_disability"
        assert veteran_val == "not_vet"
        
        print("\nAll assertions passed! Simplify Copilot Auto-fill Engine is working perfectly!")
        
        await browser.close()
        
    # Clean up mock file
    if os.path.exists(mock_file_path):
        os.remove(mock_file_path)

if __name__ == "__main__":
    asyncio.run(run_copilot_test())
