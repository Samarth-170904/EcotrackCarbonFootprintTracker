# tests/test_regression.py
import pytest
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# A "marker" to run only regression tests: pytest -m regression
regression_test = pytest.mark.regression

@pytest.fixture(scope="module")
def app_url():
    # The Flask app must be running on this URL before starting tests
    return "http://127.0.0.1:5001"

@regression_test
def test_user_login_and_logout(driver, app_url):
    """
    REGRESSION TEST (F01): Verifies that a pre-existing user can log in and log out successfully.
    """
    # Pre-condition: A user 'testuser' with password 'password' must exist in the database.
    driver.get(f"{app_url}/login")
    
    # Log in
    driver.find_element(By.NAME, "username").send_keys("testuser")
    driver.find_element(By.NAME, "password").send_keys("password")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    # Verify successful login by checking for the calculator page
    wait = WebDriverWait(driver, 10)
    calculator_header = wait.until(EC.visibility_of_element_located((By.TAG_NAME, "h1")))
    assert "Carbon Footprint Calculator" in calculator_header.text
    
    # Log out
    driver.find_element(By.LINK_TEXT, "Logout").click()
    
    # Verify successful logout by checking for the login page
    login_header = wait.until(EC.visibility_of_element_located((By.TAG_NAME, "h2")))
    assert "Login" in login_header.text
    flash_message = driver.find_element(By.CLASS_NAME, "alert-success").text
    assert "You have been logged out successfully" in flash_message

@regression_test
def test_invalid_login(driver, app_url):
    """
    REGRESSION TEST (F01): Verifies that login fails with incorrect credentials.
    """
    driver.get(f"{app_url}/login")
    driver.find_element(By.NAME, "username").send_keys("testuser")
    driver.find_element(By.NAME, "password").send_keys("wrongpassword")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    
    # Verify error message
    error_message = driver.find_element(By.CLASS_NAME, "alert-error").text
    assert "Invalid username or password" in error_message

@regression_test
def test_calculation_and_history_persistence(driver, app_url):
    """
    REGRESSION TEST (F02, F03, F04): Verifies the core calculation workflow and
    ensures the result is correctly saved to history.
    """
    # Log in first to get access to the calculator
    driver.get(f"{app_url}/login")
    driver.find_element(By.NAME, "username").send_keys("testuser")
    driver.find_element(By.NAME, "password").send_keys("password")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    
    # Wait for calculator page to load
    wait = WebDriverWait(driver, 10)
    wait.until(EC.url_contains("/calculator"))
    
    # Perform a calculation (F02, F03)
    kwh_value = "500"
    expected_co2 = "185" # Based on 500 * 0.37
    driver.find_element(By.NAME, "kwh").send_keys(kwh_value)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    
    # Verify the result is displayed on the page
    result_text = wait.until(EC.visibility_of_element_located((By.TAG_NAME, "h2"))).text
    assert expected_co2 in result_text
    
    # Navigate to history and verify persistence (F04)
    driver.find_element(By.LINK_TEXT, "History").click()
    
    # Verify the latest entry in the history table
    wait.until(EC.url_contains("/history"))
    first_row = driver.find_element(By.XPATH, "//tbody/tr[1]")
    
    assert kwh_value in first_row.text
    assert expected_co2 in first_row.text

@regression_test
def test_kwh_input_validation_boundary(driver, app_url):
    """
    REGRESSION TEST (F02): Verifies that invalid boundary inputs are rejected.
    """
    # Log in
    driver.get(f"{app_url}/login")
    driver.find_element(By.NAME, "username").send_keys("testuser")
    driver.find_element(By.NAME, "password").send_keys("password")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait = WebDriverWait(driver, 10)
    wait.until(EC.url_contains("/calculator"))
    
    # Test with a value of 0
    driver.find_element(By.NAME, "kwh").send_keys("0")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    
    # Verify error message
    error_message = driver.find_element(By.CLASS_NAME, "error").text # Assuming error class is 'error'
    assert "Value must be greater than 0" in error_message