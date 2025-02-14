import os
import requests
import pandas as pd
import time
import logging
import json
import pywhatkit as kit
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random
import itertools
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from requests_futures.sessions import FuturesSession

session = FuturesSession()

LOG_FILE = "log_script_initial_contact.log"

def setup_logging():
    """Initialize logging and prevent duplicate handlers."""
    logger = logging.getLogger("business_logger")  # Unique logger name

    if not logger.hasHandlers():  # Prevent duplicate handlers
        file_handler = logging.FileHandler(LOG_FILE)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.setLevel(logging.INFO)
    logger.info("Logging initialized.")
    return logger

# Load environment parameters and prerequisites
def load_env_parameters():
    try:
        with open("env_parameters.json", "r") as file:
            env_params = json.load(file)

        required_params = [
            "GOOGLE_MAPS_API_KEY",
            "GOOGLE_MAPS_LINK",
            "RADIUS",
            "MESSAGE_LIMIT",
            "search_phrase",
            "country_code_file",
            "message_file",
            "CHROME_DRIVER_PATH",
            "CHROME_USER_DATA_DIR",
            "CHROME_PROFILE_NAME"
        ]

        if not all(key in env_params for key in required_params):
            raise KeyError("Missing one or more required parameters in env_parameters.json.")

        return env_params
    except FileNotFoundError as e:
        logger.error(f"Error: {e}. Ensure env_parameters.json exists.")
        exit()
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {e}. Check the syntax of env_parameters.json.")
        exit()
    except KeyError as e:
        logger.error(f"Error: {e}. Ensure all required keys are in env_parameters.json.")
        exit()
def get_chrome_options(env_params):
    """Centralized function to create Chrome options with consistent configuration"""
    options = Options()
    options.add_argument(f"--user-data-dir={env_params['CHROME_USER_DATA_DIR']}")
    options.add_argument(f"--profile-directory={env_params['CHROME_PROFILE_NAME']}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return options
# Load prerequisites
def load_prerequisites(env_params):
    try:
        # Load country codes from CSV
        country_codes = pd.read_csv(env_params["country_code_file"])
        country_codes_dict = dict(zip(country_codes["Country"], country_codes["Code"]))

        # Load message template
        with open(env_params["message_file"], "r") as file:
            message = file.read().strip()

        return country_codes_dict, message
    except FileNotFoundError as e:
        logger.error(
            f"Error: {e}. Ensure files {env_params['country_code_file']} and {env_params['message_file']} exist.")
        exit()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        exit()


# Format phone numbers
def format_phone_number(phone_number, country_code):
    if not phone_number or phone_number == "No phone available":
        return "No phone available"
    phone_number = ''.join(e for e in phone_number if e.isdigit() or e == '+')
    if phone_number.startswith("+"):
        return phone_number
    if phone_number.startswith("0"):
        return f"+{country_code}{phone_number[1:]}"
    return f"+{country_code}{phone_number}"


def init_selenium_driver(env_params):
    options = get_chrome_options(env_params)
    service = Service(env_params['CHROME_DRIVER_PATH'])
    driver = webdriver.Chrome(service=service, options=options)
    return driver
def is_whatsapp_url_valid(phone_number):
    url = f"https://web.whatsapp.com/send?phone={phone_number}"
    # Get env_params from the outer scope
    env_params = load_env_parameters()  # Add this line
    driver = init_selenium_driver(env_params)  # Pass env_params
    try:
        driver.get(url)

        # Wait for up to 10 seconds for the page to load
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//body")))

        # Look for the specific error message indicating invalid number
        error_message_xpath = "//div[contains(text(), 'Phone number shared via url is invalid')]"

        try:
            # Wait for the error message to appear
            error_message = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, error_message_xpath))
            )
            if error_message.is_displayed():
                logging.warning(f"Invalid WhatsApp number: {phone_number}")
                return False
        except Exception:
            # If no error message is found, the number is valid
            return True
    except Exception as e:
        logging.error(f"Error validating WhatsApp URL for {phone_number}: {e}")
        return False
    finally:
        driver.quit()


def send_messages(phone_numbers, message, businesses, search_phrase, env_params):
    message_limit = env_params["MESSAGE_LIMIT"]
    successful_messages = []
    sent_count = 0  # Track valid messages sent

    logger.debug(f"Starting to send messages to {len(phone_numbers)} numbers")

    for phone_number in phone_numbers:
        if sent_count >= message_limit:
            break  # Stop once we reach the message limit

        try:
            logger.debug(f"Attempting to validate and send message to: {phone_number}")

            if is_whatsapp_url_valid(phone_number):  # Validate if it's a real WhatsApp number
                if send_immediate_message(phone_number, message):  # Send message
                    logger.info(f"Successfully sent message to {phone_number}")

                    business = next((b for b in businesses if b["Phone"] == phone_number), None)

                    if business:
                        if update_form_file(search_phrase, business):
                            successful_messages.append(business)
                            logger.debug(f"Added business to form file: {business['Name']}")
                        else:
                            logger.warning(f"Failed to update form file for business: {business['Name']}")

                    sent_count += 1  # Increment only for valid WhatsApp numbers
                else:
                    logger.warning(f"Failed to send message to {phone_number}")
            else:
                logger.warning(f"Invalid WhatsApp number: {phone_number}")

        except Exception as e:
            logger.error(f"Error processing number {phone_number}: {str(e)}")
            continue  # Move to the next phone number
        random_value = random.randint(45, 90)
        time.sleep(random_value)  # Wait 10 seconds between messages to avoid spam detection

    logger.info(f"Total successful messages sent: {len(successful_messages)}")
    print(f"Total successful messages sent: {len(successful_messages)}")
    return successful_messages

def send_immediate_message(phone_number, message):
    try:
        print(f"Sending message to: {phone_number}")
        kit.sendwhatmsg_instantly(
            phone_number,
            message,
            wait_time=30,  # Time in seconds for WhatsApp Web to load before sending
            tab_close=True
        )

        # Properly quit the browser on macOS using AppleScript
        os.system('osascript -e \'tell application "Google Chrome" to quit\'')
        return True
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return False
def verify_whatsapp_profile(env_params):
    try:
        # Load WhatsApp phone number - pass env_params to the function
        whatsapp_phone_number = get_whatsapp_phone_number(env_params)

        # Check if phone number was successfully retrieved
        if not whatsapp_phone_number:
            logger.error("Failed to retrieve WhatsApp phone number")
            return False

        # Load expected phone number from env_params
        expected_phone_number = env_params.get("WHATSAPP_PHONE_NUMBER")

        # Compare phone numbers
        if whatsapp_phone_number == expected_phone_number:
            logger.info("WhatsApp phone number verified successfully")
            return True
        else:
            logger.error(f"Phone number mismatch. Expected: {expected_phone_number}, Found: {whatsapp_phone_number}")
            print(f"Phone number mismatch. Expected: {expected_phone_number}, Found: {whatsapp_phone_number}")
            return False

    except Exception as e:
        logger.error(f"Error verifying WhatsApp phone number: {str(e)}")
        return False


def get_whatsapp_phone_number(env_params):
    options = get_chrome_options(env_params)
    service = Service(env_params['CHROME_DRIVER_PATH'])
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # Open WhatsApp Web
        driver.get("https://web.whatsapp.com")
        print("Please scan the QR code if required.")

        # Wait for WhatsApp Web to load (e.g., chat list becomes visible)
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Chat list']"))
        )

        # Locate and click the "New Chat" button
        new_chat_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='New chat']"))
        )
        new_chat_button.click()

        # Locate and click the "Message Yourself" contact
        message_yourself_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, '_ak8k') and text()='Message yourself']"))
        )
        message_yourself_button.click()

        # Locate and click the final "Message Yourself" button
        final_message_yourself_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH,
                                        "//div[@class='x78zum5 xdt5ytf x1iyjqo2 xl56j7k xeuugli' and @role='button']//span[text()='Message yourself']"))
        )
        final_message_yourself_button.click()

        # Wait explicitly for the phone number to load
        time.sleep(10)  # Increase wait time to ensure content is visible

        # Using the original XPath selector
        phone_number_element = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'x1rg5ohu x13faqbe _ao3e selectable-text copyable-text')]"))
        )

        phone_number = phone_number_element.text
        print("Phone number found:", phone_number)

        return phone_number if phone_number else "no number found"

    except Exception as e:
        print("An error occurred:", e)
        logger.error(f"Error in get_whatsapp_phone_number: {str(e)}")
        return None

    finally:
        try:
            driver.quit()
        except Exception as e:
            logger.error(f"Error closing driver: {str(e)}")
def update_form_file(search_phrase, business):
    """Update form file with a new successful business entry"""
    try:
        folder_name = search_phrase.lower().replace(" ", "_")
        form_file = os.path.join(os.getcwd(), folder_name, f"form_{folder_name}.csv")

        # If file doesn't exist, create it with headers
        if not os.path.exists(form_file):
            df = pd.DataFrame(
                columns=["Name", "Address", "Operation Hours", "Rating", "Reviews", "Phone", "Website", "Country"])
            df.to_csv(form_file, index=False)

        # Read existing data
        df = pd.read_csv(form_file)

        # Add new business as a new row
        new_df = pd.DataFrame([business])
        df = pd.concat([df, new_df], ignore_index=True)

        # Save updated dataframe
        df.to_csv(form_file, index=False)
        logger.info(f"Updated form file with business: {business['Name']}")
        return True
    except Exception as e:
        logger.error(f"Error updating form file: {str(e)}")
        return False


# Get full URL from a shortened Google Maps link
def get_full_url_from_short_link(short_link):
    response = requests.head(short_link, allow_redirects=True)
    return response.url


# Get coordinates from Google Maps link
def get_coordinates_from_google_maps_link(link, api_key):
    full_url = get_full_url_from_short_link(link)
    geocode_url = f'https://maps.googleapis.com/maps/api/geocode/json?address={full_url}&key={api_key}'

    response = requests.get(geocode_url)
    data = response.json()

    if response.status_code == 200 and data['status'] == 'OK':
        lat = data['results'][0]['geometry']['location']['lat']
        lng = data['results'][0]['geometry']['location']['lng']
        return lat, lng
    else:
        return None

def fetch_businesses_from_google(google_places_url, location, search_phrase, radius, api_key):
    all_results = []
    params = {'location': location, 'radius': radius, 'keyword': search_phrase, 'key': api_key}

    future = session.get(google_places_url, params=params)  # Async API request
    response = future.result()  # Get result when ready

    if response.status_code == 200:
        data = response.json()
        all_results.extend(data.get("results", []))

        next_page_token = data.get("next_page_token")
        while next_page_token:
            params["pagetoken"] = next_page_token
            time.sleep(1.2)  # Required delay for Google API
            future = session.get(google_places_url, params=params)  # Async call
            response = future.result()
            if response.status_code == 200:
                data = response.json()
                all_results.extend(data.get("results", []))
                next_page_token = data.get("next_page_token")
            else:
                break

    return {"results": all_results}

def fetch_place_details(place_id, api_key):
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {'place_id': place_id, 'key': api_key}
    response = requests.get(details_url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Error fetching place details for {place_id}: {response.status_code}")
        return None

def fetch_businesses_from_text_search(text_search_url, query, api_key):
    params = {'query': query, 'key': api_key}
    response = requests.get(text_search_url, params=params)
    if response.status_code == 200:
        return response.json().get("results", [])
    else:
        logger.error(f"Error fetching data from API: {response.status_code}")
        return []


def generate_grid(lat, lng, radius, grid_size=None):
    radius_deg = radius / 111320  # Convert meters to degrees

    if grid_size is None:
        grid_size = radius_deg * 0.75  # Increase step size (reduce overlap)

    lat_range = np.arange(lat - radius_deg, lat + radius_deg, grid_size)
    lng_range = np.arange(lng - radius_deg, lng + radius_deg, grid_size)

    return list(itertools.product(lat_range, lng_range))

def deduplicate_results(results):
    unique_results = {}
    for result in results:
        place_id = result["place_id"]
        if place_id not in unique_results:
            unique_results[place_id] = result
    return list(unique_results.values())

def filter_highly_rated_businesses(results, min_rating=4.0, min_reviews=100):
    return [
        business for business in results
        if business.get("rating", 0) >= min_rating and business.get("user_ratings_total", 0) >= min_reviews
    ]
def fetch_all_businesses(location, search_phrase, radius, api_key, grid_size=None, filter_function=False):
    google_places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    text_search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"

    lat, lng = location
    grid_coordinates = generate_grid(lat, lng, radius, grid_size)

    all_results = []
    print(f"Fetching businesses... Running {len(grid_coordinates)} parallel searches!")
    logger.info(f"Total searches to process: {len(grid_coordinates)}")

    with ProcessPoolExecutor(max_workers=20) as executor:  # Uses multiple CPU cores
        futures = [
            executor.submit(fetch_businesses_from_google, google_places_url, f"{grid[0]},{grid[1]}", search_phrase, radius, api_key)
            for grid in grid_coordinates
        ]

        text_search_future = executor.submit(fetch_businesses_from_text_search, text_search_url, f"{search_phrase} near {location}", api_key)

        for i, future in enumerate(futures):  # Track iteration progress
            try:
                results = future.result()
                all_results.extend(results["results"])
                logger.info(f"Processed {i+1}/{len(futures)} grid points")
            except Exception as e:
                logger.error(f"Error fetching businesses at {i+1}/{len(futures)}: {e}")

    # Get text search results (was running in parallel)
    text_results = text_search_future.result()
    all_results.extend(text_results)

    logger.info("Finished fetching all businesses.")

    # Apply filtering if filter_function is True
    if filter_function:
        all_results = filter_highly_rated_businesses(all_results, min_rating=4.5, min_reviews=200)

    return {"results": deduplicate_results(all_results)}

def extract_business_details(places_data, api_key, country_codes_dict):
    businesses = []
    print(f"Starting to extract details from {len(places_data.get('results', []))} places")

    for result in places_data.get("results", []):
        try:
            name = result.get("name", "No name available")
            address = result.get("vicinity", "No address available")
            rating = result.get("rating", "No rating")
            reviews = result.get("user_ratings_total", "No reviews")
            place_id = result.get("place_id")

            print(f"Processing business: {name}")

            # Fetch additional details
            details_data = fetch_place_details(place_id, api_key)
            if details_data and "result" in details_data:
                business_details = details_data["result"]

                phone = business_details.get("formatted_phone_number", "No phone available")
                website = business_details.get("website", "No website available")
                country_info = business_details.get("address_components", [])
                country = next((c["long_name"] for c in country_info if "country" in c["types"]), None)

                operation_hours = business_details.get("opening_hours", {}).get("weekday_text",
                                                                                "No operation hours available")
                if isinstance(operation_hours, list):
                    operation_hours = "; ".join(operation_hours)

                if country and country in country_codes_dict:
                    country_code = country_codes_dict.get(country)
                else:
                    country_code = "Unknown"

                phone_number = format_phone_number(phone, country_code)

                business_data = {
                    "Name": name,
                    "Address": address,
                    "Operation Hours": operation_hours,
                    "Rating": rating,
                    "Reviews": reviews,
                    "Phone": phone_number,
                    "Website": website,
                    "Country": country if country else "No country found"
                }

                businesses.append(business_data)
                print(f"Added business: {name} with phone: {phone_number}")

        except Exception as e:
            print(f"Error processing business {name}: {str(e)}")
            logger.error(f"Error processing business {name}: {str(e)}")
            continue

    print(f"Successfully processed {len(businesses)} businesses")
    return businesses

# Create folder based on the request
def create_folder_and_save_files(search_phrase, businesses):
    """Create initial folder and requests file without sorting (already sorted in main)."""
    try:
        print("\n=== Starting Folder Creation ===")
        print(f"Number of businesses to save: {len(businesses)}")

        # Format the folder name
        folder_name = search_phrase.lower().replace(" ", "_")
        current_dir = os.getcwd()
        folder_path = os.path.join(current_dir, folder_name)

        print(f"Creating folder at: {folder_path}")

        # Ensure the folder is created
        os.makedirs(folder_path, exist_ok=True)

        # Create the requests file
        requests_file = os.path.join(folder_path, f"requests_{folder_name}.csv")

        # Save businesses to requests file (already sorted in main)
        if businesses:
            df_requests = pd.DataFrame(businesses)
            df_requests.to_csv(requests_file, index=False)
            print(f"Saved requests file with {len(businesses)} businesses")

        # Create empty form file
        form_file = os.path.join(folder_path, f"form_{folder_name}.csv")
        df_form = pd.DataFrame(
            columns=["Name", "Address", "Operation Hours", "Rating", "Reviews", "Phone", "Website", "Country",
                     "Options & Packages", "Accept Card"])
        df_form.to_csv(form_file, index=False)
        print(f"Created empty form file")

        print("=== Folder Creation Completed ===\n")
        return True

    except Exception as e:
        print(f"Error in create_folder_and_save_files: {str(e)}")
        logger.error(f"Error in create_folder_and_save_files: {str(e)}")
        return False

# Generate or revert the prep_message file
def generate_message_file(env_params, reverse_message=False):
    try:
        if reverse_message:
            # Write the static message to the file
            reverted_message = "Hi, I want to schedule a {search_phrase} appointment on {APPOINTMENT_DATE}, preferably {APPOINTMENT_TIME}. Let me know if it’s possible and the cost. Thank you!"

            with open("prep_message.txt", "w") as file:
                file.write(reverted_message)
            logger.info(f"prep_message.txt has been reverted to: {reverted_message}")
        else:
            # Generate the file by replacing placeholders
            with open("prep_message.txt", "r") as file:
                message_template = file.read().strip()

            # Replace placeholders with values from env_params
            for key, value in env_params.items():
                placeholder = f"{{{key}}}"  # Placeholder format {KEY}
                if placeholder in message_template:
                    message_template = message_template.replace(placeholder, str(value))

            with open("prep_message.txt", "w") as file:
                file.write(message_template)
            logger.info("prep_message.txt has been updated with the provided parameters.")
    except FileNotFoundError as e:
        logger.error(f"Error: {e}. Ensure prep_message.txt exists.")
        exit()
    except Exception as e:
        logger.error(f"Unexpected error while updating prep_message.txt: {e}")
        exit()

def calculate_grid_size(radius):
    radius_km = radius / 1000  # Convert meters to kilometers
    if radius_km <= 5:
        return 0.005  # ~0.55 km per step
    elif radius_km <= 10:
        return 0.0075  # ~0.83 km per step
    elif radius_km <= 15:
        return 0.01  # ~1.1 km per step
    elif radius_km <= 20:
        return 0.0125  # ~1.4 km per step
    elif radius_km <= 25:
        return 0.015  # ~1.7 km per step
    elif radius_km <= 30:
        return 0.017  # ~1.9 km per step
    elif radius_km <= 35:
        return 0.02  # ~2.2 km per step
    elif radius_km <= 40:
        return 0.022  # ~2.4 km per step
    elif radius_km <= 45:
        return 0.025  # ~2.8 km per step
    elif radius_km <= 50:
        return 0.027  # ~3 km per step
    elif radius_km <= 55:
        return 0.03  # ~3.3 km per step
    elif radius_km <= 60:
        return 0.035  # ~3.8 km per step
    elif radius_km <= 65:
        return 0.04  # ~4.5 km per step
    elif radius_km <= 70:
        return 0.045  # ~5 km per step
    elif radius_km <= 75:
        return 0.05  # ~5.5 km per step
    elif radius_km <= 80:
        return 0.055  # ~6 km per step
    elif radius_km <= 85:
        return 0.06  # ~6.6 km per step
    elif radius_km <= 90:
        return 0.065  # ~7.2 km per step
    elif radius_km <= 95:
        return 0.07  # ~7.8 km per step
    else:  # 100 km and above
        return 0.075  # ~8.3 km per step


def main():
    try:
        print("\n=== Starting Script Execution ===")
        logger.info("=== Starting Script Execution ===")

        env_params = load_env_parameters()
        generate_message_file(env_params, reverse_message=True)
        generate_message_file(env_params, reverse_message=False)
        country_codes_dict, message = load_prerequisites(env_params)
        search_phrase = env_params["search_phrase"]
        print(f"Processing search phrase: {search_phrase}")

        # Retrieve coordinates
        coordinates = get_coordinates_from_google_maps_link(env_params["GOOGLE_MAPS_LINK"],
                                                            env_params["GOOGLE_MAPS_API_KEY"])

        if coordinates:
            location = coordinates  # (lat, lng)
            print(f"Retrieved location: {location}")

            # Dynamically calculate grid size based on the radius
            radius = env_params["RADIUS"]
            grid_size = calculate_grid_size(radius)
            print(f"Calculated grid size: {grid_size} for radius: {radius}")

            # Fetch businesses with dynamic grid size
            places_data = fetch_all_businesses(location, search_phrase, radius, env_params["GOOGLE_MAPS_API_KEY"],
                                               grid_size,filter_function=False)
            businesses = []

            if places_data:
                businesses = extract_business_details(places_data, env_params["GOOGLE_MAPS_API_KEY"],
                                                      country_codes_dict)
                print(f"Extracted details for {len(businesses)} businesses")

                if businesses:
                    # Sort businesses before passing them to send_messages
                    sorted_businesses = sorted(
                        businesses,
                        key=lambda x: (x.get("Reviews", 0), x.get("Rating", 0)),
                        reverse=True  # Sort in descending order
                    )

                    folder_created = create_folder_and_save_files(search_phrase, sorted_businesses)

                    if folder_created:
                        print("Successfully created folder and files")

                        try:
                            phone_numbers = [business["Phone"] for business in sorted_businesses if
                                             business["Phone"] != "No phone available"]

                            if not verify_whatsapp_profile(env_params):
                                print("WhatsApp phone number verification failed. Stopping execution.")
                                logger.error("WhatsApp phone number verification failed.")
                                return

                            # Pass the sorted list to send_messages
                            successful_businesses = send_messages(phone_numbers, message, sorted_businesses,
                                                                  search_phrase, env_params)
                        except Exception as e:
                            print(f"Error in message sending: {str(e)}")
                            logger.error(f"Error in message sending: {str(e)}")

                    else:
                        print("Failed to create folder and files")
                else:
                    print("No businesses found to process")
            else:
                print("Failed to fetch places data")
        else:
            print("Failed to get coordinates")

        print("=== Script Execution Completed ===\n")
        logger.info("=== Script Execution Completed ===")

    except Exception as e:
        print(f"Main execution error: {str(e)}")
        logger.error(f"Main execution error: {str(e)}")


# ✅ Properly delete log file before execution
if __name__ == "__main__":
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
        print(f"Existing log file {LOG_FILE} deleted.")

    # ✅ Initialize logging before calling main()
    logger = setup_logging()

    # ✅ Run the main function
    main()