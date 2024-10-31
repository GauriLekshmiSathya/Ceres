import requests

# API keys
API_KEY_RAINFALL = "09e6ab1bbf04416abbd114317242110"  # World Weather Online API key for rainfall
API_KEY_GEOCODE = "c5e084eaa0454325b524ba254e54bba2"  # OpenCage Geocoding API key for lat/lon
API_KEY_TEMP = "35bd70e9dc2fb17c9c68d0014f10540b"  # OpenWeather API key for temperature

# Pincode to use for both rainfall and temperature
pincode = input("Enter pincode: ")

# Function to get latitude and longitude using OpenCage API
def get_lat_lon(pincode):
    url = f"https://api.opencagedata.com/geocode/v1/json?q={pincode}&key={API_KEY_GEOCODE}"
    result = requests.get(url)
    result_data = result.json()
    if 'results' in result_data and len(result_data['results']) > 0:
        geometry = result_data['results'][0]['geometry']
        return geometry['lat'], geometry['lng']
    else:
        print(f"Error: Unable to fetch latitude and longitude for pincode {pincode}.")
        return None, None

# Get latitude and longitude for the given pincode
latitude, longitude = get_lat_lon(pincode)

# Check if we got valid latitude and longitude
if latitude and longitude:
    
    # Get temperature data using OpenWeather API
    urlTemp = f"https://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid={API_KEY_TEMP}&units=metric"
    response_temp = requests.get(urlTemp)
    weather_data = response_temp.json()

    if 'main' in weather_data and 'temp' in weather_data['main']:
        temp = weather_data['main']['temp']
        print(f"Temperature at pincode {pincode} is {temp}°C")
    else:
        print("Error: Unable to fetch temperature data.")
    
    # Dates for rainfall data (from June 1, 2024, to September 1, 2024)
    start_date = "2024-08-01"
    end_date = "2024-10-01"

    # URL for World Weather Online historical rainfall data
    url_rainfall = f"http://api.worldweatheronline.com/premium/v1/past-weather.ashx?key={API_KEY_RAINFALL}&q={latitude},{longitude}&format=json&date={start_date}&enddate={end_date}&tp=24"

    # Request for rainfall data
    response_rainfall = requests.get(url_rainfall)
    data_rainfall = response_rainfall.json()

    # Calculate total rainfall and average rainfall over 3 months
    total_rainfall = 0
    num_days = 0

    if 'weather' in data_rainfall['data']:
        for weather in data_rainfall['data']['weather']:
            # Sum up daily rainfall
            if 'hourly' in weather:
                daily_rainfall = sum(float(hourly_data.get('precipMM', 0)) for hourly_data in weather['hourly'])
                total_rainfall += daily_rainfall
                num_days += 1
    
        # Calculate the number of months (June, July, August)
        num_months = 2
        if num_days > 0:
            average_annual_rainfall = total_rainfall / num_months
            print(f"Average Rainfall over {num_months} months: {average_annual_rainfall:.2f} mm")
        else:
            print("No rainfall data available.")
    else:
        print("Error: Unable to fetch rainfall data.")
else:
    print("Error: Could not retrieve valid latitude and longitude.")