# Stack Overflow Enterprise Search Logs
A Python script for Stack Overflow Enterprise that automates the bulk deletion of users. 

> **WARNING: This script will permanently delete users from your Stack Overflow Enterprise instance. There is no undo. Use with caution.**

## Requirements
* Stack Overflow Enterprise and a user account with admin permissions
* Python 3.8 or higher ([download](https://www.python.org/downloads/))
* Operating system: Linux, MacOS, or Windows
* Chrome browser

## Setup
[Download](https://github.com/jklick-so/so4t_bulk_user_deletion/archive/refs/heads/main.zip) and unpack the contents of this repository

To install the required open source libraries for Python:
* Open a terminal window (or, for Windows, a command prompt)
* Navigate to the directory where you unpacked the files
* Install the dependencies: `pip3 install -r requirements.txt`

**Creating the CSV file**

Use the [CSV template](https://github.com/jklick-so/so4t_bulk_user_deletion/blob/main/Templates/users.csv) to create a CSV file with the account IDs of the users you want to delete. The CSV file must have a header row with the column name `account_id`. The script will ignore any other columns in the CSV file.

Alternatively, there's [another GitHub project](https://github.com/jklick-so/so4t_inactive_users) that generates a CSV file of inactive users, which includes the account IDs of users and has the appropriate column name (`account_id`). You can generate a report using that script, review/prune the list of users, then use it as the input for this script. Again, this script will ignore any columns in the CSV file other than `account_id`.

## Usage
In a terminal window, navigate to the directory where you unpacked the script. 
Run the script using the following format, replacing the URL with your own:

`python3 so4t_bulk_user_deletion.py --url "https://SUBDOMAIN.stackenterprise.co" --csv "users.csv"`

At the beginning of the script, a small Chrome window will appear, prompting you to login to your instance of Stack Overflow Enterprise. After logging in, the Chrome window will disappear and the script will proceed in the terminal window.

As the script runs, it will continue to update the terminal window with the status. The script will indicate when it has completed.

## Support, security, and legal
Disclaimer: the creator of this project works at Stack Overflow, but it is a labor of love that comes with no formal support from Stack Overflow. 

If you run into issues using the script, please [open an issue](https://github.com/jklick-so/so4t_bulk_user_deletion/issues). You are also welcome to edit the script to suit your needs, steal the code, or do whatever you want with it. It is provided as-is, with no warranty or guarantee of any kind. If the creator wasn't so lazy, there would likely be an MIT license file included.
