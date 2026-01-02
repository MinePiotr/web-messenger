from http.server import BaseHTTPRequestHandler
import json

# Простой in-memory WebSocket эмулятор для Vercel
ws_connections = {}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """WebSocket endpoint (упрощенный)"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        # Эмуляция WebSocket для демонстрации
        response = {
            "status": "websocket_ready",
            "message": "Use POST to send messages",
            "connections": len(ws_connections)
        }

        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        """Отправка сообщения через "WebSocket" """
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode())

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        message_type = data.get('type', '')

        if message_type == 'register':
            phone = data.get('phone', '')
            ws_connections[phone] = True
            response = {"status": "registered", "phone": phone}

        elif message_type == 'message':
            sender = data.get('sender', '')
            receiver = data.get('receiver', '')
            text = data.get('text', '')

            # В реальном приложении здесь была бы отправка через WebSocket
            response = {
                "status": "message_forwarded",
                "sender": sender,
                "receiver": receiver,
                "text": text
            }

        else:
            response = {"error": "Unknown message type"}

        self.wfile.write(json.dumps(response).encode())