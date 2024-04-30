from __future__ import annotations

from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy import Column
from sqlalchemy import Table
from sqlalchemy.orm import Session

class Base(DeclarativeBase):
    __abstract__ = True

    @classmethod
    def create(cls, session: Session, **kwargs):
        instance = cls(**kwargs)
        session.add(instance)
        session.commit()
        return instance
    
    @classmethod
    def get_or_none(cls, session: Session, id):
        return session.query(cls).filter_by(id=id).first()
    
    @classmethod
    def get_all(cls, session: Session):
        return session.query(cls).all()

    @classmethod
    def update(cls, session: Session, id, **kwargs):
        instance = session.query(cls).filter_by(id=id).first()
        for attr, value in kwargs.items():
            setattr(instance, attr, value)
        session.commit()
        return instance

    @classmethod
    def delete(cls, session: Session, id):
        instance = session.query(cls).filter_by(id=id).first()
        session.delete(instance)
        session.commit()
    

association_table = Table(
    "user_courses",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE")),
    Column("course_id", ForeignKey("courses.id", ondelete="CASCADE")),
)

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    moodle_token: Mapped[str] = mapped_column(String(200))
    courses: Mapped[List['Course']] = relationship(secondary=association_table)

    def add_courses(self, courses, session: Session):
        for course in courses:
            "Проверить существует ли курс"
            if not Course.get_or_none(id=course.id, session=session):
                session.add(course)
                session.commit()

            """Если курс не привязан к пользователю, то привязываем"""
            if course not in self.courses:
                db_course = course.get_or_none(id=course.id, session=session)
                self.courses.append(db_course)
                session.commit()
    

class Course(Base):
    __tablename__ = 'courses'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    tasks: Mapped[List['Tasks']] = relationship(cascade="all, delete")

class Tasks(Base):
    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey('courses.id'))