from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import requests
from config.db_config import get_db_connection
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flashing messages

# API keys
import requests
import mysql.connector

# API Keys
API_KEY_RAINFALL = "09e6ab1bbf04416abbd114317242110"  # World Weather Online API key
API_KEY_GEOCODE = "c5e084eaa0454325b524ba254e54bba2"  # OpenCage Geocoding API key

# Database connection function
def get_db_connection():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Cosine1012',
        database='agrihelpers'  # Replace with your actual database name
    )
    return conn

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

# Function to get temperature and rainfall data
def get_weather_data(pincode, start_date="2024-08-01", end_date="2024-10-01"):
    latitude, longitude = get_lat_lon(pincode)

    if latitude and longitude:
        # Get temperature and rainfall data using World Weather Online API
        url = f"http://api.worldweatheronline.com/premium/v1/past-weather.ashx?key={API_KEY_RAINFALL}&q={latitude},{longitude}&format=json&date={start_date}&enddate={end_date}&tp=24"
        
        response = requests.get(url)
        weather_data = response.json()
        
        # Check if data retrieval was successful
        if response.status_code != 200 or 'data' not in weather_data:
            print("Error: Unable to retrieve weather data.")
            return None, None

        # Extract temperature (average of daily max temperatures)
        temp = None
        if 'weather' in weather_data['data']:
            max_temps = [int(day.get('maxtempC', 0)) for day in weather_data['data']['weather'] if 'maxtempC' in day]
            temp = sum(max_temps) / len(max_temps) if max_temps else None

        # Calculate rainfall
        total_rainfall = 0
        num_days = 0
        for day in weather_data['data']['weather']:
            if 'hourly' in day:
                daily_rainfall = sum(float(hourly.get('precipMM', 0)) for hourly in day['hourly'])
                total_rainfall += daily_rainfall
                num_days += 1

        # Calculate monthly average rainfall
        num_months = 2  # Assuming start_date to end_date spans 2 months
        average_rainfall = (total_rainfall / num_months) if num_days > 0 else None

        return temp, average_rainfall
    else:
        return None, None

# Home page route
@app.route('/')
def index():
    return render_template('index.html')

# Route for the registration page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']

        # Insert customer data into the database
        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO Customers (Cust_Name, Phone_No, Email)
            VALUES (%s, %s, %s)
        """, (name, phone, email))

        db.commit()

        # Get the newly assigned CustomerID
        customer_id = cursor.lastrowid
        db.close()

        return render_template('registration_success.html', customer_id=customer_id)

    return render_template('registration.html')


# Customer login page
@app.route('/customer_login')
def customer_login():
    return render_template('customer_login.html')

# Customer login route
@app.route('/customer_login', methods=['GET', 'POST'])
def customer_login_route():
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        phone = request.form['phone']

        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT CropID FROM sites WHERE CustomerID = %s ", (customer_id,))
        result = cursor.fetchone();
        if result:
            CropID = result[0]
            cursor.close()
            db.close()
            return redirect(url_for('retrieve', customer_id=customer_id , crop_id=CropID) )
            
            
        else:
        
            # Validate the credentials
            db = get_db_connection()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM Customers WHERE Cust_ID = %s AND Phone_No = %s", (customer_id, phone))
            customer = cursor.fetchone()
            db.close()

            if customer:
                # Successful login: redirect to address input page
                return redirect(f'/address_input/{customer_id}')  # Redirect to address input with customer ID
            else:
                # Handle login failure (e.g., show an error message)
                return render_template('customer_login.html', error="Invalid Customer ID or Phone Number.")

    return render_template('customer_login.html')

# Address input page route
@app.route('/address_input/<int:customer_id>', methods=['GET'])
def address_input(customer_id):
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("SELECT Soil_ID, Soil_Name FROM Soil")
    soils = cursor.fetchall()
    db.close()
    return render_template('address_input.html', soils=soils, customer_id=customer_id)

# Route to save site information
@app.route('/save_site_info', methods=['POST'])
def save_site_info():
    area = request.form['area']
    pincode = request.form['pincode']
    land_size = request.form['land_size']
    soil_id = request.form['soil_id']
    customer_id = request.form['customer_id']

    # Get temperature and rainfall data based on the pincode
    temperature, avg_rainfall = get_weather_data(pincode)

    # Insert site information into the database
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO Sites (Area, Pincode, Land_size, Soil_ID, Temperature, Rainfall, CustomerID)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (area, pincode, land_size, soil_id, temperature, avg_rainfall, customer_id))
    db.commit()
    db.close()

    return redirect(url_for('suitable_crops',customer_id=customer_id))  # Redirect to crops page after submission




@app.route('/suitable_crops', methods=['GET'])
def suitable_crops():
    # Assuming CustomerID is passed as a query parameter
    customer_id = request.args.get('customer_id')

    # Step 1: Get Soil_ID, Temperature, and Rainfall from the Sites table
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT Soil_ID, Temperature, Rainfall 
        FROM Sites 
        WHERE CustomerID = %s
    """, (customer_id,))
    
    site_data = cursor.fetchone()
    
    if not site_data:
        return "No site data found for the given customer ID.", 404

    soil_id = site_data['Soil_ID']
    temperature = site_data['Temperature']
    rainfall = site_data['Rainfall']

    # Step 2: Retrieve Crop_IDs and Crop_Name associated with the Soil_ID from the Crop_Soil table
    cursor.execute("""
        SELECT cs.Crop_ID, c.Crop_Name, c.Min_Temperature, c.Max_Temperature, c.Min_Rain, c.Max_Rain
        FROM Crop_Soil cs
        JOIN Crops c ON cs.Crop_ID = c.Crop_ID
        WHERE cs.Soil_ID = %s
    """, (soil_id,))
    
    available_crops = cursor.fetchall()

    # Step 3: Filter crops based on temperature and rainfall conditions
    suitable_crops = []
    for crop in available_crops:
        if (crop['Min_Temperature'] <= temperature <= crop['Max_Temperature'] and
                crop['Min_Rain'] <= rainfall <= crop['Max_Rain']):
            suitable_crops.append(crop)

    cursor.close()
    db.close()

    # Step 4: Render the results in the HTML template
    return render_template('crops.html', crops=suitable_crops, customer_id=customer_id)



# Route to update crop information in the Sites table
@app.route('/update_crop', methods=['POST'])
def update_crop():
    # Get the posted form data
    crop_id = request.form['crop_id']  # The Crop ID entered by the user
    customer_id = request.form['customer_id']  # Customer ID from the form (optional)
    
    # Step 1: Get the site record that needs to be updated
    db = get_db_connection()
    cursor = db.cursor()

    # Update the CropID for the specific customer
    cursor.execute("""
        UPDATE Sites 
        SET CropID = %s 
        WHERE CustomerID = %s
    """, (crop_id, customer_id))
    
    # Commit the changes to the database
    db.commit()

    cursor.close()
    db.close()

    return redirect(url_for('suitable_crops', customer_id=customer_id))  # Redirect back to suitable crops

# Manager login page route
@app.route('/employee_login', methods=['GET', 'POST'])
def employee_login():
    if request.method == 'POST':
        manager_id = request.form['manager_id']
        phone_number = request.form['phone_number']  # Password is the phone number

        # Validate the manager credentials
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM Managers WHERE Manager_ID = %s AND Phone_No = %s", (manager_id, phone_number))
        manager = cursor.fetchone()
        db.close()
        # print(manager[5]);
        if manager:
            if manager[5]:
                # Successful login - you can redirect to a manager-specific page
                return redirect(url_for('manager_homepage',Manager_ID = manager_id))  # Change to the actual page for managers
            else:
                return redirect(url_for('manager_homepage_2'))
            
            
        else:
            # Handle login failure (e.g., show an error message)
            return render_template('employee_login.html', error="Invalid Manager ID or Phone Number.")

    return render_template('employee_login.html')


@app.route('/manager_homepage_2', methods=['GET', 'POST'])
def manager_homepage_2():
    if request.method == 'POST':
        return render_template('index.html')
    return render_template('employee_homepage_2.html')

@app.route('/manager_homepage', methods=['GET', 'POST'])
def manager_homepage():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        farmer_id = request.form.get('farmer_id')
        manager_id = request.form.get('manager_id')
        customer_id = request.form.get('customer_id')
        if customer_id:
            cursor.execute("UPDATE farmers SET F_availability = 0, CustomerID = %s WHERE Farmer_ID = %s", (customer_id, farmer_id))
            db.commit()
        
            cursor.close()
            db.close()
            return redirect(url_for('manager_homepage', Manager_ID=manager_id))  # Redirect to avoid form resubmission
        else:
            cursor.execute("UPDATE farmers SET F_availability = 1 , CustomerID = NULL WHERE Farmer_ID = %s",(farmer_id,))
            db.commit()

            cursor.close()
            return redirect(url_for('manager_homepage', Manager_ID=manager_id)) 
        
        

    elif request.method == 'GET' and request.method!='POST':
        manager_id =request.args.get('Manager_ID')
        # manager_id = int(manager_id)

        cursor.execute("SELECT CustomerID FROM managers WHERE Manager_ID = %s" , (manager_id,))
        manager = cursor.fetchone()
        customer_id = manager['CustomerID']

        cursor.execute("SELECT * FROM customers WHERE Cust_ID  = %s",(customer_id,))
        customer = cursor.fetchone()
        customer_name = customer['Cust_Name']
        customer_number = customer['Phone_No']

        cursor.execute("SELECT Area,Land_size,CropID FROM sites WHERE CustomerID  = %s",(customer_id,))
        info = cursor.fetchone()
        customer_area = info['Area']
        customer_land_size = info['Land_size']
        customer_crop_id = info['CropID']

        cursor.execute("SELECT Crop_Name FROM crops WHERE Crop_ID  = %s",(customer_crop_id,))
        crop_info = cursor.fetchone()
        customer_crop = crop_info['Crop_Name']

        customer_data = {
                'id':customer_id,
                'name': customer_name,
                'crop':customer_crop,
                'area': customer_area,
                'land_size': customer_land_size,
                'number': customer_number,
                'manager_id':manager_id
            }
        
        cursor.execute("SELECT Farmer_ID,Farmer_Name,Phone_No FROM farmers WHERE Specialization = %s AND F_availability = 1",(customer_crop_id,))
        farmer_info = cursor.fetchall();
        available_farmers=[]
        for farmer in farmer_info:
            available_farmers.append(farmer)

        
        cursor.execute("SELECT Farmer_ID,Farmer_Name,Phone_No FROM farmers WHERE Specialization = %s AND CustomerID = %s",(customer_crop_id,customer_id))
        farmer_info = cursor.fetchall();
        allocated_farmers=[]
        for farmer in farmer_info:
            allocated_farmers.append(farmer)

        cursor.close()
        db.close()
    return render_template('employee_homepage.html',customer = customer_data,available_farmers=available_farmers, allocated_farmers = allocated_farmers )




@app.route('/assign', methods=['POST'])
def assign():
    customer_id = request.form.get('customer_id')
    
    crop_id = request.form.get('crop_id')

    
    
    db = get_db_connection()
    cursor = db.cursor()
    query="Select land_size from sites where CustomerID=%s"
    cursor.execute(query,(customer_id,))
    result = cursor.fetchone()
    land_size = result[0]
    cursor.close()
    db.close()

    num_farmers = 2 * land_size
    
    # Retrieve an available manager and mark them unavailable
    manager = get_available_manager()
    if manager:
        update_availability(manager['Manager_ID'], available=0, entity='manager')
    
    # Retrieve and update the required number of available farmers specialized in the selected crop
    farmers = get_crop_specialized_farmers(crop_id, num_farmers)
    for farmer in farmers:
        update_availability(farmer['Farmer_ID'], available=0, entity='farmer')
    
    return render_template('customer_homepage.html', manager=manager, num_farmers=num_farmers, farmers=farmers)

#Helper function to fetch crops based on soil type
def get_crops_for_soil(soil_type):
    connection = get_db_connection()
    cursor = connection.cursor()
    query = """
    SELECT crop_name FROM Crops 
    WHERE soil_type_id = (
        SELECT soil_id FROM Soil WHERE soil_name = %s
    )
    """
    cursor.execute(query, (soil_type,))
    crops = [row[0] for row in cursor.fetchall()]
    cursor.close()
    connection.close()
    return crops

# Function to fetch an available manager
def get_available_manager():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    query = "SELECT * FROM Managers WHERE M_availability = 1 LIMIT 1"
    cursor.execute(query)
    manager = cursor.fetchone()
    cursor.close()
    connection.close()
    return manager

# Function to update availability status of an entity
def update_availability(entity_id, available, entity):
    connection = get_db_connection()
    cursor = connection.cursor()
    if entity == 'manager':
        query = "UPDATE Managers SET M_availability = %s WHERE Manager_ID = %s"
    elif entity == 'farmer':
        query = "UPDATE Farmers SET F_availability = %s WHERE Farmer_ID = %s"
    cursor.execute(query, (available, entity_id))
    connection.commit()
    cursor.close()
    connection.close()

# Function to fetch the required number of farmers with specialization in the selected crop
def get_crop_specialized_farmers(crop_id, num_farmers):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Farmers WHERE F_availability = 1 AND specialization = %s LIMIT %s", (crop_id, int(num_farmers)))
    farmers = cursor.fetchall()
    cursor.close()
    connection.close()
    return farmers


@app.route('/retrieve', methods = ['POST'])
def retrieve():
    customer_id = request.args.get('customer_id')
    crop_id = request.args.get('crop_id') 

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM managers where CustomerID = %s",(customer_id,))
    manager=cursor.fetchone()
    cursor.execute("Select land_size from sites where CustomerID=%s",(customer_id,))
    result = cursor.fetchone()
    land_size = result['Land_size']
    num_farmers= 2 * land_size

    return render_template('customer_homepage.html', manager=manager, num_farmers=num_farmers)


@app.route('/next_step', methods=['POST'])
def next_step():
    # Handle the next step after assignment
    # return redirect(url_for('customer_login'))  # Redirects tioi customer 
    if request.method == 'POST':
        return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
