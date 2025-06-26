"""Thin wrapper around Keeper Commander SDK."""
import os, base64, json
from keepercommander import api

def _login():
    vault = os.environ["KPR_VAULT"]
    device = os.environ.get("KPR_DEVICE", "")
    return api.login(vault, device)

def get_client():
    if not hasattr(get_client, "_sdk"):
        get_client._sdk = _login()
    return get_client._sdk

def get_record(uid: str):
    return api.get_record(get_client(), uid)

def put_record(record):
    return api.update_record(get_client(), record)

def create_record(record):
    return api.add_record(get_client(), record)

def upload_file(folder_uid: str, file_path, title: str):
    return api.upload_attachment(get_client(), folder_uid, file_path, title)
