"""
Flight Booking Agent implementation.

IMPORTANT: Uses playwright-stealth to avoid bot detection on aa.com.
"""
import asyncio
import logging
from typing import Optional

from playwright.async_api import async_playwright, Browser, Page, Playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

from src.agents.bitwarden_agent import BitwardenAgent
from src.models.credential_response import CredentialStatus
from src.utils.credential_handler import SecureCredential

logger = logging.getLogger(__name__)


class FlightBookingAgent:
    """Agent responsible for aa.com login automation."""

    def __init__(
            self,
            bitwarden_agent: BitwardenAgent,
            headless: bool = False
    ):
        """
        Initialize flight booking agent.

        Args:
            bitwarden_agent: BitwardenAgent instance for credential requests
            headless: Whether to run browser in headless mode
        """
        self.bitwarden_agent = bitwarden_agent
        self.headless = headless

    async def run(self) -> bool:
        """
        Execute flight booking task (login to aa.com).

        Returns:
            True if login successful, False otherwise
        """
        # Use stealth context manager for the entire browser session
        async with Stealth().use_async(async_playwright()) as playwright:
            try:
                # Launch browser with stealth mode applied
                logger.info(f"Launching browser with stealth mode (headless={self.headless})...")
                browser = await playwright.chromium.launch(headless=self.headless)
                page = await browser.new_page()
                logger.debug("Stealth mode applied to browser")

                # Navigate to login page
                logger.info("Navigating to aa.com...")
                await page.goto("https://www.aa.com/login")

                # Wait for login form
                await self._wait_for_login_form(page)

                # Request credentials
                logger.info("Requesting credentials from Bitwarden...")
                response = self.bitwarden_agent.request_credential(
                    domain="aa.com",
                    reason="Logging in to search and book flights",
                    agent_id="flight-booking-001",
                    agent_name="Flight Booking Agent"
                )

                # Handle response
                if response.status == CredentialStatus.DENIED:
                    logger.info("User denied credential access")
                    return False

                if response.status == CredentialStatus.NOT_FOUND:
                    logger.error(f"Credential not found: {response.error_message}")
                    return False

                if response.status == CredentialStatus.ERROR:
                    logger.error(f"Error retrieving credential: {response.error_message}")
                    return False

                # Fill login form with credential
                with response.credential as cred:
                    success = await self._login(page, cred)

                return success

            finally:
                # Cleanup browser
                if 'page' in locals():
                    await page.close()
                if 'browser' in locals():
                    await browser.close()
                # playwright context manager handles cleanup

    async def _wait_for_login_form(self, page: Page) -> None:
        """
        Wait for login form to appear.

        Args:
            page: Playwright page object
        """
        logger.info("Waiting for login form...")
        await page.wait_for_selector(
            'input[type="email"], input[name="username"]',
            timeout=30000
        )

    async def _dismiss_cookie_consent(self, page: Page) -> None:
        """Dismiss OneTrust cookie consent popup (often in iframe)."""
        try:
            logger.info("Checking for cookie consent popup...")

            # OneTrust cookie popup is often in an iframe
            # Wait for iframe to load
            await page.wait_for_timeout(2000)

            # Try to find the OneTrust iframe
            frames = page.frames
            logger.debug(f"Found {len(frames)} frames on page")

            for frame in frames:
                # Look for Reject All button in each frame
                try:
                    reject_button = await frame.query_selector('button.ot-pc-refuse-all-handler')
                    if reject_button and await reject_button.is_visible():
                        logger.info("Found Reject All button in iframe, clicking...")
                        await reject_button.click()
                        await page.wait_for_timeout(1000)
                        logger.info("Cookie popup dismissed")
                        return
                except:
                    continue

            # If not in iframe, try main page
            reject_button = await page.query_selector('button.ot-pc-refuse-all-handler')
            if reject_button and await reject_button.is_visible():
                logger.info("Dismissing cookie consent popup (Reject All)...")
                await reject_button.click()
                await page.wait_for_timeout(1000)
                logger.info("Cookie popup dismissed")
            else:
                logger.debug("No visible cookie consent popup found (may have auto-dismissed)")

        except Exception as e:
            logger.warning(f"Cookie consent handling failed (non-critical): {e}")
            # Don't fail - proceed anyway

    async def _login(self, page: Page, credential: SecureCredential) -> bool:
        """
        Fill login form and submit.

        Args:
            page: Playwright page object
            credential: SecureCredential with username/password

        Returns:
            True if login successful, False otherwise
        """
        try:
            # STEP 1: Dismiss cookie consent popup
            await self._dismiss_cookie_consent(page)

            logger.info("Filling login form...")

            # Find and focus username field
            username_field = await page.query_selector('input[type="email"], input[name="username"]')
            if not username_field:
                logger.error("Username field not found")
                return False

            # Click to focus, then type (triggers validation events)
            await username_field.click()
            await page.wait_for_timeout(500)  # Brief pause
            await username_field.type(credential.username, delay=50)  # Type with delay
            logger.debug("Username typed")

            # Tab or click to password field (triggers blur event on username)
            await page.keyboard.press('Tab')
            await page.wait_for_timeout(500)

            # Type password
            password_field = await page.query_selector('input[type="password"], input[name="password"]')
            if not password_field:
                logger.error("Password field not found")
                return False

            await password_field.type(credential.password, delay=50)  # Type with delay
            logger.debug("Password typed")

            # Wait a moment for any validation to complete
            await page.wait_for_timeout(1000)

            # STEP 2: Submit form
            logger.info("Submitting login form...")

            # Check if submit button is now enabled (validation may have disabled it)
            submit_button = await page.query_selector('button.adc-button.kind-primary')

            if not submit_button:
                logger.error("Submit button not found")
                await page.screenshot(path="no_submit_button.png")
                return False

            # Check if button is disabled
            is_disabled = await submit_button.is_disabled()
            if is_disabled:
                logger.error("Submit button is disabled (validation may have failed)")
                await page.screenshot(path="button_disabled.png")
                return False

            logger.info("Clicking submit button...")
            await submit_button.click()

            # Wait for navigation
            try:
                # Wait for URL to change away from login page
                await page.wait_for_function(
                    "window.location.href.toLowerCase().indexOf('login') === -1",
                    timeout=15000
                )
                current_url = page.url
                logger.info(f"✅ Login successful! Navigated to: {current_url}")
                return True

            except PlaywrightTimeoutError:
                # Still on login page after timeout
                current_url = page.url
                logger.warning(f"Still on login page after 15s: {current_url}")

                # Take screenshot
                await page.screenshot(path="login_failed.png")
                logger.info("Screenshot saved to login_failed.png")

                # Check for any visible errors
                error_text = await page.evaluate('''() => {
                    // Look for any element with error-related classes or text
                    const errorElements = document.querySelectorAll('[class*="error"], [class*="alert"], [role="alert"]');
                    return Array.from(errorElements)
                        .filter(el => el.offsetParent !== null)  // Only visible elements
                        .map(el => el.textContent.trim())
                        .join(' | ');
                }''')

                if error_text:
                    logger.error(f"Errors found on page: {error_text}")
                else:
                    logger.error("No error messages found - check login_failed.png")

                return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            await page.screenshot(path="login_error.png")
            return False