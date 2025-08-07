from telegram.ext import Updater, CommandHandler
from Deal import run_micro_scalper
import threading

# 🔐 ВСТАВЬ СЮДА СВОЙ ТОКЕН
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

# Флаг, чтобы не запускать два раза
is_running = False

def start(update, context):
    global is_running
    if is_running:
        context.bot.send_message(chat_id=update.effective_chat.id, text="⏳ Уже запущено.")
        return

    context.bot.send_message(chat_id=update.effective_chat.id, text="🚀 Запускаю стратегию...")

    def run_bot():
        global is_running
        is_running = True
        try:
            run_micro_scalper()
        except Exception as e:
            print(f"Ошибка в стратегии: {e}")
        is_running = False

    threading.Thread(target=run_bot).start()

def main():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
