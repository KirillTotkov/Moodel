import os
from dotenv import load_dotenv
from vkbottle import API, BuiltinStateDispenser
from vkbottle.bot import BotLabeler
from moodle import Moodle


load_dotenv()

MOODLE_URL = os.getenv('MOODLE_URL')
BOT_TOKEN = os.getenv('VK_BOT_TOKEN')
MOODLE_TOKEN = os.getenv('MOODLE_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

api = API(BOT_TOKEN)
labeler = BotLabeler()
state_dispenser = BuiltinStateDispenser()

moodle = Moodle(MOODLE_URL + '/webservice/rest/server.php', MOODLE_TOKEN)
