from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Count, Max
from .models import ChatRoom, Message, UserProfile, MessageReadStatus, Notification
from .forms import RegisterForm, ProfileUpdateForm, GroupChatForm
import json


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            UserProfile.objects.update_or_create(user=user, defaults={'is_online': True})
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        UserProfile.objects.filter(user=request.user).update(
            is_online=False, last_seen=timezone.now()
        )
    logout(request)
    return redirect('login')


@login_required
def home_view(request):
    user = request.user
    rooms = user.chat_rooms.all().order_by('-messages__timestamp').distinct()

    rooms_data = []
    for room in rooms:
        last_msg = room.get_last_message()
        unread = room.unread_count(user)
        if room.room_type == 'private':
            other = room.members.exclude(id=user.id).first()
            name = other.get_full_name() or other.username if other else 'Unknown'
            profile = getattr(other, 'profile', None) if other else None
            avatar = profile.avatar.url if profile and profile.avatar else None
            is_online = profile.is_online if profile else False
        else:
            name = room.name
            avatar = room.avatar.url if room.avatar else None
            is_online = False

        rooms_data.append({
            'room': room,
            'name': name,
            'avatar': avatar,
            'is_online': is_online,
            'last_message': last_msg,
            'unread_count': unread,
        })

    users = User.objects.exclude(id=user.id).select_related('profile')
    notifications = Notification.objects.filter(user=user, is_read=False).count()

    return render(request, 'chat/home.html', {
        'rooms_data': rooms_data,
        'users': users,
        'notifications': notifications,
    })


@login_required
def room_view(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id, members=request.user)
    messages = room.messages.select_related('sender', 'sender__profile').order_by('timestamp')

    # Mark room as read
    MessageReadStatus.objects.update_or_create(room=room, user=request.user)

    # Room display info
    if room.room_type == 'private':
        other = room.members.exclude(id=request.user.id).first()
        room_name = other.get_full_name() or other.username if other else 'Unknown'
        profile = getattr(other, 'profile', None) if other else None
        room_avatar = profile.avatar.url if profile and profile.avatar else None
        other_user_online = profile.is_online if profile else False
        last_seen = profile.last_seen if profile else None
    else:
        room_name = room.name
        room_avatar = room.avatar.url if room.avatar else None
        other_user_online = False
        last_seen = None

    # Load all rooms for sidebar
    user = request.user
    all_rooms = user.chat_rooms.all().order_by('-messages__timestamp').distinct()
    rooms_data = []
    for r in all_rooms:
        last_msg = r.get_last_message()
        unread = r.unread_count(user)
        if r.room_type == 'private':
            other_member = r.members.exclude(id=user.id).first()
            name = other_member.get_full_name() or other_member.username if other_member else 'Unknown'
            prof = getattr(other_member, 'profile', None) if other_member else None
            avatar = prof.avatar.url if prof and prof.avatar else None
            is_online = prof.is_online if prof else False
        else:
            name = r.name
            avatar = r.avatar.url if r.avatar else None
            is_online = False
        rooms_data.append({
            'room': r,
            'name': name,
            'avatar': avatar,
            'is_online': is_online,
            'last_message': last_msg,
            'unread_count': unread,
            'active': r.id == room.id,
        })

    users = User.objects.exclude(id=user.id).select_related('profile')
    notifications = Notification.objects.filter(user=user, is_read=False).count()

    return render(request, 'chat/room.html', {
        'room': room,
        'room_name': room_name,
        'room_avatar': room_avatar,
        'other_user_online': other_user_online,
        'last_seen': last_seen,
        'messages': messages,
        'rooms_data': rooms_data,
        'users': users,
        'notifications': notifications,
        'members': room.members.select_related('profile').all(),
    })


@login_required
def start_private_chat(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    if other_user == request.user:
        return redirect('home')
    room, created = ChatRoom.get_or_create_private_room(request.user, other_user)
    return redirect('room', room_id=room.id)


@login_required
def create_group_view(request):
    if request.method == 'POST':
        form = GroupChatForm(request.POST, request.FILES, current_user=request.user)
        if form.is_valid():
            room = form.save(commit=False)
            room.room_type = 'group'
            room.created_by = request.user
            room.save()
            form.save_m2m()
            room.members.add(request.user)
            return redirect('room', room_id=room.id)
    else:
        form = GroupChatForm(current_user=request.user)
    return render(request, 'chat/create_group.html', {'form': form})


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            request.user.first_name = form.cleaned_data.get('first_name', '')
            request.user.last_name = form.cleaned_data.get('last_name', '')
            request.user.save()
            form.save()
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=profile)
    return render(request, 'chat/profile.html', {'form': form, 'profile': profile})


@login_required
def api_notifications(request):
    notifs = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': notifs})


@login_required
def api_mark_notifications_read(request):
    Notification.objects.filter(user=request.user).update(is_read=True)
    return JsonResponse({'status': 'ok'})


@login_required
def api_user_status(request, user_id):
    try:
        profile = UserProfile.objects.get(user_id=user_id)
        return JsonResponse({
            'is_online': profile.is_online,
            'last_seen': profile.last_seen.isoformat(),
        })
    except UserProfile.DoesNotExist:
        return JsonResponse({'is_online': False, 'last_seen': None})


@login_required
def api_search_users(request):
    q = request.GET.get('q', '')
    if len(q) < 2:
        return JsonResponse({'users': []})
    users = User.objects.filter(
        Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
    ).exclude(id=request.user.id)[:10]
    data = [{'id': u.id, 'username': u.username, 'name': u.get_full_name() or u.username} for u in users]
    return JsonResponse({'users': data})
