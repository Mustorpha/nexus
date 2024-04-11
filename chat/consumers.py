from channels.generic.websocket import AsyncWebsocketConsumer
from datetime import datetime
from django.conf import settings

from .autogen_chat import AutogenChat

import uuid
import openai
import os
import asyncio
import json

openai.api_key = settings.OPENAI_API_KEY

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        room_id = str(uuid.uuid4())
        self.room_group_name = "room_" + room_id
        response = {
            'type': 'send_message',
            'message': room_id,
        }
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        self.start_signal = True
        await self.channel_layer.group_send(self.room_group_name, response,)

    async def receive(self, text_data):
        received_data = json.loads(text_data)
        data = received_data["message"]
        if self.start_signal:
            self.autogen_chat = AutogenChat(websocket=self)
            self.start_signal = False
            asyncio.create_task(self.autogen_chat.start(data))
        else:
            if data and data == "END":
                await self.autogen_chat.client_sent_queue.put("END")
            await self.autogen_chat.client_sent_queue.put(data)

    async def disconnect(self, code):
        disconnection_time = str(datetime.now())
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        response = {
            'type': 'send_message',
            'message': 'Session was disconnected successfully',
            'disconnection_time': disconnection_time,
            'status': str(code)
        }
        await self.channel_layer.group_send(self.room_group_name, response)

    async def send_message(self, event):
        print('\n', event)
        text = event.get("message", None)
        author = event.get("author", "system")
        response_ = {
                'author': author,
                'message': text,
                }
        await self.send(json.dumps({
            'type': 'websocket.send',
            'text': response_,
            }))
