import os

BOT_TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get('PORT', '8443'))
GOOGLE_BOT_PKEY = os.environ.get('GOOGLE_BOT_PKEY')
ENV_IS_SERVER = os.environ.get('ENV_IS_SERVER', False)

ORDERS_DOCUMENT_ID = '12hvOj1OvJC6tsMYfKCcLbv6UlYf-6iZ-I9h6mLQruNM'
ORDER_FORM_URL = 'https://forms.gle/NdHd4H15tj7PND9v6'
ORDERS_TABLE_URL = 'https://docs.google.com/spreadsheets/d/12hvOj1OvJC6tsMYfKCcLbv6UlYf-6iZ-I9h6mLQruNM'


ORDER_RESPONSE_TIME = 10 * 60  # seconds
# Todo оставить в диспетчерах только Серёгу
# DISPATCHER_TELEGRAM_ID = [279777025]
DISPATCHER_TELEGRAM_ID = [279777025, 256887570, ]
