#!/usr/bin/env python
# pylint: disable=C0116,W0613
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few callback functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
import os
from typing import Dict

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get('PORT', '8443'))
SERVER_ENV = os.environ.get('SERVER_ENV', False)

heroku_app_name = 'gidropod'

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# ADDRESS, PHOTO, LOCATION, BIO = range(4)
NEW, ADDRESS, TASK, PHONE, PRICE = range(5)


def facts_to_str(user_data: Dict[str, str]) -> str:
    """Helper function for formatting the gathered user info."""
    facts = [f'{key} - {value}' for key, value in user_data.items()]
    return "\n".join(facts).join(['\n', '\n'])


def start(update: Update, context: CallbackContext) -> int:
    """Starts the conversation and asks the user create a new order."""
    reply_keyboard = [['Давай']]

    update.message.reply_text(
        'Привет! Создадим новый заказ?\n'
        'Жми /cancel если передумал.\n\n',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True
        ),
    )

    return NEW


def new(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("User %s created new order", user)

    update.message.reply_text('Отлично, куда едем?', reply_markup=ReplyKeyboardRemove())

    return ADDRESS


def address(update: Update, context: CallbackContext) -> int:
    """Stores the info about the address."""
    context.user_data['address'] = update.message.text
    logger.info("Address: %s", update.message.text)

    update.message.reply_text('Отлично, какой вид работ?')

    return TASK


def task(update: Update, context: CallbackContext) -> int:
    """Stores the info about the task."""
    context.user_data['task'] = update.message.text
    logger.info("Task: %s", update.message.text)

    update.message.reply_text('Отлично, а телефон?\n'
                              '/skip чтобы не давать')

    return PHONE


def phone(update: Update, context: CallbackContext) -> int:
    """Stores the info about the task."""
    context.user_data['phone'] = update.message.text
    logger.info("Phone: %s", update.message.text)

    update.message.reply_text('А цена?')

    return PRICE


def skip_phone(update: Update, context: CallbackContext) -> int:
    """Skips the phone and asks for a location."""
    user = update.message.from_user
    logger.info("User %s did not provide a phone.", user.first_name)
    update.message.reply_text(
        'Ну нет так нет. А цена?.'
    )

    return PRICE


def price(update: Update, context: CallbackContext) -> int:
    """Stores the info about the task."""
    context.user_data['price'] = update.message.text
    logger.info("Price: %s", update.message.text)

    update.message.reply_text('Готово. Заказ создан!')

    user_data = context.user_data
    update.message.reply_text(
        f"Инфо по заказу: {facts_to_str(user_data)}"
        f"\nТы - пидор!"
    )

    user_data.clear()

    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Ну ладно, пока.', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(BOT_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NEW: [MessageHandler(Filters.regex('^(Давай)$'), new)],
            ADDRESS: [MessageHandler(Filters.text & ~Filters.command, address)],
            TASK: [MessageHandler(Filters.text, task)],
            PHONE: [
                MessageHandler(Filters.text & ~Filters.command, phone),
                CommandHandler('skip', skip_phone),
            ],
            PRICE: [MessageHandler(Filters.text & ~Filters.command, price)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)

    # # Start the Bot

    if SERVER_ENV:  # running on server
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"https://{heroku_app_name}.herokuapp.com/{BOT_TOKEN}")
        updater.idle()
    else:  # running locally
        updater.start_polling()
    logger.info('Bot started successfully')


if __name__ == '__main__':
    main()
