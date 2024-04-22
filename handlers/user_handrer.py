from vkbottle.bot import Message
from vkbottle import BaseStateGroup, Bot
from vkbottle import CtxStorage

from config import labeler, moodle, MOODLE_URL, bot
from database.models import User, Course, Tasks
from database.sessions import get_db

class LoginStates(BaseStateGroup):
    AWAITING_LOGIN = "awaiting_login"
    AWAITING_PASSWORD = "awaiting_password"

ctx_storage = CtxStorage()


@labeler.message(payload={"command": "start"})
@labeler.message(text=["Начать", "Привет", "Hi"])
async def start_handler(message: Message):
	await message.answer("Привет! Я бот для уведомлений о новых заданиях в Moodle.")
	db = next(get_db())
	user = db.query(User).filter(User.id == message.from_id).first()
	
	if user:
		await message.answer("Вы уже зарегистрированы")
		return
	
	await message.answer("Для начала работы, введите логин и пароль от Moodle. \n"
                         "Для отмены введите /cancel")
	await message.answer("Логин:")
	 
	await bot.state_dispenser.set(message.peer_id, LoginStates.AWAITING_LOGIN)


@labeler.message(state=LoginStates.AWAITING_LOGIN)
async def login_handler(message: Message):
	db = next(get_db())
	user = db.query(User).filter(User.id == message.from_id).first()
	if user:
		await message.answer("Вы уже зарегистрированы")
		return
	login = message.text

	ctx_storage.set(message.peer_id, login)

	await message.answer("Пароль:")
	await bot.state_dispenser.set(message.peer_id, LoginStates.AWAITING_PASSWORD)



@labeler.message(state=LoginStates.AWAITING_PASSWORD)
async def password_handler(message: Message):
	db = next(get_db())
	user = db.query(User).filter(User.id == message.from_id).first()
	if user:
		await message.answer("Вы уже зарегистрированы")
		return
	

	login = ctx_storage.get(message.peer_id)
	password = message.text

	token_res = moodle.get_tokens(MOODLE_URL, login, password).get('token')
	ctx_storage.delete(message.peer_id)

	if token_res is None:
		await message.answer("Неверный логин или пароль")
		return
	
	User.create(db, id=message.from_id, moodle_token=token_res)

	await message.answer("Вы успешно зарегистрированы \n Вам будут приходить сообщения о новых заданиях.")
	await bot.state_dispenser.delete(message.peer_id)
	await courses_handler(message)


@labeler.message(regexp="(?i)курсы")
async def courses_handler(message: Message):
	db = next(get_db())
	moodle.token = User.read(db, id=message.from_id).moodle_token

	coursesMoodle = moodle.core.course.get_enrolled_courses_by_timeline_classification(classification="all")
	if not coursesMoodle:
		await message.answer("У вас нет курсов")
		return

	courses_text = 'Ваши курсы:\n'
	for num, course in enumerate(coursesMoodle):
		courses_text += f"{num + 1}⃣ {course.fullname} \n"
	await message.answer(courses_text)

