import telebot
import requests
from dotenv import load_dotenv
from telebot import types
import os

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
SERVER_URL = os.getenv('SERVER_URL', "http://127.0.0.1:5000")
bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=['start'])
def handle_start(message):
    telegram_id = message.from_user.id
    args = message.text.split()

    if len(args) > 1:
        user_id = args[1]

        response = requests.post(SERVER_URL + '/update_telegram', json={"user_id": user_id, "telegram_id": telegram_id})

        if response.status_code == 200:
            keyboard = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(text="🔗 Обратно на сайт", url=f"{SERVER_URL}/profile")
            keyboard.add(button)
            bot.send_message(telegram_id, "✅ Ваш Telegram успешно привязан!", reply_markup=keyboard)
            tx = f"""Новый пользователь в системе:
                            user_id: {user_id}
                            telegram_id: {telegram_id}
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
            bot.send_message(815480347, tx)
        else:
            bot.send_message(telegram_id, "❌ Ошибка: не удалось привязать Telegram.")
    else:
        bot.send_message(telegram_id, "Привет! Чтобы привязать Telegram к аккаунту, нажмите кнопку на сайте.")


if __name__ == '__main__':
    print("Бот запущен...")
    bot.send_message(815480347, f"Хендлер запущен {SERVER_URL}")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        bot.send_message(815480347, f"Бот упав: {e}")
        print(f"Ошибка при запуске бота: {e}")
