import json
import base64
import uuid
import os
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.base import ContentFile
from .models import ChatRoom, Message, UserProfile, MessageReadStatus, Notification


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Mark user online
        await self.set_user_online(True)

        # Notify others user joined
        await self.channel_layer.group_send(
            f'presence_{self.user.id}',
            {'type': 'presence_update', 'user_id': self.user.id, 'is_online': True}
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        if hasattr(self, 'user') and self.user.is_authenticated:
            await self.set_user_online(False)
            await self.update_last_seen()

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'chat_message')

        if msg_type == 'chat_message':
            await self.handle_chat_message(data)
        elif msg_type == 'typing':
            await self.handle_typing(data)
        elif msg_type == 'read_receipt':
            await self.handle_read_receipt(data)
        elif msg_type == 'file_message':
            await self.handle_file_message(data)

    async def handle_chat_message(self, data):
        content = data.get('content', '').strip()
        if not content:
            return

        message = await self.save_message(content, 'text')
        timestamp = message.timestamp.strftime('%I:%M %p')
        date_str = message.timestamp.strftime('%b %d, %Y')

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': message.id,
                'content': content,
                'sender_id': self.user.id,
                'sender_username': self.user.username,
                'sender_avatar': await self.get_user_avatar(self.user.id),
                'timestamp': timestamp,
                'date': date_str,
                'message_type': 'text',
            }
        )

        # Send notifications to offline members
        await self.send_notifications(message)

    async def handle_file_message(self, data):
        file_data = data.get('file_data')
        file_name = data.get('file_name', 'file')
        file_type = data.get('file_type', 'file')

        if not file_data:
            return

        message = await self.save_file_message(file_data, file_name, file_type)
        if not message:
            return

        timestamp = message.timestamp.strftime('%I:%M %p')
        msg_type = 'image' if file_type.startswith('image/') else 'file'

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': message.id,
                'content': message.content,
                'file_url': message.file_attachment.url if message.file_attachment else '',
                'file_name': file_name,
                'sender_id': self.user.id,
                'sender_username': self.user.username,
                'sender_avatar': await self.get_user_avatar(self.user.id),
                'timestamp': timestamp,
                'date': message.timestamp.strftime('%b %d, %Y'),
                'message_type': msg_type,
            }
        )

    async def handle_typing(self, data):
        is_typing = data.get('is_typing', False)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'sender_id': self.user.id,
                'sender_username': self.user.username,
                'is_typing': is_typing,
            }
        )

    async def handle_read_receipt(self, data):
        await self.mark_room_read()

    # ─── Event handlers ───────────────────────────────────────────────────────

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    async def typing_indicator(self, event):
        if event['sender_id'] != self.user.id:
            await self.send(text_data=json.dumps(event))

    async def presence_update(self, event):
        await self.send(text_data=json.dumps(event))

    # ─── DB helpers ───────────────────────────────────────────────────────────

    @database_sync_to_async
    def save_message(self, content, msg_type):
        room = ChatRoom.objects.get(id=self.room_id)
        return Message.objects.create(
            room=room,
            sender=self.user,
            content=content,
            message_type=msg_type,
        )

    @database_sync_to_async
    def save_file_message(self, file_data, file_name, file_type):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            # Decode base64 file
            if ',' in file_data:
                file_data = file_data.split(',')[1]
            file_content = base64.b64decode(file_data)
            ext = os.path.splitext(file_name)[1]
            unique_name = f"{uuid.uuid4()}{ext}"
            msg_type = 'image' if file_type.startswith('image/') else 'file'
            msg = Message(
                room=room,
                sender=self.user,
                content=file_name,
                message_type=msg_type,
            )
            msg.file_attachment.save(unique_name, ContentFile(file_content), save=True)
            return msg
        except Exception as e:
            print(f"File save error: {e}")
            return None

    @database_sync_to_async
    def set_user_online(self, status):
        UserProfile.objects.update_or_create(
            user=self.user,
            defaults={'is_online': status, 'last_seen': timezone.now()}
        )

    @database_sync_to_async
    def update_last_seen(self):
        UserProfile.objects.filter(user=self.user).update(
            last_seen=timezone.now(), is_online=False
        )

    @database_sync_to_async
    def mark_room_read(self):
        room = ChatRoom.objects.get(id=self.room_id)
        MessageReadStatus.objects.update_or_create(
            room=room, user=self.user
        )

    @database_sync_to_async
    def get_user_avatar(self, user_id):
        try:
            profile = UserProfile.objects.get(user_id=user_id)
            if profile.avatar:
                return profile.avatar.url
        except UserProfile.DoesNotExist:
            pass
        return None

    @database_sync_to_async
    def send_notifications(self, message):
        room = ChatRoom.objects.get(id=self.room_id)
        for member in room.members.exclude(id=self.user.id):
            Notification.objects.create(user=member, message=message)


class PresenceConsumer(AsyncWebsocketConsumer):
    """Handles global online presence tracking."""

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = f'presence_{self.user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        # Add to global presence group
        await self.channel_layer.group_add('global_presence', self.channel_name)
        await self.accept()

        await self.set_online(True)

        # Broadcast online status
        await self.channel_layer.group_send(
            'global_presence',
            {'type': 'user_status', 'user_id': self.user.id, 'is_online': True}
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'user') and self.user.is_authenticated:
            await self.set_online(False)
            await self.channel_layer.group_send(
                'global_presence',
                {'type': 'user_status', 'user_id': self.user.id, 'is_online': False}
            )
            await self.channel_layer.group_discard('global_presence', self.channel_name)
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def user_status(self, event):
        await self.send(text_data=json.dumps(event))

    async def presence_update(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def set_online(self, status):
        UserProfile.objects.update_or_create(
            user=self.user,
            defaults={'is_online': status, 'last_seen': timezone.now()}
        )
