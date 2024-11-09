from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from sqlite3 import *
from datetime import datetime

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    filename="bot.log",
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


TOKEN = "TOKEN"
NAME, DATE, TIME = range(3)

db = connect('laundry.db')
curs = db.cursor()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Давай познакомимся)\nНапиши мне своё имя и комнату\nНапример: Саша 1\n")
    return NAME

async def meet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_tag = update.message.from_user.username
        text = update.message.text.split()
        if len(text) == 2 and text[0].isalpha() and text[1].isdigit():
            name, room = text
            com = f"""
                INSERT INTO users (tag, name, room)
                VALUES ("{user_tag}", "{name}", {room})"""
            curs.executescript(com)
            await update.message.reply_text(f"Приятно познакомиться, {name}!\n" + 
                                            "Чтобы забронировать вермя, напиши /book_time\n" +
                                            "Если ты хочешь поменять имя или комнату, напиши /start")
            logger.info(f"New user: %s\nFrom %s", user_tag, update.message.from_user.username)
            return ConversationHandler.END
        else:
            await update.message.reply_text("Я тебя не понял, напиши ещё раз")
    except:
        com = f"""
                UPDATE users
                SET (name, room) = ("{name}", {room})
                WHERE (tag) = ("{user_tag}")
            """
        curs.executescript(com)

        await update.message.reply_text("Изменил твои данные\nЧтобы забронировать время, напиши /book_time")
        logger.info(f"Changed user data: %s\nFrom %s", user_tag, update.message.from_user.username)
        return ConversationHandler.END


async def booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напиши дату, на которую хочешь забронировать стирку\nНапример: 12.05.24")
    return DATE

async def book_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = update.message.text
    logger.info(f"Request to book date: %s\nFrom %s", date, update.message.from_user.username)
    try:
        date = datetime.strptime(date, "%d.%m.%y").date()
        context.user_data['date'] = date
        com = f"""
                SELECT * FROM books
                WHERE date = ("{date}")
            """
        res = curs.execute(com).fetchall()
        res = sorted(res, key = lambda x: datetime.strptime(x[3], "%H:%M:%S").time())
        if not res:
            await update.message.reply_text("На эту дату ещё нет броней, напиши время начала и окончания твоей стирки\n"+
                                            "Например: 16:25-18:00")
        else:
            text = "На эту дату уже забронировано такое время:\n\n"
            for i in res:
                com = f"""
                        SELECT * FROM users
                        WHERE tag = ("{i[1]}")
                    """
                user = curs.execute(com).fetchone()
                text += f"@{i[1]} - {user[1]}, {user[2]}   {i[3][:5]}-{i[4][:5]}\n"
            text += "\nНапиши время начала и окончания твоей стирки\nНапример: 16:25-18:00"
            await update.message.reply_text(text)
        return TIME
    except:
        await update.message.reply_text("Я тебя не понял, напиши ещё раз")

async def book_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = context.user_data['date']
    logger.info(f"Request to book time on %s: %s\nFrom %s", date, update.message.text, update.message.from_user.username)
    try:
        user_tag = update.message.from_user.username
        time = update.message.text.split("-")
        start_time = datetime.strptime(time[0], "%H:%M").time()
        end_time = datetime.strptime(time[1], "%H:%M").time()
        f = True
        com = f"""
                SELECT start_time, end_time FROM books
                WHERE date = ("{date}")
            """
        books = curs.execute(com).fetchall()
        if start_time > end_time:
            raise Exception
        if books:
            for i in books:
                start = datetime.strptime(i[0], "%H:%M:%S").time()
                end = datetime.strptime(i[1], "%H:%M:%S").time()
                if not(start_time > end and end_time > end) and not(start_time < start and end_time < start)\
                and not(start_time == end and end_time > end) and not(start_time < start and end_time == start):
                    f = False
        if f or not books:
            com = f"""
                    INSERT INTO books (user_tag, date, start_time, end_time, discription)
                    VALUES ("{user_tag}", "{date}", "{start_time}", "{end_time}", "")
                """
            res = curs.executescript(com)        
            await update.message.reply_text("Время забронировано\nЕсли хочешь удалить запись, напиши /delete")
            return ConversationHandler.END
        else:
            await update.message.reply_text("Это время уже занято")
    except Exception:
        await update.message.reply_text("Я тебя не понял, напиши ещё раз")

async def show_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напиши дату, на которую хочешь посмотреть забронированное время\nНапример: 12.05.24")
    return DATE

async def showing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = update.message.text
    logger.info(f"Request to view bookings for date: %s\nFrom %s", date, update.message.from_user.username)
    try:
        date = datetime.strptime(date, "%d.%m.%y").date()
        com = f"""
                SELECT * FROM books
                WHERE date = ("{date}")
            """
        res = curs.execute(com).fetchall()
        res = sorted(res, key = lambda x: datetime.strptime(x[3], "%H:%M:%S").time())
        if not res:
            await update.message.reply_text("На эту дату ещё нет броней")
        else:
            text = "На эту дату забронировано такое время:\n\n"
            for i in res:
                com = f"""
                        SELECT * FROM users
                        WHERE tag = ("{i[1]}")
                    """
                user = curs.execute(com).fetchone()
                text += f"@{i[1]} - {user[1]}, {user[2]}   {i[3][:5]}-{i[4][:5]}\n"
            await update.message.reply_text(text)
        return ConversationHandler.END
    except:
        await update.message.reply_text("Я тебя не понял, напиши ещё раз")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напиши дату брони, которую хочешь удалить\nНапример: 12.05.24")
    return DATE

async def delete_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = update.message.text
    logger.info(f"Request to delete booking for date: %s\nFrom %s", date, update.message.from_user.username)
    try:
        date = datetime.strptime(date, "%d.%m.%y").date()
        com = f"""
                SELECT * FROM books
                WHERE (user_tag, date) = ("{update.message.from_user.username}", "{date}")
            """
        res = curs.execute(com).fetchall()
        res = sorted(res, key = lambda x: datetime.strptime(x[3], "%H:%M:%S").time())
        if not res:
            await update.message.reply_text("На эту дату нет твоих броней")
            return ConversationHandler.END
        elif len(res) == 1:
            com = f"""
                DELETE FROM books
                WHERE (user_tag, date) == ("{update.message.from_user.username}", "{date}")
                """
            res = curs.executescript(com)
            await update.message.reply_text("Запись удалена")   
            return ConversationHandler.END
        else:
            context.user_data['date'] = date
            text = "На эту дату у тебя забронировано такое время:\n\n"
            for i in res:
                text += f"@{i[1]}   {i[3][:5]}-{i[4][:5]}\n"
            text += "\nНапиши номер стирки, которую хочешь удалить"
            await update.message.reply_text(text)
            return TIME
    except:
        await update.message.reply_text("Я тебя не понял, напиши ещё раз")

async def delete_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = context.user_data['date']
    num = int(update.message.text)
    logger.info(f"Request to delete booking on %s: %s\nFrom %s", date, update.message.text, update.message.from_user.username)
    try:
        com = f"""
                SELECT start_time, end_time FROM books
                WHERE (user_tag, date) = ("{update.message.from_user.username}", "{date}")
            """
        res = curs.execute(com).fetchall()
        com = f"""
                DELETE FROM books
                WHERE (user_tag, date, start_time, end_time) = ("{update.message.from_user.username}", "{date}", "{res[num-1][0]}", "{res[num-1][1]}")
            """
        res = curs.executescript(com)
        await update.message.reply_text("Запись удалена")
        return ConversationHandler.END
    except:
        await update.message.reply_text("Я тебя не понял, напиши ещё раз")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Help request from %s", update.message.from_user.username)
    await update.message.reply_text("Если ты хочешь забронировать время, напиши /book_time\n" +
                                    "Если ты хочешь посмотреть какое время уже забронировано, напиши /show_books\n" +
                                    "Если ты хочешь удалить бронь, напиши /delete")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Stop request from %s", update.message.from_user.username)
    await update.message.reply_text('Стоп машина!')
    return ConversationHandler.END

if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("help", help, filters.ChatType.PRIVATE))

    meet_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start, filters.ChatType.PRIVATE) #входные точки
        ],
        states={
            NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, meet) #забирает текст и не забирает команды
            ]
        },
        fallbacks=[MessageHandler(filters.COMMAND, stop)], #стоп машина
    )

    booking_handler = ConversationHandler(
        entry_points=[
            CommandHandler("book_time", booking, filters.ChatType.PRIVATE) 
        ],
        states={
            DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, book_date) 
            ],
            TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, book_time) 
            ]
        },
        fallbacks=[MessageHandler(filters.COMMAND, stop)],
    )

    show_handler = ConversationHandler(
        entry_points=[
            CommandHandler("show_books", show_books, filters.ChatType.PRIVATE) 
        ],
        states={
            DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, showing)
            ] 
        },
        fallbacks=[MessageHandler(filters.COMMAND, stop)],
    )

    delete_handler = ConversationHandler(
        entry_points=[
            CommandHandler("delete", delete, filters.ChatType.PRIVATE) 
        ],
        states={
            DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_date) 
            ],
            TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_time) 
            ] 
        },
        fallbacks=[MessageHandler(filters.COMMAND, stop)],
    )

    application.add_handler(meet_handler)
    application.add_handler(booking_handler)
    application.add_handler(show_handler)
    application.add_handler(delete_handler)

    application.run_polling()