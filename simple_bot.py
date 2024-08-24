import telebot
import config
import os
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

TELEGRAM_BOT_TOKEN = config.TOKEN
CHAT_ID = config.ADMIN_CHAT

class TelegramBot:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)
        self.user_data = {}

    def start(self, message):
        user_id = message.chat.id
        self.bot.send_message(
            chat_id=user_id,
            text="Привет! Пожалуйста, введите ваши ФИО и группу через пробел."
        )
        self.bot.register_next_step_handler(message, self.get_user_info)

    def get_user_info(self, message):
        user_id = message.chat.id
        user_input = message.text.split()
        name = ' '.join(user_input[:-1])
        group = user_input[-1]
        self.user_data[user_id] = {'name': name, 'group': group}
        self.bot.send_message(
            chat_id=user_id,
            text="Отлично! Теперь пожалуйста, пришлите фотографию."
        )
        self.bot.register_next_step_handler(message, self.process_photo)
    

    def process_photo(self, message):
        user_id = message.chat.id
        if message.photo:
            file_info = self.bot.get_file(message.photo[-1].file_id)
            downloaded_file = self.bot.download_file(file_info.file_path)
            with open(f"{user_id}.jpg", 'wb') as file:
                file.write(downloaded_file)
            user_data = self.user_data[user_id]
            message_text = f"Пользователь: {user_data['name']}\nГруппа: {user_data['group']}"
            with open(f"{user_id}.jpg", 'rb') as file:
                self.bot.send_photo(chat_id=CHAT_ID, photo=file, caption=message_text)
            os.remove(f"{user_id}.jpg")
            text = "Спасибо, брат/брат женского пола\n\
*для отправки новых достижений, введите /start"
            self.bot.send_message(chat_id=user_id, text=text)
        else:
            self.bot.send_message(
                chat_id=user_id,
                text="Извините, но вы должны прислать фотографию."
            )
            self.bot.register_next_step_handler(message, self.process_photo)
        

    def run(self):
        self.bot.polling()

if __name__ == '__main__':
    bot = TelegramBot(TELEGRAM_BOT_TOKEN)
    bot.bot.set_my_commands([
        telebot.types.BotCommand('/start', 'Начать работу с ботом')
    ])
    bot.bot.message_handler(commands=['start'])(bot.start)
    bot.run()
