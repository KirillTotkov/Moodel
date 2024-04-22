import os
from dotenv import load_dotenv
from vkbottle import API, Bot, BuiltinStateDispenser
from vkbottle.bot import BotLabeler
from moodle import Moodle


load_dotenv()

MOODLE_URL = os.getenv('MOODLE_HOST')
BOT_TOKEN = os.getenv('VK_BOT_TOKEN')
MOODLE_TOKEN = os.getenv('MOODLE_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

print(MOODLE_URL)

api = API(BOT_TOKEN)
labeler = BotLabeler()
state_dispenser = BuiltinStateDispenser()

bot = Bot(
    api=api,
    labeler=labeler,
    state_dispenser=state_dispenser,
)

moodle = Moodle(MOODLE_URL + '/webservice/rest/server.php', "")
