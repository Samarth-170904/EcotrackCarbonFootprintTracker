import pytest
import unittest
import threading
import socket
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import os
from app import app, validate_kwh_input, calculate_co2_emission, init_db

# URL of the local Flask application
APP_URL = "http://127.0.0.1:5001"


# ==============================================================================
# WHITE BOX TESTING (Unit Tests)
# ==============================================================================

class TestWhiteBoxTesting(unittest.TestCase):
    """
    White box testing using Dynamic Testing and formal methodologies
    like Logic Coverage and Basis Path Testing.
    """

    def setUp(self):
        """Set up a test-specific application context and in-memory database."""
        self.app = app
        self.app.config['TESTING'] = True
        # Use an in-memory database to not interfere with the main DB
        self.app.config['DATABASE'] = 'file:memory?mode=memory&cache=shared'
        self.client = self.app.test_client()
        with self.app.app_context():
            init_db()

    # --- Start of Basis Path Testing for validate_kwh_input ---
    # The function's logic has a cyclomatic complexity of 5, requiring 5 test cases
    # to cover all independent paths through the code.

    def test_basis_path_1_empty_input(self):
        """Tests Path 1: Empty or whitespace input which fails the initial check."""
        is_valid, error, value = validate_kwh_input("   ")
        self.assertFalse(is_valid)
        self.assertEqual(error, "Please enter a value.")
        self.assertIsNone(value)

    def test_basis_path_2_non_numeric_input(self):
        """Tests Path 2: Non-numeric input that raises a ValueError."""
        is_valid, error, value = validate_kwh_input("abc")
        self.assertFalse(is_valid)
        self.assertEqual(error, "Please enter a valid number.")
        self.assertIsNone(value)

    def test_basis_path_3_less_than_or_equal_to_zero(self):
        """Tests Path 3: Numeric input that is not positive (<= 0)."""
        is_valid, error, value = validate_kwh_input("-100")
        self.assertFalse(is_valid)
        self.assertEqual(error, "Value must be greater than 0.")
        self.assertIsNone(value)

    def test_basis_path_4_exceeds_upper_boundary(self):
        """Tests Path 4: Numeric input that exceeds the maximum limit."""
        is_valid, error, value = validate_kwh_input("100000")
        self.assertFalse(is_valid)
        self.assertEqual(error, "Value cannot exceed 99,999.")
        self.assertIsNone(value)
        
    def test_basis_path_5_valid_input(self):
        """Tests Path 5: A fully valid input that passes all checks."""
        is_valid, error, value = validate_kwh_input("500")
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        self.assertEqual(value, 500.0)

    # --- End of Basis Path Testing ---

    def test_calculate_co2_emission(self):
        """Tests the simple multiplication logic of the calculation function."""
        self.assertAlmostEqual(calculate_co2_emission(100), 37.0)
        self.assertAlmostEqual(calculate_co2_emission(123.45), 45.6765)


# ==============================================================================
# BLACK BOX TESTING (UI/E2E Tests)
# ==============================================================================

def _is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        try:
            sock.connect((host, port))
            return True
        except Exception:
            return False


def _start_server_if_needed():
    if not _is_port_open('127.0.0.1', 5001):
        def run_app():
            app.config['TESTING'] = True
            # Keep default file DB for E2E; ensure tables exist
            with app.app_context():
                init_db()
            app.run(debug=False, port=5001, use_reloader=False)

        thread = threading.Thread(target=run_app, daemon=True)
        thread.start()
        # Wait for server to come up
        for _ in range(50):
            if _is_port_open('127.0.0.1', 5001):
                break
            time.sleep(0.1)


@pytest.fixture(scope="module", autouse=True)
def live_server():
    _start_server_if_needed()
    yield


@pytest.fixture(scope="module")
def driver(live_server):
    """Selenium WebDriver fixture using Selenium Manager when possible."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = None
    init_errors = []
    # Try Selenium Manager (no explicit service path)
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e1:
        init_errors.append(e1)
        # Try explicit empty service (Selenium Manager fallback)
        try:
            driver = webdriver.Chrome(service=ChromeService(), options=options)
        except Exception as e2:
            init_errors.append(e2)

    if driver is None:
        pytest.fail(f"Failed to initialize WebDriver: {init_errors}")

    driver.implicitly_wait(5)
    yield driver
    driver.quit()

def enter_kwh_and_submit(driver, kwh_value):
    """
    An efficient helper function to log in (if needed) and submit a calculation.
    It checks login status to avoid redundant registration/login steps.
    """
    # Ensure we're on the app and not a blank page
    driver.get(APP_URL)
    try:
        driver.find_element(By.CLASS_NAME, "btn-logout")
    except NoSuchElementException:
        # Not logged in, so register and/or log in.
        driver.get(f"{APP_URL}/register")
        try:
            WebDriverWait(driver, 10).until(EC.url_contains("register"))
            driver.find_element(By.NAME, "username").send_keys("testuser")
            driver.find_element(By.NAME, "email").send_keys("test@example.com")
            driver.find_element(By.NAME, "password").send_keys("testpass123")
            driver.find_element(By.NAME, "confirm_password").send_keys("testpass123")
            driver.find_element(By.XPATH, "//button[@type='submit']").click()
        except TimeoutException: # Already on login page, user exists
            pass

        WebDriverWait(driver, 10).until(EC.url_contains("login"))
        driver.find_element(By.NAME, "username").send_keys("testuser")
        driver.find_element(By.NAME, "password").send_keys("testpass123")
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        WebDriverWait(driver, 10).until(EC.url_contains("calculator"))

    driver.get(f"{APP_URL}/calculator")
    kwh_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "kwh")))
    kwh_input.clear()
    kwh_input.send_keys(str(kwh_value))
    driver.find_element(By.XPATH, "//button[@type='submit']").click()


class TestEquivalenceClassPartitioning:
    """Tests using the Equivalence Class Partitioning (ECP) technique."""
    
    def test_ecp_valid_integer_input(self, driver):
        enter_kwh_and_submit(driver, "5000")
        result = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "result-value")))
        assert "1850.00" in result.text
    
    def test_ecp_invalid_string_input(self, driver):
        enter_kwh_and_submit(driver, "not_a_number")
        error = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "error-card")))
        assert "Please enter a valid number" in error.text
    
    def test_ecp_invalid_negative_input(self, driver):
        enter_kwh_and_submit(driver, "-100")
        error = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "error-card")))
        assert "Value must be greater than 0" in error.text


class TestBoundaryValueAnalysis:
    """Tests using the Boundary Value Analysis (BVA) technique."""
    
    def test_bva_zero_boundary(self, driver):
        enter_kwh_and_submit(driver, "0")
        error = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "error-card")))
        assert "Value must be greater than 0" in error.text
    
    def test_bva_maximum_valid_value(self, driver):
        enter_kwh_and_submit(driver, "99999")
        result = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "result-value")))
        expected = 99999 * 0.37
        assert f"{expected:.2f}" in result.text
    
    def test_bva_just_above_maximum_valid(self, driver):
        enter_kwh_and_submit(driver, "100000")
        error = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "error-card")))
        assert "Value cannot exceed 99,999" in error.text


class TestStateTransitions:
    """Tests using the State Table-Based Testing technique."""
    
    def test_state_transition_login_logout(self, driver):
        # Initial State: Guest. Action: Login.
        enter_kwh_and_submit(driver, "1") # This helper function logs us in.
        
        # New State: Authenticated. Verify by waiting for welcome text to be present.
        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element((By.CLASS_NAME, "welcome-text"), "Welcome, testuser!")
        )
        
        # Action: Logout.
        driver.find_element(By.CLASS_NAME, "btn-logout").click()
        
        # Final State: Guest. Verify by checking URL and trying to access protected page.
        WebDriverWait(driver, 10).until(EC.url_contains("login"))
        driver.get(f"{APP_URL}/history")
        WebDriverWait(driver, 10).until(EC.url_contains("login"))
        assert "login" in driver.current_url.lower()


class TestDecisionTable:
    """Tests using the Decision Table-Based Testing technique."""
    
    @pytest.mark.parametrize("input_val, expected_result_type", [
        ("", "error"),          # Rule 1: Empty input
        ("abc", "error"),       # Rule 2: Non-numeric
        ("-100", "error"),      # Rule 3: Out of range (low)
        ("150000", "error"),    # Rule 4: Out of range (high)
        ("5000", "success"),    # Rule 5: Valid input
    ])
    def test_decision_table_validation(self, driver, input_val, expected_result_type):
        enter_kwh_and_submit(driver, input_val)
        if expected_result_type == "error":
            element = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "error-card")))
            assert element.is_displayed()
        else:
            element = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "result-value")))
            assert element.is_displayed()


class TestErrorGuessing:
    """Tests using the Error Guessing technique for non-standard inputs."""

    @pytest.mark.parametrize("edge_case_input", [
        "1,000",      # Comma formatting
        "1e3",        # Scientific notation
        "+100",       # Leading plus sign
    ])
    def test_edge_case_inputs(self, driver, edge_case_input):
        enter_kwh_and_submit(driver, edge_case_input)
        # The application should handle these by showing a validation error, not crashing.
        error = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "error-card")))
        assert "Please enter a valid number" in error.text

    def test_sql_injection_attempt(self, driver):
        """Guesses that a user might attempt SQL injection."""
        enter_kwh_and_submit(driver, "1'; DROP TABLE users; --")
        error = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "error-card")))
        assert error.is_displayed()


class TestIntegration:
    """An integration test covering a complete user workflow (STLC)."""
    
    def test_complete_user_journey(self, driver):
        # 1. Start as a guest and register a new, unique user
        test_user = f"journey_user_{os.urandom(4).hex()}"
        driver.get(f"{APP_URL}/register")
        driver.find_element(By.NAME, "username").send_keys(test_user)
        driver.find_element(By.NAME, "email").send_keys(f"{test_user}@example.com")
        driver.find_element(By.NAME, "password").send_keys("password123")
        driver.find_element(By.NAME, "confirm_password").send_keys("password123")
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        
        # 2. Log in with the new credentials
        WebDriverWait(driver, 10).until(EC.url_contains("login"))
        driver.find_element(By.NAME, "username").send_keys(test_user)
        driver.find_element(By.NAME, "password").send_keys("password123")
        driver.find_element(By.XPATH, "//button[@type='submit']").click()

        # 3. Perform multiple calculations
        WebDriverWait(driver, 10).until(EC.url_contains("calculator"))
        enter_kwh_and_submit(driver, "100") # First calculation
        WebDriverWait(driver, 5).until(EC.text_to_be_present_in_element((By.CLASS_NAME, "result-value"), "37.00"))
        
        enter_kwh_and_submit(driver, "500") # Second calculation
        WebDriverWait(driver, 5).until(EC.text_to_be_present_in_element((By.CLASS_NAME, "result-value"), "185.00"))

        # 4. View the history page and verify the calculations are present
        driver.get(f"{APP_URL}/history")
        history_table = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        table_text = history_table.text
        assert "100.00 kWh" in table_text
        assert "37.00 kg CO₂e" in table_text
        assert "500.00 kWh" in table_text
        assert "185.00 kg CO₂e" in table_text

        # 5. Log out
        driver.find_element(By.CLASS_NAME, "btn-logout").click()
        WebDriverWait(driver, 10).until(EC.url_contains("login"))
        assert "login" in driver.current_url.lower()