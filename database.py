import gspread
import ast
import logging

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
        logger.info(f'Last order: {last_order}')

        return last_order

    def get_operators(self):
        operators = self.operators_sheet.get_all_records()
        logger.info(f'Fetched operators: {len(operators)}')

        return operators


# order_updater = OrderUpdater(ORDERS_DOCUMENT_ID, GOOGLE_BOT_PKEY)
#
# print(order_updater.get_last_order())
