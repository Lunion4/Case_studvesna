import telebot
import requests
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
#SERVER_URL = "http://127.0.0.1:5000/update_telegram"  # Адрес API сервера
SERVER_URL = os.getenv('SERVER_URL')
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
            tx = f"""Новый пользователь в системе:
                            message.from_user.id: {message.from_user.id}
                            message.from_user.is_bot: {message.from_user.is_bot}
                            message.from_user.first_name: {message.from_user.first_name}
                            message.from_user.last_name: {message.from_user.last_name}
                            message.from_user.username: {message.from_user.username}
                            message.from_user.language_code: {message.from_user.language_code}
                            message.from_user.is_premium: {message.from_user.is_premium}
                            message.from_user.added_to_attachment_menu: {message.from_user.added_to_attachment_menu}
                            message.from_user.can_join_groups: {message.from_user.can_join_groups}
                            message.from_user.can_read_all_group_messages: {message.from_user.can_read_all_group_messages}
                            message.from_user.supports_inline_queries: {message.from_user.supports_inline_queries}
                            message.from_user.can_connect_to_business: {message.from_user.can_connect_to_business}
                            message.from_user.has_main_web_app: {message.from_user.has_main_web_app}
                            """
            print(tx)
            send_telegram_message(815480347, tx)
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
