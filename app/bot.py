import telebot
import requests

TOKEN = ''
SERVER_URL = "http://127.0.0.1:5000/update_telegram"  # Адрес API сервера
bot = telebot.TeleBot(TOKEN)

def send_telegram_message(telegram_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        'chat_id': telegram_id,
        'text': text,
        'parse_mode': 'HTML',
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Ошибка при отправке Telegram-сообщения: {e}")


@bot.message_handler(commands=['start'])
def handle_start(message):
    telegram_id = message.from_user.id
    args = message.text.split()

    if len(args) > 1:
        user_id = args[1]  # Получаем user_id из параметра start

        # Отправляем данные на сервер
        response = requests.post(SERVER_URL, json={"user_id": user_id, "telegram_id": telegram_id})

        if response.status_code == 200:
            bot.send_message(telegram_id, "✅ Ваш Telegram успешно привязан!")
        else:
            bot.send_message(telegram_id, "❌ Ошибка: не удалось привязать Telegram.")
    else:
        bot.send_message(telegram_id, "Привет! Чтобы привязать Telegram к аккаунту, нажмите кнопку на сайте.")



if __name__ == '__main__':
    print("Бот запущен...")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
