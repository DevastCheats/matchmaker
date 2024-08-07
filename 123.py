import os
import re
import requests

# Создаем папку img, если её нет
if not os.path.exists('audio'):
    os.makedirs('audio')

# Открываем файл 777.txt и читаем его содержимое
with open('777.txt', 'r') as file:
    content = file.read()

# Находим все строки, содержащие "img/(название картинки).png"
pattern = re.compile(r'audio/([^/]+\.mp3)')
matches = pattern.findall(content)

# Формируем и скачиваем URL для каждой найденной картинки
base_url = 'https://devast.io/audio/'

for match in matches:
    image_url = base_url + match
    response = requests.get(image_url)
    
    if response.status_code == 200:
        with open(os.path.join('audio', match), 'wb') as f:
            f.write(response.content)
        print(f'Successfully downloaded {match}')
    else:
        print(f'Failed to download {match}')

print('All images have been processed.')
