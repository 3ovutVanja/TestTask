import os
from dotenv import load_dotenv
import logging


logger = logging.getLogger(__name__)

load_dotenv()

db_host = os.getenv("DB_HOST", "localhost")
db_user = os.getenv("DB_USER", "root")
db_pass = os.getenv("DB_PASS", "12451245")
db_name = os.getenv("DB_NAME", "bet_maker")
db_port = os.getenv("DB_PORT", "3306")

mq_user = os.getenv("MQ_USER", "guest")
mq_pwd = os.getenv("MQ_PWD", "guest")
mq_host = os.getenv("MQ_HOST", "127.0.0.1")

lp_host = os.getenv("LP_HOST", "localhost")
