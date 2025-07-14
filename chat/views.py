from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout
from django.contrib import messages

from chat.models import GroupChat, Member, Message

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

channel_layer = get_channel_layer()


class RegisterView(View):
    template_name = 'chat/register.html'
    form_class = UserCreationForm

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration completed successfully!')
            return redirect('chat:index')
        return render(request, self.template_name, {'form': form})


class LogoutView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'

    def get(self, request):
        logout(request)
        return render(request, 'registration/logged_out.html')


class IndexView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    template_name = 'chat/index.html'
    redirect_field_name = 'next'

    def get(self, request):
        user_groups = GroupChat.objects.filter(
            members=request.user
        ).prefetch_related('members').order_by('-created_at')

        return render(request, self.template_name, {
            'groups': user_groups,
            'user': request.user
        })


class CreateChatView(View):
    def post(self, request):

        group_name = request.POST.get('name', '').strip()

        if not group_name:
            messages.error(request, 'Group name cannot be empty.', extra_tags='chat')
            return redirect('chat:index')

        try:
            group = GroupChat.objects.create(
                title=group_name,
                creator=request.user
            )
            Member.objects.create(user=request.user, group=group)

            messages.success(request, f'Group "{group.title}" created successfully.', extra_tags='chat')
            return redirect('chat:index')

        except Exception as e:
            messages.error(request, f'Error creating group: {str(e)}', extra_tags='chat')
            return redirect('chat:index')


class JoinChatView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'

    def get(self, request, chat_id):
        group = get_object_or_404(GroupChat, unique_id=chat_id)

        is_member = Member.objects.filter(user=request.user, group=group).exists()

        if is_member:
            messages.info(request, f'You are already a member of the group "{group.title}".')
            return render(request, 'chat/join_chat.html', {
                'group': group,
                'already_member': True
            })

        Member.objects.create(user=request.user, group=group)

        async_to_sync(channel_layer.group_send)(
            f'chat_{group.unique_id}',
            {
                'type': 'system_message',
                'message': f'{request.user.username} joined the group.'
            }
        )
        messages.success(request, f'You have successfully joined the group "{group.title}".', extra_tags='chat')

        return render(request, 'chat/join_chat.html', {
            'group': group,
            'already_member': False
        })


class ChatRoomView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'

    def get(self, request, chat_id):
        try:
            group = GroupChat.objects.get(unique_id=chat_id)

            if not group.members.filter(id=request.user.id).exists():
                messages.error(request, 'You do not have access to this group.')
                return redirect('chat:index')

            member = Member.objects.get(user=request.user, group=group)

            chat_messages = group.messages.all().filter(timestamp__gte=member.created_at).order_by('timestamp')
            context = {
                'group': group,
                'chat_messages': chat_messages,
                'online_users': group.members.all(),
                'join_link': request.build_absolute_uri(reverse('chat:join_chat', args=[chat_id])),
                'is_creator': group.creator == request.user,
            }
            return render(request, 'chat/chat_room.html', context)

        except GroupChat.DoesNotExist:
            messages.error(request, 'Group not found.')
            return redirect('chat:index')

        except Member.DoesNotExist:
            messages.error(request, 'You are not a member of this group.')
            return redirect('chat:index')


class LeaveChatView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'

    def post(self, request, chat_id):
        group = get_object_or_404(GroupChat, unique_id=chat_id)
        member = Member.objects.get(user=request.user, group=group)
        is_creator = group.creator == request.user

        system_message = Message.objects.create(
            group=group,
            message=f'{request.user.username} left the group.',
            is_system_message=True
        )

        async_to_sync(channel_layer.group_send)(
            f'chat_{group.unique_id}',
            {
                'type': 'system_message',
                'message': system_message.message,
                'message_id': system_message.id
            }
        )

        if is_creator:
            group.delete()
            messages.success(request, 'Group deleted successfully.')
        else:
            member.delete()
            messages.success(request, 'You have successfully left the group.')

        return redirect('chat:index')
