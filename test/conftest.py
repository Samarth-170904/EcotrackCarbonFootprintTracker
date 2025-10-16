# test\conftest.py

# This is the NEW and CORRECT code
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService

@pytest.fixture(scope="session")
def driver():
    """Provides a single WebDriver instance for the entire test session."""
    # Selenium will now automatically download and manage the driver!
    service = ChromeService()
    driver = webdriver.Chrome(service=service)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()