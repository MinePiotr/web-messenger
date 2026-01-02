import sqlite3
import hashlib
from datetime import datetime


class Database:
    def __init__(self, db_name='messenger.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Пользователи
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE NOT NULL,
                nickname TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Контакты (кто кого добавил)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                user_phone TEXT NOT NULL,
                contact_phone TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_phone, contact_phone)
            )
        ''')

        # Сообщения
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_phone TEXT NOT NULL,
                receiver_phone TEXT NOT NULL,
                message TEXT NOT NULL,
                is_delivered INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def register_user(self, phone, nickname, password):
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            self.cursor.execute(
                "INSERT INTO users (phone, nickname, password_hash) VALUES (?, ?, ?)",
                (phone, nickname, password_hash)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Номер уже существует

    def authenticate_user(self, phone, password):
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        self.cursor.execute(
            "SELECT nickname FROM users WHERE phone=? AND password_hash=?",
            (phone, password_hash)
        )
        result = self.cursor.fetchone()
        return result[0] if result else None

    def search_users(self, query, exclude_phone=None):
        query = f"%{query}%"
        sql = """
            SELECT phone, nickname 
            FROM users 
            WHERE (phone LIKE ? OR nickname LIKE ?) 
            AND phone != ?
            LIMIT 20
        """
        self.cursor.execute(sql, (query, query, exclude_phone or ""))
        return self.cursor.fetchall()

    def add_contact(self, user_phone, contact_phone):
        try:
            # Добавляем в обе стороны автоматически
            self.cursor.execute(
                "INSERT OR IGNORE INTO contacts (user_phone, contact_phone) VALUES (?, ?)",
                (user_phone, contact_phone)
            )
            # Добавляем обратную связь (симметрично)
            self.cursor.execute(
                "INSERT OR IGNORE INTO contacts (user_phone, contact_phone) VALUES (?, ?)",
                (contact_phone, user_phone)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка при добавлении контакта: {e}")
            return False
    def get_contacts(self, user_phone):
        self.cursor.execute('''
            SELECT u.phone, u.nickname, 
                   (SELECT COUNT(*) FROM messages 
                    WHERE receiver_phone=? AND sender_phone=u.phone AND is_delivered=0) as unread
            FROM contacts c
            JOIN users u ON c.contact_phone = u.phone
            WHERE c.user_phone=?
            ORDER BY u.nickname
        ''', (user_phone, user_phone))
        return self.cursor.fetchall()

    def save_message(self, sender_phone, receiver_phone, message):
        self.cursor.execute('''
            INSERT INTO messages (sender_phone, receiver_phone, message) 
            VALUES (?, ?, ?)
        ''', (sender_phone, receiver_phone, message))
        self.conn.commit()
        return self.cursor.lastrowid  # Возвращаем ID сообщения

    def get_messages(self, user_phone, contact_phone, limit=100):
        self.cursor.execute('''
            SELECT sender_phone, message, timestamp 
            FROM messages 
            WHERE (sender_phone=? AND receiver_phone=?) 
               OR (sender_phone=? AND receiver_phone=?)
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (user_phone, contact_phone, contact_phone, user_phone, limit))

        messages = self.cursor.fetchall()
        # Помечаем как доставленные
        self.cursor.execute('''
            UPDATE messages 
            SET is_delivered=1 
            WHERE sender_phone=? AND receiver_phone=? AND is_delivered=0
        ''', (contact_phone, user_phone))
        self.conn.commit()

        return messages[::-1]  # Возвращаем в хронологическом порядке

    def get_user_info(self, phone):
        self.cursor.execute(
            "SELECT phone, nickname FROM users WHERE phone=?",
            (phone,)
        )
        return self.cursor.fetchone()

    def get_users_with_contact(self, contact_phone):
        """Получаем всех пользователей, у которых есть данный контакт"""
        self.cursor.execute(
            "SELECT user_phone FROM contacts WHERE contact_phone = ?",
            (contact_phone,)
        )
        return [row[0] for row in self.cursor.fetchall()]