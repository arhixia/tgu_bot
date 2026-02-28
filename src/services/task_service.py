from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models import Answer, AnswerStatus, Group, Task, TaskType, Theme, User


async def get_all_themes(session: AsyncSession) -> list[Theme]:
    result = await session.execute(select(Theme))
    return result.scalars().all()


async def get_theme_by_id(session: AsyncSession, theme_id: int) -> Theme | None:
    result = await session.execute(select(Theme).where(Theme.id == theme_id))
    return result.scalar_one_or_none()

async def get_next_task(
    session: AsyncSession,
    student_id: int,
    theme_id: int,
    mode: str
) -> Task | None:
    task_type = TaskType.TRAINING if mode == "study" else TaskType.TESTING

    student_subq = (
        select(Group.teacher_id)
        .join(User, User.group_id == Group.id)
        .where(User.id == student_id)
        .scalar_subquery()
    )

    # Задания которые студент уже решал или пропустил
    answered_subq = (
        select(Answer.task_id)
        .where(Answer.student_id == student_id)
    )

    result = await session.execute(
        select(Task)
        .where(Task.theme_id == theme_id)
        .where(Task.task_type == task_type)
        .where(Task.is_approved == True)
        .where(Task.id.not_in(answered_subq))
        .where(Task.creator_id == student_subq)  
        .limit(1)
    )
    return result.scalar_one_or_none()


async def save_task(
    session: AsyncSession,
    theme_id: int,
    creator_id: int,
    task_type: TaskType,
    image_url: str,
    description: str | None = None,
    hint: str | None = None,
    correct_answer: str | None = None,
) -> Task:
    task = Task(
        theme_id=theme_id,
        creator_id=creator_id,
        task_type=task_type,
        image_url=image_url,
        description=description,
        hint=hint,
        correct_answer=correct_answer,
        is_approved=True,  
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def save_answer(
    session: AsyncSession,
    student_id:int,
    task_id:int,
    status:AnswerStatus,
    student_response_image: str | None = None,
    llm_verdict: str | None = None,
) -> Answer:
    answer = Answer(
        student_id = student_id,
        task_id = task_id,
        status = status,
        student_response_image = student_response_image,
        llm_verdict = llm_verdict
    )
    session.add(answer)
    await session.commit()
    await session.refresh(answer)
    return answer
    