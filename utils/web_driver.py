import undetected_chromedriver as uc
from screeninfo import get_monitors
import os
import time
import psutil
import socket
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    monitor = get_monitors()[0]
except Exception:
    # Default values for headless environments like EC2
    pass

def is_port_in_use(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def get_driver(position, screen_width=1920, screen_height=1080):
    # Find an available debugging port
    debug_port = 9222 + position
    while is_port_in_use(debug_port):
        debug_port += 1
    
    options = uc.ChromeOptions()
    
    # Essential options for stability on cloud VMs
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Set unique debugging port
    options.add_argument(f'--remote-debugging-port={debug_port}')
    
    # Memory optimization
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--js-flags=--max-old-space-size=1024')
    
    # Disable automation detection
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Bypass Google Consent screen
    options.add_argument("--disable-features=SameSiteByDefaultCookies,CookiesWithoutSameSiteMustBeSecure")
    
    # Prevent pop-ups and infobars
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-infobars")
    
    # Set a unique user data directory for each instance
    options.add_argument(f"--user-data-dir=/tmp/chrome-data-{position}")
    
    # Create driver with retry mechanism
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            driver = uc.Chrome(options=options)
            driver.set_page_load_timeout(30)
            driver.set_script_timeout(30)
            
            # Store the debugging port with the driver
            driver.debug_port = debug_port
            
            # Calculate window dimensions
            window_width = int(screen_width / 2)
            window_height = int(screen_height / 2)

            # Set window size first
            driver.set_window_size(window_width, window_height)

            # Then set position based on quadrant
            if position == 1:
                driver.set_window_position(0, 0)  # top left
            elif position == 2:
                driver.set_window_position(window_width, 0)  # top right
            elif position == 3:
                driver.set_window_position(0, window_height)  # bottom left
            elif position == 4:
                driver.set_window_position(window_width, window_height)  # bottom right

            # Force Google to English
            driver.get("https://www.google.com/ncr")
            driver.get("https://www.google.com/?hl=en&gl=us")

            # Test that the driver is responsive
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            driver.id = position
            return driver
            
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {str(e)}")
            # Clean up any orphaned processes before retrying
            try:
                kill_chrome_processes(debug_port)
            except:
                pass
            
            if attempt == max_attempts - 1:
                raise

def kill_chrome_processes(debug_port=None):
    """Kill Chrome processes, optionally filtering by debug port."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if it's a Chrome process
            if 'chrome' in proc.info['name'].lower():
                # If debug_port is specified, only kill Chrome with that debugging port
                if debug_port is not None:
                    cmdline = proc.info.get('cmdline', [])
                    if any(f'--remote-debugging-port={debug_port}' in arg for arg in cmdline):
                        proc.kill()
                else:
                    # Kill all Chrome processes
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

def quit_driver_and_reap_children(driver):
    """Properly quit the driver and clean up Chrome processes."""
    debug_port = getattr(driver, 'debug_port', None)
    
    try:
        driver.quit()
    except Exception as e:
        print(f"Error quitting driver: {str(e)}")
    
    # Kill any remaining Chrome processes with this debugging port
    if debug_port:
        kill_chrome_processes(debug_port)
    
    # Clean up child processes
    try:
        pid = True
        while pid:
            pid = os.waitpid(-1, os.WNOHANG)
            if pid[0] == 0:
                pid = False
    except ChildProcessError:
        pass
