import gspread
import ast
import json
import logging
import threading

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


class OrderUpdater(object):
    def __init__(self, shreadsheet_id, pkey):
        pkey = ast.literal_eval(pkey)
        gc = gspread.service_account_from_dict(pkey)
        spreadsheet = gc.open_by_key(shreadsheet_id)

        self.orders_sheet = spreadsheet.get_worksheet(0)  # orders
        self.operators_sheet = spreadsheet.get_worksheet(1)  # operators

        # self.operators = self.update_operators()

    def get_last_order(self):
        orders = self.orders_sheet.get_all_records()

        logger.info(f'Fetched orders: {len(orders)}')

        last_order = orders[-1]
        last_order.pop('Отметка времени', None)
        logger.info(f'Last order: {last_order}')

        return last_order

    def get_operators(self):
        operators = self.operators_sheet.get_all_records()
        logger.info(f'Fetched operators: {len(operators)}')

        return operators


class ActiveOrder(object):
    def __init__(self, order_dict):
        self.order = order_dict
        self.operator_list = None
        self.timer = None
        self.current_operator = None

    # def start_polling(self, timer_sec):
    #     for operator in self.operator_list:

    def format_order(self):
        return "\n".join(": ".join((str(k), '*' + str(v) + '*')) for k, v in self.order.items())

    def set_operators(self, operator_list):
        self.operator_list = operator_list

    def get_next_operator(self):
        try:
            self.current_operator = self.operator_list.pop(0)
            return self.current_operator
        except IndexError:
            return None

    def set_timer(self, timer):
        self.timer = timer
        timer.start()


# order_updater = OrderUpdater(ORDERS_DOCUMENT_ID, GOOGLE_BOT_PKEY)
#
# print(order_updater.get_last_order())
