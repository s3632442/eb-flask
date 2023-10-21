

from flask import Flask, redirect, request, render_template, flash, session
from boto3.dynamodb.conditions import Key
import json
import os
import requests
import boto3

app = Flask(__name__, static_url_path='/static')
app.secret_key = 'ac3b06a1-6db9-4e2a-b74a-ea24572ed710'


# Initialize the DynamoDB resource and specify the region
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1')  # Replace 'us-east-1' with your desired region

# Define the table name and attributes for the music table
table_name = 'music'


@app.route("/")
def home():
    return redirect("/login")

def read_all_entities(table_name):
    # Initialize the DynamoDB resource
    dynamodb = boto3.resource('dynamodb')

    # Get a reference to the DynamoDB table
    table = dynamodb.Table(table_name)

    try:
        # Use the scan method to read all items from the table
        response = table.scan()

        # Check if the scan was successful
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            # Return the list of items
            return response.get('Items', [])
        else:
            print("Error scanning the table.")
            return []
    except Exception as e:
        print("An error occurred:", e)
        return []

@app.route("/login", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    login_details = []  # Initialize an empty list for login details
    
    # Retrieve login details from DynamoDB
    table_name = 'Login'  # Replace with your table name
    login_details = read_all_entities(table_name)  # Get login details

    if request.method == "POST":
        # Obtain the provided username and password
        provided_username = request.form.get("username")
        provided_password = request.form.get("password")
        print("Provided Username:", provided_username)
        print("Provided Password:", provided_password)

    
        for entity in login_details:
            if (
                provided_username == entity["user_name"] and
                provided_password == entity["password"]
            ):
                # Valid credentials, redirect to main-page page and store user_name in the session
                session['user_name'] = entity["user_name"]
                flash("Logged in")
                return redirect("/main-page")

        # Invalid credentials, show an error message
        flash("Invalid username or password")
    
    return render_template("login.html", login_details=login_details)


@app.route("/main-page")
def user_home():
    if 'user_name' in session:
        user_name = session['user_name']

        # Retrieve the user's subscriptions from DynamoDB
        subscriptions = get_user_subscriptions(user_name)

        # Create a list to store subscribed music
        subscribed_music = []

        # Get a reference to the DynamoDB music table
        music_table = dynamodb.Table(music_table_name)  # Add this line

        # Iterate through the subscriptions and add the subscribed music to the list
        for subscription in subscriptions:
            title = subscription['title']
            release_year = subscription['release_year']
            artist = subscription['artist']

            # Query the music table to get additional information
            response = music_table.get_item(
                Key={'title': title}
            )

            if 'Item' in response:
                music_info = response['Item']
                subscribed_music.append({
                    'title': title,
                    'artist': artist,
                    'release_year': release_year,
                    'web_url': music_info.get('web_url'),
                    'img_url': music_info.get('image_url')
                })

        return render_template("main-page.html", subscriptions=subscribed_music)
    else:
        return render_template("main-page.html")


def create_login_table(dynamodb=None):
    if not dynamodb:
        dynamodb = boto3.resource('dynamodb')

    table_name = 'Login'
    table = dynamodb.Table(table_name)

    # Table doesn't exist, so create it
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'email',
                'KeyType': 'HASH'  # Partition key
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'email',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10
        }
    )
    # Wait for the table to be created (this can take some time)
    table.wait_until_exists()
    
    return table


def generate_password(i):
    # Generate the password using a loop, similar to your old example
    return ''.join(str(j % 10) for j in range(i, i + 6))

def delete_all_logins(dynamodb=None):
    if not dynamodb:
        dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table('Login')

    # Use scan to get all items in the table
    response = table.scan()
    items = response.get('Items', [])

    # Delete each item
    for item in items:
        table.delete_item(Key={'email': item['email']})

def insert_initial_logins(dynamodb=None):
    if not dynamodb:
        dynamodb = boto3.resource('dynamodb')

    # Delete all existing login entities
    delete_all_logins(dynamodb)

    table = dynamodb.Table('Login')
    for i in range(10):
        email = f"s3######{i}@student.rmit.edu.au"
        username = f"Firstname Lastname{i}"
        password = generate_password(i)

        item = {
            'email': email,
            'user_name': username,
            'password': password
        }
        
        table.put_item(Item=item)

# Define the table name and attributes
table_name = 'music'
table_attributes = [
    {
        'AttributeName': 'title',
        'AttributeType': 'S'
    },
    {
        'AttributeName': 'artist',
        'AttributeType': 'S'
    },
    {
        'AttributeName': 'release_year',
        'AttributeType': 'N'
    },
    {
        'AttributeName': 'web_url',
        'AttributeType': 'S'
    },
    {
        'AttributeName': 'image_url',
        'AttributeType': 'S'
    }
]

def table_exists(table_name):
    # Check if the table exists
    existing_tables = dynamodb.meta.client.list_tables()
    return table_name in existing_tables['TableNames']

def create_music_table():
    
        try:
            table = dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'title',
                        'KeyType': 'HASH'  # Partition key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'title',
                        'AttributeType': 'S'
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            table.wait_until_exists()
            print(f'Table {table_name} has been created.')
        except Exception as e:
            print(f'Error creating table: {e}')
    
def load_data_to_table():
    # Check if the table already has data
    table = dynamodb.Table(table_name)

    # Define a condition to check if data already exists
    condition = "attribute_not_exists(title)"

    if table.item_count > 0:
        print(f'Table {table_name} already has data. Skipping data loading.')
        return

    try:
        with open('a2.json', 'r') as json_file:
            data = json.load(json_file)
            songs = data.get('songs', [])  # Access the "songs" key in the JSON data

            for item in songs:
                # Check if the item with the given title doesn't already exist
                if not table.get_item(Key={'title': item['title']}, ConsistentRead=True).get("Item"):
                    # Item with the same title doesn't exist, so put the item
                    table.put_item(Item=item)
                    print(f'Data has been loaded for {item["title"]}.')
                else:
                    print(f'Data for {item["title"]} already exists. Skipping.')

    except Exception as e:
        print(f'Error loading data: {e}')


def image_exists_in_s3(s3, bucket_name, s3_object_key):
    try:
        # Attempt to head the S3 object (check for existence)
        s3.head_object(Bucket=bucket_name, Key=s3_object_key)
        return True
    except Exception as e:
        # An exception is raised if the object doesn't exist
        return False

def download_and_upload_images(json_file_path):
    if not table_exists_and_populated(table_name, dynamodb):
        print(f'Table {table_name} does not exist or is empty. Skipping image download.')
        return

    # Load the JSON data
    with open(json_file_path, 'r') as json_file:
        data = json.load(json_file)

    # Define the S3 bucket name
    bucket_name = '201c4962-cb1a-4775-9b92-889393597be0'

    # Check if the S3 bucket exists, and create it if not
    if bucket_name not in [bucket['Name'] for bucket in s3.list_buckets()['Buckets']]:
        s3.create_bucket(Bucket=bucket_name)

    # Directory to store downloaded images temporarily
    download_dir = 'downloaded_images'

    # Create the directory if it doesn't exist
    os.makedirs(download_dir, exist_ok=True)

    # Loop through each song and upload the image to S3
    for song in data['songs']:
        image_url = song['img_url']
        artist_name = song['artist']

        # Generate a unique key for the S3 object using the artist's name
        s3_object_key = f'artists/{artist_name}.jpg'

        if image_exists_in_s3(s3, bucket_name, s3_object_key):
            print(f'Image for {artist_name} already exists in S3. Skipping.')
            continue

        # Download the image
        response = requests.get(image_url)

        if response.status_code == 200:
            # Save the downloaded image to the local directory
            image_path = os.path.join(download_dir, f'{artist_name}.jpg')
            with open(image_path, 'wb') as image_file:
                image_file.write(response.content)

            # Upload the image to S3
            s3.upload_file(image_path, bucket_name, s3_object_key)

            # Clean up: remove the local image file
            os.remove(image_path)

            print(f'Uploaded image for {artist_name} to S3.')

        else:
            print(f'Failed to download the image for {artist_name}.')

    print('Image upload to S3 completed.')
    
def table_exists_and_populated(table_name, dynamodb):
    try:
        table = dynamodb.Table(table_name)
        response = table.scan()
        return table.table_status == 'ACTIVE' and len(response.get('Items', [])) > 0
    except Exception as e:
        return False
    

@app.route("/logout")
def logout():
    # Clear the user's session
    session.clear()
    flash("Logged out")  # Optional: Display a message to indicate successful logout
    return redirect("/login")

music_table_name = 'music'

# ... (your other code)

@app.route("/search", methods=["GET", "POST"])
def search():
    # Retrieve user input from the form or query parameters
    title = request.form.get("title") if request.method == "POST" else request.args.get("title")
    release_year = request.form.get("release_year") if request.method == "POST" else request.args.get("release_year")
    artist = request.form.get("artist") if request.method == "POST" else request.args.get("artist")

    # Debug: Print the user input
    print("User Input - Title:", title)
    print("User Input - release_year:", release_year)
    print("User Input - Artist:", artist)

    # Initialize the filter expression and expression attribute values
    filter_expression = ""
    expression_attribute_values = {}

    # Debug: Print the initial filter expression and values
    print("Initial Filter Expression:", filter_expression)
    print("Initial Expression Attribute Values:", expression_attribute_values)

    # Initialize the DynamoDB resource and get a reference to the table
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table(music_table_name)

    # Create a filter expression based on user input
    filter_expression_parts = []

    if artist:
        filter_expression_parts.append("contains(artist, :artist)")
        expression_attribute_values[":artist"] = artist
    if title:
        filter_expression_parts.append("contains(title, :title)")
        expression_attribute_values[":title"] = title
    if release_year and release_year.isdigit():
        filter_expression_parts.append("release_year = :release_year")
        expression_attribute_values[":release_year"] = int(release_year)

    # Combine filter expressions with "AND" if there are multiple conditions
    if filter_expression_parts:
        filter_expression = " AND ".join(filter_expression_parts)

    # Debug: Print the filter expression after combining user input
    print("Filter Expression after Combining User Input:", filter_expression)

    # Check if no search criteria are provided
    if not filter_expression:
        # Handle the case where no attributes are passed in
        message = "Please enter search criteria."
        return render_template("main-page.html", message=message)

    # Create a DynamoDB query based on the filter expression for search results
    query = table.scan(
        FilterExpression=filter_expression,
        ExpressionAttributeValues=expression_attribute_values
    )

    # Retrieve the matching items (search results)
    search_results = query.get("Items", [])

    if 'user_name' in session:
        user_name = session['user_name']

        # Retrieve the user's subscriptions from DynamoDB
        subscriptions = get_user_subscriptions(user_name)

        # Create a list to store subscribed music
        subscribed_music = []

        # Get a reference to the DynamoDB music table
        music_table = dynamodb.Table(music_table_name)

        # Iterate through the subscriptions and add the subscribed music to the list
        for subscription in subscriptions:
            title = subscription['title']
            release_year = subscription['release_year']
            artist = subscription['artist']

            # Query the music table to get additional information
            response = music_table.get_item(
                Key={'title': title}
            )

            if 'Item' in response:
                music_info = response['Item']
                subscribed_music.append({
                    'title': title,
                    'artist': artist,
                    'release_year': release_year,
                    'web_url': music_info.get('web_url'),
                    'img_url': music_info.get('image_url')
                })

        # Pass the subscribed music and search results to the main-page template
        return render_template("main-page.html", subscriptions=subscribed_music, search_results=search_results)

    # Pass only the search results to the main-page template
    return render_template("main-page.html", search_results=search_results)


@app.route("/subscribe", methods=["POST"])
def subscribe():
    if 'user_name' not in session:
        flash("Please log in to subscribe.")
        return redirect("/login")

    # Retrieve the subscribed music details from the request form
    title = request.form.get("title")
    artist = request.form.get("artist")
    user_name = session['user_name']

    # Check if release_year is provided in the form
    if "release_year" in request.form:
        release_year = int(request.form["release_year"])
    else:
        release_year = None  # Set release_year to None if not provided

    # Create a new item in the subscriptions table to store the subscription information
    table = dynamodb.Table(subscriptions_table_name)

    table.put_item(Item={
        'user_name': user_name,
        'title': title,
        'release_year': release_year,
        'artist': artist
    })

    flash(f"Subscribed to '{title}' by {artist}")

    # Redirect the user back to the main-page
    return redirect("/main-page")

def delete_all_tables():
    # Initialize the DynamoDB resource
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')  # Specify your desired region

    # List all the tables
    existing_tables = dynamodb.meta.client.list_tables()

    # Iterate through the table names and delete each table
    for table_name in existing_tables['TableNames']:
        table = dynamodb.Table(table_name)
        table.delete()

        print(f"Table '{table_name}' has been deleted.")


def delete_subscriptions_table():
    # Initialize the DynamoDB resource and specify the region
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')  # Change the region as needed

    table_name = 'subscriptions'  # Name of the table to be deleted

    try:
        # Get a reference to the table
        table = dynamodb.Table(table_name)

        # Check if the table exists
        if table.table_status == 'ACTIVE':
            # If the table is in an active state, delete it
            table.delete()

            # Wait for the table to be deleted
            table.wait_until_not_exists()

            print(f"Table '{table_name}' has been successfully deleted.")
        else:
            print(f"Table '{table_name}' does not exist or is not in an active state. No deletion is performed.")
    except Exception as e:
        print(f"An error occurred while deleting the table: {e}")


def create_subscriptions_table():
    table_name = 'subscriptions'
    
    # Check if the table already exists
    if table_exists(table_name):
        print(f"Table {table_name} already exists. Skipping table creation.")
        return

    # Define the table name and attributes for the subscriptions table
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'user_name',
                'KeyType': 'HASH'  # Partition key
            },
            {
                'AttributeName': 'title',
                'KeyType': 'RANGE'  # Sort key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'user_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'title',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        },
        GlobalSecondaryIndexes=[  # Define the Global Secondary Index here
            {
                'IndexName': 'UserSubscriptionsIndex',
                'KeySchema': [
                    {
                        'AttributeName': 'user_name',
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'title',
                        'KeyType': 'RANGE'  # Sort key
                    }
                ],
                'Projection': {
                    'ProjectionType': 'ALL'  # You can adjust this based on your needs
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ]
    )

    # Wait for the table to be created
    table.wait_until_exists()
    print(f'Table {table_name} has been created with the UserSubscriptionsIndex.')

def get_user_subscriptions(user_name):
    # Initialize the DynamoDB resource
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # Get a reference to the subscriptions table
    table_name = 'subscriptions'
    table = dynamodb.Table(table_name)

    try:
        # Use the query method to retrieve subscriptions for the given user
        response = table.query(
            IndexName='UserSubscriptionsIndex',
            KeyConditionExpression=Key('user_name').eq(user_name)
        )

        # Check if the query was successful
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            # Return the list of subscription items
            return response.get('Items', [])
        else:
            print("Error querying the subscriptions table.")
            return []
    except Exception as e:
        print("An error occurred:", e)
        return []


@app.route("/unsubscribe", methods=["POST"])
def unsubscribe():
    if 'user_name' not in session:
        flash("Please log in to unsubscribe.")
        return redirect("/login")

    # Retrieve the details of the music item to unsubscribe
    title = request.form.get("title")
    artist = request.form.get("artist")
    user_name = session['user_name']

    # Check if release_year is provided in the form
    release_year = request.form.get("year")

    if release_year is not None and release_year.isdigit():
        release_year = int(release_year)
    else:
        release_year = None  # Set release_year to None if not provided or not a valid integer

    # Get a reference to the DynamoDB subscriptions table
    subscriptions_table = dynamodb.Table(subscriptions_table_name)

    # Delete the subscription entry
    response = subscriptions_table.delete_item(
        Key={
            'user_name': user_name,
            'title': title
        }
    )

    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        flash(f"Unsubscribed from '{title}' by {artist}")
    else:
        flash("Failed to unsubscribe")

    return redirect("/main-page")


# Define the table name and attributes for the music table
music_table_name = 'music'
subscriptions_table_name = 'subscriptions'
login_table_name = 'Login'

if not table_exists_and_populated(login_table_name, dynamodb):
    create_login_table()  # Create the 'Login' table
    insert_initial_logins()  # Insert initial login data
else:
    print(f'Table {login_table_name} already exists and is populated. Skipping table creation.')

if not table_exists_and_populated(music_table_name, dynamodb):
    create_music_table()  # Create the DynamoDB music table if it doesn't exist
    load_data_to_table()  # Load data from a2.json into the music table if it's empty
    json_file_path = 'a2.json'  # Define the path to your JSON file
    download_and_upload_images(json_file_path)  # Pass json_file_path as an argument
else:
    print(f'Table {music_table_name} already exists and is populated. Skipping table creation.')

if not table_exists_and_populated(subscriptions_table_name, dynamodb):
    create_subscriptions_table()  # Create the DynamoDB subscriptions table if it doesn't exist
else:
    print(f'Table {subscriptions_table_name} already exists and is populated. Skipping table creation.')



if __name__ == '__main__':    
    app.run(host='0.0.0.0')