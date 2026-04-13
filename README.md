# ⚡ NexusChat — Real-Time Chat Application

A production-ready, full-featured real-time chat application built with Django, Django Channels, WebSockets, and Docker.

---

## ✨ Features

| Feature | Status |
|---|---|
| User Registration & Login | ✅ |
| Real-time Messaging (WebSockets) | ✅ |
| Private Chats (User to User) | ✅ |
| Group Chats (Rooms) | ✅ |
| Online / Offline Status | ✅ |
| Typing Indicators | ✅ |
| Last Seen Timestamps | ✅ |
| Unread Message Badges | ✅ |
| File & Image Sharing | ✅ |
| Message Timestamps | ✅ |
| User Profile & Avatars | ✅ |
| Modern WhatsApp-style UI | ✅ |
| Docker + Docker Compose | ✅ |
| Render Deployment Ready | ✅ |

---

## 🛠 Tech Stack

- **Backend:** Django 4.2
- **Real-time:** Django Channels 4 + WebSockets
- **Channel Layer:** Redis (via channels-redis)
- **Database:** SQLite (swap to PostgreSQL for prod)
- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **Server:** Daphne (ASGI)
- **Container:** Docker + Docker Compose

---

## 🚀 Quick Start (Docker)

### Prerequisites
- Docker & Docker Compose installed

### 1. Clone / unzip the project
```bash
cd nexuschat
```

### 2. Start the application
```bash
docker-compose up --build
```

### 3. Open in browser
```
http://localhost:8000
```

### 4. Create a superuser (optional)
```bash
docker-compose exec web python manage.py createsuperuser
```

---

## 💻 Local Development (Without Docker)

### Prerequisites
- Python 3.11+
- Redis running locally (`redis-server`)

### 1. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set environment variables
```bash
cp .env.example .env
# Edit .env with your values
```

### 4. Run migrations
```bash
python manage.py migrate
```

### 5. Collect static files
```bash
python manage.py collectstatic --noinput
```

### 6. Start Daphne (ASGI server)
```bash
daphne -b 0.0.0.0 -p 8000 nexuschat.asgi:application
```

---

## 🌐 Deploy on Render

### Option A: Using render.yaml (Blueprint)
1. Push code to GitHub
2. Go to [render.com](https://render.com) → New → Blueprint
3. Connect your GitHub repo
4. Render will auto-detect `render.yaml` and deploy both the web service and Redis

### Option B: Manual
1. Create a **Redis** service on Render (Free plan)
2. Create a **Web Service** on Render:
   - Environment: Docker
   - Build Command: (auto from Dockerfile)
   - Add env vars:
     - `SECRET_KEY` → generate a secure random string
     - `REDIS_URL` → your Redis internal URL from step 1
     - `DEBUG` → `False`
     - `ALLOWED_HOSTS` → your render domain

---

## 📁 Project Structure

```
nexuschat/
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── requirements.txt
├── manage.py
├── .env.example
├── nexuschat/              # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── asgi.py             # ASGI + Channels routing
├── chat/                   # Main chat app
│   ├── models.py           # User, ChatRoom, Message, etc.
│   ├── consumers.py        # WebSocket consumers
│   ├── routing.py          # WS URL routing
│   ├── views.py
│   ├── urls.py
│   └── forms.py
├── templates/
│   ├── base.html
│   ├── registration/
│   │   ├── login.html
│   │   └── register.html
│   └── chat/
│       ├── home.html       # Main layout (no room)
│       ├── room.html       # Active chat view
│       ├── profile.html
│       └── create_group.html
└── static/
    ├── css/main.css        # Full design system
    └── js/
        ├── main.js
        └── chat.js         # WebSocket client
```

---

## 🗄 Database Models

| Model | Description |
|---|---|
| `UserProfile` | Extends User with avatar, bio, online status, last seen |
| `ChatRoom` | Private or group chat room with members |
| `Message` | Text, image, or file message linked to a room |
| `MessageReadStatus` | Tracks last read position per user per room |
| `Notification` | Unread message notifications |

---

## ⚙️ WebSocket Events

| Event | Direction | Description |
|---|---|---|
| `chat_message` | Server → Client | New message broadcast |
| `typing_indicator` | Server → Client | User is/stopped typing |
| `presence_update` | Server → Client | User online/offline |
| `chat_message` | Client → Server | Send a text message |
| `file_message` | Client → Server | Send a file/image |
| `typing` | Client → Server | Typing state update |
| `read_receipt` | Client → Server | Mark room as read |

---

## 🔒 Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Set a strong `SECRET_KEY`
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Use PostgreSQL instead of SQLite
- [ ] Use a persistent Redis (not free tier for prod)
- [ ] Set up SSL/HTTPS (Render handles this)
- [ ] Configure proper media storage (e.g. AWS S3)

---

## 📝 License

MIT — free to use and modify.
