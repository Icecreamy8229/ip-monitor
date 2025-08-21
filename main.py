import random
import time
import os
import datetime
import json
import requests
from art import logo
from math import ceil
import yaml
from colorama import Fore, Style, Back, init
import ipaddress
from dotenv import load_dotenv

load_dotenv()

init(autoreset=True)
with open("config.yaml", 'r') as config:
    cfg = yaml.safe_load(config)

with open("version.json", 'r') as version:
    version = json.load(version)

VERSION = version['version']
DNS_PROVIDERS = cfg['DNS_PROVIDERS']
STATIC_DESCRIPTIONS = cfg['STATICS']['DESCRIPTIONS']
PRIMARY_IP_ADDRESS = cfg['STATICS']['PRIMARY']
SECONDARY_IP_ADDRESSES = cfg['STATICS']['SECONDARIES']
ALL_STATIC_ADDRESSES = [PRIMARY_IP_ADDRESS] + SECONDARY_IP_ADDRESSES

PRIMARY_DESCRIPTION = STATIC_DESCRIPTIONS[0]
SECONDARY_DESCRIPTIONS = STATIC_DESCRIPTIONS[1:]
TEST_MODE = bool(cfg['TEST_MODE'])
current_ip_address = None
check_interval = cfg['INTERVAL']
ez_outlet_reset_attempts = 0
log_entry = ""

def is_ip_address(item: str) -> bool:
    try:
        ipaddress.ip_address(item)
        return True
    except ValueError:
        return False


def send_to_api(message = None):

    if cfg['API']['URL'] == "":
        return
    headers = {
        'Authorization': cfg['API']['KEY'],
        'Content-Type': 'application/json',
        'From': f"{cfg['API']['HEADER_FROM_PREFIX']}ip_monitor"
    }

    data = {
        "ip_address": current_ip_address,
        "msg": message
    }

    attempts = 0
    log_output(f"sending data to {cfg['API']['URL']}")


    while attempts < cfg['API']['MAX_ATTEMPTS']:

        try:
            r = requests.post(cfg['API']['URL'], headers=headers, timeout=cfg['API']['TIMEOUT'], json=data)
            return

        except requests.exceptions.ConnectionError as e:
            log_output(f"Error, cannot reach api endpoint. {e}")
            time.sleep(1)
        except Exception as e:
            log_output('Reaching api endpoint failed: {}'.format(e))
            time.sleep(1)

        attempts += 1

def send_to_webhook(message):
    attempts = 0
    headers = {
        'Content-Type': 'application/json',
    }

    payload = {
        'content': message,

    }
    max_attempts = cfg['WEBHOOK']['MAX_ATTEMPTS']
    timeout = cfg['WEBHOOK']['TIMEOUT']
    url = cfg['WEBHOOK']['URL']

    while attempts < max_attempts:
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if r.status_code in (200, 204):
                return
            log_output(f"Webhook non-2xx ({r.status_code}): {r.text[:200]}")
        except requests.exceptions.ConnectionError as e:
            log_output(f"Error, cannot reach webhook. {e}")
        except Exception as e:
            log_output(f"Reaching webhook failed: {e}")
        attempts += 1


def ping_primary_gateway():
    os.makedirs("gateway-checks", exist_ok=True)
    ip_address = cfg['STATICS']['PRIMARY_GATEWAY']
    router_ip = cfg['STATICS']['PRIMARY']
    dt = str(datetime.datetime.now().replace(microsecond=0)).replace(" ", "-").replace(":", "-")
    os.system(f'ping {ip_address} -n 15 > "gateway-checks/{dt}-Outage-gateway.txt"')
    os.system(f'ping {router_ip} -n 15 > "gateway-checks/{dt}-Outage-router.txt"')


def log_output(msg):
    global log_entry
    msg = str(datetime.datetime.now().strftime("%m/%d/%y %H:%M:%S")) + " - " + msg
    print("Outputting to log: " + msg)
    if cfg['LOGGING_ENABLED']:
        with open('log.txt', 'a') as f:
            f.writelines(msg + "\n")
    log_entry = msg


timestamp = datetime.datetime.now()

def reset_ez_outlet():
    global ez_outlet_reset_attempts

    if ez_outlet_reset_attempts >= cfg['EZ_OUTLET']['MAX_RESET_ATTEMPTS']:
        log_output("ez outlet reset limit has been reached.")
        return

    ez_outlet_reset_attempts += 1
    send_to_api("Sending Reset signal to EZ Outlet.")
    log_output("Sending Reset signal to EZ Outlet.")
    if TEST_MODE:
        return

    username = cfg['EZ_OUTLET']['USERNAME']
    password = cfg['EZ_OUTLET']['PASSWORD']
    try:
        url = f"{cfg['EZ_OUTLET']['URL']}/cgi-bin/control2.cgi?user={username}&passwd={password}"
        action = "&target=1&control=3"
        r = requests.get(url + action)
        send_to_api("XML Output from EZ Outlet:\n" + str(r.text))
    except Exception as e:
        send_to_api("Error sending reset signal. " + str(e))


def fetch_json(url, timeout=3):
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()  # ensure HTTP status is OK (2xx)
    except requests.RequestException as e:
        raise RuntimeError(f"HTTP request failed: {e}")

    content_type = response.headers.get('Content-Type', '')
    if not content_type.lower().startswith('application/json'):
        raise ValueError(f"Unexpected content type: {content_type!r}")

    try:
        data = response.json()
    except ValueError as e:
        raise ValueError(f"Response is not valid JSON: {e}")

    return data

def fetch_text(url, timeout=3):
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()  # ensure HTTP status is OK (2xx)
    except requests.RequestException as e:
        raise RuntimeError(f"HTTP request failed: {e}")

    content_type = response.headers.get('Content-Type', '')
    if not content_type.lower().startswith('text/plain'):
        raise ValueError(f"Unexpected content type: {content_type!r}")

    try:
        data = response.text.strip()
    except ValueError as e:
        raise ValueError(f"Response is not valid text: {e}")

    return data


def get_ip() -> dict:
    """

    :return: a dictionary containing the method used to get the address, and the machines current WAN address.
    """
    return_dict = {"provider": None, "ip": None}

    while not return_dict['ip']:
        provider = random.choice(DNS_PROVIDERS)
        try:
            data = fetch_json(provider)
            log_output(f"Fetching IP from JSON {provider}")
            return_dict['provider'] = provider
            return_dict['ip'] = data['origin']

        except ValueError as _:
            pass

        except Exception as e:
            log_output(f"Error fetching json from provider {provider} : {e}")

        if not return_dict['ip']:
            try:
                data = fetch_text(provider)
                return_dict['ip'] = data
                log_output(f"Fetched from text: {provider}")
                return_dict['provider'] = provider
            except ValueError as _:
                pass

            except Exception as e:
                log_output(f"Error fetching text from provider {provider} : {e}")

    return return_dict


def refresh_display(check:dict) -> None:
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.CYAN + logo)
    if TEST_MODE:
        print(Back.RED + "TEST MODE!")
    print(f'VERSION: {VERSION}')
    print(f'PROVIDER: {check["provider"]}')
    print(f'WAN ADDRESS: {Fore.GREEN} {check["ip"]}')
    if check['ip'] != PRIMARY_IP_ADDRESS and cfg['EZ_OUTLET']['URL']:

        delta = ceil(cfg['EZ_OUTLET']['LIMIT'] * 60 - (datetime.datetime.now() - timestamp).total_seconds())
        delta = delta if delta > 0 else 0
        if ez_outlet_reset_attempts >= cfg['EZ_OUTLET']['MAX_RESET_ATTEMPTS']:
            print(Fore.YELLOW + "EZ Outlet reset limit has been reached.")
        else:
            print(Fore.YELLOW + f"Seconds until EZ Outlet reset is {delta}")
    print(f'Next check in {countdown_timer} seconds')

    if len(log_entry) > 1:
        print(f'\nLatest Log Entry Below:\n{log_entry}')

countdown_timer = check_interval

def main():
    global countdown_timer
    global timestamp
    global ez_outlet_reset_attempts
    global current_ip_address

    check: dict = get_ip()
    if not is_ip_address(check['ip']):
        log_output(f"The IP address is invalid: {check['ip']}")
        return


    if current_ip_address is None:  

        current_ip_address = check["ip"]
        msg = "IP Monitor Started, IP address is " + current_ip_address
        log_output(msg)
        if cfg['API']['URL']:
            send_to_api()

        if cfg['WEBHOOK']['URL']:
            send_to_webhook(msg)

    elif current_ip_address != check['ip']:  # This means the IP address has changed.
        label = None
        for index, address in enumerate(ALL_STATIC_ADDRESSES):
            if check['ip'] == address:
                label = f"{address} : {STATIC_DESCRIPTIONS[index]}"
                timestamp = datetime.datetime.now()
                if address == PRIMARY_IP_ADDRESS:
                    ez_outlet_reset_attempts = 0
                break

        msg = f"{cfg['LOCATION']['NAME']} : {label or 'Dynamic/Unknown IP'} : Provider was {check['provider']}"

        current_ip_address = check['ip']  # sets the previous IP to the current IP after the check logic

        log_output(msg)

        if cfg['API']['URL']:
            send_to_api(msg)
        if cfg['WEBHOOK']['URL']:
            send_to_webhook(msg)
        if current_ip_address != PRIMARY_IP_ADDRESS and cfg['STATICS']['PRIMARY_GATEWAY'] != "":
            ping_primary_gateway()

    elif check['ip'] != PRIMARY_IP_ADDRESS and (datetime.datetime.now() > (timestamp + datetime.timedelta(minutes=cfg['EZ_OUTLET']['LIMIT']))) and ez_outlet_reset_attempts < cfg['EZ_OUTLET']['MAX_RESET_ATTEMPTS']:  # This means IP address is secondary address and has not hit the
        
        if cfg['EZ_OUTLET']['URL'] != "":
            reset_ez_outlet()


    while countdown_timer != 0:
        countdown_timer -= 1
        refresh_display(check=check)
        time.sleep(1)

    if countdown_timer == 0:
        countdown_timer = check_interval
        send_to_api()



if __name__ == "__main__":
    while True:
        main()
