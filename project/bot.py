import psycopg2
import telebot
from telebot import types
import config

# Конфигурация
API_TOKEN = config.TOKEN
DATABASE_URL = config.DB_URL
SUPPORT_CHAT_ID = config.ADMIN_CHAT
SENIOR_CURATOR_CHAT_ID = config.SENIOR_CHAT

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
        show_options(message, user[1])
    else:
        msg = bot.send_message(message.chat.id, "Добро пожаловать! Пожалуйста, укажите ваше полное имя.")
        bot.register_next_step_handler(msg, process_full_name)

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

# Обработка обращений в тех.поддержку
@bot.message_handler(func=lambda message: message.text == "Тех. поддержка")
def tech_support(message):
    msg = bot.send_message(message.chat.id, "Пожалуйста, напишите ваше сообщение в тех.поддержку.")
    bot.register_next_step_handler(msg, process_support_message)

# Обработка сообщения для тех.поддержки
def process_support_message(message):
    support_message = message.text
    user_id = message.from_user.id
    name = message.from_user.username

    # Отправляем сообщение в тех.поддержку
    bot.send_message(SUPPORT_CHAT_ID, f"Сообщение от пользователя @{name}:\n{support_message}")

    # Отправляем подтверждение пользователю
    bot.send_message(message.chat.id, "Ваше сообщение отправлено в тех.поддержку. Спасибо!")

    # Возвращаемся к меню выбора опций
    cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
    role = cursor.fetchone()
    if role:
        show_options(message, role[0])

# Обработка отчетов кураторов
@bot.message_handler(func=lambda message: message.text == "Отчитаться")
def curator_report(message):
    user_id = message.from_user.id

    cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
    role = cursor.fetchone()

    if role is None or role[0] != "Куратор":
        bot.send_message(message.chat.id, "Эта опция доступна только для кураторов.")
        show_options(message, role[0] if role else 'Неизвестно')
        return

    bot.send_message(message.chat.id, "Введите ваш отчет...")  # Здесь будет логика обработки отчетов

# Обработка отзывов первокурсников
@bot.message_handler(func=lambda message: message.text == "Расскажу о кураторе")
def freshman_feedback(message):
    user_id = message.from_user.id

    cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
    role = cursor.fetchone()

    if role is None or role[0] != "Первокурсник":
        bot.send_message(message.chat.id, "Эта опция доступна только для первокурсников.")
        show_options(message, role[0] if role else 'Неизвестно')
        return

    bot.send_message(message.chat.id, "Введите ваш отзыв о кураторе...")  # Логика обработки отзывов

# Обработка обращения к старшему куратору
@bot.message_handler(func=lambda message: message.text == "Старший куратор")
def senior_curator(message):
    msg = bot.send_message(message.chat.id, "Пожалуйста, напишите ваше сообщение для старшего куратора.")
    bot.register_next_step_handler(msg, process_senior_curator_message)

# Обработка сообщения для старшего куратора
def process_senior_curator_message(message):
    senior_message = message.text
    user_id = message.from_user.id
    name = message.from_user.username

    # Отправляем сообщение старшему куратору
    bot.send_message(SENIOR_CURATOR_CHAT_ID, f"Сообщение от пользователя @{name}:\n{senior_message}")

    # Отправляем подтверждение пользователю
    bot.send_message(message.chat.id, "Ваше сообщение отправлено старшему куратору. Спасибо!")

    # Возвращаемся к меню выбора опций
    cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
    role = cursor.fetchone()
    if role:
        show_options(message, role[0])

# Запуск бота
bot.polling()