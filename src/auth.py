from functools import wraps
from flask import request, jsonify
from src.json_utils import load_keys, save_keys, load_tasks
from config import REQUEST_LIMIT, TASK_CLEANUP_TIME
from datetime import datetime, timedelta
import secrets

def generate_key():
    return secrets.token_urlsafe(32)

def check_memory_limit(api_key, new_size=0):
    keys = load_keys()
    key_name = get_key_name(api_key)
    if not key_name:
        return False

    current_time = datetime.now()
    key_info = keys[key_name]
    
    if 'memory_usage' not in key_info:
        key_info['memory_usage'] = []
    key_info['memory_usage'] = [
        usage for usage in key_info['memory_usage']
        if datetime.fromisoformat(usage['timestamp']) > current_time - timedelta(minutes=10)
    ]
    
    total_usage = sum(usage['size'] for usage in key_info['memory_usage'])
    memory_limit = 5 * 1024 * 1024 * 1024  # 5GB in bytes
    
    if total_usage + new_size > memory_limit:
        return False
    if new_size > 0:
        key_info['memory_usage'].append({
            'timestamp': current_time.isoformat(),
            'size': new_size
        })
        save_keys(keys)
    return True

def check_rate_limit(api_key):
    tasks = load_tasks()
    key_name = get_key_name(api_key)
    rate = 0
    for task_name, task_info in tasks.items():
        if task_info['key_name'] == key_name:
            rate += 1
    if rate >= REQUEST_LIMIT: return False
    return True

def check_api_key(required_permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = request.headers.get('X-API-Key')
            if not api_key:
                return jsonify({'error': 'No API key provided'}), 401
            if not check_rate_limit(api_key):
                return jsonify({'error': f'Rate limit exceeded. Maximum {REQUEST_LIMIT} requests per {TASK_CLEANUP_TIME} minutes.'}), 429
            key_info = get_key_info(api_key)
            if not key_info:
                return jsonify({'error': 'Invalid API key'}), 401
            permissions = key_info['permissions']
            if required_permission not in permissions:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_key_name(api_key):
    keys = load_keys()
    for key_name, key_info in keys.items():
        if key_info['key'] == api_key:
            return key_name
    return None

def create_api_key(name, permissions):
    keys = load_keys()
    new_key = generate_key()
    keys[name] = {
        'key': new_key,
        'permissions': permissions
    }
    save_keys(keys)
    return new_key

def delete_api_key(name):
    keys = load_keys()
    if name in keys:
        del keys[name]
        save_keys(keys)
        return True
    return False

def get_all_keys():
    return load_keys()

def get_key_info(api_key):
    keys = load_keys()
    key_info = next((item for item in keys.values() if item['key'] == api_key), None)
    return key_info

if load_keys() == {}: create_api_key("admin", ["create_key", "delete_key", "get_key", "get_keys", "get_video", "get_audio", "get_live_video", "get_live_audio", "get_info"])
