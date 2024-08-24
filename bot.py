import telebot
from telebot import types

# Укажите свой токен бота
API_TOKEN = '7092073070:AAGFOnZHUR86RdAjb7pgSN7plOiQe1_4Qow'
bot = telebot.TeleBot(API_TOKEN)

# Словари для хранения данных пользователей
users = {}

# Enum для ролей
class Role:
    CURATOR = "Куратор"
    FRESHMAN = "Первокурсник"

# Стартовая команда
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Куратор")
    item2 = types.KeyboardButton("Первокурсник")
    markup.add(item1, item2)

    bot.send_message(message.chat.id, "Привет! Выберите, кем вы являетесь:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_role_selection)

# Обработка выбора роли
def handle_role_selection(message):
    if message.text == "Куратор":
        role = Role.CURATOR
    elif message.text == "Первокурсник":
        role = Role.FRESHMAN
    else:
        bot.send_message(message.chat.id, "Некорректный выбор. Пожалуйста, выберите 'Куратор' или 'Первокурсник'.")
        return

    # Сохраняем данные пользователя
    user_id = message.from_user.id
    users[user_id] = {
        "role": role,
        "name": "",
        "group": ""
    }
    
    bot.send_message(message.chat.id, "Введите ваше ФИО:")
    bot.register_next_step_handler(message, enter_name)

# Ввод ФИО
def enter_name(message):
    user_id = message.from_user.id
    users[user_id]["name"] = message.text
    
    bot.send_message(message.chat.id, "Введите вашу группу:")
    bot.register_next_step_handler(message, enter_group)

# Ввод группы
def enter_group(message):
    user_id = message.from_user.id
    users[user_id]["group"] = message.text
    
    role = users[user_id]["role"]
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if role == Role.CURATOR:
        item1 = types.KeyboardButton("Отчитаться за мероприятие")
        item2 = types.KeyboardButton("Добавить мероприятие")
        markup.add(item1, item2)
        bot.send_message(message.chat.id, "Вы куратор. Вы можете выбрать действие:", reply_markup=markup)
    elif role == Role.FRESHMAN:
        item1 = types.KeyboardButton("Задать вопрос куратору")
        item2 = types.KeyboardButton("Поблагодарить куратора")
        markup.add(item1, item2)
        bot.send_message(message.chat.id, "Вы первокурсник. Вы можете выбрать действие:", reply_markup=markup)

# Обработка инструкций для кураторов

@bot.message_handler(func=lambda message: users.get(message.from_user.id, {}).get('role') == Role.CURATOR)
def handle_curator_actions(message):
    if message.text == 'Отчитаться за мероприятие':
        bot.send_message(message.chat.id, "Пожалуйста, пришлите фото мероприятия:")
        bot.register_next_step_handler(message, upload_activity_photo)
    elif message.text == 'Добавить мероприятие':
        bot.send_message(message.chat.id, "Пожалуйста, опишите мероприятие:")
        bot.register_next_step_handler(message, add_activity)

def upload_activity_photo(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, "Спасибо! Фото получено.")

def add_activity(message):
    description = message.text
    bot.send_message(message.chat.id, f"Мероприятие добавлено: {description}")

# Обработка инструкций для первокурсников
@bot.message_handler(func=lambda message: users.get(message.from_user.id, {}).get('role') == Role.FRESHMAN)
def handle_freshman_actions(message):
    if message.text == 'Задать вопрос куратору':
        bot.send_message(message.chat.id, "Пожалуйста, напишите свой вопрос:")
        bot.register_next_step_handler(message, submit_question)
    elif message.text == 'Поблагодарить куратора':
        bot.send_message(message.chat.id, "Пожалуйста, пришлите фото с вашим куратором:")
        bot.register_next_step_handler(message, upload_thank_you_photo)

def submit_question(message):
    question = message.text
    bot.send_message(message.chat.id, f"Ваш вопрос отправлен: {question}")

def upload_thank_you_photo(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, "Спасибо! Фото получено.")

# Запуск бота
if __name__ == '__main__':
    bot.polling(none_stop=True)