import telebot
import requests

TOKEN = ''
SERVER_URL = "https://opensource.pythonanywhere.com/update_telegram"  # Адрес API сервера
bot = telebot.TeleBot(TOKEN)

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

bot.polling()
