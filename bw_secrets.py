"""Secrets management"""
from bitwarden_sdk import BitwardenClient, DeviceType, client_settings_from_dict
import os

API_URL = os.getenv("BW_API_URL")
IDENTITY_URL = os.getenv("BW_ID_URL")
ACCESS_TOKEN = os.getenv("BW_ACCESS_TOKEN")

if (API_URL is None or
    IDENTITY_URL is None or
        ACCESS_TOKEN is None):
    raise Exception(
        "Environment variables aren't set: "
        f"API_URL={API_URL}, "
        f"IDENTITY_URL={IDENTITY_URL}, "
        f"ACCESS_TOKEN={ACCESS_TOKEN}")

client = BitwardenClient(
    client_settings_from_dict(
        {
            "apiUrl": API_URL,
            "deviceType": DeviceType.SDK,
            "identityUrl": IDENTITY_URL,
            "userAgent": "Python",
        }
    )
)

client.access_token_login(ACCESS_TOKEN)

################# ENVIRONMENT VARIABLES #################

# Discord
BOT_TOKEN = client.secrets().get(
    "af2e1610-c629-4ea9-9610-b2dd0000988a").data.value
DEV_GUILD_ID = client.secrets().get(
    "d0f6db4e-fecb-4ec4-adab-b2dd0000a6fa").data.value
DISCORD_API_URL = client.secrets().get(
    "2c787aca-338a-4394-b2ad-b2dd0000fbb8").data.value

# MongoDB
CLIPPED_SESSIONS_COLLECTION = client.secrets().get(
    "8940a032-0ed4-41d3-ac61-b2dd0000ba15").data.value
CLIPS_METADATA_COLLECTION = client.secrets().get(
    "5762957e-3ba1-41a0-b2e0-b2dd0000c2a5").data.value
MONGO_CONN_STRING = client.secrets().get(
    "8fc71769-0255-4491-a3f7-b2dd0000dabf").data.value
MONGO_DB_NAME = client.secrets().get(
    "f3ba901e-6086-4ac3-bf91-b2dd0000ecc4").data.value
