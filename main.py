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

import telegram.error
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    CallbackContext,
    MessageHandler,
    Filters
)

import threading

from database import OrderUpdater, ActiveOrder

from config import (
    BOT_TOKEN,
    PORT,
    GOOGLE_BOT_PKEY,
    ORDERS_DOCUMENT_ID,
    ORDER_FORM_URL,
    ORDERS_TABLE_URL,
    ENV_IS_SERVER,
    ORDER_RESPONSE_TIME,
    DISPATCHER_TELEGRAM_ID
)

heroku_app_name = 'gidropod'

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


# Stages
ADD_ORDER_STAGE, REVIEW_ORDER_STAGE, ASSIGN_OPERATORS_STAGE = range(3)


order_updater = OrderUpdater(ORDERS_DOCUMENT_ID, GOOGLE_BOT_PKEY)
global operators
global active_order


def new_order(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.first_name)
    if user.id == DISPATCHER_TELEGRAM_ID:
        logger.info("User %s is a dispatcher", user.first_name)
        # logger.info(update.message.chat_id)
        # Build InlineKeyboard where each button has a displayed text
        # and a string as callback_data
        # The keyboard is a list of button rows, where each row is in turn
        # a list (hence `[[...]]`).

        global operators
        operators = order_updater.get_operators()
        operators = [dict(item, **{'Selected': False, 'DisplayName': item['ФИО']}) for item in operators]

        keyboard = [[
            InlineKeyboardButton("✅ Посмотреть заказ", callback_data=str("task")),
            InlineKeyboardButton("❌ Отмена", callback_data=str("cancel_order")),
        ]]

        reply_markup = InlineKeyboardMarkup(keyboard)
        # Send message with text and appended InlineKeyboard
        update.message.reply_text(
            f"Привет!\nНе забудь добавить заказ, прежде чем выбрать операторов:\n{ORDER_FORM_URL}", reply_markup=reply_markup)
        # Tell ConversationHandler that we're in state `FIRST` now
        return ADD_ORDER_STAGE
    else:
        logger.info("User %s is NOT a dispatcher, refusing to place an order", user.first_name)
        update.message.reply_text(
            'Заказы может создавать только диспетчер.\n'
            'Обратитесь к [Сергею Железнову](tg://user?id=279777025)',
            parse_mode='markdown')


def review_order(update: Update, context: CallbackContext) -> int:
    """Show new choice of buttons"""
    query = update.callback_query
    query.answer()

    keyboard = [[
        InlineKeyboardButton("✅ Выбрать операторов", callback_data=str("select")),
        InlineKeyboardButton("❌ Отмена", callback_data=str("cancel_order")),
    ]]

    global active_order
    active_order = ActiveOrder(order_updater.get_last_order())
    formatted_order = active_order.format_order()
    logger.info(formatted_order)

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text=f"*Заказ:*\n{formatted_order}", reply_markup=reply_markup, parse_mode='markdown'
    )
    return REVIEW_ORDER_STAGE


def assign_operators(update: Update, context: CallbackContext) -> int:
    """Show new choice of buttons"""
    query = update.callback_query
    query.answer()

    if query.data == 'select':
        selected_person = 0
    else:
        selected_person = query.data

    logger.info('DATA: ' + str(selected_person))

    for operator in operators:
        if operator['telegram_id'] == int(selected_person):
            operator['Selected'] = not operator['Selected']
            if operator['DisplayName'].startswith('👨🏿 '):
                operator['DisplayName'] = operator['DisplayName'].replace('👨🏿 ', '')
            else:
                operator['DisplayName'] = '👨🏿 ' + operator['DisplayName']

    operator_buttons = [
        InlineKeyboardButton(operator['DisplayName'], callback_data=str(operator['telegram_id'])) for operator in operators]
    control_buttons = [
        InlineKeyboardButton("✅ Назначить", callback_data=str("done")),
        InlineKeyboardButton("❌ Отмена", callback_data=str("cancel_order"))]

    keyboard = [[button] for button in operator_buttons] + [control_buttons]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text="Операторы:", reply_markup=reply_markup
    )

    return ASSIGN_OPERATORS_STAGE


def end(update: Update, context: CallbackContext) -> int:
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over.
    """
    global operators
    selected_operators = [operator for operator in operators if operator['Selected']]
    query = update.callback_query
    query.answer()

    if selected_operators:

        query.edit_message_text(text="Готово! На заказ выбраны:\n{}".format('\n'.join(
            operator['ФИО'] for operator in selected_operators)))

        # operators = [operator['telegram_id'] for operator in selected_operators]
        global active_order
        active_order.set_operators(selected_operators)
        operator = active_order.get_next_operator()
        ask(context, operator)

        return ConversationHandler.END
    else:
        return ASSIGN_OPERATORS_STAGE


def get_orders_table(update: Update, _: CallbackContext):
    user = update.message.from_user
    if user.id == DISPATCHER_TELEGRAM_ID:
        update.message.reply_text(
            f'[Таблица заказов]({ORDERS_TABLE_URL})',
            parse_mode='markdown')
    else:
        logger.info("User %s is NOT a dispatcher, refusing to show orders", user.first_name)
        update.message.reply_text(
            'Заказы может просматривать только диспетчер.\n'
            'Обратитесь к [Сергею Железнову](tg://user?id=279777025)',
            parse_mode='markdown')


def cancel_order(update: Update, _: CallbackContext) -> int:
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over.
    """

    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Отмена. На заказ никто не выбран")
    return ConversationHandler.END


def ask(context: CallbackContext, operator):
    logger.info(f'Proposing order to {operator["ФИО"]}')
    operator_id = operator['telegram_id']

    keyboard = [[
        InlineKeyboardButton("Уже лечу", callback_data=str("1")),
        InlineKeyboardButton("Я в запое, отмена", callback_data=str("0")),
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    global active_order

    try:
        message = context.bot.send_message(
            chat_id=operator_id, text=f'*Новый заказ!*\n'
            f'{active_order.format_order()}\n\n'
            f'_Через {ORDER_RESPONSE_TIME} мин. заказ будет передан следующему оператору_',
            reply_markup=reply_markup, parse_mode='markdown')

        timer = threading.Timer(ORDER_RESPONSE_TIME * 60, timeout_proposal, [context, operator_id, message.message_id])
        active_order.set_timer(timer)

    except telegram.error.BadRequest:
        logger.info(f'Chat id {operator_id} does not exist. Double-check it')
        operator = active_order.get_next_operator()
        pass_order_to_next_operator(context, operator)
    # return message.message_id


def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()

    global active_order

    # query.edit_message_text(text=f"Selected option: {query.data}")
    if query.data == '0':
        query.edit_message_text(text=f"❌ Вы отказались от заказа, его передадут другому")
        # ask next user
        operator = active_order.get_next_operator()
        pass_order_to_next_operator(context, operator)

    elif query.data == '1':
        query.edit_message_text(text=f"✅ Вы приняли заказ")
        active_order.timer.cancel()
        logger.info('Order picked within set time, timer was canceled')
        logger.info('Reporting to dispatcher')
        context.bot.send_message(
            chat_id=DISPATCHER_TELEGRAM_ID,
            text=f'✅ *Заказ принят!*'
                 f'\nПодробности:\n'
                 f'{active_order.format_order()}\n\n'
                 f'Заказ принял:\n'
                 f'*{active_order.current_operator["ФИО"]}*',
            parse_mode='markdown')


def pass_order_to_next_operator(context: CallbackContext, operator):
    if operator:
        ask(context, operator)
    else:
        logger.info('No operators left in the queue, reporting to dispatcher')
        context.bot.send_message(
            chat_id=DISPATCHER_TELEGRAM_ID,
            text='Внимание!\nЗаказ ❌*НЕ ПРИНЯТ*❌ ни одним из выбранных операторов',
            parse_mode='markdown')


def timeout_proposal(context: CallbackContext, chat_id, message_id) -> None:
    context.bot.editMessageText(chat_id=chat_id,
                                message_id=message_id,
                                text="Заказ не принят во время")
    # ask next user
    global active_order
    operator = active_order.get_next_operator()
    pass_order_to_next_operator(context, operator)


def unknown_command(update: Update, _: CallbackContext):
    update.message.reply_text('Неверная команда. Список доступных команд - в меню')


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
        entry_points=[CommandHandler('new_order', new_order)],
        states={
            ADD_ORDER_STAGE: [
                CallbackQueryHandler(review_order, pattern='^(task)$'),
                CallbackQueryHandler(cancel_order, pattern='^(cancel_order)$'),
            ],
            REVIEW_ORDER_STAGE: [
                CallbackQueryHandler(assign_operators, pattern='^(select)$'),
                CallbackQueryHandler(cancel_order, pattern='^(cancel_order)$'),
            ],
            ASSIGN_OPERATORS_STAGE: [
                CallbackQueryHandler(assign_operators, pattern=f'^({"|".join(str(operator["telegram_id"]) for operator in operators)})$'),
                CallbackQueryHandler(end, pattern='^(done)$'),
                CallbackQueryHandler(cancel_order, pattern='^(cancel_order)$'),
            ],

        },
        fallbacks=[CommandHandler('cancel_order', cancel_order)],
        allow_reentry=True
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(CommandHandler('get_orders_table', get_orders_table))
    dispatcher.add_handler(MessageHandler(Filters.command, unknown_command))

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
