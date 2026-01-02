from http.server import BaseHTTPRequestHandler
import json
import sqlite3
import hashlib
from datetime import datetime

# Простая "база данных" в памяти
users_db = {}
messages_db = []
contacts_db = {}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Обработка GET запросов"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        path = self.path

        if path.startswith('/api/user/'):
            phone = path.split('/')[-1]
            user = users_db.get(phone)
            if user:
                self.wfile.write(json.dumps(user).encode())
            else:
                self.wfile.write(json.dumps({"error": "User not found"}).encode())

        elif path.startswith('/api/users'):
            query = self.path.split('?')[-1] if '?' in self.path else ''
            search = None
            if 'search=' in query:
                search = query.split('search=')[-1].split('&')[0]

            result = []
            for phone, user in users_db.items():
                if not search or search in phone or search in user.get('nickname', ''):
                    result.append({"phone": phone, "nickname": user.get('nickname', '')})

            self.wfile.write(json.dumps(result).encode())

        elif path.startswith('/api/contacts/'):
            user_phone = path.split('/')[-1]
            user_contacts = contacts_db.get(user_phone, [])

            contacts_info = []
            for contact_phone in user_contacts:
                if contact_phone in users_db:
                    contacts_info.append({
                        "phone": contact_phone,
                        "nickname": users_db[contact_phone].get('nickname', '')
                    })

            self.wfile.write(json.dumps(contacts_info).encode())

        elif path.startswith('/api/messages'):
            query = self.path.split('?')[-1] if '?' in self.path else ''
            params = {}
            if query:
                for param in query.split('&'):
                    if '=' in param:
                        key, value = param.split('=')
                        params[key] = value

            user1 = params.get('user1', '')
            user2 = params.get('user2', '')

            relevant_messages = []
            for msg in messages_db:
                if (msg['sender'] == user1 and msg['receiver'] == user2) or \
                        (msg['sender'] == user2 and msg['receiver'] == user1):
                    relevant_messages.append(msg)

            self.wfile.write(json.dumps(relevant_messages).encode())

    def do_POST(self):
        """Обработка POST запросов"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode())

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        path = self.path

        if path == '/api/register':
            phone = data.get('phone', '')
            nickname = data.get('nickname', '')

            if phone and nickname:
                users_db[phone] = {
                    "phone": phone,
                    "nickname": nickname,
                    "password": data.get('password', ''),
                    "registered_at": datetime.now().isoformat()
                }
                self.wfile.write(json.dumps({"status": "success", "phone": phone}).encode())
            else:
                self.wfile.write(json.dumps({"error": "Invalid data"}).encode())

        elif path == '/api/send':
            sender = data.get('sender', '')
            receiver = data.get('receiver', '')
            text = data.get('text', '')

            if sender and receiver and text:
                message = {
                    "id": len(messages_db) + 1,
                    "sender": sender,
                    "receiver": receiver,
                    "text": text,
                    "timestamp": data.get('timestamp', datetime.now().isoformat())
                }
                messages_db.append(message)
                self.wfile.write(json.dumps({"status": "sent", "id": message["id"]}).encode())
            else:
                self.wfile.write(json.dumps({"error": "Invalid message"}).encode())

        elif path == '/api/contacts':
            user_phone = data.get('user_phone', '')
            contact_phone = data.get('contact_phone', '')

            if user_phone and contact_phone:
                if user_phone not in contacts_db:
                    contacts_db[user_phone] = []

                if contact_phone not in contacts_db[user_phone]:
                    contacts_db[user_phone].append(contact_phone)

                # Симметричное добавление
                if contact_phone not in contacts_db:
                    contacts_db[contact_phone] = []
                if user_phone not in contacts_db[contact_phone]:
                    contacts_db[contact_phone].append(user_phone)

                self.wfile.write(json.dumps({"status": "added"}).encode())
            else:
                self.wfile.write(json.dumps({"error": "Invalid data"}).encode())

    def do_OPTIONS(self):
        """Обработка CORS preflight запросов"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()