# WhatsApp Business Automation Tool

This tool automates the process of finding businesses in a specific geographic area and sending them WhatsApp messages. It uses Google Places API to find businesses and Selenium WebDriver to automate WhatsApp Web interactions.

## Features

- Search for businesses within a specified radius using Google Places API
- Extract detailed business information including contact details
- Automatically send WhatsApp messages to businesses
- Create organized folders for each search query
- Track successful message deliveries
- Comprehensive logging system

## Prerequisites

- Python 3.6 or higher
- Chrome Browser
- ChromeDriver (matching your Chrome version)
- Active WhatsApp Web account
- Google Maps API key

### Required Python Packages

```
selenium
pandas
requests
pywhatkit
webdriver_manager
```

## Setup

1. Clone the repository to your local machine
2. Install required packages:
   ```bash
   pip install selenium pandas requests pywhatkit webdriver_manager
   ```
3. Create the following configuration files:

### env_parameters.json
```json
{
    "GOOGLE_MAPS_API_KEY": "your_api_key",
    "GOOGLE_MAPS_LINK": "google_maps_link",
    "RADIUS": "search_radius_in_meters",
    "MESSAGE_LIMIT": "max_messages_to_send",
    "search_phrase": "business_type_to_search",
    "country_code_file": "path_to_country_codes.csv",
    "message_file": "path_to_message_template.txt",
    "CHROME_DRIVER_PATH": "path_to_chromedriver",
    "CHROME_USER_DATA_DIR": "path_to_chrome_user_data",
    "CHROME_PROFILE_NAME": "chrome_profile_name",
    "WHATSAPP_PHONE_NUMBER": "your_whatsapp_number",
    "APPOINTMENT_DATE": "desired_appointment_date",
    "APPOINTMENT_TIME": "desired_appointment_time"
}
```

### prep_message.txt
Create this file with your message template. You can use placeholders like {search_phrase}, {APPOINTMENT_DATE}, and {APPOINTMENT_TIME}.

### country_codes.csv
Create this file with columns for "Country" and "Code" containing country names and their respective phone country codes.

## Usage

1. Ensure all configuration files are properly set up
2. Run the script:
   ```bash
   python script_name.py
   ```

The script will:
1. Load all necessary configuration
2. Search for businesses based on your criteria
3. Create a folder structure for the search results
4. Send WhatsApp messages to found businesses
5. Track successful messages
6. Generate detailed logs

## Folder Structure

For each search, the script creates:
```
search_phrase/
├── requests_search_phrase.csv  # All found businesses
└── form_search_phrase.csv      # Successfully contacted businesses
```

## Logging

The script creates a detailed log file: `log_script_initial_contact.log`
- Tracks all operations
- Records errors and successes
- Helps in troubleshooting

## Safety Features

- WhatsApp number verification before sending messages
- Rate limiting for message sending
- Phone number format validation
- Error handling and logging
- Message limit controls

## Important Notes

1. Ensure your WhatsApp Web is logged in before running the script
2. Keep your Google Maps API key secure
3. Respect rate limits for both Google Places API and WhatsApp messaging
4. Monitor the log file for any issues
5. Make sure Chrome profile is properly configured

## Troubleshooting

If you encounter issues:
1. Check the log file for specific error messages
2. Verify all configuration files exist and are properly formatted
3. Ensure Chrome and ChromeDriver versions match
4. Confirm WhatsApp Web is properly logged in
5. Verify Google Maps API key is valid and has required permissions

## Legal Considerations

- Ensure compliance with WhatsApp's terms of service
- Follow local regulations regarding automated messaging
- Respect business contact preferences
- Handle business information according to privacy laws

## Support

For issues or questions:
1. Check the log file for error details
2. Verify configuration settings
3. Ensure all prerequisites are properly installed
4. Check Chrome and ChromeDriver compatibility
