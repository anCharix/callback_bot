import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from .models import User, Employee


async def add_telegram_user(session: AsyncSession, user_id: int, username: str | None, full_name: str | None,
                            phone_number: str | None, balance: int | None, success_task: int | None):
    new_user = User(
        user_id=user_id,
        username=username,
        full_name=full_name,
        registered_at=datetime.datetime.utcnow(),
        phone_number=phone_number,
        balance=balance,
        success_task=success_task
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


async def add_success_task(session: AsyncSession, telegram_id: int) -> int:
    user = await get_user_by_telegram_id(session, telegram_id)
    user.success_task += 1
    await session.commit()
    return user.success_task


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.user_id == telegram_id))
    return result.scalars().first()


async def get_success_tasks(session: AsyncSession, telegram_id: int) -> int:
    user = await get_user_by_telegram_id(session, telegram_id)
    if not user:
        return 0  # Если пользователь не найден, вернуть 0 или None
    return user.success_task


async def add_feedback(session: AsyncSession, username: str, text: str, rate: int):
    result = await session.execute(select(Employee).where(Employee.username == username))
    employee = result.scalars().first()

    if not employee:
        employee = Employee(
            username=username,
            feedbacks=[text],
            rates=[rate]
        )
        session.add(employee)
        await session.commit()
        return

    if not employee.feedbacks:
        employee.feedbacks = []
    if not employee.rates:
        employee.rates = []

    employee.feedbacks.append(text)
    employee.rates.append(rate)

    flag_modified(employee, "feedbacks")
    flag_modified(employee, "rates")

    await session.commit()


async def get_feedbacks_by_username(session: AsyncSession, username: str) -> (list[str], int):
    result = await session.execute(select(Employee).where(Employee.username == username))
    employer = result.scalars().first()

    if employer and employer.feedbacks and employer.rates:
        rate = sum(employer.rates) / len(employer.rates) #оценка пользователя
        rate = round(float(rate), 2)
        return employer.feedbacks, rate

    return None  # если отзывов нет или пользователь не найден


#Проверка на админов
async def check_admins(user_id):
    admins_id = [285907768, 1132743840, 1443646292]

    if user_id in admins_id:
        return True
    return False