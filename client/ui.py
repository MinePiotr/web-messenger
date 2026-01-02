import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import socket
import threading
from datetime import datetime


def get_server_config():
    """Получает конфигурацию сервера с возможностью выбора"""
    import json
    import os

    if not os.path.exists('config.json'):
        # Создаём конфиг по умолчанию
        default_config = {
            "host": "127.0.0.1",
            "port": 55555,
            "buffer_size": 4096
        }
        with open('config.json', 'w') as f:
            json.dump(default_config, f)
        return default_config

    with open('config.json', 'r') as f:
        config = json.load(f)

    return config


class MessengerUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Messenger")
        self.root.geometry("900x600")

        self.current_user = None
        self.current_phone = None
        self.socket = None
        self.receive_thread = None

        self.setup_styles()
        self.show_login_window()

    def handle_message_from_new_contact(self, sender_phone, text, timestamp):
        """Обработка сообщения от пользователя, которого нет в контактах"""
        from client.database import Database
        db = Database()

        # Получаем информацию об отправителе
        sender_info = db.get_user_info(sender_phone)
        if not sender_info:
            return

        sender_nick = sender_info[1]

        # Автоматически добавляем отправителя в контакты (двусторонне)
        db.add_contact(self.current_phone, sender_phone)

        # Показываем уведомление
        notification = f"Новое сообщение от {sender_nick} ({sender_phone}): {text}"

        # Создаем всплывающее уведомление
        if not hasattr(self, 'notification_window'):
            self.notification_window = None

        def show_notification():
            if self.notification_window and self.notification_window.winfo_exists():
                self.notification_window.destroy()

            self.notification_window = tk.Toplevel(self.root)
            self.notification_window.title("Новое сообщение")
            self.notification_window.geometry("400x100+100+100")
            self.notification_window.attributes('-topmost', True)

            msg = f"💬 {sender_nick}:\n{text}"
            label = ttk.Label(self.notification_window, text=msg, wraplength=350, padding=10)
            label.pack(expand=True, fill=tk.BOTH)

            def close_and_open_chat():
                self.notification_window.destroy()
                # Обновляем контакты и открываем чат
                self.load_contacts()
                # Находим и выбираем этого пользователя в списке
                for i in range(self.contacts_listbox.size()):
                    if sender_phone in self.contacts_listbox.get(i):
                        self.contacts_listbox.selection_clear(0, tk.END)
                        self.contacts_listbox.selection_set(i)
                        self.contacts_listbox.see(i)
                        self.on_contact_select(None)
                        break

            ttk.Button(self.notification_window, text="Открыть чат",
                       command=close_and_open_chat).pack(pady=(0, 10))

            # Автоматическое закрытие через 10 секунд
            self.notification_window.after(10000, self.notification_window.destroy)

        # Показываем уведомление в основном потоке
        self.root.after(0, show_notification)

        # Обновляем список контактов
        self.root.after(0, self.load_contacts)

    def setup_styles(self):
        style = ttk.Style()
        style.configure("TButton", padding=6, font=('Arial', 10))
        style.configure("TLabel", font=('Arial', 10))
        style.configure("TEntry", font=('Arial', 10))

    def show_login_window(self):
        self.clear_window()

        # Фрейм для логина
        login_frame = ttk.Frame(self.root, padding=40)
        login_frame.pack(expand=True)

        ttk.Label(login_frame, text="Simple Messenger", font=('Arial', 20, 'bold')).grid(row=0, column=0, columnspan=2,
                                                                                         pady=(0, 30))

        # Регистрация
        ttk.Label(login_frame, text="РЕГИСТРАЦИЯ", font=('Arial', 12, 'bold')).grid(row=1, column=0, columnspan=2,
                                                                                    pady=(10, 5))

        ttk.Label(login_frame, text="Номер телефона:").grid(row=2, column=0, sticky='e', pady=5)
        self.reg_phone = ttk.Entry(login_frame, width=25)
        self.reg_phone.grid(row=2, column=1, pady=5, padx=(10, 0))

        ttk.Label(login_frame, text="Никнейм:").grid(row=3, column=0, sticky='e', pady=5)
        self.reg_nick = ttk.Entry(login_frame, width=25)
        self.reg_nick.grid(row=3, column=1, pady=5, padx=(10, 0))

        ttk.Label(login_frame, text="Пароль:").grid(row=4, column=0, sticky='e', pady=5)
        self.reg_pass = ttk.Entry(login_frame, width=25, show="*")
        self.reg_pass.grid(row=4, column=1, pady=5, padx=(10, 0))

        ttk.Button(login_frame, text="Зарегистрироваться",
                   command=self.do_register).grid(row=5, column=0, columnspan=2, pady=15)

        # Разделитель
        ttk.Separator(login_frame, orient='horizontal').grid(row=6, column=0, columnspan=2, pady=20, sticky='ew')

        # Вход
        ttk.Label(login_frame, text="ВХОД", font=('Arial', 12, 'bold')).grid(row=7, column=0, columnspan=2,
                                                                             pady=(5, 10))

        ttk.Label(login_frame, text="Номер телефона:").grid(row=8, column=0, sticky='e', pady=5)
        self.login_phone = ttk.Entry(login_frame, width=25)
        self.login_phone.grid(row=8, column=1, pady=5, padx=(10, 0))

        ttk.Label(login_frame, text="Пароль:").grid(row=9, column=0, sticky='e', pady=5)
        self.login_pass = ttk.Entry(login_frame, width=25, show="*")
        self.login_pass.grid(row=9, column=1, pady=5, padx=(10, 0))

        ttk.Button(login_frame, text="Войти",
                   command=self.do_login).grid(row=10, column=0, columnspan=2, pady=15)

    def do_register(self):
        from client.database import Database
        db = Database()

        phone = self.reg_phone.get().strip()
        nick = self.reg_nick.get().strip()
        password = self.reg_pass.get().strip()

        if not phone or not nick or not password:
            messagebox.showerror("Ошибка", "Все поля обязательны!")
            return

        if db.register_user(phone, nick, password):
            messagebox.showinfo("Успех", "Регистрация успешна! Теперь войдите.")
            self.login_phone.delete(0, tk.END)
            self.login_phone.insert(0, phone)
            self.login_pass.focus()
        else:
            messagebox.showerror("Ошибка", "Номер телефона уже занят!")

    def do_login(self):
        from client.database import Database
        db = Database()

        phone = self.login_phone.get().strip()
        password = self.login_pass.get().strip()

        if not phone or not password:
            messagebox.showerror("Ошибка", "Введите номер и пароль!")
            return

        nickname = db.authenticate_user(phone, password)
        if nickname:
            self.current_user = nickname
            self.current_phone = phone
            self.connect_to_server()
            self.show_main_window()
        else:
            messagebox.showerror("Ошибка", "Неверный номер или пароль!")

    def connect_to_server(self):
        try:
            # Получаем конфигурацию
            config = get_server_config()
            server_host = config['host']
            server_port = config['port']

            print(f"Подключение к серверу {server_host}:{server_port}...")

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)  # Таймаут 5 секунд
            self.socket.connect((server_host, server_port))

            # Регистрируемся на сервере
            reg_msg = json.dumps({
                'type': 'register',
                'phone': self.current_phone
            })
            self.socket.send(reg_msg.encode('utf-8'))

            # Запускаем поток для приема сообщений
            self.receive_thread = threading.Thread(
                target=self.receive_messages,
                daemon=True
            )
            self.receive_thread.start()

            print("Успешно подключено к серверу")

        except socket.timeout:
            messagebox.showerror("Ошибка", "Таймаут подключения к серверу!")
            return False
        except ConnectionRefusedError:
            messagebox.showerror("Ошибка", "Сервер недоступен!")
            return False
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка подключения: {str(e)}")
            return False

        return True
    def receive_messages(self):
        while True:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break

                message = json.loads(data.decode('utf-8'))

                if message['type'] == 'new_message':
                    sender = message['sender']
                    text = message['text']
                    timestamp = message.get('timestamp', '')

                    # Проверяем, не отправляли ли мы это сообщение сами
                    if sender == self.current_phone:
                        # Это эхо от нашего же сообщения - пропускаем
                        continue

                    # Проверяем, есть ли отправитель в наших контактах
                    from client.database import Database
                    db = Database()
                    contacts = db.get_contacts(self.current_phone)
                    contact_phones = [c[0] for c in contacts] if contacts else []

                    if sender in contact_phones:
                        # От знакомого контакта
                        self.root.after(0, self.display_received_message, sender, text, timestamp)
                    else:
                        # От нового пользователя
                        self.root.after(0, self.handle_message_from_new_contact, sender, text, timestamp)

                elif message['type'] == 'message_sent':
                    # Подтверждение отправки - можно добавить отметку "доставлено"
                    receiver = message.get('receiver')
                    # Здесь можно обновить статус сообщения в UI (галочку)
                    pass

            except json.JSONDecodeError:
                print("Ошибка декодирования JSON")
            except Exception as e:
                print(f"Ошибка в receive_messages: {e}")
                break

    def show_main_window(self):
        self.clear_window()

        # Разделение на две части
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Левая панель - контакты
        left_frame = ttk.Frame(main_paned, width=250)
        main_paned.add(left_frame, weight=1)

        # Заголовок с информацией о пользователе
        user_frame = ttk.Frame(left_frame)
        user_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(user_frame, text=f"Вы: {self.current_user}",
                  font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Label(user_frame, text=f"({self.current_phone})",
                  font=('Arial', 9)).pack(side=tk.LEFT, padx=(5, 0))

        # Кнопка поиска
        ttk.Button(left_frame, text="Найти пользователя",
                   command=self.search_user).pack(fill=tk.X, padx=5, pady=(10, 5))

        # Список контактов
        ttk.Label(left_frame, text="Контакты:", font=('Arial', 11, 'bold')).pack(anchor='w', padx=5, pady=(15, 5))

        self.contacts_listbox = tk.Listbox(left_frame, font=('Arial', 10))
        self.contacts_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 10))
        self.contacts_listbox.bind('<<ListboxSelect>>', self.on_contact_select)

        # Загрузка контактов
        self.load_contacts()

        # Правая панель - чат
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=3)

        # Заголовок чата
        self.chat_header = ttk.Label(right_frame, text="Выберите контакт",
                                     font=('Arial', 12, 'bold'), background='#f0f0f0')
        self.chat_header.pack(fill=tk.X, padx=10, pady=10)

        # Область сообщений
        self.chat_frame = tk.Frame(right_frame)
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Полоса прокрутки
        chat_scrollbar = ttk.Scrollbar(self.chat_frame)
        chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.chat_text = tk.Text(self.chat_frame, font=('Arial', 10),
                                 yscrollcommand=chat_scrollbar.set, state=tk.DISABLED,
                                 wrap=tk.WORD)
        self.chat_text.pack(fill=tk.BOTH, expand=True)
        chat_scrollbar.config(command=self.chat_text.yview)

        # Панель ввода сообщения
        input_frame = ttk.Frame(right_frame)
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.message_entry = ttk.Entry(input_frame, font=('Arial', 10))
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.message_entry.bind('<Return>', lambda e: self.send_message())

        ttk.Button(input_frame, text="Отправить",
                   command=self.send_message).pack(side=tk.RIGHT)

        # Выбранный контакт
        self.selected_contact = None

    def load_contacts(self):
        from client.database import Database
        db = Database()

        self.contacts_listbox.delete(0, tk.END)
        contacts = db.get_contacts(self.current_phone)

        if not contacts:
            self.contacts_listbox.insert(tk.END, "Контактов пока нет")
            self.contacts_listbox.itemconfig(0, fg='gray')
            return

        for phone, nickname, unread in contacts:
            display = f"📱 {nickname}"
            if unread > 0:
                display += f" ● {unread}"
            self.contacts_listbox.insert(tk.END, display)

            # Сохраняем телефон в дополнительном атрибуте
            self.contacts_listbox.itemconfig(tk.END, {'bg': '#f0f8ff' if unread > 0 else 'white'})
    def search_user(self):
        query = simpledialog.askstring("Поиск", "Введите номер телефона или никнейм:")
        if not query:
            return

        from client.database import Database
        db = Database()

        results = db.search_users(query, self.current_phone)

        if not results:
            messagebox.showinfo("Результат", "Пользователи не найдены")
            return

        # Окно с результатами
        result_win = tk.Toplevel(self.root)
        result_win.title("Результаты поиска")
        result_win.geometry("400x300")

        listbox = tk.Listbox(result_win, font=('Arial', 10))
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Храним связь между элементами списка и номерами телефонов
        self.search_results_map = {}

        for i, (phone, nickname) in enumerate(results):
            display_text = f"{nickname} ({phone})"
            listbox.insert(tk.END, display_text)
            self.search_results_map[i] = phone

        def add_selected():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Выбор", "Выберите пользователя из списка!")
                return

            index = selection[0]
            phone = self.search_results_map.get(index)

            if not phone:
                messagebox.showerror("Ошибка", "Не удалось определить номер телефона")
                return

            # Проверяем, не добавлен ли уже этот контакт
            from client.database import Database
            db = Database()

            # Проверка через БД
            contacts = db.get_contacts(self.current_phone)
            existing_phones = [c[0] for c in contacts]  # phone находится в позиции 0

            if phone in existing_phones:
                messagebox.showinfo("Информация", "Этот пользователь уже у вас в контактах!")
                return

            if phone == self.current_phone:
                messagebox.showwarning("Предупреждение", "Нельзя добавить самого себя!")
                return

            # Добавляем контакт
            if db.add_contact(self.current_phone, phone):
                self.load_contacts()
                result_win.destroy()
                messagebox.showinfo("Успех", "Контакт успешно добавлен!")

                # Обновляем список контактов
                self.load_contacts()

                # Автоматически выбираем добавленный контакт
                for i in range(self.contacts_listbox.size()):
                    item = self.contacts_listbox.get(i)
                    if phone in item:
                        self.contacts_listbox.selection_clear(0, tk.END)
                        self.contacts_listbox.selection_set(i)
                        self.contacts_listbox.see(i)
                        self.on_contact_select(None)
                        break
            else:
                messagebox.showerror("Ошибка", "Не удалось добавить контакт. Возможно, он уже добавлен.")

        # Кнопки
        button_frame = ttk.Frame(result_win)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Button(button_frame, text="Добавить в контакты",
                   command=add_selected).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(button_frame, text="Закрыть",
                   command=result_win.destroy).pack(side=tk.RIGHT)

        # Двойной клик для быстрого добавления
        def on_double_click(event):
            add_selected()

        listbox.bind('<Double-Button-1>', on_double_click)

    def on_contact_select(self, event):
        selection = self.contacts_listbox.curselection()
        if not selection:
            return

        index = selection[0]

        # Получаем реальный телефон из БД
        from client.database import Database
        db = Database()

        contacts = db.get_contacts(self.current_phone)
        if not contacts or index >= len(contacts):
            return

        phone = contacts[index][0]  # phone находится в позиции 0
        contact_nick = contacts[index][1]

        self.selected_contact = phone
        self.chat_header.config(text=f"💬 Чат с {contact_nick} ({phone})")
        self.load_chat_history()
    def load_chat_history(self):
        if not self.selected_contact:
            return

        from client.database import Database
        db = Database()

        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.delete(1.0, tk.END)

        messages = db.get_messages(self.current_phone, self.selected_contact)

        for sender, text, timestamp in messages:
            time_str = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%H:%M")

            if sender == self.current_phone:
                self.chat_text.insert(tk.END, f"[{time_str}] Вы: {text}\n", 'outgoing')
            else:
                self.chat_text.insert(tk.END, f"[{time_str}] Собеседник: {text}\n", 'incoming')

        self.chat_text.tag_config('outgoing', foreground='blue')
        self.chat_text.tag_config('incoming', foreground='green')

        self.chat_text.config(state=tk.DISABLED)
        self.chat_text.see(tk.END)

    def send_message(self):
        if not self.selected_contact:
            return

        text = self.message_entry.get().strip()
        if not text:
            return

        # Проверяем, есть ли получатель в нашей БД
        from client.database import Database
        db = Database()
        receiver_info = db.get_user_info(self.selected_contact)

        if not receiver_info:
            messagebox.showerror("Ошибка", "Пользователь не найден в системе!")
            return

        # ОТОБРАЖАЕМ сообщение локально (без сохранения в БД)
        time_str = datetime.now().strftime("%H:%M")
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"[{time_str}] Вы: {text}\n", 'outgoing')
        self.chat_text.tag_config('outgoing', foreground='blue')
        self.chat_text.config(state=tk.DISABLED)
        self.chat_text.see(tk.END)

        # Отправляем на сервер
        if self.socket:
            msg = json.dumps({
                'type': 'message',
                'sender': self.current_phone,
                'receiver': self.selected_contact,
                'text': text
            })
            self.socket.send(msg.encode('utf-8'))

        self.message_entry.delete(0, tk.END)

    def display_received_message(self, sender, text, timestamp):
        """Отображение полученного сообщения (без дублирования)"""
        # Проверяем, не отображали ли мы уже это сообщение
        current_chat = self.chat_text.get(1.0, tk.END)
        message_to_check = f"{sender}: {text}"

        if message_to_check in current_chat:
            # Сообщение уже отображено
            return

        from client.database import Database
        db = Database()

        # Если сообщение от текущего выбранного контакта
        if self.selected_contact == sender:
            time_str = timestamp if timestamp else datetime.now().strftime("%H:%M")
            self.chat_text.config(state=tk.NORMAL)
            self.chat_text.insert(tk.END, f"[{time_str}] Собеседник: {text}\n", 'incoming')
            self.chat_text.tag_config('incoming', foreground='green')
            self.chat_text.config(state=tk.DISABLED)
            self.chat_text.see(tk.END)

        # Обновляем список контактов (показать непрочитанные)
        self.load_contacts()

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()