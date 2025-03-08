import undetected_chromedriver as uc
from screeninfo import get_monitors
import os
import time

try:
    monitor = get_monitors()[0]
except Exception:
    # Default values for headless environments like EC2
    pass

def get_driver(position, screen_width=1920, screen_height=1080):
    options = uc.ChromeOptions()
    
    # Enable headless mode with proper settings
    options.add_argument("--headless=new")  # New headless mode for Chrome
    options.add_argument("--window-size=1920,1080")  # Set window size in headless mode
    
    # Essential options for stability on cloud VMs
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Memory optimization
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    
    # Set unique debugging port for each instance
    options.add_argument(f'--remote-debugging-port={9222 + position}')
    
    # Disable automation detection
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Bypass Google Consent screen
    options.add_argument("--disable-features=SameSiteByDefaultCookies,CookiesWithoutSameSiteMustBeSecure")
    
    # Prevent pop-ups and infobars
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-infobars")
    
    # Create the driver
    driver = uc.Chrome(options=options)
    
    # Set timeouts
    driver.set_page_load_timeout(30)
    driver.set_script_timeout(30)

    # Force Google to English
    driver.get("https://www.google.com/ncr")
    driver.get("https://www.google.com/?hl=en&gl=us")

    driver.id = position
    return driver


def quit_driver_and_reap_children(driver):
    driver.quit()
    try:
        pid = True
        while pid:
            pid = os.waitpid(-1, os.WNOHANG)
            try:
                if pid[0] == 0:
                    pid = False
            except:
                pass

    except ChildProcessError:
        pass
