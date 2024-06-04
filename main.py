from loguru import logger
from handlers import labelers
from config import labeler, bot, scheduler
from database.sessions import get_db, create
from database.models import User
from handlers.user_handrer import send_new_courses, tasks_handler

for labeler in labelers:
    bot.labeler.load(labeler)

    
@scheduler.scheduled_job('interval', seconds=30, id='tasks')
async def main():
    db = next(get_db())
    all_users = User.get_all(db)
    
    all_tasks = set()
        
    for user in all_users:
        await send_new_courses(user)
        tasks = await tasks_handler(user.id)
        all_tasks.update(tasks)
        
    db = next(get_db())
    
    for task in all_tasks:
        db.add(task)
    db.commit()
    
if __name__ == "__main__":
    create()
    scheduler.start()
    bot.run_forever()
    
