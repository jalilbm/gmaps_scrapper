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
    
    # Basic options that are less likely to cause issues
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-features=TranslateUI")
    
    # Force English language and locale
    options.add_argument("--lang=en-US")
    
    # Disable automation detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Simplified experimental options
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Simplified preferences
    prefs = {
        "profile.default_content_setting_values.geolocation": 1,
        "profile.managed_default_content_settings.images": 1,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2
    }
    options.add_experimental_option('prefs', prefs)

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


    # Set geolocation to US
    driver.execute_cdp_cmd("Emulation.setGeolocationOverride", {
        "latitude": 37.7749,  # San Francisco, CA
        "longitude": -122.4194,
        "accuracy": 10
    })

    # Set page load strategy
    driver.execute_script("""
        Object.defineProperty(navigator, 'language', {get: function() {return 'en-US';}});
        Object.defineProperty(navigator, 'languages', {get: function() {return ['en-US', 'en'];}});
        document.documentElement.setAttribute('lang', 'en-US');
        document.documentElement.setAttribute('dir', 'ltr');
    """)

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
