from django.urls import path

from .views import IndexView, CreateChatView, JoinChatView, LeaveChatView, ChatRoomView

app_name = 'chat'

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('create_group/', CreateChatView.as_view(), name='create_group'),
    path('join/<str:chat_id>/', JoinChatView.as_view(), name='join_chat'),
    path('chat_view/<str:chat_id>/', ChatRoomView.as_view(), name='chat_view'),
    path('leave/<str:chat_id>/', LeaveChatView.as_view(), name='leave_chat'),
]
