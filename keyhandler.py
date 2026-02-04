import json
import time
import random
import string
import os

# Ensure necessary directories and files exist
if not os.path.exists('keys'):
    os.makedirs('keys')
if not os.path.exists('bulks'):
    os.makedirs('bulks')

for file in ['keys/keys.json', 'keys/redeemedKeys.json']:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump({}, f)

def read_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return {}

def write_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

def generate_random_string(length):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def redeem_key(key, msg):
    # In Python Telegram Bot, we extract the user ID from the message object
    # Assuming 'msg' passed here is the update object or message object
    try:
        user_id = str(msg.from_user.id)
    except:
        # Fallback if msg is just an ID
        user_id = str(msg)

    key_list = read_json('keys/keys.json')
    
    if key in key_list:
        seconds = key_list[key]
        days_calc = seconds / 3600
        
        if days_calc >= 24:
            days_str = f"{days_calc / 24} day(s)"
        else:
            days_str = f"{days_calc} hour(s)"
        
        acc_days = key_list[key]
        del key_list[key]
        
        write_json('keys/keys.json', key_list)
        print(f"The key '{key}' was redeemed with {days_str} access.")
        
        redeemed_list = read_json('keys/redeemedKeys.json')
        current_time = int(time.time())
        
        if user_id in redeemed_list and redeemed_list[user_id] >= current_time:
            redeemed_list[user_id] += acc_days
        else:
            redeemed_list[user_id] = current_time + acc_days
            
        write_json('keys/redeemedKeys.json', redeemed_list)
        return [True, days_str]
    else:
        return [False, None]

def create_key(days):
    try:
        days = int(days)
        if days >= 1:
            key_list = read_json('keys/keys.json')
            epoch_time = days * 86400
            
            key = f"DRTYOTP-{generate_random_string(9)}-{generate_random_string(9)}"
            
            key_list[key] = epoch_time
            write_json('keys/keys.json', key_list)
            
            print(f"New key entry '{key}' was created with {days} day(s) access.")
            return key
        else:
            return f"{days} amount of days isn't valid!"
    except ValueError:
        return f"The input '{days}' is either a decimal or string!"

def create_hour():
    data = read_json('keys/keys.json')
    
    key = f"DRTYOTP-{generate_random_string(9)}-{generate_random_string(9)}"
    
    data[key] = 3600
    write_json('keys/keys.json', data)
    
    print(f"New key entry '{key}' was created with one hour of access.")
    return key

def bulk_create(days):
    try:
        days = int(days)
        if days >= 1:
            key_list = read_json('keys/keys.json')
            epoch_time = days * 86400
            total_keys = ""
            
            for _ in range(100):
                key = f"DRTYOTP-{generate_random_string(9)}-{generate_random_string(9)}"
                key_list[key] = epoch_time
                total_keys += f"{key}\n"
            
            write_json('keys/keys.json', key_list)
            
            with open(f"bulks/{days}.txt", "w") as f:
                f.write(total_keys)
                
            return days
        else:
            return f"{days} amount of days isn't valid!"
    except ValueError:
        return f"The input '{days}' is either a decimal or string!"
