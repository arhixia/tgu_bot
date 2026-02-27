from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ENUM
import enum
from src.db.database import Base


class UserRole(enum.Enum):
    TEACHER = "teacher"
    STUDENT = "student"

class TaskType(enum.Enum):
    TRAINING = "training"
    TESTING = "testing"

class AnswerStatus(enum.Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    SKIPPED = "skipped"
    PENDING = "pending"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False) 
    role = Column(SQLEnum(UserRole), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True) 

    managed_groups = relationship("Group", back_populates="teacher", foreign_keys="Group.teacher_id")
    student_group = relationship("Group", back_populates="students", foreign_keys=[group_id])
    created_tasks = relationship("Task", back_populates="creator")
    submitted_answers = relationship("Answer", back_populates="student")


class Group(Base):
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    teacher = relationship("User", back_populates="managed_groups", foreign_keys=[teacher_id])
    students = relationship("User", back_populates="student_group", foreign_keys=[User.group_id])


class Theme(Base):
    __tablename__ = "themes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    llm_prompt = Column(Text, nullable=False)
    theory = Column(Text, nullable=True) 
    
    tasks = relationship("Task", back_populates="theme")


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    theme_id = Column(Integer, ForeignKey("themes.id"), nullable=False)
    
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    task_type = Column(SQLEnum(TaskType), nullable=False)
    image_url = Column(String, nullable=False)
    description = Column(Text, nullable=True) #описание
    hint = Column(Text, nullable=True)          #подсказка
    correct_answer = Column(Text, nullable=True) #правильный ответ к заданию
    is_approved = Column(Boolean, default=False)
    
    theme = relationship("Theme", back_populates="tasks")
    creator = relationship("User", back_populates="created_tasks")
    answers = relationship("Answer", back_populates="task")


class Answer(Base):
    __tablename__ = "answers"
    
    id = Column(Integer, primary_key=True, index=True)
    
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    
    student_response_image = Column(String, nullable=True)
    llm_verdict = Column(Text, nullable=True)
    status = Column(SQLEnum(AnswerStatus), default=AnswerStatus.PENDING)
    
    student = relationship("User", back_populates="submitted_answers")
    task = relationship("Task", back_populates="answers")