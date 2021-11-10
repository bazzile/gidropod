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
from typing import Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    CallbackContext,
)

from database import OrderUpdater

from config import (
    BOT_TOKEN,
    PORT,
    GOOGLE_BOT_PKEY,
    ORDERS_DOCUMENT_ID,
    ORDER_FORM_URL,
    ENV_IS_SERVER
)

heroku_app_name = 'gidropod'

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

logger.info(BOT_TOKEN)

# Stages
FIRST, SECOND = range(2)
# Callback data
ONE, TWO, THREE, FOUR = range(4)


d = [
    {'id': 0, 'Name': 'Vas', 'Selected': True},
    {'id': 1, 'Name': 'Ser', 'Selected': True},
]

order_updater = OrderUpdater(ORDERS_DOCUMENT_ID, GOOGLE_BOT_PKEY)
global operators


def start(update: Update, context: CallbackContext) -> int:
    """Send message on `/start`."""
    # Get user that sent /start and log his name
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.first_name)
    # Build InlineKeyboard where each button has a displayed text
    # and a string as callback_data
    # The keyboard is a list of button rows, where each row is in turn
    # a list (hence `[[...]]`).

    global operators

    operator_buttons = [
        InlineKeyboardButton(operator['DisplayName'], callback_data=str(operator['telegram_id'])) for operator in operators]
    control_buttons = [
        InlineKeyboardButton("Готово", callback_data=str("done")),
        InlineKeyboardButton("Отмена", callback_data=str("cancel"))]

    keyboard = [[button] for button in operator_buttons] + [control_buttons]

    reply_markup = InlineKeyboardMarkup(keyboard)
    # Send message with text and appended InlineKeyboard
    update.message.reply_text("Кто?", reply_markup=reply_markup)
    # Tell ConversationHandler that we're in state `FIRST` now
    return FIRST


def one(update: Update, context: CallbackContext) -> int:
    """Show new choice of buttons"""
    query = update.callback_query
    query.answer()

    selected_person = query.data

    logger.info('DATA: ' + selected_person)

    # for item in d:
    #     if item['id'] == int(selected_person):
    #         item['Selected'] = not item['Selected']
    #         if item['Name'].startswith('+'):
    #             item['Name'] = item['Name'].replace('+', '')
    #         else:
    #             item['Name'] = '+' + item['Name']

    for operator in operators:
        if operator['telegram_id'] == int(selected_person):
            operator['Selected'] = not operator['Selected']
            if operator['DisplayName'].startswith('+'):
                operator['DisplayName'] = operator['DisplayName'].replace('+', '')
            else:
                operator['DisplayName'] = '+' + operator['DisplayName']

    operator_buttons = [
        InlineKeyboardButton(operator['DisplayName'], callback_data=str(operator['telegram_id'])) for operator in operators]
    control_buttons = [
        InlineKeyboardButton("Готово", callback_data=str("done")),
        InlineKeyboardButton("Отмена", callback_data=str("cancel"))]

    keyboard = [[button] for button in operator_buttons] + [control_buttons]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text="Кто?", reply_markup=reply_markup
    )
    return FIRST


def end(update: Update, context: CallbackContext) -> int:
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over.
    """
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="See you next time!")
    return ConversationHandler.END


def main() -> None:
    global operators
    operators = order_updater.get_operators()
    operators = [dict(item, **{'Selected': False, 'DisplayName': item['ФИО']}) for item in operators]
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(BOT_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Setup conversation handler with the states FIRST and SECOND
    # Use the pattern parameter to pass CallbackQueries with specific
    # data pattern to the corresponding handlers.
    # ^ means "start of line/string"
    # $ means "end of line/string"
    # So ^ABC$ will only allow 'ABC'
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FIRST: [
                # CallbackQueryHandler(one, pattern='^(0|1)$'),
                CallbackQueryHandler(one, pattern=f'^({"|".join(str(operator["telegram_id"]) for operator in operators)})$'),
                CallbackQueryHandler(end, pattern='^(cancel|done)$'),
            ],
            # SECOND: [
            #     CallbackQueryHandler(start_over, pattern='^' + str(ONE) + '$'),
            #     CallbackQueryHandler(end, pattern='^' + str(TWO) + '$'),
            # ],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    dispatcher.add_handler(conv_handler)

    # # Start the Bot
    if ENV_IS_SERVER:  # running on server
        # Start the webhook
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"https://{heroku_app_name}.herokuapp.com/{BOT_TOKEN}")
        updater.idle()
    else:  # running locally
        logger.info('Running locally...')
        updater.start_polling()
    logger.info('Bot started successfully')


if __name__ == '__main__':
    main()
