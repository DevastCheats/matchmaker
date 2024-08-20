import requests
import json
import asyncio
import websockets
import logging
import random
import string
import threading
import time
from flask import Flask, jsonify
from flask_cors import CORS

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)

# URL и заголовки для API
API_URL = 'https://api.rivet.gg/matchmaker/lobbies'
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://devast.io"
}

def generate_random_string(length=16):
    """Генерация случайной строки из букв и цифр."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def count_specific_values(message):
    """Подсчет количества '0' и 119 в сообщении."""
    count_zeros = message.count('0')
    count_119 = message.count('119')
    return count_zeros, count_119

async def get_zero_count_from_server(player_token, hostname):
    """Подключение к серверу по WebSocket и получение количества '0' в первом сообщении."""
    ws_url = f"wss://{hostname}/?token={player_token}"
    try:
        async with websockets.connect(ws_url) as ws:
            # Генерация случайных данных
            random_letters = generate_random_string()
            random_number = random.randint(1, 100)

            # Сообщение для отправки
            message = [30, random_letters, str(random_number), 62, 0, 'listserver', 0, 0, 0]
            await ws.send(json.dumps(message))

            # Ждем первое сообщение
            response = await ws.recv()
            response_str = response if isinstance(response, str) else response.decode('utf-8')

            # Подсчитываем количество '0' и 119
            count_zeros, count_119 = count_specific_values(response_str)
            total_player_count = 119 - count_zeros

            return total_player_count
    except Exception as e:
        logging.error(f"Ошибка при работе с WebSocket: {e}, URL: {ws_url}")
        return None

def get_zero_count(player_token, hostname):
    """Запускает асинхронную функцию для получения количества '0' и 119."""
    return asyncio.run(get_zero_count_from_server(player_token, hostname))

def join_lobby_and_get_token(lobby_id):
    """Выполняет запрос OPTIONS и POST /join, возвращает player_token и hostname."""
    options_url = f"{API_URL}/join"
    try:
        # Выполняем OPTIONS запрос
        requests.options(options_url, headers=HEADERS)
    except requests.RequestException as e:
        logging.error(f"Ошибка при OPTIONS запросе к {options_url}: {e}")
        return None, None

    # Выполняем POST запрос
    post_url = f"{API_URL}/join"
    payload = {
        "lobby_id": lobby_id,
    }
    try:
        response = requests.post(post_url, headers=HEADERS, json=payload)
        response.raise_for_status()
        response_data = response.json()

        player_token = response_data['player']['token']
        hostname = response_data['lobby']['ports']['default']['hostname']
        logging.info(f"Успешно присоединились к лобби: {lobby_id}")
        return player_token, hostname
    except requests.RequestException as e:
        logging.error(f"Ошибка при выполнении запроса POST к {post_url} для lobby_id {lobby_id}: {e}, Response: {response.text if 'response' in locals() else 'No response'}")
        return None, None

def update_lobbies():
    """Функция для обновления списка лобби каждые 40 секунд."""
    while True:
        list_url = f"{API_URL}/list"
        try:
            logging.info(f"Отправка запроса на {list_url}")
            servers_list = requests.get(list_url, headers=HEADERS)
            servers_list.raise_for_status()
            response_json = servers_list.json()
            updated_lobbies = []

            for lobby in response_json['lobbies']:
                # Получаем данные для подключения через /join
                player_token, hostname = join_lobby_and_get_token(lobby['lobby_id'])

                if player_token and hostname:
                    # Подключаемся через WebSocket и получаем количество '0'
                    total_player_count = get_zero_count(player_token, hostname)

                    if total_player_count is not None:
                        lobby['total_player_count'] = total_player_count
                        updated_lobbies.append(lobby)

            response_json['lobbies'] = updated_lobbies

            # Сохраняем обновленный список серверов в файл
            with open("updated_servers_list.json", "w") as file:
                json.dump(response_json, file, indent=4)

            logging.info("Список лобби обновлен и сохранен в файл.")
        except requests.RequestException as e:
            logging.error(f"Ошибка при запросе списка серверов: {e}, URL: {list_url}")
        except Exception as e:
            logging.error(f"Неизвестная ошибка при обновлении списка лобби: {e}")

        # Задержка в 40 секунд
        time.sleep(40)

@app.route('/list', methods=['GET'])
def ServersList():
    """Отображение содержимого файла с обновленным списком серверов."""
    try:
        with open("updated_servers_list.json", "r") as file:
            response_json = json.load(file)
        return jsonify(response_json)
    except FileNotFoundError:
        return "Файл с данными не найден.", 404
    except json.JSONDecodeError:
        return "Ошибка чтения данных из файла.", 500
    except Exception as e:
        logging.error(f"Ошибка при чтении файла: {e}")
        return "Ошибка при чтении файла.", 500

if __name__ == "__main__":
    # Запускаем поток для периодического обновления данных
    threading.Thread(target=update_lobbies, daemon=True).start()
    app.run(host="0.0.0.0", port=8069)
