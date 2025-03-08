import contextlib
import random
from utils import web_driver, parsers, helpers, geo
import time
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    TimeoutException,
    WebDriverException,
    InvalidSessionIdException,
    SessionNotCreatedException,
    NoSuchWindowException,
)
import re
# from outputs import output_generator
from random import shuffle
from datetime import datetime
from selenium.webdriver.common.action_chains import ActionChains
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Semaphore
from urllib3.exceptions import MaxRetryError
from threading import Thread
from logger.logger import CustomLogger

# Initialize logger
logger = CustomLogger("google_maps_scraper").get_logger()

# Global variables for compatibility with existing code
location_name = "dubai"
non_allowed_categories = []
places_details = []
scraped_places = []
scraped_urls = []

# def generate_outputs(places_details, keyword):
#     formatted_datetime = datetime.now().strftime("_%Y-%m-%d_H%H_M%M_S%S")
#     output_file_name = (
#         keyword.replace(" ", "_") + f"_{len(places_details)}" + formatted_datetime
#     )
#     with open("test_2.json", "w") as f:
#         json.dump(places_details, f, indent=2)
#     with open(f"./outputs/{output_file_name}.json", "w") as f:
#         json.dump(places_details, f, indent=2)
#     logger.info(f"Generated output file: {output_file_name}")
#     output_generator.output_generator(places_details, output_file_name)


def get_selectors():
    with open("utils/selectors.json", "r") as json_file:
        return json.load(json_file)


class GoogleMaps:
    def __init__(self, search_url, driver, selectors):
        self.driver = driver
        self.search_url = search_url
        selectors = selectors
        self.retrying_times = 0
        self.logger = CustomLogger("GoogleMaps").get_logger()

    def wait_for_css_selector(self, css_selector, timeout=10):
        """
        Wait for the presence of a css selector in self.driver

        Parameters:
        css_selector (str): The CSS selector to wait for.
        timeout (int, optional): The number of seconds to wait before timing out. Default is 10 seconds.
        """

        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
            )
            return True
        except (
            InvalidSessionIdException,
            SessionNotCreatedException,
            NoSuchWindowException,
        ):
            self.logger.error(f"Browser session error while waiting for selector: {css_selector}", exc_info=True)
            raise NoSuchWindowException
        except Exception as e:
            self.logger.warning(f"Timeout waiting for selector: {css_selector}, Exception: {e}")
            return False

    def wait_for_css_selector_to_disappear(self, css_selector, timeout=10):
        """
        Wait for the absence of a css selector in self.driver

        Parameters:
        css_selector (str): The CSS selector to wait for.
        timeout (int): Maximum number of seconds to wait for the element to disappear.
        """
        WebDriverWait(self.driver, timeout).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, css_selector))
        )

    def scroll_element_into_viewport(self, element):
        """
        Scroll element into center of the viewport makes sure that the element is in the center of the viewport so we can interact with it

        Args:
            element (WebElement): a selenium web element
        """

        while not self.driver.execute_script(
            """
                const rect = arguments[0].getBoundingClientRect();
                const windowHeight = (window.innerHeight || document.documentElement.clientHeight);
                const windowWidth = (window.innerWidth || document.documentElement.clientWidth);
                return (
                    rect.top >= 0 &&
                    rect.left >= 0 &&
                    rect.bottom <= windowHeight &&
                    rect.right <= windowWidth
                );
            """,
            element,
        ):
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", element
            )
            time.sleep(0.1)

    def get_element_text(self, css_selector, element=None):
        """
        get text from an element using its css_selector

        Args:
            css_selector (string): css selector of the element
            element (webelement): exact element to locate the css_selector otherwise we will search in the full driver

        Returns:
            string or None: text of the element or None in case it was not found
        """
        try:
            if element is not None:
                element = element.find_element(by=By.CSS_SELECTOR, value=css_selector)
            else:
                element = self.driver.find_element(
                    by=By.CSS_SELECTOR, value=css_selector
                )
            return element.text
        except NoSuchElementException:
            return None

    def click_coordinates(self, x, y):
        coordinates_css_selector = selectors["coordinates"]["css_selector"]
        actions = ActionChains(self.driver)
        body = self.driver.find_element(By.TAG_NAME, "body")
        actions.move_to_element_with_offset(body, x, y)
        actions.context_click()
        actions.perform()
        self.wait_for_css_selector(coordinates_css_selector)
        time.sleep(1000)

    def get_bounds(self):
        # actions = ActionChains(self.driver)
        # coordinates_css_selector = selectors["coordinates"]["css_selector"]
        bounds = {"min_lat": None, "max_lat": None, "min_lon": None, "max_lon": None}
        # Get left bound and top bound
        places_list_css_selector = selectors["places_list"]["css_selector"]
        places_list = self.driver.find_element(
            By.CSS_SELECTOR, value=places_list_css_selector
        )
        search_div_css_selector = selectors["search_div"]["css_selector"]
        search_div = self.driver.find_element(
            By.CSS_SELECTOR, value=search_div_css_selector
        )
        x = places_list.location["x"] + places_list.size["width"] + 10
        y = search_div.location["y"] + search_div.size["height"] + 10
        self.click_coordinates(x, y)
        self.logger.info("Exiting after clicking coordinates for debugging")
        exit()
        # actions.move_to_element_with_offset(
        #     places_list, places_list.size["width"] + 10, 0
        # )
        # actions.context_click()
        # actions.perform()
        # self.wait_for_css_selector(coordinates_css_selector)
        # places_list = self.driver.find_element(
        #     By.CSS_SELECTOR, value=coordinates_css_selector
        # )
        # tmp = self.get_element_text(coordinates_css_selector)
        # bounds["min_lon"] = tmp.split(",")[0].strip()
        # bounds["min_lat"] = tmp.split(",")[1].strip()
        # # Get right bound and bottom bound

    def click_place_from_list(self, place_div):
        """
        Scroll to place from the left list and click it, then wait for title to load

        Args:
            place_div (webelement): the div element to click
        """
        self.scroll_element_into_viewport(place_div)
        title_css_selector = selectors["places_list"]["inner_elements"]["places_divs"][
            "inner_elements"
        ]["place_details"]["title"]["css_selector"]
        try:
            while True:
                place_div.click()
                # Wait for place details to load
                while not self.wait_for_css_selector(title_css_selector, timeout=3):
                    place_div.click()
                break
        except ElementClickInterceptedException:
            self.scroll_element_into_viewport(place_div)
            time.sleep(1)

    def get_url(self):
        title_css_selector = selectors["places_list"]["inner_elements"]["places_divs"][
            "inner_elements"
        ]["place_details"]["title"]["css_selector"]
        places_list_css_selector = selectors["places_list"]["css_selector"]
        try:
            self.driver.get(self.search_url)
            if not self.wait_for_css_selector(places_list_css_selector, timeout=10):
                if not self.wait_for_css_selector(title_css_selector, timeout=2):
                    raise TimeoutException
        except TimeoutException:
            return False
        except Exception:
            return False
        return True

    def scrap_data_from_search_url(self):
        """
        Go through the list of search urls in inputs and scrap the places
        """
        global scraped_urls

        while True:
            try:                
                # create thread for the url check
                get_url = Thread(target=self.get_url)
                get_url.start()

                # wait for 12 seconds for the thread to finish
                get_url.join(timeout=12)

                # check if the thread is still alive (i.e., it didn't finish within 12 seconds)
                if get_url.is_alive() or not get_url:
                    raise WebDriverException("Failed to get url")
                
                logger.info(f"Scrolling all places in list")
                result = self.scroll_all_places_in_list()
                if result == "No list":
                    self.get_data_from_place(one_item=True)
                    break

                logger.info(f"Getting all places divs")
                all_places_divs = self.get_all_places_divs()
                self.logger.info(f"All places divs: {len(all_places_divs)}")

                logger.info(f"Getting bounds")
                # self.get_bounds()

                logger.info(f"Getting data from places")
                for i, place_div in enumerate(all_places_divs):
                    self.logger.info(
                        f"URLS:[{len(scraped_urls)}/{len(urls)}]-LIST:[{i+1}/{len(all_places_divs)}]-DONE:[{len(places_details)}]"
                    )
                    self.get_data_from_place(place_div=place_div)
                break
            except (
                InvalidSessionIdException,
                SessionNotCreatedException,
                NoSuchWindowException,
                WebDriverException,
                MaxRetryError,
            ):
                self.logger.error("Browser session error while scrap_data_from_search_url", exc_info=True, extra={"url": self.search_url})
                raise NoSuchWindowException
            except Exception:
                self.logger.error("Unexpected error while scrap_data_from_search_url", exc_info=True, extra={"url": self.search_url})
        scraped_urls.append(self.search_url)
        return

    def scroll_all_places_in_list(self):
        """
        Scroll the list of places that shows on the left of google maps search result
        """
        place_css_selector = selectors["places_list"]["inner_elements"]["places_divs"][
            "css_selector"
        ]
        title_css_selector = selectors["places_list"]["inner_elements"]["places_divs"][
            "inner_elements"
        ]["place_details"]["title"]["css_selector"]
        places_list_css_selector = selectors["places_list"]["css_selector"]
        
        logger.info(f"Waiting for places list to load: {places_list_css_selector}", )

        if self.wait_for_css_selector(places_list_css_selector, timeout=20):
            places_list = self.driver.find_element(
                by=By.CSS_SELECTOR, value=places_list_css_selector
            )
        elif self.wait_for_css_selector(title_css_selector, timeout=15):
            self.logger.info("No list found, only one place")
            return "No list"
        else:
            self.logger.error("No list found after waiting for 20 seconds", extra={"url": self.search_url})
            raise (NoSuchWindowException)
        # Loop until "You've reached the end of the list." appears or it kept loading for 10 seconds

        # Get the initial height of the list
        initial_height = self.driver.execute_script(
            "return arguments[0].scrollHeight", places_list
        )

        # Initialize a counter for the number of times the height has not changed
        no_change_count = 0

        while True:
            # Scroll the div by randint(300, 600) pixels
            scroll = random.randint(300, 600)
            self.driver.execute_script(
                f"arguments[0].scrollTop += {scroll}", places_list
            )

            # Check if the specified paragraph is present
            try:
                if WebDriverWait(self.driver, 0.1).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            selectors["places_list"]["inner_elements"][
                                "stop_paragraph"
                            ]["css_selector"],
                        )
                    )
                ):
                    break
            except (
                InvalidSessionIdException,
                SessionNotCreatedException,
                NoSuchWindowException,
            ):
                self.logger.error("Browser session error while scrolling places list", exc_info=True)
                raise NoSuchWindowException
            except Exception:
                # Get the current height of the reviews list
                current_height = self.driver.execute_script(
                    "return arguments[0].scrollHeight", places_list
                )
                # If the height is the same as the initial height, increment the no_change_count
                if initial_height == current_height:
                    no_change_count += 1
                else:
                    no_change_count = 0
                # Update the initial_height
                initial_height = current_height
                # If no changes after 10 attempts, raise exception
                if no_change_count >= 20:
                    self.logger.warning("No change in scroll places list height after 20 attempts", extra={"url": self.search_url, "no_change_count": no_change_count})
                    current_place_count = len(
                        places_list.find_elements(By.CSS_SELECTOR, place_css_selector)
                    )
                    self.logger.debug(f"Current place count: {current_place_count}")
                    if current_place_count >= 70:
                        return
                    self.retrying_times += 1
                    self.logger.warning(f"Places loading error, attempt {self.retrying_times}")
                    if self.retrying_times >= 2:
                        self.retrying_times = 0
                        return
                    raise NoSuchWindowException

    def get_all_places_divs(self):
        css_selector = selectors["places_list"]["inner_elements"]["places_divs"][
            "css_selector"
        ]
        return list(
            dict.fromkeys(
                self.driver.find_elements(by=By.CSS_SELECTOR, value=css_selector)
            )
        )

    def close_place_details(self):
        while True:
            try:
                close_place_details_selector = selectors["places_list"][
                    "inner_elements"
                ]["places_divs"]["inner_elements"]["place_details"]["close"][
                    "css_selector"
                ]
                self.driver.find_element(
                    by=By.CSS_SELECTOR, value=close_place_details_selector
                ).click()
                no_change_count = 0
                while True:
                    try:
                        self.wait_for_css_selector_to_disappear(
                            close_place_details_selector, timeout=1
                        )
                        break
                    except TimeoutException:
                        no_change_count += 1
                        if no_change_count >= 20:
                            raise Exception
                        self.driver.find_element(
                            by=By.CSS_SELECTOR, value=close_place_details_selector
                        ).click()
                break
            except (
                InvalidSessionIdException,
                SessionNotCreatedException,
                NoSuchWindowException,
            ):
                self.logger.error("Browser session error while closing place details", exc_info=True, extra={"url": self.search_url})
                raise NoSuchWindowException
            except Exception:
                self.logger.error("Unexpected error while closing place details", exc_info=True, extra={"url": self.search_url})
                return

    def get_place_title(self):
        title_css_selector = selectors["places_list"]["inner_elements"]["places_divs"][
            "inner_elements"
        ]["place_details"]["title"]["css_selector"]
        return self.get_element_text(title_css_selector)

    def get_place_category(self):
        category_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["category"]["css_selector"]
        return self.get_element_text(category_css_selector)

    def get_place_number_of_reviews(self):
        number_of_reviews_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["number_of_reviews"]["css_selector"]
        number_of_reviews = self.get_element_text(number_of_reviews_css_selector)
        if number_of_reviews:
            return int(
                number_of_reviews.replace("(", "").replace(")", "").replace(",", "")
            )
        return None

    def get_place_average_reviews(self):
        average_reviews_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["average_reviews"]["css_selector"]
        return self.get_element_text(average_reviews_css_selector)

    def get_place_address(self):
        address_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["address"]["css_selector"]
        return self.get_element_text(address_css_selector)

    def get_place_phone_number(self):
        phone_number_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["phone_number"]["css_selector"]
        return self.get_element_text(phone_number_css_selector)

    def get_place_website(self):
        website_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["website"]["css_selector"]
        return self.get_element_text(website_css_selector)

    def get_place_plus_code(self):
        plus_code_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["plus_code"]["css_selector"]
        return self.get_element_text(plus_code_css_selector)

    def get_place_working_hours_table(self):
        working_hours_table_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["working_hours_table"]["css_selector"]

        try:
            element = self.driver.find_element(
                by=By.CSS_SELECTOR, value=working_hours_table_css_selector
            )
            return parsers.working_hours_parser(element.get_attribute("outerHTML"))
        except NoSuchElementException:
            return None

    def get_place_coordinates(self, place_div):
        place_coordinates_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["coordinate_from_list"]["css_selector"]
        if place_div:
            href = place_div.find_element(
                by=By.CSS_SELECTOR,
                value=place_coordinates_css_selector,
            ).get_attribute("href")
        else:
            href = (
                self.driver.find_element(
                    by=By.CSS_SELECTOR,
                    value="body",
                )
                .find_element(
                    by=By.CSS_SELECTOR,
                    value=place_coordinates_css_selector,
                )
                .get_attribute("href")
            )
        return (
            href.split("!3d")[1].split("!4d")[0]
            + ","
            + href.split("!3d")[1].split("!4d")[1].split("!16")[0]
        )

    def get_reviewer_name(self, review_element):
        reviewer_name_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["review"]["inner_elements"]["reviewer"][
            "inner_elements"
        ][
            "name"
        ][
            "css_selector"
        ]
        return self.get_element_text(reviewer_name_css_selector, element=review_element)

    def get_reviewer_number_of_reviews(self, review_element):
        reviewer_number_of_reviews_css_selector = selectors["places_list"][
            "inner_elements"
        ]["places_divs"]["inner_elements"]["place_details"]["review"]["inner_elements"][
            "reviewer"
        ][
            "inner_elements"
        ][
            "number_of_reviews"
        ][
            "css_selector"
        ]
        number_of_reviews_text = self.get_element_text(
            reviewer_number_of_reviews_css_selector, element=review_element
        )
        if not number_of_reviews_text:
            return None
        try:
            return int(
                re.search(
                    r"\d+",
                    number_of_reviews_text,
                ).group()
            )
        except (
            InvalidSessionIdException,
            SessionNotCreatedException,
            NoSuchWindowException,
        ):
            self.logger.error("Browser session error while getting reviewer number of reviews", exc_info=True, extra={"url": self.search_url})
            raise NoSuchWindowException
        except Exception:
            self.logger.error("Unexpected error while getting reviewer number of reviews", exc_info=True, extra={"url": self.search_url, "number_of_reviews_text": number_of_reviews_text})

    def get_review_text(self, review_element: WebElement):
        # check if there is a "More" to click it
        more = review_element.find_elements(
            by=By.CSS_SELECTOR,
            value=selectors["places_list"]["inner_elements"]["places_divs"][
                "inner_elements"
            ]["place_details"]["review"]["inner_elements"]["see_more_button"][
                "css_selector"
            ],
        )
        if len(more) > 0:
            no_change_count = 0
            while True:
                try:
                    self.scroll_element_into_viewport(more[0])
                    # Wait for the "More" button to be clickable
                    more_button = WebDriverWait(review_element, 10).until(
                        EC.element_to_be_clickable(
                            (
                                By.CSS_SELECTOR,
                                selectors["places_list"]["inner_elements"][
                                    "places_divs"
                                ]["inner_elements"]["place_details"]["review"][
                                    "inner_elements"
                                ][
                                    "see_more_button"
                                ][
                                    "css_selector"
                                ],
                            )
                        )
                    )

                    self.driver.execute_script("arguments[0].click();", more_button)
                    time.sleep(0.1)
                    break
                except (
                    InvalidSessionIdException,
                    SessionNotCreatedException,
                    NoSuchWindowException,
                ):
                    self.logger.error("Browser session error while getting review text", exc_info=True, extra={"url": self.search_url})
                    raise NoSuchWindowException
                except ElementClickInterceptedException:
                    self.logger.error("Element click intercepted while getting review text", exc_info=True, extra={"url": self.search_url, "review_element": review_element})
                    self.scroll_element_into_viewport(more[0])
                    time.sleep(0.5)
                except Exception:
                    self.logger.error("Unexpected error while getting review text", exc_info=True, extra={"url": self.search_url, "review_element": review_element})
                    if no_change_count >= 20:
                        raise NoSuchWindowException
                    no_change_count += 1
                    time.sleep(0.5)
                    break

        # Get review text
        review_text_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["review"]["inner_elements"]["review_text"][
            "css_selector"
        ]
        return self.get_element_text(review_text_css_selector, element=review_element)

    def get_review_rating(self, review_element: WebElement):
        review_rating_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["review"]["inner_elements"][
            "review_rating"
        ][
            "css_selector"
        ]
        review_rating_element = review_element.find_element(
            by=By.CSS_SELECTOR,
            value=review_rating_css_selector,
        )
        aria_label_value = review_rating_element.get_attribute("aria-label")
        while True:
            try:
                return int(re.search(r"\d+", aria_label_value).group())
            except (
                InvalidSessionIdException,
                SessionNotCreatedException,
                NoSuchWindowException,
            ):
                self.logger.error("Browser session error while getting review rating", exc_info=True)
                raise NoSuchWindowException
            except Exception:
                self.logger.error(
                    "Error parsing review rating",
                    extra={
                        "url": self.search_url,
                        "data": {
                            "aria_label": aria_label_value,
                            "element_html": review_rating_element.get_attribute("outerHTML")
                        }
                    },
                    exc_info=True
                )
                time.sleep(1)

    def get_review_time(self, review_element: WebElement):
        review_time_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["review"]["inner_elements"]["review_time"][
            "css_selector"
        ]
        return self.get_element_text(review_time_css_selector, element=review_element)

    def get_review_likes_count(self, review_element: WebElement):
        """Get the number of likes for a review."""
        review_likes_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["review"]["inner_elements"][
            "review_number_of_likes"
        ]["css_selector"]
        
        likes_text = self.get_element_text(review_likes_css_selector, element=review_element)
        if not likes_text:
            return 0
        
        try:
            # Extract the number from text like "5" or similar
            return int(re.search(r'\d+', likes_text).group())
        except (AttributeError, ValueError):
            self.logger.warning(f"Could not parse review likes count: '{likes_text}'", 
                               extra={"url": self.search_url})
            return 0

    def get_review_data(self, review_element):
        review_rating = self.get_review_rating(review_element)
        review_time = self.get_review_time(review_element)
        reviewer_name = self.get_reviewer_name(review_element)
        reviewer_number_of_reviews = self.get_reviewer_number_of_reviews(review_element)
        review_text = self.get_review_text(review_element)
        review_likes = self.get_review_likes_count(review_element)
        
        return {
            "review_rating": review_rating,
            "review_time": review_time,
            "reviewer_name": reviewer_name,
            "reviewer_number_of_reviews": reviewer_number_of_reviews,
            "review_text": review_text,
            "review_likes": review_likes
        }

    def sort_reviews_by_time(self):
        reviews_sort_button_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["reviews_sort_button"]["css_selector"]
        self.wait_for_css_selector(reviews_sort_button_css_selector)
        time.sleep(2)
        reviews_sort_button = self.driver.find_element(
            by=By.CSS_SELECTOR, value=reviews_sort_button_css_selector
        )
        reviews_sort_button.click()
        # self.driver.execute_script("arguments[0].click();", reviews_sort_button)
        reviews_newest_sort_option_css_selector = selectors["places_list"][
            "inner_elements"
        ]["places_divs"]["inner_elements"]["place_details"][
            "reviews_newest_sort_option"
        ][
            "css_selector"
        ]
        self.wait_for_css_selector(reviews_newest_sort_option_css_selector)
        time.sleep(1)
        reviews_newest_sort_option = self.driver.find_element(
            by=By.CSS_SELECTOR, value=reviews_newest_sort_option_css_selector
        )
        self.driver.execute_script("arguments[0].click();", reviews_newest_sort_option)

        while True:
            try:
                self.wait_for_css_selector_to_disappear(
                    reviews_newest_sort_option_css_selector, timeout=2
                )
                time.sleep(1)
                break
            except (
                InvalidSessionIdException,
                SessionNotCreatedException,
                NoSuchWindowException,
            ):
                self.logger.error("Browser session error while sorting reviews by time", exc_info=True, extra={"url": self.search_url})
                raise NoSuchWindowException
            except Exception:
                self.logger.error("Unexpected error while sorting reviews by time", exc_info=True, extra={"url": self.search_url})
                reviews_sort_button.click()
                self.driver.execute_script(
                    "arguments[0].click();", reviews_newest_sort_option
                )

        review_css_selector = selectors["places_list"]["inner_elements"]["places_divs"][
            "inner_elements"
        ]["place_details"]["review"]["css_selector"]
        self.wait_for_css_selector(review_css_selector)

    def click_reviews_tab(self):
        no_changes_count = 0
        while True:
            try:
                more_reviews_css_selector = selectors["places_list"]["inner_elements"][
                    "places_divs"
                ]["inner_elements"]["place_details"]["more_reviews_button"][
                    "css_selector"
                ]
                self.driver.find_element(
                    by=By.CSS_SELECTOR, value=more_reviews_css_selector
                ).click()

                # wait for review tab to load
                self.wait_for_css_selector(
                    selectors["places_list"]["inner_elements"]["places_divs"][
                        "inner_elements"
                    ]["place_details"]["review_tab_selected"]["css_selector"],
                    timeout=5,
                )
                break
            except (
                InvalidSessionIdException,
                SessionNotCreatedException,
                NoSuchWindowException,
            ):
                self.logger.error("Browser session error while clicking reviews tab", exc_info=True, extra={"url": self.search_url})
                raise NoSuchWindowException
            except Exception:
                if no_changes_count >= 10:
                    self.logger.error("Unexpected error while clicking reviews tab", exc_info=True, extra={"url": self.search_url})
                    raise Exception
                self.logger.warning(f"Retrying to click reviews tab for the {no_changes_count} time")
                no_changes_count += 1
                time.sleep(0.5)

    def scroll_all_reviews(self, number_of_reviews):
        """
        Scroll the list of reviews that shows in reviews tab
        """
        review_css_selector = selectors["places_list"]["inner_elements"]["places_divs"][
            "inner_elements"
        ]["place_details"]["review"]["css_selector"]
        all_reviews_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["all_reviews"]["css_selector"]
        loading_spin_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["end_of_reviews"]["css_selector"]
        self.wait_for_css_selector(all_reviews_css_selector)
        reviews_list = self.driver.find_element(
            by=By.CSS_SELECTOR, value=all_reviews_css_selector
        )
        # Get the initial height of the reviews list
        initial_height = self.driver.execute_script(
            "return arguments[0].scrollHeight", reviews_list
        )

        # Initialize a counter for the number of times the height has not changed
        no_change_count = 0

        # Loop until "the loading spin" at the end is no more there
        while True:
            # Scroll the div by 600 pixels
            self.driver.execute_script("arguments[0].scrollTop += 5000", reviews_list)
            try:
                WebDriverWait(self.driver, 0.1).until(
                    EC.invisibility_of_element_located(
                        (By.CSS_SELECTOR, loading_spin_css_selector)
                    )
                )
                break
            except (
                InvalidSessionIdException,
                SessionNotCreatedException,
                NoSuchWindowException,
            ):
                self.logger.error("Browser session error while scrolling reviews", exc_info=True)
                raise NoSuchWindowException
            except Exception as e:
                # Get the current height of the reviews list
                current_height = self.driver.execute_script(
                    "return arguments[0].scrollHeight", reviews_list
                )
                # If the height is the same as the initial height, increment the no_change_count
                if initial_height == current_height:
                    no_change_count += 1
                else:
                    no_change_count = 0
                # Update the initial_height
                initial_height = current_height
                # If no changes after 10 attempts, raise exception
                if no_change_count >= 50:
                    current_review_count = len(
                        reviews_list.find_elements(By.CSS_SELECTOR, review_css_selector)
                    )
                    self.logger.debug(f"Current review count: {current_review_count}")
                    if current_review_count >= number_of_reviews:
                        return
                    self.retrying_times += 1
                    self.logger.warning(f"Reviews loading error, attempt {self.retrying_times}")
                    if self.retrying_times >= 2 or current_review_count > 1000:
                        self.retrying_times = 0
                        return
                    raise Exception(
                        "Stuck while waiting for more reviews to load"
                    ) from e

    def get_data_from_reviews(self):
        reviews_data = []
        reviews_elements_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["review"]["css_selector"]
        reviews_elements = self.driver.find_elements(
            by=By.CSS_SELECTOR, value=reviews_elements_css_selector
        )
        for review in reviews_elements:
            review_data = self.get_review_data(review)
            reviews_data.append(review_data)
        return reviews_data

    def get_place_reviews(self, number_of_reviews):
        if number_of_reviews is not None:
            if number_of_reviews > 3:
                self.logger.info(f"Fetching {number_of_reviews} reviews")
                self.click_reviews_tab()
                self.sort_reviews_by_time()
                self.scroll_all_reviews(number_of_reviews)
            self.retrying_times = 0
            reviews = self.get_data_from_reviews()
            self.logger.info(f"Successfully fetched {len(reviews)} reviews")
            return reviews
        return None

    def get_place_url(self):
        share_button_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["share_button"]["css_selector"]
        self.wait_for_css_selector(share_button_css_selector)
        share_button = self.driver.find_element(
            by=By.CSS_SELECTOR, value=share_button_css_selector
        )
        self.driver.execute_script("arguments[0].click();", share_button)
        share_url_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["share_url"]["css_selector"]
        while not self.wait_for_css_selector(share_url_css_selector, timeout=3):
            self.driver.execute_script("arguments[0].click();", share_button)
        share_url = None
        while not share_url:
            time.sleep(1)
            share_url = self.driver.find_element(
                by=By.CSS_SELECTOR, value=share_url_css_selector
            ).get_attribute("value")
        close_share_modal_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["close_share_modal"]["css_selector"]
        self.driver.find_element(
            by=By.CSS_SELECTOR, value=close_share_modal_css_selector
        ).click()
        while True:
            try:
                self.wait_for_css_selector_to_disappear(
                    close_share_modal_css_selector, timeout=1
                )
                time.sleep(1)
                break
            except TimeoutException:
                with contextlib.suppress(Exception):
                    self.driver.find_element(
                        by=By.CSS_SELECTOR, value=close_share_modal_css_selector
                    ).click()
        return share_url

    def get_address_from_list(self, place_div):
        address_from_list_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["address_from_list"]["css_selector"]
        try:
            return place_div.find_element(
                by=By.CSS_SELECTOR, value=address_from_list_css_selector
            ).text
        except NoSuchElementException:
            return "No outside address"

    def get_title_from_list(self, place_div):
        title_from_list_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["title_from_list"]["css_selector"]
        return place_div.find_element(
            by=By.CSS_SELECTOR, value=title_from_list_css_selector
        ).get_attribute("aria-label")

    def get_category_from_list(self):
        category_from_list_css_selector = selectors["places_list"]["inner_elements"][
            "places_divs"
        ]["inner_elements"]["place_details"]["category_from_list"]["css_selector"]
        try:
            if tmp := self.find_element(
                by=By.CSS_SELECTOR, value=category_from_list_css_selector
            ).text:
                return tmp.lower().strip()
        except NoSuchElementException:
            return "no outside category"

    def get_data_from_place(self, place_div: WebElement = None, one_item=False):
        global places_details
        global scraped_places
        """
        Click the place from the left places list and get the necessary data from it

        Args:
            place_div (WebElement): a selenium web element
        """
        # Avoid elements with no height as they won't show
        if not one_item and int(place_div.get_attribute("offsetHeight")) <= 0:
            return
        unique_place = None
        no_changes_count = 0
        while True:
            try:
                try:
                    place_coordinates = self.get_place_coordinates(place_div)
                except Exception:
                    self.logger.error("Failed to get place coordinates", exc_info=True)
                    break
                coordinates = place_coordinates.split(",")
                coordinates.reverse()
                # check if the place is outside the location bounds
                if not geo.check_point_in_bounds(coordinates[0], coordinates[1], location_name):
                    address_from_list = self.get_address_from_list(place_div)
                    title_from_list = self.get_title_from_list(place_div)
                    self.logger.warning(
                        f"Place outside location bounds - Coordinates: {place_coordinates}, Title: {title_from_list}, Address: {address_from_list}",
                        extra={"url": self.search_url, "data": {"coordinates": place_coordinates, "title": title_from_list, "address": address_from_list}}
                    )
                    break
                # if the place is not a single item, check if it's a duplicate
                if not one_item:
                    address_from_list = self.get_address_from_list(place_div)
                    title_from_list = self.get_title_from_list(place_div)
                    unique_place = (title_from_list, address_from_list)
                    if (title_from_list, address_from_list) in scraped_places:
                        self.logger.info(
                            f"Skipping duplicate place - Title: {title_from_list}, Address: {address_from_list}",
                            extra={"url": self.search_url, "data": {"title": title_from_list, "address": address_from_list}}
                        )
                        time.sleep(0.05)
                        return
                    # add the place to the scraped places list so we don't process it again by other running threads
                    scraped_places.append((title_from_list, address_from_list))
                    self.logger.info(
                        f"Processing place - Title: {title_from_list}, Address: {address_from_list}",
                        extra={"url": self.search_url, "data": {"title": title_from_list, "address": address_from_list}}
                    )
                    self.click_place_from_list(place_div)
                title = self.get_place_title()
                address = self.get_place_address()
                if one_item:
                    unique_place = (title, address)
                    if (title, address) in scraped_places:
                        self.logger.info("Skipping duplicate single place", extra={"url": self.search_url, "data": {"title": title, "address": address}})
                        time.sleep(0.05)
                        return
                    scraped_places.append((title, address))
                    self.logger.info(f"Processing single place", extra={"url": self.search_url, "data": {"title": title, "address": address}})
                if not title:
                    self.retrying_times += 1
                    if self.retrying_times >= 6:
                        self.retrying_times = 0
                        raise WebDriverException("Failed to get place title after maximum retries")
                    time.sleep(0.5)
                    continue
                
                url = self.driver.current_url
                category = self.get_place_category()
                if category.lower() in non_allowed_categories:
                    self.logger.info(f"Skipping non-allowed category: {category}", extra={"url": self.search_url, "data": {"category": category}})
                    break

                number_of_reviews = self.get_place_number_of_reviews()
                average_reviews = self.get_place_average_reviews()
                phone_number = self.get_place_phone_number()
                website = self.get_place_website()
                plus_code = self.get_place_plus_code()
                working_hours_table = self.get_place_working_hours_table()
                reviews = self.get_place_reviews(number_of_reviews)

                self.close_place_details()
                places_details.append(
                    {
                        "title": title,
                        "category": category,
                        "number_of_reviews": number_of_reviews,
                        "average_reviews": average_reviews,
                        "address": address,
                        "phone_number": phone_number,
                        "website": website,
                        "plus_code": plus_code,
                        "working_hours_table": working_hours_table,
                        "place_coordinates": place_coordinates,
                        "reviews": reviews,
                        "url": url,
                    }
                )
                self.logger.info("Successfully scraped place data", extra={"url": url, "data": {"title": title, "category": category}})
                break

            except (
                InvalidSessionIdException,
                WebDriverException,
                SessionNotCreatedException,
            ) as e:
                self.logger.warning(f"Browser session error while get_data_from_place for the {no_changes_count} time", extra={"url": self.search_url})
                if no_changes_count >= 10:
                    self.logger.error("Browser session error while get_data_from_place after 10 attempts", exc_info=True, extra={"url": self.search_url})
                    return
                no_changes_count += 1
                if unique_place:
                    scraped_places.remove(unique_place)
                raise InvalidSessionIdException
            except Exception as e:
                self.logger.error(f"Error processing place: {str(e)}", exc_info=True, extra={"url": self.search_url})
                if no_changes_count >= 10:
                    return
                no_changes_count += 1
                time.sleep(0.5)
                if unique_place:
                    scraped_places.remove(unique_place)
                if str(e) != "Stuck while waiting for more reviews to load":
                    self.click_place_from_list(place_div)


def initialize_config():
    """Initialize configuration for the scraper."""
    global location_name, non_allowed_categories, places_details, scraped_places, scraped_urls
    
    logger.info("Starting Google Maps scraper")
    
    # Set default location
    location_name = "dubai"
    # location_name = "new-york-city"
    logger.info(f"Target location: {location_name}")
    
    # Initialize empty lists for storing results
    places_details = []
    scraped_places = []
    scraped_urls = []
    
    # Get geographical points for the location
    points = geo.get_16_z_points(location_name)
    
    # Get search parameters from input configuration
    tmp = helpers.get_inputs()[0]
    keyword = tmp["keyword"]
    non_allowed_categories = [_ for _ in tmp["avoid_categories"].split(";") if _ != ""]
    
    logger.info(f"Search keyword: {keyword}")
    logger.info(f"Non-allowed categories: {non_allowed_categories}")
    
    return {
        "location_name": location_name,
        "places_details": places_details,
        "scraped_places": scraped_places,
        "scraped_urls": scraped_urls,
        "points": points,
        "keyword": keyword,
        "non_allowed_categories": non_allowed_categories
    }

def generate_search_urls(config):
    """Generate Google Maps search URLs based on configuration."""
    points = config["points"]
    keyword = config["keyword"]
    
    # Add US region and English language parameters to avoid consent pages
    urls = [
        f"https://www.google.com/maps/search/{keyword.replace(' ', '+')}/@{point['lat']},{point['lon']},16z?gl=US&hl=en"
        for point in points
    ]
    # Override with specific test URLs if needed
    urls = [
        "https://www.google.com/maps/search/clinics/@25.2908331,55.4165928,16z/data=!3m1!4b1?gl=US&hl=en",
        "https://www.google.com/maps/search/clinics/@25.2908331,55.4165929,16z/data=!3m1!4b1?gl=US&hl=en",
        "https://www.google.com/maps/search/clinics/@25.1450395,55.2436334,15z/data=!3m1!4b1?gl=US&hl=en",
    ]
    shuffle(urls)
    logger.info(f"Generated {len(urls)} search URLs with US region")
    return urls

def initialize_drivers(num_drivers=2):
    """Initialize and return a queue of web drivers with proper delays."""
    drivers = Queue()
    
    # First, make sure no Chrome processes are running
    try:
        import psutil
        web_driver.kill_chrome_processes()
    except ImportError:
        pass
    
    for i in range(1, num_drivers + 1):
        try:
            logger.info(f"Initializing driver {i}...")
            driver = web_driver.get_driver(i)
            drivers.put((i, driver))
            # Add a significant delay between driver initializations
            time.sleep(10)
        except Exception as e:
            logger.error(f"Failed to initialize driver {i}: {str(e)}")
    
    actual_num_drivers = drivers.qsize()
    logger.info(f"Successfully initialized {actual_num_drivers} web drivers")
    
    return drivers, actual_num_drivers

def save_results(places_details, keyword):
    """Save the scraped data to JSON files."""
    formatted_datetime = datetime.now().strftime("_%Y-%m-%d_H%H_M%M_S%S")
    output_file_name = (
        keyword.replace(" ", "_") + f"_{len(places_details)}" + formatted_datetime
    )
    
    with open("test_2.json", "w") as f:
        json.dump(places_details, f, indent=2)
    with open(f"./outputs/{output_file_name}.json", "w") as f:
        json.dump(places_details, f, indent=2)
        
    logger.info(f"Generated output files: test_2.json and ./outputs/{output_file_name}.json")
    logger.info(f"Total places scraped: {len(places_details)}")
    
    # output_generator.output_generator(places_details, output_file_name, keyword)
    # logger.info("Finished generating all outputs")
    
    return output_file_name

def run_scraper_with_thread_pool(urls, drivers, max_drivers, selectors):
    """Run the scraper using a thread pool executor."""
    global places_details
    
    semaphore = Semaphore(max_drivers)
    executor_shutdown = False
    
    # Use a counter to track active tasks
    active_tasks = len(urls)
    
    def task_complete(future):
        nonlocal active_tasks
        driver_id, driver, url = futures[future]
        try:
            future.result()  # This will re-raise any exception that occurred during the task execution.
            # Task completed successfully, decrement the counter
            active_tasks -= 1
        except NoSuchWindowException:
            logger.error(f"Browser window error for driver {driver_id}", exc_info=True, extra={"url": url})
            if not executor_shutdown:  # only retry if the executor has not been shutdown
                # Attempt to close the current driver
                while True:
                    try:
                        web_driver.quit_driver_and_reap_children(driver)
                        # Recreate the driver and the GoogleMaps instance.
                        driver = web_driver.get_driver(driver_id)
                        # Modify the URL to use US region to avoid consent page
                        modified_url = url
                        if 'gl=' in modified_url:
                            modified_url = modified_url.replace('gl=SE', 'gl=US')
                        else:
                            modified_url += '&gl=US&hl=en'
                        google_maps_instance = GoogleMaps(modified_url, driver, selectors)
                        # Retry with the same URL.
                        retry_future = executor.submit(
                            google_maps_instance.scrap_data_from_search_url
                        )
                        futures[retry_future] = (driver_id, driver, url)
                        retry_future.add_done_callback(task_complete)
                        break
                    except Exception as ex:
                        logger.error(f"Error while restarting driver {driver_id}: {str(ex)}", exc_info=True, extra={"url": url})
                        time.sleep(1)
            else:
                logger.info("Executor has been shutdown, not retrying", extra={"url": url})
                # Make sure to release the semaphore and return the driver to the pool
                # even if we're not retrying
                try:
                    drivers.put((driver_id, driver))
                    semaphore.release()
                    # Task won't be retried, decrement the counter
                    active_tasks -= 1
                except Exception:
                    logger.error(f"Error returning driver {driver_id} to pool after shutdown", exc_info=True)
        else:
            # Only put the driver back and release the semaphore if the task succeeded.
            drivers.put((driver_id, driver))
            semaphore.release()

    with ThreadPoolExecutor(max_workers=max_drivers) as executor:
        # set executor_shutdown to False when the executor starts
        executor_shutdown = False
        futures = {}
        for url in urls:
            semaphore.acquire()  # decrease the semaphore, wait if it's 0
            driver_id, driver = drivers.get()  # get a driver from the pool
            google_maps_instance = GoogleMaps(url, driver, selectors)
            future = executor.submit(google_maps_instance.scrap_data_from_search_url)
            futures[future] = (driver_id, driver, url)
            future.add_done_callback(task_complete)
            logger.debug(f"Submitted scraping task for URL with driver {driver_id}")
        
        # Wait for all tasks to complete (including retries)
        while active_tasks > 0:
            logger.debug(f"Waiting for {active_tasks} active tasks to complete")
            time.sleep(1)  # Sleep to avoid busy waiting

    # Now it's safe to set executor_shutdown to True
    executor_shutdown = True
    logger.info("All scraping tasks completed")
    
    return places_details

if __name__ == "__main__":
    # Initialize configuration
    config = initialize_config()
    
    # Generate search URLs
    urls = generate_search_urls(config)
    
    # Load selectors
    selectors = get_selectors()
    logger.debug("Loaded selectors configuration")
    
    # Initialize drivers
    drivers, max_drivers = initialize_drivers(2)
    
    # Run the scraper
    places_details = run_scraper_with_thread_pool(
        urls, 
        drivers, 
        max_drivers, 
        selectors
    )
    
    # Save results
    output_file_name = save_results(places_details, config["keyword"])
