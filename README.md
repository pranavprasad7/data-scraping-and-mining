README: Business Scraper and WhatsApp Messenger
Overview
This Python project allows users to search for businesses using the Google Places API, extract their details, and send WhatsApp messages to the businesses. The program leverages Selenium for WhatsApp URL validation and pywhatkit for message sending.
 
Features
•	Search businesses using keywords like "restaurants" or "hotels".
•	Extract details such as name, address, phone number, rating, reviews, and website.
•	Validate WhatsApp numbers to ensure message delivery.
•	Automatically send WhatsApp messages to valid phone numbers.
•	Save extracted business data to a CSV file.
 
Prerequisites
Python Packages:
Install the required Python libraries:
pip install requests pandas selenium pywhatkit webdriver-manager
Files Needed:
1.	country_code.csv: Contains country names and their respective dialing codes.
o	Columns: Country, Code
2.	message.txt: Contains the message to be sent via WhatsApp.
API Key:
•	Get a Google Places API key from the Google Cloud Console.
•	You can watch this short video for reference: https://youtu.be/hsNlz7-abd0?si=tV7h7Ow2bTWtB63x
•	Or head to https://developers.google.com/maps

Google Chrome:
•	Install Google Chrome on your system.
•	Install the corresponding Chrome Driver for your browser version (Chrome Driver Download). Link below!
•	https://developer.chrome.com/docs/chromedriver/downloads
NOTE: Make sure chrome is your default browser and you are logged in on whatsapp web
 
Configuration
Modify Global Parameters:
Open the script and set the following:
1.	Location (LOCATION): pass the google maps location link for a place 
2.	Radius (RADIUS): Define the search radius in meters.
RADIUS = 1000 # 1 km radius
3.	Google API Key (API_KEY): Replace with your Google Places API key.
API_KEY = "Your-API-Key-Here"
4.	Profile Directory in Selenium: Update the user data directory and profile path in the code at line 121 and 122.
5.	options.add_argument("--user-data-dir=/Path/To/Your/Chrome/User/Data")
options.add_argument("--profile-directory=Your-Profile-Name")
 
Running the Program
1.	Start the Script: Run the script using Python:
python script_name.py
2.	Provide Input: When prompted, enter the search phrase (e.g., "restaurants", "hotels").
3.	Output Files:
o	Extracted business details are saved in a CSV file named <search_phrase>_businesses.csv.
4.	Message Sending:
o	The script will automatically send WhatsApp messages to valid phone numbers.
 
Troubleshooting
Common Issues:
1.	File Not Found: Ensure country_code.csv and message.txt exist in the same directory as the script.
2.	Invalid API Key: Verify your Google Places API key is correct and has sufficient quota.
3.	WhatsApp Validation Fails: Check that:
o	Chrome and Chrome Driver are compatible.
o	The Chrome profile is correctly set up in the Selenium options.
Logs:
•	Check business_scraper.log for detailed logs and error messages.

