from moodle import Moodle
from loguru import logger
from vkbottle import Bot
from vkbottle.bot import Message
from vkbot.handlers import labelers
from config import labeler, bot


for labeler in labelers:
    bot.labeler.load(labeler)

bot.run_forever()