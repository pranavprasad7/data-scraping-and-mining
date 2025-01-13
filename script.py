import requests
import pandas as pd
import time
import logging
import pywhatkit as kit
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta

# Global Parameters
LOCATION = "25.0657,55.17128"  # Coordinates for the search center (e.g., New Delhi, India)
RADIUS = 1000  # in meters
API_KEY = "YOUR_API_KEY"  # Replace with your API key
COUNTRY_CODE_FILE = "country_code.csv"
MESSAGE_FILE = "message.txt"
MESSAGE_LIMIT = 10  # Number of messages to send
search_phrase = "restaurants"  # Default search phrase

# Set up logging
logging.basicConfig(filename="business_scraper.log", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

# Load prerequisites
def load_prerequisites():
    try:
        country_codes = pd.read_csv(COUNTRY_CODE_FILE)
        country_codes_dict = dict(zip(country_codes["Country"], country_codes["Code"]))
        with open(MESSAGE_FILE, "r") as file:
            message = file.read().strip()
        return country_codes_dict, message
    except FileNotFoundError as e:
        logger.error(f"Error: {e}")
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

# Fetch businesses from Google Places API
def fetch_businesses_from_google(google_places_url, location, search_phrase, radius, api_key):
    params = {
        'location': location,
        'radius': radius,
        'keyword': search_phrase,
        'key': api_key
    }
    response = requests.get(google_places_url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Error fetching data from Google Places API: {response.status_code}")
        return None

# Fetch place details
def fetch_place_details(place_id, api_key):
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {'place_id': place_id, 'key': api_key}
    response = requests.get(details_url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Error fetching place details for {place_id}: {response.status_code}")
        return None

# Extract and process business details
def extract_business_details(places_data, api_key, country_codes_dict):
    businesses = []
    for result in places_data.get("results", []):
        name = result.get("name", "No name available")
        address = result.get("vicinity", "No address available")
        rating = result.get("rating", "No rating")
        reviews = result.get("user_ratings_total", "No reviews")
        place_id = result.get("place_id")
        
        details_data = fetch_place_details(place_id, api_key)
        if details_data and "result" in details_data:
            business_details = details_data["result"]
            phone = business_details.get("formatted_phone_number", "No phone available")
            website = business_details.get("website", "No website available")
            country_info = business_details.get("address_components", [])
            country = next((c["long_name"] for c in country_info if "country" in c["types"]), None)

            if country and country in country_codes_dict:
                country_code = country_codes_dict.get(country)
            else:
                country_code = "Unknown"
            
            phone_number = format_phone_number(phone, country_code)
            
            businesses.append({
                "Name": name,
                "Address": address,
                "Rating": rating,
                "Reviews": reviews,
                "Phone": phone_number,
                "Website": website,
                "Country": country if country else "No country found"
            })
    return businesses

# Initialize Selenium driver
def init_selenium_driver():
    options = Options()
    # Add the correct user data directory and profile path
    options.add_argument("--user-data-dir=/Users/pranav/Library/Application Support/Google/Chrome")
    options.add_argument("--profile-directory=Profile 3")  # Use the "Profile 3" folder for the profile
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def is_whatsapp_url_valid(phone_number):
    url = f"https://web.whatsapp.com/send?phone={phone_number}"
    driver = init_selenium_driver()
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

# Send WhatsApp messages
def send_messages(phone_numbers, message):
    for phone_number in phone_numbers[:MESSAGE_LIMIT]:
        try:
            if is_whatsapp_url_valid(phone_number):
                send_immediate_message(phone_number, message)
                logging.info(f"Sent message to {phone_number}")
            else:
                logging.warning(f"Skipped sending message to invalid number: {phone_number}")
        except Exception as e:
            logging.error(f"Error sending message to {phone_number}: {e}")

# Send message immediately
def send_immediate_message(phone_number, message):
    current_time = datetime.now()
    send_time = current_time + timedelta(minutes=1)
    kit.sendwhatmsg(phone_number, message, send_time.hour, send_time.minute)

# Main function
def main():
    global search_phrase
    search_phrase = input("Enter the search phrase (e.g., restaurants, hotels): ").strip()
    country_codes_dict, message = load_prerequisites()
    google_places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    places_data = fetch_businesses_from_google(google_places_url, LOCATION, search_phrase, RADIUS, API_KEY)

    if places_data:
        businesses = extract_business_details(places_data, API_KEY, country_codes_dict)
        if businesses:
            df = pd.DataFrame(businesses)
            df.to_csv(f"{search_phrase}_businesses.csv", index=False)
            logger.info(f"Business data saved to {search_phrase}_businesses.csv")
            phone_numbers = [business["Phone"] for business in businesses if business["Phone"] != "No phone available"]
            send_messages(phone_numbers, message)
        else:
            logger.info("No businesses found.")
    else:
        logger.error("Failed to fetch businesses from Google API.")

if __name__ == "__main__":
    main()
