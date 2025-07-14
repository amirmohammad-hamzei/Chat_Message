import json
import time

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import GroupChat, Message

connected_users = {}


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.room_name = self.scope['url_route']['kwargs']['room_id']
            self.room_group_name = f'chat_{self.room_name}'
            self.user = self.scope['user']

            if not self.user.is_authenticated:
                await self.close(code=4003)
                return

            # Add user to connected users
            if self.room_name not in connected_users:
                connected_users[self.room_name] = set()
            connected_users[self.room_name].add(self.user.username)

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            # Send updated online users list to all users in the room
            await self.send_online_users()

        except Exception as e:
            print(f"Error in connect: {str(e)}")
            await self.close(code=4001)

    async def disconnect(self, close_code):
        try:
            if hasattr(self, 'room_name') and hasattr(self, 'user') and hasattr(self.user, 'username'):
                if self.room_name in connected_users and self.user.username in connected_users[self.room_name]:
                    connected_users[self.room_name].remove(self.user.username)
                    if not connected_users[self.room_name]:
                        del connected_users[self.room_name]

                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
                await self.send_online_users()
        except Exception as e:
            print(f"Error in disconnect: {str(e)}")

    async def receive(self, text_data=None, bytes_data=None):
        print(text_data)
        try:
            if not text_data:
                return

            data = json.loads(text_data)

            if data.get('type') == 'chat_message':
                message = data.get('message', '').strip()
                if message:
                    await self.save_message(message)
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_message',
                            'message': message,
                            'username': self.user.username,
                            'timestamp': time.strftime("%H:%M")
                        }
                    )

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid message format'
            }))
        except Exception as e:
            print(f"Error in receive: {str(e)}")

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'username': event['username'],
            'timestamp': event['timestamp']
        }))

    async def send_online_users(self):
        if not hasattr(self, 'room_name') or self.room_name not in connected_users:
            return

        users = list(connected_users[self.room_name])
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'online_users',
                'users': users
            }
        )

    async def online_users(self, event):
        await self.send(text_data=json.dumps({
            'type': 'online_users',
            'users': event['users']
        }))

    @database_sync_to_async
    def save_message(self, message_content):
        try:
            group = GroupChat.objects.get(unique_id=self.room_name)
            return Message.objects.create(
                group=group,
                sender=self.user,
                message=message_content
            )
        except Exception as e:
            print(f"Error saving message: {str(e)}")
            return None

    async def system_message(self, event):
        # Only save if this is a new message (no message_id in event)
        if 'message_id' not in event:
            await self.save_system_message(event['message'])

        await self.send(text_data=json.dumps({
            'type': 'system_message',
            'message': event['message']
        }))

    @database_sync_to_async
    def save_system_message(self, message_content):
        try:
            group = GroupChat.objects.get(unique_id=self.room_name)
            return Message.objects.create(
                group=group,
                message=message_content,
                is_system_message=True
            )
        except Exception as e:
            print(f"Error saving system message: {str(e)}")
            return None
