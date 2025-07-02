from bw_secrets import BOT_TOKEN

from discord import abc, Client, gateway, VoiceClient

import asyncio
import datetime
import json
import random
import requests
import socket
import websockets
from websockets.asyncio.client import ClientConnection


class ClippedVoiceClient(VoiceClient):
    def __init__(self,
                 client: Client,
                 channel: abc.Connectable):
        super().__init__(client, channel)

        self.last_sequence = None
        self.vc_last_sequence = None
        self.vc_server_data = None
        self.vc_state_data = None
        self.vc_secret_key = None
        self.endpoint = None
        self.server_id = channel.guild.id
        self.channel_id = channel.id

        headers = {
            "Authorization": f"Bot {BOT_TOKEN}",
            "Content-Type": "application/json"
        }
        response = requests.get(
            "https://discord.com/api/v10/gateway", headers=headers)
        self.wss_url = response.json()["url"]
        self.wss_url += "?v=10&encoding=json"

    async def voice_connect(self):
        websocket = await websockets.connect(self.wss_url)

        # Receive Hello event, then initiate heartbeats in the background
        hello = json.loads(await websocket.recv())

        if hello["op"] != 10:
            raise Exception("Hello event failed")

        hb_interval = hello["d"]["heartbeat_interval"]
        asyncio.create_task(
            self._heartbeat_task(websocket=websocket,
                                 hb_opcode=1,
                                 hb_interval=hb_interval),
            name="heartbeat"
        )

        # Identify
        await websocket.send(json.dumps({
            "op": 2,
            "d": {
                "token": BOT_TOKEN,
                "intents": 0b111010000001,
                "properties": {
                    "os": "linux",
                    "browser": "clipped_voice_client",
                    "device": "clipped_voice_client"
                }
            }
        }))
        ready = json.loads(await websocket.recv())

        if ready["op"] != 0:
            raise Exception("Ready event failed")

        # Initialize event listener
        asyncio.create_task(
            self._event_loop(websocket),
            name="event_loop"
        )

        # Connect to the voice channel
        await websocket.send(json.dumps({
            "op": 4,
            "d": {
                "guild_id": self.server_id,
                "channel_id": self.channel_id,
                "self_mute": False,
                "self_deaf": False
            }
        }))

    async def _event_loop(self, websocket: ClientConnection):
        # Start listening for events
        while True:
            event = json.loads(await websocket.recv())

            if event["op"] == 0:
                self.last_sequence = event["s"]
                if event["t"] == "GUILD_CREATE":
                    print(f"Connected to '{event["d"]["name"]}' server")
                elif event["t"] == "VOICE_STATE_UPDATE":
                    print(f"Voice state updated")
                    self.vc_state_data = event["d"]
                    self._voice_state_complete.set()
                if event["t"] == "VOICE_SERVER_UPDATE":
                    print(f"Voice server updated")
                    self.vc_server_data = event["d"]
                    self.endpoint = event["d"]["endpoint"]
                    self.token = event["d"]["token"]
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self._voice_server_complete.set()
                else:
                    # print(json.dumps(event, indent=4))
                    pass
            elif event["op"] == 1:
                await self._heartbeat(websocket=websocket, hb_opcode=1)
            elif event["op"] == 11:
                print("Heartbeat ACK received")

    async def _heartbeat(self,
                         websocket: ClientConnection,
                         hb_opcode: int,
                         delay: int = 0):
        await asyncio.sleep(delay)
        await websocket.send(json.dumps({
            "op": hb_opcode,
            "d": self.last_sequence if hb_opcode == 1 else {
                "t": int(datetime.datetime.now().timestamp()),
                "seq_ack": self.vc_last_sequence
            }
        }, skipkeys=True))

    async def _heartbeat_task(self,
                              websocket: ClientConnection,
                              hb_opcode: int,
                              hb_interval: int):
        await self._heartbeat(websocket=websocket,
                              hb_opcode=hb_opcode,
                              delay=hb_interval / 1000 * random.random())
        while True:
            await self._heartbeat(websocket=websocket,
                                  hb_opcode=hb_opcode,
                                  delay=hb_interval / 1000)
