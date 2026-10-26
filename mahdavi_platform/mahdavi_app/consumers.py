# mahdavi_app/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import LiveStream, LiveStreamViewer
from django.utils import timezone

class LiveStreamConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.stream_id = self.scope['url_route']['kwargs']['stream_id']
        self.room_group_name = f'live_{self.stream_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Register viewer
        await self.register_viewer()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Unregister viewer
        await self.unregister_viewer()

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'viewer_count':
            # Send current viewer count
            count = await self.get_viewer_count()
            await self.send(text_data=json.dumps({
                'type': 'viewer_count',
                'count': count
            }))
        elif message_type == 'chat_message':
            # Broadcast chat message
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': data['message'],
                    'user': data['user']
                }
            )

    async def chat_message(self, event):
        # Send chat message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'user': event['user']
        }))

    async def stream_data(self, event):
        # Send stream data to viewers
        await self.send(text_data=json.dumps({
            'type': 'stream_data',
            'data': event['data']
        }))

    @database_sync_to_async
    def register_viewer(self):
        try:
            stream = LiveStream.objects.get(id=self.stream_id)
            viewer, created = LiveStreamViewer.objects.get_or_create(
                live_stream=stream,
                user=self.scope['user'],
                defaults={'join_time': timezone.now()}
            )
            if created:
                stream.viewer_count += 1
                stream.save()
        except LiveStream.DoesNotExist:
            pass

    @database_sync_to_async
    def unregister_viewer(self):
        try:
            stream = LiveStream.objects.get(id=self.stream_id)
            viewer = LiveStreamViewer.objects.get(
                live_stream=stream,
                user=self.scope['user'],
                leave_time__isnull=True
            )
            viewer.leave_time = timezone.now()
            viewer.save()
            
            stream.viewer_count = max(0, stream.viewer_count - 1)
            stream.save()
        except (LiveStream.DoesNotExist, LiveStreamViewer.DoesNotExist):
            pass

    @database_sync_to_async
    def get_viewer_count(self):
        try:
            stream = LiveStream.objects.get(id=self.stream_id)
            return stream.viewer_count
        except LiveStream.DoesNotExist:
            return 0

class LiveStreamBroadcastConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.stream_id = self.scope['url_route']['kwargs']['stream_id']
        self.room_group_name = f'broadcast_{self.stream_id}'
        
        # Check if user is the stream owner
        if not await self.is_stream_owner():
            await self.close()
            return
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'stream_data':
            # Broadcast stream data to all viewers
            await self.channel_layer.group_send(
                f'live_{self.stream_id}',
                {
                    'type': 'stream_data',
                    'data': data['data']
                }
            )

    @database_sync_to_async
    def is_stream_owner(self):
        try:
            stream = LiveStream.objects.get(id=self.stream_id)
            return stream.marja == self.scope['user']
        except LiveStream.DoesNotExist:
            return False