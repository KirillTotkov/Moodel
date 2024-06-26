from dataclasses import dataclass
import random
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
@labeler.message(text=["Начать", "начать", "Привет", "Привет", "Старт", "старт", "Hi", "hi"])
async def start_handler(message: Message):
	await message.answer("Привет! Я бот для уведомлений о новых заданиях в Moodle.")
	db = next(get_db())
	user = db.query(User).filter(User.id == message.from_id).first()
	db.close()
 
	if user:
		await message.answer("Вы уже зарегистрированы")
		return
	
	await message.answer("Для начала работы, введите логин и пароль от Moodle. \n"
                         "Для отмены введите 'Отмена'")
	await message.answer("Логин:")
	 
	await bot.state_dispenser.set(message.peer_id, LoginStates.AWAITING_LOGIN)


@labeler.message(state=LoginStates.AWAITING_LOGIN)
async def login_handler(message: Message):
	if message.text.lower() == "отмена":
		await bot.state_dispenser.delete(message.peer_id)
		await message.answer("Вход отменен")
		return

	db = next(get_db())
	user = db.query(User).filter(User.id == message.from_id).first()
	db.close()
 
	if user:
		await message.answer("Вы уже зарегистрированы")
		return

	login = message.text
	
	ctx_storage.set(message.peer_id, login)
 
	await message.answer("Пароль:")

	await bot.state_dispenser.set(message.peer_id, LoginStates.AWAITING_PASSWORD)
	
	await bot.api.messages.delete(message_ids=[message.id], peer_id=message.peer_id)
 


@labeler.message(state=LoginStates.AWAITING_PASSWORD)
async def password_handler(message: Message):
	if message.text.lower() == "отмена":
		await bot.state_dispenser.delete(message.peer_id)
		await message.answer("Вход отменен")
		return
    
	db = next(get_db())
	user = db.query(User).filter(User.id == message.from_id).first()
	if user:
		db.close()
		await message.answer("Вы уже зарегистрированы")
		return

	login = ctx_storage.get(message.peer_id)
	password = message.text

	token_res = moodle.get_tokens(MOODLE_URL, login, password).get('token')
	ctx_storage.delete(message.peer_id)
 
	id = message.from_id
 
	if token_res is None:
		await bot.api.messages.delete(message_ids=[message.id], peer_id=message.peer_id)
		await message.answer("Неверный логин или пароль")
		return

	await bot.api.messages.delete(message_ids=[message.id], peer_id=message.peer_id)

	user = User.create(db, id=id, moodle_token=token_res)

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

	db.close()
 
	await message.answer("Вы успешно зарегистрированы \n Вам будут приходить сообщения о новых заданиях.")
	await bot.state_dispenser.delete(message.peer_id)
	await courses_handler(message)


@labeler.message(regexp="(?i)курсы")
async def courses_handler(message: Message):
	db = next(get_db())
	user = User.get_or_none(db, id=message.from_id)
	db.close()
 
	if not user:
		await message.answer("Вы не зарегистрированы")
		return

	moodle.token = user.moodle_token

	coursesMoodle = moodle.core.course.get_enrolled_courses_by_timeline_classification(classification="all")
	if not coursesMoodle:
		await message.answer("У вас нет курсов")
		return

	courses_text = 'Ваши курсы:\n'
	for num, course in enumerate(coursesMoodle):
		courses_text += f"{num + 1}⃣ {course.fullname} \n"
	await message.answer(courses_text)


@labeler.message(text=["Удалить аккаунт", "удалить аккаунт"])
async def delete_account_handler(message: Message):
	db = next(get_db())
	user = db.query(User).filter(User.id == message.from_id).first()

	if not user:
		await message.answer("Вы не зарегистрированы")
		return
 
	user.remove_courses(db)

	db.delete(user)
	db.commit()
	db.close()

	await message.answer("Ваш аккаунт успешно удален")


async def send_new_courses(user: User):
	courses = user.courses
 
	moodle.token = user.moodle_token
	coursesMoodle = moodle.core.course.get_enrolled_courses_by_timeline_classification(classification="all")

	course_db_ids = [c.id for c in courses]
 
	new_courses = []
 
	db = next(get_db())
 
	for course in coursesMoodle:
		if course.id in course_db_ids: continue

		new_course = Course.create(db, id=course.id, name=course.fullname)
		new_courses.append(new_course)

		await bot.api.messages.send(user_id=user.id, random_id=0, message=f"Новый курс:\n {course.fullname}")
  
	db.close()
 
	return new_courses
			

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

async def download_and_upload_file(file_url: str, file_name: str, peer_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as resp:
            file_content = await resp.read()
    doc = await uploader.upload(file_source=file_content, peer_id=peer_id, title=file_name)
    return doc


async def tasks_handler(user_id: int) -> list[Tasks]:
	db = next(get_db())
	user = User.get_or_none(db, id=user_id)
	if user is None: 
		db.close()
		return
  
	moodle.token = user.moodle_token

	courses = user.courses
	if not courses:
		db.close()
		return

	new_tasks = []
 
	for course in courses:
		tasks_moodle = moodle.core.course.get_contents(course.id)
		tasks_db_ids = [task.id for task in db.query(Tasks).filter_by(course_id= course.id).all()]

		for section in tasks_moodle:
			for task in section.modules:
				if task.modplural == "Форумы" or task.id in tasks_db_ids:
					continue
				
				t = Tasks(id=task.id, course_id=course.id)
				new_tasks.append(t)

				task_text= get_task_text(task, course.name)
    
				if task.modplural == 'Файлы':
					file_url = task.contents[0].fileurl + '&token=' + moodle.token
					file_name = task.contents[0].filename
     
					doc = await download_and_upload_file(file_url, file_name, user_id)
     
					await bot.api.messages.send(user_id=user_id, message=task_text, attachment=doc, random_id=0)

					continue
				
				await bot.api.messages.send(user_id=user_id, message=task_text, random_id=0)

	db.close()
    
	return new_tasks