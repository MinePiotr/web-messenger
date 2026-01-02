import httpx
import json
import websockets
import asyncio
import threading
from datetime import datetime


class VercelMessenger:
    def __init__(self, config_file='config.json'):
        with open(config_file, 'r') as f:
            config = json.load(f)

        self.api_url = config.get('api_url', 'https://messenger-api.vercel.app/api')
        self.ws_url = config.get('ws_url', 'wss://messenger-ws.vercel.app')
        self.current_user = None
        self.ws = None
        self.running = False
        self.message_callbacks = []

        print(f"✅ Клиент инициализирован. Сервер: {self.api_url}")

    # ==================== РЕГИСТРАЦИЯ И ВХОД ====================

    def register(self, phone, nickname, password="123"):
        """Регистрация нового пользователя"""
        try:
            response = httpx.post(
                f"{self.api_url}/register",
                json={
                    "phone": phone,
                    "nickname": nickname,
                    "password": password
                },
                timeout=10
            )

            if response.status_code == 200:
                self.current_user = phone
                print(f"✅ Пользователь {nickname} ({phone}) зарегистрирован")
                return True
            else:
                print(f"❌ Ошибка: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False

    def login(self, phone, password="123"):
        """Вход существующего пользователя"""
        try:
            response = httpx.get(
                f"{self.api_url}/user/{phone}",
                timeout=10
            )

            if response.status_code == 200:
                self.current_user = phone
                print(f"✅ Вход выполнен: {phone}")
                return True
            else:
                print("❌ Пользователь не найден")
                return False

        except Exception as e:
            print(f"❌ Ошибка входа: {e}")
            return False

    # ==================== РАБОТА С КОНТАКТАМИ ====================

    def search_users(self, query=""):
        """Поиск пользователей по номеру или имени"""
        try:
            response = httpx.get(
                f"{self.api_url}/users",
                params={"search": query} if query else {},
                timeout=10
            )

            if response.status_code == 200:
                users = response.json()
                # Исключаем текущего пользователя
                return [u for u in users if u.get('phone') != self.current_user]
            return []

        except Exception as e:
            print(f"❌ Ошибка поиска: {e}")
            return []

    def add_contact(self, contact_phone):
        """Добавление контакта"""
        try:
            response = httpx.post(
                f"{self.api_url}/contacts",
                json={
                    "user_phone": self.current_user,
                    "contact_phone": contact_phone
                },
                timeout=10
            )
            return response.status_code == 200
        except:
            return False

    def get_contacts(self):
        """Получение списка контактов"""
        try:
            response = httpx.get(
                f"{self.api_url}/contacts/{self.current_user}",
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []

    # ==================== СООБЩЕНИЯ ====================

    def send_message(self, receiver, text):
        """Отправка сообщения"""
        if not self.current_user:
            return False

        try:
            response = httpx.post(
                f"{self.api_url}/send",
                json={
                    "sender": self.current_user,
                    "receiver": receiver,
                    "text": text,
                    "timestamp": datetime.now().isoformat()
                },
                timeout=10
            )

            if response.status_code == 200:
                print(f"📨 Отправлено: {self.current_user} -> {receiver}")
                return True
            return False

        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")
            return False

    def get_messages(self, contact_phone, limit=100):
        """Получение истории переписки"""
        try:
            response = httpx.get(
                f"{self.api_url}/messages",
                params={
                    "user1": self.current_user,
                    "user2": contact_phone,
                    "limit": limit
                },
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            return []

        except Exception as e:
            print(f"❌ Ошибка получения сообщений: {e}")
            return []

    # ==================== REAL-TIME WEBSOCKET ====================

    def start_realtime(self, on_message_callback):
        """Запуск реаль-тайм соединения"""
        if not self.current_user:
            return False

        self.message_callbacks.append(on_message_callback)
        self.running = True

        thread = threading.Thread(
            target=self._run_websocket,
            daemon=True
        )
        thread.start()
        return True

    def _run_websocket(self):
        """Запуск WebSocket в отдельном потоке"""

        async def connect():
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    self.ws = websocket

                    # Регистрируемся на сервере
                    await websocket.send(json.dumps({
                        "type": "register",
                        "phone": self.current_user
                    }))

                    print("✅ WebSocket подключен. Ожидание сообщений...")

                    # Слушаем сообщения
                    while self.running:
                        try:
                            message = await websocket.recv()
                            data = json.loads(message)

                            # Вызываем все callback'и
                            for callback in self.message_callbacks:
                                callback(data)

                        except websockets.exceptions.ConnectionClosed:
                            print("❌ WebSocket соединение закрыто")
                            break
                        except Exception as e:
                            print(f"⚠️ Ошибка получения: {e}")
                            continue

            except Exception as e:
                print(f"❌ WebSocket ошибка подключения: {e}")

        asyncio.run(connect())

    def stop_realtime(self):
        """Остановка реаль-тайм соединения"""
        self.running = False
        if self.ws:
            asyncio.run(self.ws.close())
        print("🔇 WebSocket остановлен")