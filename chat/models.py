from django.contrib.auth.models import User
from django.db import models
import uuid
from django.core.exceptions import ValidationError


def generate_short_uuid():
    # Get a UUID and take first 10 characters
    return uuid.uuid4().hex[:10]


class GroupChat(models.Model):
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_groups'
    )
    title = models.CharField(max_length=50)
    unique_id = models.CharField(
        max_length=10,
        unique=True,
        default=generate_short_uuid,
        editable=False
    )
    members = models.ManyToManyField(
        User,
        through='Member',
        related_name='group_chats'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Member(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='group_memberships'
    )
    group = models.ForeignKey(
        GroupChat,
        on_delete=models.CASCADE,
        related_name='group_members'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'group')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.group.title}"


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_sent', null=True, blank=True)
    group = models.ForeignKey(GroupChat, on_delete=models.CASCADE, related_name='messages')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    is_system_message = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['group', 'timestamp']),
        ]

    def __str__(self):
        return self.message
