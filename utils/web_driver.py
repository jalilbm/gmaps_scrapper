import undetected_chromedriver as uc
from screeninfo import get_monitors
import os

try:
    monitor = get_monitors()[0]
except Exception:
    # Default values for headless environments like EC2
    pass

def get_driver(position, screen_width=1920, screen_height=1080):
    options = uc.ChromeOptions()
    
    # Set a US location to avoid consent pages (may help in some cases)
    options.add_argument("--lang=en-US")
    options.add_argument("--country=US")
    
    # Disable automation detection
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Bypass Google Consent screen
    options.add_argument("--disable-features=SameSiteByDefaultCookies,CookiesWithoutSameSiteMustBeSecure")
    
    # Prevent pop-ups and infobars
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-infobars")
    
    driver = uc.Chrome(options=options)

    # Calculate window dimensions - each window should be half the screen
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

    # Force Google to English and US region
    driver.get("https://www.google.com/ncr")  # No Country Redirect
    
    
    # Set Google to US region
    driver.get("https://www.google.com/?gl=us&hl=en")

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
