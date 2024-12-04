"""
# Program Description and Usage Instructions

## Purpose:
This script interacts with the AutoCare API to retrieve and download data from a selected database and table. It handles authentication, table selection, and file output automatically.

## Prerequisites:
1. **Python Environment**: Ensure you have Python 3.x installed.
2. **Dependencies**: Install the required Python packages:
   - `requests`
   - `dotenv`
   - These can be installed using `pip install requests python-dotenv`.

3. **.env File**:
   - Create a `.env` file in the same directory as the script.
   - Add the following keys with appropriate values:
     ```
     AC_CLIENT_ID=your_client_id
     AC_CLIENT_SECRET=your_client_secret
     AC_USERNAME=your_username
     AC_PASSWORD=your_password
     ```
   - Replace `your_client_id`, `your_client_secret`, `your_username`, and `your_password` with the credentials provided by AutoCare.

4. **SSL Verification**:
   - If you encounter SSL issues, ensure the API endpoint certificates are trusted or disable SSL verification in the script (not recommended for production).
   - Disabled currently while debugging and early days of API access.

## Using the Program:
1. **Run the Script**:
   - Launch the script from any Python-compatible terminal or IDE.
   - It will prompt you to select a database and a table from the AutoCare API.

2. **Token Handling**:
   - The script will manage and save the API token automatically to your desktop (`token.txt`).
   - If the token is valid, it will reuse it; otherwise, it will request a new one and save it.

3. **Selecting Data**:
   - The program will display available databases and tables.
   - Use the displayed menu to make your selections.

4. **Output Files**:
   - Downloaded table data is saved to your desktop in JSON format.
   - File name format: `<database_name>_<table_name>.json`.

## Notes:
- The program dynamically detects the user's desktop path, ensuring all files are saved where the user can easily find them.
- Ensure your `.env` file is correctly formatted and accessible for the script to work.
- Handle API credentials with care—avoid sharing or exposing your `.env` file.

## Troubleshooting:
- **Invalid Token**: If authentication fails, ensure your credentials in `.env` are accurate.
- **Output Not Found**: Verify the desktop path is accessible and the program has write permissions.
"""
import requests
from dotenv import load_dotenv
import os
import json
from pathlib import Path
from datetime import datetime, timedelta

class TokenService:
    def __init__(self, client_id, client_secret, username, password):
        self.base_url = "https://autocare-identity.autocare.org/connect/token"
        self.scope = "CommonApis QDBApis PcadbApis BrandApis VcdbApis offline_access"
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password

    def get_bearer_token(self, verify_ssl=False):
        try:
            payload = {
                "grant_type": "password",
                "username": self.username,
                "password": self.password,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": self.scope,
            }

            response = requests.post(self.base_url, data=payload, verify=verify_ssl)

            if response.status_code == 200:
                token_data = response.json()
                if "access_token" in token_data:
                    expires_in = token_data.get("expires_in", 3600)
                    expiration_time = datetime.now() + timedelta(seconds=expires_in)
                    token_data["expiration_time"] = expiration_time.isoformat()
                    return token_data
                else:
                    raise Exception("Access token not found in the response.")
            else:
                error_content = response.text
                raise Exception(f"Error retrieving token: {response.reason}, Details: {error_content}")

        except requests.exceptions.SSLError:
            raise Exception("SSL error occurred. Consider verifying certificates or bypassing SSL verification.")
        except Exception as e:
            raise Exception(f"An error occurred while retrieving the token: {str(e)}")

def save_token_to_file(token_data, file_path):
    with open(file_path, "w") as file:
        json.dump(token_data, file)

def load_token_from_file(file_path):
    if not Path(file_path).exists() or os.path.getsize(file_path) == 0:
        return None
    with open(file_path, "r") as file:
        return json.load(file)

def is_token_valid(token_data):
    if not token_data or "expiration_time" not in token_data:
        return False
    expiration_time = datetime.fromisoformat(token_data["expiration_time"])
    return datetime.now() < expiration_time

def fetch_data(api_url, token):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(api_url, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to fetch data. Status: {response.status_code}, Details: {response.text}")

    except Exception as e:
        raise Exception(f"An error occurred while fetching data: {str(e)}")

def fetch_tables_for_database(database_name, token):
    try:
        api_url = f"https://common.autocarevip.com/api/v1.0/databases/{database_name}/tables"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(api_url, headers=headers)

        if response.status_code == 200:
            tables = response.json()
            # Extract table names
            return [table["TableName"] for table in tables]
        else:
            raise Exception(f"Failed to fetch tables for database {database_name}. Status: {response.status_code}")
    except Exception as e:
        raise Exception(f"An error occurred while fetching tables: {str(e)}")

def download_table(database_name, table_name, token, output_file_path):
    try:
        # Construct the initial URL
        api_url = f"https://{database_name.lower()}.autocarevip.com/api/v1.0/{database_name}/{table_name}"
        headers = {"Authorization": f"Bearer {token}"}
        all_records = []

        while api_url:  # Continue until there are no more pages
            print(f"Downloading from URL: {api_url}")
            response = requests.get(api_url, headers=headers)

            if response.status_code == 200:
                # Append current page's data to all_records
                data = response.json()
                all_records.extend(data)

                # Extract pagination details
                pagination = response.headers.get("X-Pagination")
                if pagination:
                    pagination_info = json.loads(pagination)
                    api_url = pagination_info.get("nextPageLink")  # Update URL to next page
                else:
                    break  # Exit if no pagination info
            else:
                raise Exception(f"Failed to fetch table '{table_name}'. Status: {response.status_code}, Details: {response.text}")

        # Save all collected records to the output file
        with open(output_file_path, "w") as file:
            json.dump(all_records, file, indent=4)
        print(f"Table '{table_name}' downloaded successfully with {len(all_records)} records to {output_file_path}.")
    except Exception as e:
        raise Exception(f"An error occurred while downloading the table: {str(e)}")

def display_menu_and_choose(data, prompt):
    print(prompt)
    for i, item in enumerate(data):
        print(f"{i + 1}. {item}")
    print("\nEnter the number corresponding to your choice or 'q' to quit:")
    choice = input("Your choice: ").strip()

    if choice.lower() == "q":
        print("Exiting.")
        exit(0)

    try:
        choice_index = int(choice) - 1
        if 0 <= choice_index < len(data):
            return data[choice_index]
        else:
            print("Invalid choice. Please try again.")
            return display_menu_and_choose(data, prompt)
    except ValueError:
        print("Invalid input. Please enter a number.")
        return display_menu_and_choose(data, prompt)

if __name__ == "__main__":
    load_dotenv("C:/Users/rhenderson/Desktop/.env")

    client_id = os.getenv("AC_CLIENT_ID")
    client_secret = os.getenv("AC_CLIENT_SECRET")
    username = os.getenv("AC_USERNAME")
    password = os.getenv("AC_PASSWORD")

    token_file_path = Path("C:/Users/rhenderson/Desktop/token.txt")

    token_data = load_token_from_file(token_file_path)

    if not is_token_valid(token_data):
        token_service = TokenService(client_id, client_secret, username, password)
        try:
            token_data = token_service.get_bearer_token(verify_ssl=False)
            save_token_to_file(token_data, token_file_path)
            print("New token saved.")
        except Exception as error:
            print(f"Error: {error}")
            exit(1)
    else:
        print("Token is valid.")

    token = token_data["access_token"]
    api_url = "https://common.autocarevip.com/api/v1.0/databases"

    try:
        databases = fetch_data(api_url, token)
        database_names = [db["databaseName"] for db in databases]

        selected_database = display_menu_and_choose(database_names, "Available Databases:")
        tables = fetch_tables_for_database(selected_database, token)

        selected_table = display_menu_and_choose(tables, f"Available Tables in {selected_database}:")
        output_file_path = Path(f"C:/Users/rhenderson/Desktop/{selected_database}_{selected_table}.json")

        download_table(selected_database, selected_table, token, output_file_path)
    except Exception as error:
        print(f"Error: {error}")