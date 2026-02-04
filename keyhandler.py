import json
import time
import random
import string
import os

# Crear carpetas necesarias
if not os.path.exists('keys'):
    os.makedirs('keys')
if not os.path.exists('bulks'):
    os.makedirs('bulks')

# Crear archivos JSON si no existen
for file in ['keys/keys.json', 'keys/redeemedKeys.json']:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump({}, f)

def read_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def write_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

def generate_random_string(length):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def redeem_key(key, user_id):
    key_list = read_json('keys/keys.json')
    
    if key in key_list:
        seconds = key_list[key]
        days_calc = seconds / 3600
        if days_calc >= 24:
            duration_text = f"{days_calc/24} day(s)"
        else:
            duration_text = f"{days_calc} hour(s)"
        
        del key_list[key]
        write_json('keys/keys.json', key_list)
        
        print(f"The key '{key}' was redeemed with {duration_text} access.")
        
        redeemed_list = read_json('keys/redeemedKeys.json')
        current_time = int(time.time())
        str_user_id = str(user_id)
        
        if str_user_id in redeemed_list and redeemed_list[str_user_id] >= current_time:
            redeemed_list[str_user_id] += seconds
        else:
            redeemed_list[str_user_id] = current_time + seconds
            
        write_json('keys/redeemedKeys.json', redeemed_list)
        return [True, duration_text]
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
            return key
        return f"{days} amount of days isn't valid!"
    except:
        return "Input error"

def create_hour():
    data = read_json('keys/keys.json')
    key = f"DRTYOTP-{generate_random_string(9)}-{generate_random_string(9)}"
    data[key] = 3600
    write_json('keys/keys.json', data)
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
        return "Invalid days"
    except:
        return "Input error"
