from django.contrib import admin
from .models import ChatRoom, Message, UserProfile, Notification, MessageReadStatus

admin.site.register(ChatRoom)
admin.site.register(Message)
admin.site.register(UserProfile)
admin.site.register(Notification)
admin.site.register(MessageReadStatus)
