from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, String, Integer, ARRAY
from .session import Base
import datetime


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[str | None] = mapped_column(String(50))
    full_name: Mapped[str | None] = mapped_column(String(100))
    registered_at: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    phone_number: Mapped[str | None] = mapped_column(String(12))
    balance: Mapped[int] = mapped_column(Integer)
    success_task: Mapped[int] = mapped_column(Integer)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(50))
    feedbacks: Mapped[list[str]] = mapped_column(ARRAY(String))
    rates: Mapped[list[int]] = mapped_column(ARRAY(Integer))