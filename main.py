from telebot import *

bot = telebot.TeleBot('token')

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, 'Привет! Это бот для удобного бронирования времени стрики!\nДля начала напиши /help')

@bot.message_handler(commands=["book_time"])
def book_time(message):
    # Добавляем две кнопки
    reply_keyboard = [["Сегодня", "Завтра", "Послезавтра"]]
    markup=types.ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    bot.send_message(message.chat.id, 
                     'Когда хочешь забронировать время?\nВыбери один из вариантов или напиши свою дату, например: 21.10', 
                     reply_markup=markup)

@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, 
                     'Если ты хочешь забронировать время, напиши /book_time\nЕсли ты хочешь посмотреть какое время сегодня уже занято, напиши /show_books\nЕсли ты хочешь удалить бронь, напиши /delete')

@bot.message_handler(commands=["show_books"])
def show_books(message):
    bot.send_message(message.chat.id, "")

@bot.message_handler(commands=["delete"])
def delete(message):
    bot.send_message(message.chat.id, "")

@bot.message_handler(content_types=["text"])
def handle_text(message):
    bot.send_message(message.chat.id, 'Ой, я вас не понял')

bot.polling(none_stop=True, interval=0)