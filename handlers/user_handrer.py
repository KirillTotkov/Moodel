import aiohttp
from vkbottle.bot import Message
from vkbottle import BaseStateGroup
from vkbottle import CtxStorage

from bs4 import BeautifulSoup
from moodle.core.course import Module
from loguru import logger

from config import labeler, moodle, MOODLE_URL, bot, uploader
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
	
	user = User.create(db, id=message.from_id, moodle_token=token_res)

	moodle.token = user.moodle_token
	coursesMoodle = moodle.core.course.get_enrolled_courses_by_timeline_classification(classification="all")
	courses = [
		Course(
			id=c.id,
			name=c.fullname
		) for c in coursesMoodle
	]	
	user.add_courses(courses, db)

	for cource in courses:
		tasks_moodle = moodle.core.course.get_contents(cource.id)
		for section in tasks_moodle:
			for task in section.modules:
				if task.modplural == "Форумы": continue
				Tasks.create(db, id=task.id, course_id=cource.id)


	await message.answer("Вы успешно зарегистрированы \n Вам будут приходить сообщения о новых заданиях.")
	await bot.state_dispenser.delete(message.peer_id)
	await courses_handler(message)


@labeler.message(regexp="(?i)курсы")
async def courses_handler(message: Message):
	db = next(get_db())
	user = User.get_or_none(db, id=message.from_id)
	if user is None: return

	moodle.token = user.moodle_token

	coursesMoodle = moodle.core.course.get_enrolled_courses_by_timeline_classification(classification="all")
	if not coursesMoodle:
		await message.answer("У вас нет курсов")
		return

	courses_text = 'Ваши курсы:\n'
	for num, course in enumerate(coursesMoodle):
		courses_text += f"{num + 1}⃣ {course.fullname} \n"
	await message.answer(courses_text)


def _parse_task_description(task: Module) -> str:
    if task.description:
        soup = BeautifulSoup(task.description, 'html.parser')
        return soup.get_text(separator='\n') or ""
    return ""

def get_task_text(task: Module, cource_name: str) -> str:
	text = f"Курс: {cource_name}\n"
	text += f"Тип: {task.modplural}\n"
	text += f"Название: {task.name}\n"
	
	if task.modplural != 'Пояснения':
		text += f'Ссылка: {task.url}\n'

	if task.description:
		text += f"Описание: {_parse_task_description(task)}\n"
		
	if task.modplural == 'Файлы':
		return text

	if task.contents is not None and len(task.contents) > 0 and task.modplural not in ['Папки', 'Страницы']:
		text += f"Гиперссылка: {task.contents[0].fileurl.replace('forcedownload=1', '')}\n"
	return text

async def download_and_upload_file(file_url: str, file_name: str, message: Message):
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as resp:
            file_content = await resp.read()
    doc = await uploader.upload(file_source=file_content, peer_id=message.peer_id, title=file_name)
    return doc


@labeler.message(regexp="(?i)задания")
async def tasks_handler(message: Message):
	db = next(get_db())
	user = User.get_or_none(db, id=message.from_id)
	if user is None: return

	moodle.token = user.moodle_token

	courses = user.courses
	if not courses:
		await message.answer("У вас нет курсов")
		return

	for course in courses:
		tasks_moodle = moodle.core.course.get_contents(course.id)
		tasks_db_ids = [task.id for task in db.query(Tasks).filter_by(course_id= course.id).all()]

		for section in tasks_moodle:
			for task in section.modules:
				if task.modplural == "Форумы" or task.id in tasks_db_ids:
					continue
				
				Tasks.create(db, id=task.id, course_id=course.id)
		
				task_text= get_task_text(task, course.name)
    
				if task.modplural == 'Файлы':
					file_url = task.contents[0].fileurl + '&token=' + moodle.token
					file_name = task.contents[0].filename
     
					doc = await download_and_upload_file(file_url, file_name, message)
					await message.answer(task_text, attachment=doc)

					continue
				
				await message.answer(task_text)