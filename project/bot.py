import psycopg2
import telebot
from telebot import types
import re
from datetime import datetime, timedelta

import config

# Конфигурация
API_TOKEN = config.TOKEN
DATABASE_URL = config.DB_URL
SUPPORT_CHAT_ID = config.ADMIN_CHAT
SENIOR_CURATOR_CHAT_ID = config.SENIOR_CHAT
REQUEST_INTERVAL = timedelta(minutes=10)  # Интервал между обращениями

bot = telebot.TeleBot(API_TOKEN)

# Подключение к базе данных
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Команда /start
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id

    cursor.execute("SELECT full_name, role FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()

    if user:
        bot.send_message(message.chat.id, f"Ваши данные:\nФИО: {user[0]}\nРоль: {user[1]}")
        if user[1] == "Модератор":
            show_moderator_options(message)
        else:
            show_options(message, user[1])
    else:
        msg = bot.send_message(message.chat.id, "Добро пожаловать! Пожалуйста, укажите ваше полное имя.")
        bot.register_next_step_handler(msg, process_full_name)

# Функция для отображения опций модератора
def show_moderator_options(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Просмотр сообщений', 'Тех. поддержка', 'Старший куратор')
    bot.send_message(message.chat.id, "Выберите одну из опций, Модератор:", reply_markup=markup)
    
    
# Команда для просмотра всех сообщений, на которые можно ответить
@bot.message_handler(func=lambda message: message.text == "Просмотр сообщений")
def view_messages(message):
    cursor.execute("SELECT message_id, user_id, message_text FROM messages WHERE moderator_id IS NULL ORDER BY timestamp DESC")
    messages = cursor.fetchall()

    if messages:
        response = "Сообщения, на которые можно ответить:\n\n"
        for msg in messages:
            response += f"ID: {msg[0]}\nОт пользователя: {msg[1]}\nСообщение: {msg[2]}\n\n"
    else:
        response = "Нет сообщений, на которые можно ответить."

    bot.send_message(message.chat.id, response)

# Команда для ответа на сообщение
@bot.message_handler(commands=['reply'])
def reply_to_user(message):
    try:
        args = message.text.split(' ', 2)  # /reply <message_id> <response_text>
        message_id = int(args[1])
        response_text = args[2]

        # Получаем информацию о пользователе по ID сообщения
        cursor.execute("SELECT user_id FROM messages WHERE message_id = %s", (message_id,))
        user_id = cursor.fetchone()

        if user_id:
            user_id = user_id[0]
            bot.send_message(user_id, f"Ответ от модератора:\n{response_text}")

            # Обновляем информацию о модераторе, который ответил
            cursor.execute(
                "UPDATE messages SET moderator_id = %s WHERE message_id = %s",
                (message.from_user.id, message_id)
            )
            conn.commit()

            bot.send_message(message.chat.id, "Ваш ответ был отправлен пользователю.")
        else:
            bot.send_message(message.chat.id, "Сообщение с таким ID не найдено.")
    except (IndexError, ValueError):
        bot.send_message(message.chat.id, "Неверный формат команды. Используйте /reply <ID сообщения> <текст ответа>.")

# Получаем ФИО пользователя
def process_full_name(message):
    full_name = message.text
    user_id = message.from_user.id

    cursor.execute("INSERT INTO users (user_id, full_name) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET full_name = EXCLUDED.full_name", (user_id, full_name))
    conn.commit()

    # Запрос роли пользователя с кнопками
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Куратор', 'Первокурсник')
    msg = bot.send_message(message.chat.id, "Пожалуйста, выберите вашу роль.", reply_markup=markup)
    bot.register_next_step_handler(msg, process_role)

# Получаем роль пользователя
def process_role(message):
    role = message.text
    user_id = message.from_user.id

    if role not in ["Куратор", "Первокурсник"]:
        msg = bot.send_message(message.chat.id, "Пожалуйста, выберите роль из предложенных вариантов.")
        bot.register_next_step_handler(msg, process_role)
        return

    cursor.execute("UPDATE users SET role = %s WHERE user_id = %s", (role, user_id))
    conn.commit()

    if role == "Куратор":
        msg = bot.send_message(message.chat.id, "Какую группу вы курируете?")
    else:
        msg = bot.send_message(message.chat.id, "В какой группе вы учитесь?")
    
    bot.register_next_step_handler(msg, process_group)

# Получаем группу пользователя
def process_group(message):
    group_name = message.text
    user_id = message.from_user.id

    # Регулярное выражение для проверки формата группы
    pattern = r'^[бсмБСМаА]\d{2}-\d{3}$'

    if not re.match(pattern, group_name):
        msg = bot.send_message(message.chat.id, "Некорректный формат группы. Пожалуйста, введите группу в формате: БXX-XXX (СXX-XXX)")
        bot.register_next_step_handler(msg, process_group)
        return

    cursor.execute("SELECT full_name, role FROM users WHERE user_id = %s", (user_id,))
    user_data = cursor.fetchone()

    if user_data is None:
        bot.send_message(message.chat.id, "Произошла ошибка. Пожалуйста, начните регистрацию заново.")
        return

    cursor.execute(
        "UPDATE users SET group_name = %s WHERE user_id = %s",
        (group_name, user_id)
    )
    conn.commit()

    bot.send_message(message.chat.id, f"Регистрация завершена!\nФИО: {user_data[0]}\nРоль: {user_data[1]}")
    
    show_options(message, user_data[1])
    
# Функция для отображения опций
def show_options(message, role):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    if role == "Куратор":
        markup.add('Отчитаться', 'Тех. поддержка', 'Старший куратор')
    elif role == "Первокурсник":
        markup.add('Расскажу о кураторе', 'Тех. поддержка', 'Старший куратор')

    bot.send_message(message.chat.id, "Выберите одну из опций:", reply_markup=markup)

# Проверка интервала времени с последнего обращения
def can_send_request(last_request_time):
    if last_request_time is None:
        return True
    return datetime.now() - last_request_time >= REQUEST_INTERVAL

# Обработка обращений в тех.поддержку
@bot.message_handler(func=lambda message: message.text == "Тех. поддержка")
def tech_support(message):
    user_id = message.from_user.id

    cursor.execute("SELECT last_support_request FROM users WHERE user_id = %s", (user_id,))
    last_support_request = cursor.fetchone()[0]


    if not can_send_request(last_support_request):
        diff = 10 - int(datetime.now().minute - last_support_request.minute)
        minute_str = '' 
        if(diff == 1): minute_str = 'минута' 
        elif(diff in (2, 5)): minute_str = 'минуты'
        else: minute_str = 'минут'
        bot.send_message(message.chat.id, f"Вы недавно обращались в тех.поддержку. Пожалуйста, подождите {diff} {minute_str} перед следующим обращением.")
        return show_options(message, "Куратор" if message.text == "Куратор" else "Первокурсник")

    msg = bot.send_message(message.chat.id, "Пожалуйста, напишите ваше сообщение в тех.поддержку.")
    bot.register_next_step_handler(msg, process_support_message)

# Обработка сообщения для тех.поддержки
def process_support_message(message):
    support_message = message.text
    user_id = message.from_user.id
    name = message.from_user.username

    # Отправляем сообщение в тех.поддержку
    bot.send_message(SUPPORT_CHAT_ID, f"Сообщение от пользователя @{name}:\n{support_message}")

    # Обновляем время последнего обращения в тех.поддержку
    cursor.execute("UPDATE users SET last_support_request = %s WHERE user_id = %s", (datetime.now(), user_id))
    conn.commit()

    # Отправляем подтверждение пользователю
    bot.send_message(message.chat.id, "Ваше сообщение отправлено в тех.поддержку. Спасибо!")

    # Возвращаемся к меню выбора опций
    cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
    role = cursor.fetchone()
    if role:
        show_options(message, role[0])

# Обработка обращения к старшему куратору
@bot.message_handler(func=lambda message: message.text == "Старший куратор")
def senior_curator(message):
    user_id = message.from_user.id

    cursor.execute("SELECT last_curator_request FROM users WHERE user_id = %s", (user_id,))
    last_curator_request = cursor.fetchone()[0]
    

    if not can_send_request(last_curator_request):
        diff = 10 - int(datetime.now().minute - last_curator_request.minute)
        minute_str = '' 
        if(diff == 1): minute_str = 'минута' 
        elif(diff in (2, 5)): minute_str = 'минуты'
        else: minute_str = 'минут'
        bot.send_message(message.chat.id, f"""Вы недавно обращались к старшему куратору. Пожалуйста, подождите {diff} {minute_str} перед следующим обращением.""")
        return show_options(message, "Куратор" if message.text == "Куратор" else "Первокурсник")

    msg = bot.send_message(message.chat.id, "Пожалуйста, напишите ваше сообщение для старшего куратора.")
    bot.register_next_step_handler(msg, process_senior_curator_message)

# Обработка сообщения для старшего куратора
def process_senior_curator_message(message):
    senior_message = message.text
    user_id = message.from_user.id
    name = message.from_user.username

    # Отправляем сообщение старшему куратору
    bot.send_message(SENIOR_CURATOR_CHAT_ID, f"Сообщение от пользователя @{name}:\n{senior_message}")

    # Обновляем время последнего обращения к старшему куратору
    cursor.execute("UPDATE users SET last_curator_request = %s WHERE user_id = %s", (datetime.now(), user_id))
    conn.commit()

    # Отправляем подтверждение пользователю
    bot.send_message(message.chat.id, "Ваше сообщение отправлено старшему куратору. Спасибо!")

    # Возвращаемся к меню выбора опций
    cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
    role = cursor.fetchone()
    if role:
        show_options(message, role[0])

# Запуск бота
bot.polling(none_stop=True)