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

class Base(DeclarativeBase):
    pass

association_table = Table(
    "user_courses",
    Base.metadata,
    Column("user_id", ForeignKey("users.id")),
    Column("course_id", ForeignKey("courses.id")),
)

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    moodle_token: Mapped[str] = mapped_column(String(200))
    courses: Mapped[List['Course']] = relationship(secondary=association_table)
    

class Course(Base):
    __tablename__ = 'courses'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    tasks: Mapped[List['Tasks']] = relationship()

class Tasks(Base):
    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey('courses.id'))