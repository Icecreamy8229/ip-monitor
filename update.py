import os
import zipfile

import requests
import json
import re
from main import log_output
from colorama import Fore, Back, Style, init
import time
from dotenv import load_dotenv



init(autoreset=True)
OWNER = "YourUsername"
REPO = "IpMonitor"
DOWNLOAD_URL = f"https://github.com/{OWNER}/{REPO}/releases/latest/download/ipmonitor.zip"
VERSION_URL = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/version.json"
VERSION = "0.0.0"
BRANCH = "main"


def get_local_version():
    with open("version.json", "r") as version_file:
        contents = json.load(version_file)
        return contents["version"]

def download_files():
    print(Fore.YELLOW + "Downloading latest version.")
    log_output("Downloading latest version.")
    r = requests.get(DOWNLOAD_URL)
    content_disposition = r.headers.get('Content-Disposition',"")
    filename_match = re.findall('filename="?([^"]+)"?', content_disposition)
    filename = filename_match[0] if filename_match else None
    with open(filename_match[0], "wb") as local_file:
        local_file.write(r.content)
    return filename


def unzip_file(filename):
    print(Fore.YELLOW + "Unzipping " + filename)
    log_output("Unzipping downloaded update")
    with zipfile.ZipFile(filename, "r") as zip_ref:
        zip_ref.extractall()


def save_previous_config():
    directory_contents = os.listdir(os.getcwd())
    if "backup" not in directory_contents:
        os.mkdir("backup")
        backup_files = []

    else:
        backup_files = os.listdir("./backup")


    with open("config.yaml", "r") as config_file:
        contents = config_file.read()

    with open(f"./backup/{len(backup_files)}-config.yaml", "a+") as backup_config:
        backup_config.write(contents)

def restore_previous_config():
    log_output("restoring previous config file")
    backup_folder = "./backup"
    backup_config_files = sorted(os.listdir(backup_folder), key=lambda f: os.path.getctime(os.path.join(backup_folder, f)))
    latest_backup_version = backup_config_files[-1]
    with open(f'{backup_folder}/{latest_backup_version}', 'r') as backup_config:
        contents = backup_config.read()

    with open("config.yaml", "w+") as config_file:
        config_file.write(contents)




def compare_versions():
    print("Checking for Updates...")
    r = requests.get(VERSION_URL)
    r = r.json()
    server_version = r['version']
    local_version = get_local_version()
    if server_version != local_version:
        print(Fore.YELLOW + "Update Found!")
        log_output("Server version is different from local version")
        if not is_test_update():
            save_previous_config()
        filename = download_files()
        if not is_test_update():
            unzip_file(filename)
            restore_previous_config()
            log_output("removing downloaded zip file.")
            os.remove(filename)
            print(Fore.GREEN + "Successfully Updated!")

    else:
        print(Fore.GREEN + "No update found!")
        log_output("No update found.")

    time.sleep(2)

def is_test_update():
    if not load_dotenv(dotenv_path='.env'):
        return False
    return bool(os.getenv("TEST_UPDATE"))



def main():
    if is_test_update():
        print("Test Update Enabled.")

    compare_versions()


if __name__ == "__main__":
    if load_dotenv(dotenv_path='.env') and not is_test_update():
        print("Development ENV loaded, skipping version check.")
        time.sleep(2)
        quit()

    main()