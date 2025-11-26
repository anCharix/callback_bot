from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import (Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardMarkup,
                           KeyboardButton)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from testing import questions_and_answers

from sqlalchemy import select

from database.session import get_session
from database.models import User, Employee
from database.functions import add_telegram_user, add_success_task, get_success_tasks, get_feedbacks_by_username, \
    add_feedback

router = Router()


class UsersAnswers(StatesGroup):
    task = State()
    place = State()
    conditions = State()


class Feedback(StatesGroup):
    username = State()
    feedback = State()
    rate = State()


@router.message(CommandStart())
async def command_start_handler(message: Message, bot: Bot) -> None:
    username = message.from_user.username
    async for session in get_session():
        # Можно добавить проверку, есть ли уже такой пользователь, чтобы не дублировать
        user = await session.execute(
            select(User).where(User.username == username)
        )
        existing_user = user.scalars().first()

        if not existing_user:
            keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="Отправить номера телефона", request_contact=True)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            await message.answer("👋 Добро пожаловать! Чтобы продолжить, пожалуйста, поделитесь своим номером телефона, нажав на кнопку ниже. Это нужно для вашей идентификации."
            , reply_markup=keyboard)
        else:
            kb_list = [[InlineKeyboardButton(text="🖋️ Создать заявку", callback_data="task_for_channel")],
                       [InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
                       InlineKeyboardButton(text="❗ Правила", callback_data="rules")],
                       [InlineKeyboardButton(text="👷‍♂️ Проверить рабочего", callback_data="check_employer")]]
            markup = InlineKeyboardMarkup(inline_keyboard=kb_list)
            await message.answer(
                text="🎉 Отлично, вы прошли верификацию!\nТеперь вы можете отправлять заявки прямо в наш канал.\n\nВыберите действие ниже 👇",
                reply_markup=markup)



@router.message(F.contact)
async def get_contact(message: Message, bot: Bot) -> None:
    phone_number = message.contact.phone_number

    #Добавляем пользователя в БД
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()

    async for session in get_session():
        # Добавляем юзера
        await add_telegram_user(session, user_id, username, full_name, phone_number, 0, 0)

        kb_list = [[InlineKeyboardButton(text="🖋️ Создать заявку", callback_data="task_for_channel")],
                   [InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
                    InlineKeyboardButton(text="❗ Правила", callback_data="rules")],
                   [InlineKeyboardButton(text="👷‍♂️ Проверить рабочего", callback_data="check_employer")]]
        markup = InlineKeyboardMarkup(inline_keyboard=kb_list)
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
        await message.delete()
        await message.answer(text="🎉 Отлично, вы прошли верификацию!\nТеперь вы можете отправлять заявки прямо в наш канал.\n\nВыберите действие ниже 👇",
                             reply_markup=markup)


@router.callback_query(F.data == "task_for_channel" or F.data == "cancel_task")
async def request_task_information(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📝 Пожалуйста, отправьте подробную информацию о вашей заявке.\nЧем точнее описание, тем быстрее найдётся исполнитель!"
)
    await state.set_state(UsersAnswers.task)


@router.message(F.text, UsersAnswers.task)
async def apply_place(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(task=message.text)
    await message.answer(
        "📝 Пожалуйста, отправьте точный адресс выполения работ."
        )
    await state.set_state(UsersAnswers.place)


@router.message(F.text, UsersAnswers.place)
async def apply_place(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(place=message.text)
    await message.answer(
        "📝 Пожалуйста, отправьте требования к кандидатам."
        )
    await state.set_state(UsersAnswers.conditions)


@router.message(F.text, UsersAnswers.conditions)
async def apply_conditions(message: Message, state: FSMContext, bot: Bot):
    kb_list = [[InlineKeyboardButton(text="Отправить", callback_data="send_task")],
               [InlineKeyboardButton(text="Отменить", callback_data="cancel_task")]]
    markup = InlineKeyboardMarkup(inline_keyboard=kb_list)
    await state.update_data(conditions=message.text)
    await message.answer("🔍 Проверьте информацию:\nЕсли всё правильно — нажмите «Отправить».\nЕсли хотите внести правки — нажмите «Отменить».",
                            reply_markup=markup)


@router.callback_query(F.data == "send_task")
async def send_task(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    task_information = data.get("task", 0)
    place = data.get("place", 0)
    conditions = data.get("conditions", 0)

    async for session in get_session():
        telegram_id = int(callback.from_user.id)

        success_task = await get_success_tasks(session, telegram_id=telegram_id)
        await add_success_task(session, telegram_id=telegram_id)

    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id - 1)

    new_task = (
    "🚨 *Новая заявка на выполнение работ!*\n\n"
    f"👤 *Заказчик*: @{callback.from_user.username}\n\n"
    f"📄 *Успешных заявок*: {success_task}\n\n"
    f"📝 *Описание:*\n{task_information}\n\n"
    f"📌 *Требования:*\n{conditions}\n\n"
    f"📍 *Место работы:*\n{place}\n\n"
    "💬 Для связи с заказчиком нажмите кнопку ниже 👇"
    )

    meneger_url = f'https://t.me/{callback.from_user.username}'
    markup = InlineKeyboardBuilder()
    markup.add(InlineKeyboardButton(text="Заказчик", url=meneger_url))
    await bot.send_message(chat_id=-1003088612163, text=new_task, reply_markup=markup.as_markup(), parse_mode="markdown")

    kb_list = [[InlineKeyboardButton(text="🖋️ Создать заявку", callback_data="task_for_channel")],
               [InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
                InlineKeyboardButton(text="❗ Правила", callback_data="rules")],
               [InlineKeyboardButton(text="👷‍♂️ Проверить рабочего", callback_data="check_employer")]]
    markup = InlineKeyboardMarkup(inline_keyboard=kb_list)
    await callback.message.edit_text("✅ Заявка успешно отправлена!\nОжидайте откликов от исполнителей.",
                                     reply_markup=markup)

    await state.clear()



@router.callback_query(F.data == "balance")
async def balance(callback: CallbackQuery):
    kb_list = [[InlineKeyboardButton(text="Назад", callback_data="cancel")]]
    markup = InlineKeyboardMarkup(inline_keyboard=kb_list)
    await callback.message.edit_text("Бот работает в тестовом режиме, оплата за использование временно не требуется.",
                                     reply_markup=markup)


@router.callback_query(F.data == "rules")
async def balance(callback: CallbackQuery):
    kb_list = [[InlineKeyboardButton(text="Назад", callback_data="cancel")]]
    markup = InlineKeyboardMarkup(inline_keyboard=kb_list)
    rules_text = (
        "📋 <b>Правила использования бота</b>:\n\n"
        "1. Бот предназначен для подачи заявок в каналы.\n"
        "2. Запрещено размещать:\n"
        "   • Спам, рекламу казино/ставок/крипты\n"
        "   • Контент 18+ и запрещённые материалы\n"
        "   • Оскорбления, нецензурную лексику\n"
        "   • Ложную или вводящую в заблуждение информацию\n\n"
        "3. Соблюдайте формат заявки:\n"
        "   • Пишите чётко и грамотно\n"
        "   • Указывайте необходимые контакты\n"
        "   • Без излишних смайлов и CAPS LOCK\n\n"
        "4. Некоторые заявки проходят модерацию.\n"
        "5. Нарушение правил может привести к блокировке.\n\n"
        "ℹ️ Используя бота, вы соглашаетесь с этими правилами.\n"
        "По вопросам: @support_username"
    )
    await callback.message.edit_text(text=rules_text,
                                     reply_markup=markup,
                                     parse_mode="HTML")


@router.callback_query(F.data == "check_employer")
async def check_employer(callback: CallbackQuery):
    kb_list = [[InlineKeyboardButton(text="Назад", callback_data="cancel")]]
    markup = InlineKeyboardMarkup(inline_keyboard=kb_list)
    rules_text = (
        "<b>✉️ Отправьте мне @username пользователя</b>.\n"
        "Я пришлю вам отзывы о нём, если они есть в базе данных.\n"
        "Если отзывов нет — вы получите сообщение: <i>«Данных нет»</i>."
    )
    await callback.message.edit_text(text=rules_text,
                                     reply_markup=markup,
                                     parse_mode="HTML")


@router.message(F.text.startswith("@"))
async def get_username(message: Message, state: FSMContext):
    username = message.text.strip().lstrip("@")

    kb_list = [[InlineKeyboardButton(text="Оставить отзыв", callback_data="take_feedback")],
               [InlineKeyboardButton(text="Назад", callback_data="cancel")]]
    markup = InlineKeyboardMarkup(inline_keyboard=kb_list)

    async for session in get_session():
        feedbacks = await get_feedbacks_by_username(session, username=username)

    await state.update_data(username=username)
    if feedbacks:
        feedback_text = "\n".join(f"• {fb}" for fb in feedbacks[0])
        await message.answer(
            f"<b>Отзывы о @{username}:</b>\n{feedback_text}\n\n"
            f"<b>Рейтинг:</b> {feedbacks[1]}",
            parse_mode="HTML",
            reply_markup=markup
        )
    else:
        await message.answer(f"ℹ️ Отзывов о @{username} не найдено.",
                             reply_markup=markup)


@router.callback_query(F.data == "take_feedback")
async def take_feedback(callback: CallbackQuery, state: FSMContext):
    kb_list = [[InlineKeyboardButton(text="Отменить", callback_data="cancel")]]
    markup = InlineKeyboardMarkup(inline_keyboard=kb_list)
    text = (
        "<b>✉️ Отправьте мне отзыв о пользователе и я его сохраню</b>."
    )
    await callback.message.edit_text(text=text,
                                     reply_markup=markup,
                                     parse_mode="HTML")
    await state.set_state(Feedback.feedback)


@router.message(F.text, Feedback.feedback)
async def take_rate(message: Message, state: FSMContext):
    kb_list = [[InlineKeyboardButton(text="⭐", callback_data="rate_1")],
               [InlineKeyboardButton(text="⭐⭐", callback_data="rate_2")],
               [InlineKeyboardButton(text="⭐⭐⭐", callback_data="rate_3")],
               [InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data="rate_4")],
               [InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data="rate_5")],
               [InlineKeyboardButton(text="Отменить", callback_data="cancel")]]
    markup = InlineKeyboardMarkup(inline_keyboard=kb_list)
    await state.update_data(feedback=message.text)

    await message.answer("<b>✉️ Оцените работника по пятибальной шкале</b>.", reply_markup=markup, parse_mode="HTML")
    await state.set_state(Feedback.rate)


@router.callback_query(F.data.startswith("rate_"), Feedback.rate)
async def save_feedback(callback: CallbackQuery, state: FSMContext):
    rate_str = callback.data.split("_")[1]  # "rate_3" → "3"
    rate = int(rate_str)

    data = await state.get_data()
    feedback_text = data.get("feedback")
    username = data.get("username")

    async for session in get_session():
        await add_feedback(session, username=username, text=feedback_text, rate=rate)

    kb_list = [[InlineKeyboardButton(text="В меню", callback_data="cancel")]]
    markup = InlineKeyboardMarkup(inline_keyboard=kb_list)
    await callback.message.edit_text("✅ Спасибо за ваш отзыв и оценку!", reply_markup=markup)
    await state.clear()



@router.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    kb_list = [[InlineKeyboardButton(text="🖋️ Создать заявку", callback_data="task_for_channel")],
               [InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
                InlineKeyboardButton(text="❗ Правила", callback_data="rules")],
               [InlineKeyboardButton(text="👷‍♂️ Проверить рабочего", callback_data="check_employer")]]
    markup = InlineKeyboardMarkup(inline_keyboard=kb_list)
    await callback.message.edit_text(text="Выберите действие ниже 👇",
                                     reply_markup=markup)