'''
This Python script is offered with no formal support from Stack Overflow. 
If you run into difficulties, open an issue on GitHub: 
https://github.com/jklick-so/so4t_bulk_user_deletion/issues
'''

# Standard Python libraries
import argparse
import csv
import pickle
import re
import time

# Third-party libraries
import requests
from selenium import webdriver
from bs4 import BeautifulSoup

def main():

    args = parse_args()

    # Load an existing session if one exists; otherwise, create a new session
    session_file = 'so4t_session'
    try:
        with open(session_file, 'rb') as f:
            client = pickle.load(f)
        if client.base_url != args.url or not client.test_session():
            raise FileNotFoundError # force creation of new session
    except FileNotFoundError:
        client = WebClient(args.url)
        with open(session_file, 'wb') as f:
            pickle.dump(client, f)

    account_ids = get_account_ids_from_csv(args.csv)
    client.delete_users(account_ids, int(args.chunk_size))


def parse_args():

    parser = argparse.ArgumentParser(description="Delete users from Stack Overflow for Teams")
    parser.add_argument('--url', 
                        required=True, 
                        help='URL of the Stack Overflow for Teams instance')
    parser.add_argument('--csv', 
                        required=True, 
                        help='Path to CSV file with users to delete')
    parser.add_argument('--chunk-size', 
                        required=False, 
                        default=25, 
                        help='Maximum number of users to delete at once')
    args = parser.parse_args()

    return args


def get_account_ids_from_csv(csv_path):

    account_ids = []
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            account_ids.append(row['account_id'])
    
    return account_ids


class WebClient(object):
    
    def __init__(self, url):
    
        if "stackoverflowteams.com" in url: # Stack Overflow Business or Basic
            self.soe = False
        else: # Stack Overflow Enterprise
            self.soe = True
        
        self.base_url = url
        self.s = self.create_session() # create a Requests session with authentication cookies
        self.admin = self.validate_admin_permissions() # check if user has admin permissions


    def create_session(self):

        s = requests.Session()

        # Configure Chrome driver
        options = webdriver.ChromeOptions()
        options.add_argument("--window-size=500,800")
        options.add_experimental_option("excludeSwitches", ['enable-automation'])
        driver = webdriver.Chrome(options=options)

        # Check if URL is valid
        try:
            response = requests.get(self.base_url)
        except requests.exceptions.SSLError:
            print(f"SSL certificate error when trying to access {self.base_url}.")
            print("Please check your URL and try again.")
            raise SystemExit
        except requests.exceptions.ConnectionError:
            print(f"Connection error when trying to access {self.base_url}.")
            print("Please check your URL and try again.")
            raise SystemExit
        
        if response.status_code != 200:
            print(f"Error when trying to access {self.base_url}.")
            print(f"Status code: {response.status_code}")
            print("Please check your URL and try again.")
            raise SystemExit
        
        # Open a Chrome window and log in to the site
        print('Opening a Chrome window to authenticate Stack Overflow for Teams...')
        driver.get(self.base_url)
        while True:
            try:
                # if user card is found, login is complete
                driver.find_element("class name", "s-user-card")
                break
            except:
                time.sleep(1)
        
        # pass authentication cookies from Selenium driver to Requests session
        cookies = driver.get_cookies()
        for cookie in cookies:
            s.cookies.set(cookie['name'], cookie['value'])
        driver.close()
        driver.quit()
        
        return s
    

    def test_session(self):

        soup = self.get_page_soup(f"{self.base_url}/users")
        if soup.find('li', {'role': 'none'}): # this element is only shows if the user is logged in
            print("Successfully authenticated Stack Overflow for Teams.")
            return True
        else:
            print("Error authenticating Stack Overflow for Teams.")
            return False


    def validate_admin_permissions(self):

        # The following URLs are only accessible to users with admin permissions
        # If the user does not have admin permissions, the page will return a 404 error
        if self.soe:
            admin_url = self.base_url + '/enterprise/admin-settings'
        else:
            admin_url = self.base_url + '/admin/settings'

        response = self.get_page_response(admin_url)
        if response.status_code != 200:
            print("User does not have admin permissions.")
            return False
        else:
            return True


    def delete_users(self, account_ids, chunk_size=25):
        """
        This function deletes users from the Stack Overflow for Teams instance.
        It requires admin permissions, which is checked for at the beginning of the function.
        It also requires an fkey, which is obtained (scraped) from the homepage.

        The list of account IDs is split into chunks of 25. The function then loops through each 
        chunk and deletes the users in that chunk.

        If any of the users in a chunk fail to be deleted, the function will return a 500 error
        and the undeleted users will be returned in the response text. The rest of the users in
        the chunk will still be deleted. The function will then move on to the next chunk.

        A sample 500 error message looks like this:
            '{"ErrorMessage":"There were some issues:\\r\\n\\r\\nNo User with Account ID 2 
                was found on this site.\\r\\nERROR (AccountId: 287): Moderators cannot be 
                deleted - tried to delete Rachel A. Adjust role to User.\\r\\n"}'
        
        Testing showed that deleting 25 users with no content attribution took about 16 seconds.
        If there is content attribution, it will take longer, possibly much longer if a user has
        a lot of content. Reaching 30 seconds could result in a timeout, so a default chunk size
        of 25 was chosen. More testing would be needed to determine the optimal chunk size.

        Args:
            account_ids (list of integers): list of account IDs to delete; not to be confused with
                user IDs, which are different
            chunk_size (int): maximum number of users to delete at once; default is 25. 
        """

        if not self.admin:
            print('Not able to delete users. This requires admin permissions.')
            return None
        
        bulk_delete_url = f"{self.base_url}/enterprise/manageusers/bulk-delete-users"
        fkey = self.get_fkey()

        payload = {
            'fkey': fkey,
            'accountIds': account_ids
        }
        
        if len(account_ids) > chunk_size:
            account_id_chunks = [account_ids[x:x+chunk_size] for x in range(
                0, len(account_ids), chunk_size)]
        else:
            account_id_chunks = [account_ids]
        
        print() # blank line
        undeleted_account_ids = []
        error_messages = []
        aggregate_response_time = 0
        for chunk in account_id_chunks:
            print(f"Deleting users: {chunk}")
            payload = {
                'fkey': fkey,
                'accountIds': chunk
            }

            start_time = time.time()
            response = self.s.post(bulk_delete_url, data=payload)
            end_time = time.time()
            response_time = end_time - start_time
            print(f"Server responded in {round(response_time, 2)} seconds.")
            aggregate_response_time += response_time

            if response.status_code == 200:
                print(f"Successfully deleted users.")
            elif response.status_code == 500:
                response_json = response.json()
                error_message = response_json['ErrorMessage']
                undeleted_account_ids += re.findall(r'\d+', error_message)

                # Separate error message into a list of strings
                error_message = error_message.split('\r\n')
                error_message.pop(0) # Remove the opening text of the error message
                error_messages += error_message

                # print(f"{error_message}")
                # print(f"Response text: {response.text}")
            else:
                print(f"Error deleting users: {chunk}")
                print(f"Response code: {response.status_code}")
                print(f"Response text: {response.text}")
                print("Exiting script.")
                raise SystemExit
            print() # blank line

        print(f"All user deletion tasks completed in {round(aggregate_response_time, 2)} seconds.")
        if error_messages:
            print(f"{len(undeleted_account_ids)} account IDs failed to be deleted:")
            number = 1
            for message in error_messages:
                if message:
                    print(f"{number}. {message}")
                    number += 1


    def get_fkey(self):
        # The fkey is a unique identifier that is required for some API calls. It can be found in
        # the HTML of most/all pages on the site. This function gets the fkey from the homepage.
        # The fkey is often used to validate that the user has permissions to perform an action.

        soup = self.get_page_soup(self.base_url)
        json_data = soup.find('script', {'data-module-name': 'Shared/options.mod'}).text
        fkey = json_data.split('"fkey":"')[1].split('"')[0]

        return fkey

        
    def get_page_response(self, url):
        # Uses the Requests session to get page response

        response = self.s.get(url)
        if not response.status_code == 200:
            print(f'Error getting page {url}')
            print(f'Response code: {response.status_code}')
        
        return response
    

    def get_page_soup(self, url):
        # Uses the Requests session to get page response and returns a BeautifulSoup object

        response = self.get_page_response(url)
        try:
            return BeautifulSoup(response.text, 'html.parser')
        except AttributeError:
            return None

if __name__ == "__main__":
    main()      