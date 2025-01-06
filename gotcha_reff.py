# -*- coding: utf-8 -*-
import requests
import json
import time
from datetime import datetime
from colorama import init, Fore, Style
from concurrent.futures import ThreadPoolExecutor, as_completed  # Import multithreading
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize colorama
init(autoreset=True)

def print_status(message, status=None):
    if status == "success":
        print(f"{Fore.GREEN}[SUKSES] {message}{Style.RESET_ALL}")
    elif status == "error":
        print(f"{Fore.RED}[GAGAL] {message}{Style.RESET_ALL}")
    elif status == "info":
        print(f"{Fore.YELLOW}[INFO] {message}{Style.RESET_ALL}")
    elif status == "header":
        print(f"\n{Fore.BLUE+Style.BRIGHT}{'='*50}")
        print(f"{Fore.CYAN}{message}")
        print(f"{Fore.BLUE+Style.BRIGHT}{'='*50}{Style.RESET_ALL}")

# Base configuration
base_url = "https://gotch.blast0x.xyz/api"

def retry_request(url, method="GET", data=None, proxies=None, retries=3):
    for attempt in range(retries):
        try:
            if method == "GET":
                response = requests.get(url, verify=False, proxies=proxies, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, verify=False, proxies=proxies, timeout=10)
            if response.status_code == 200:
                return response
            else:
                print_status(f"Attempt {attempt + 1}: {response.status_code} - {response.text}", "info")
        except requests.exceptions.RequestException as e:
            print_status(f"Attempt {attempt + 1}: {str(e)}", "error")
        time.sleep(2)  # Wait before retrying
    return None

def get_one_referral(address, proxies=None):
    url = f"{base_url}/referral/getOne?address={address}"
    response = retry_request(url, method="GET", proxies=proxies)
    if response:
        return response.json().get('success', False), response.json().get('data', None)
    return False, None

def check_referral(address, proxies=None):
    url = f"{base_url}/referral/check"
    response = retry_request(url, method="POST", data={"address": address}, proxies=proxies)
    if response:
        return response.json().get('exist', False)
    return False

def get_balance(address, proxies=None):
    url = "https://api.testnet.abs.xyz/"
    response = retry_request(url, method="POST", data={
        "jsonrpc": "2.0",
        "id": 0,
        "method": "eth_getBalance",
        "params": [address, "latest"]
    }, proxies=proxies)
    if response:
        return int(response.json().get('result', '0x0'), 16)
    return 0

def check_account(address, proxies=None):
    url = f"{base_url}/account/check"
    response = retry_request(url, method="POST", data={"address": address}, proxies=proxies)
    if response:
        return response.json().get('success', False)
    return False

def use_referral_address(address, referral_code, proxies=None):
    url = f"{base_url}/referral/usageReferralAddress"
    response = retry_request(url, method="POST", data={"address": address, "referencedCode": referral_code}, proxies=proxies)
    if response:
        return response.json().get('success', False), response.json().get('message', '')
    return False, "Request failed"

def load_referral_code(file_path):
    try:
        with open(file_path, 'r') as file:
            referral_code = file.readline().strip()
            if referral_code:
                return referral_code
            else:
                raise ValueError("Referral code is empty.")
    except FileNotFoundError:
        raise FileNotFoundError(f"File {file_path} not found.")

def load_proxies(file_path):
    try:
        with open(file_path, 'r') as file:
            proxies = [line.strip() for line in file.readlines() if line.strip()]
            return proxies
    except FileNotFoundError:
        return []

def get_proxy_for_index(proxies, index):
    if not proxies:
        return None
    proxy = proxies[index % len(proxies)]
    return {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}"
    }

def process_single_wallet(address, referral_code, index, total, proxies):
    print_status(f"Wallet {index}/{total}", "header")
    proxy = get_proxy_for_index(proxies, index)
    try:
        success, data = get_one_referral(address, proxies=proxy)
        if not data:
            print_status("No existing referral found", "info")
        else:
            print_status("Existing referral found", "info")
        time.sleep(1)

        if check_account(address, proxies=proxy):
            print_status("Account verified", "success")
        else:
            print_status("Account check failed", "error")
        time.sleep(1)

        balance = get_balance(address, proxies=proxy)
        print_status(f"Balance: {balance} wei", "info")
        time.sleep(1)

        has_referral = check_referral(address, proxies=proxy)
        if not has_referral:
            print_status("No active referral, attempting to use referral code", "info")
            success, message = use_referral_address(address, referral_code, proxies=proxy)
            if success:
                print_status("Referral code applied successfully", "success")
                return True
            else:
                print_status(f"Failed to apply referral code: {message}", "error")
                return False
        else:
            print_status("Referral already exists", "info")

        time.sleep(2)

    except Exception as e:
        print_status(f"Error processing wallet: {str(e)}", "error")

    print_status("Waiting before next wallet...", "info")
    time.sleep(2)
    return False

def process_wallet_addresses(wallet_addresses, referral_code, proxies, num_threads=100):
    total = len(wallet_addresses)
    success_count = 0

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for index, address in enumerate(wallet_addresses, 1):
            futures.append(executor.submit(process_single_wallet, address, referral_code, index, total, proxies))

        for future in as_completed(futures):
            if future.result():
                success_count += 1

    print_status(f"Processing complete! Summary", "header")
    print(f"{Fore.YELLOW}Total wallets processed: {total}")
    print(f"{Fore.GREEN}Successful referrals: {success_count}")
    print(f"{Fore.RED}Failed referrals: {total - success_count}{Style.RESET_ALL}")

def main():
    print(Fore.GREEN + Style.BRIGHT + "SELAMAT DATANG DI JERPANG BOT" + Fore.RESET)
    print(Fore.CYAN + Style.BRIGHT + "No rusuh babi! \n\n" + Fore.RESET)
    try:
        referral_code = load_referral_code('refferal_code.txt')
        print_status(f"Loaded referral code: {referral_code}", "info")

        proxies = load_proxies('proxy.txt')
        if proxies:
            print_status(f"Loaded {len(proxies)} proxies", "info")
        else:
            print_status("No proxies loaded. Proceeding without proxies.", "info")

        with open('address.txt', 'r') as file:
            wallet_addresses = [line.strip() for line in file.readlines() if line.strip()]

        if not wallet_addresses:
            print_status("No wallet addresses found in address.txt", "error")
            return

        print_status(f"Found {len(wallet_addresses)} wallet addresses", "info")
        process_wallet_addresses(wallet_addresses, referral_code, proxies, num_threads=100)

    except FileNotFoundError as e:
        print_status(str(e), "error")
    except Exception as e:
        print_status(f"An error occurred: {str(e)}", "error")

if __name__ == "__main__":
    main()
