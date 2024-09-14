import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import psycopg2

# Логирование для отслеживания работы бота
logging.basicConfig(level=logging.INFO)

# Инициализация памяти для хранения состояний FSM
storage = MemoryStorage()

# Инициализируем бот и диспетчер
bot = Bot(token="####")
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Устанавливаем соединение с базой данных
conn = psycopg2.connect(
    dbname="cherdak",
    user="postgres",
    password="####",
    host="localhost"
)
cursor = conn.cursor()

# Создаём кнопки для ассортимента табака, чая, местоположения и админ-панели
button_tobacco = KeyboardButton("🍂 Табак")
button_tea = KeyboardButton("🍵 Чай")
button_location = KeyboardButton("📍 Как нас найти?")
button_admin = KeyboardButton("⚙️ Админ панель")
keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
keyboard.add(button_tobacco, button_tea, button_location, button_admin)

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """Приветствие и отображение главных кнопок"""
    await bot.send_message(chat_id=message.chat.id,
                           text="Вас приветствует кальянный бот 'Чердак'",
                           reply_markup=keyboard)

# Обработчик нажатия кнопки 🍂 Ассортимент табака
@dp.message_handler(lambda message: message.text == "🍂 Табак")
async def send_tobacco_list(message: types.Message):
    """Запрос данных из таблицы табака"""
    cursor.execute("SELECT name, flavor, available FROM tobacco")
    tobaccos = cursor.fetchall()

    """Формирование списка табака"""
    if tobaccos:
        tobacco_list = "🍂 *Доступные сорта табака:*\n\n"
        for tobacco in tobaccos:
            name, flavor, available = tobacco
            available_text = "✅ *В наличии*" if available else "❌ *Нет в наличии*"
            tobacco_list += f"**Название:** {name}\n**Вкус:** {flavor}\n{available_text}\n\n"
            tobacco_list += "----------------------\n"
    else:
        tobacco_list = "😔 _К сожалению, сейчас нет доступных сортов табака._"

    """Отправка списка пользователю"""
    await bot.send_message(message.chat.id, tobacco_list, parse_mode="Markdown")

# Обработчик нажатия кнопки 🍵 Ассортимент чая
@dp.message_handler(lambda message: message.text == "🍵 Чай")
async def send_tea_list(message: types.Message):
    """Запрос данных из таблицы чая"""
    cursor.execute("SELECT name, description, available FROM tea")
    teas = cursor.fetchall()

    """Формирование списка чая"""
    if teas:
        tea_list = "🍵 *Доступные сорта чая:*\n\n"
        for tea in teas:
            name, description, available = tea
            available_text = "✅ *В наличии*" if available else "❌ *Нет в наличии*"
            tea_list += f"**Название:** {name}\n**Описание:** {description}\n{available_text}\n\n"
            tea_list += "----------------------\n"
    else:
        tea_list = "😔 _К сожалению, весь чай выпит, но мы скоро завезем еще!_ 😉"

    """Отправка списка пользователю"""
    await bot.send_message(message.chat.id, tea_list, parse_mode="Markdown")

# Обработчик нажатия кнопки 📍 Как нас найти?
@dp.message_handler(lambda message: message.text == "📍 Как нас найти?")
async def send_location(message: types.Message):
    """Отправка ссылки на местоположение через Яндекс.Карты"""
    location_link = "https://yandex.ru/maps/org/cherdak/134444637764/?ll=39.964232%2C53.244942&z=16.59"
    await bot.send_message(
        message.chat.id,
        f"Наше местоположение: [Кальянная 'Чердак']({location_link})",
        parse_mode="Markdown"
    )

# Классы для управления состояниями админ-панели
class AddItemStates(StatesGroup):
    """Ожидание выбора категории, названия, описания, наличия и редактирования"""
    waiting_for_category = State()
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_availability = State()
    waiting_for_edit_action = State()
    waiting_for_selection = State()
    waiting_for_edit_detail = State()  # Новое состояние для выбора, что редактировать
    waiting_for_new_name = State()
    waiting_for_new_description = State()
    waiting_for_new_availability = State()

def is_admin(user_id):
    """Проверка, является ли пользователь администратором"""
    cursor.execute("SELECT * FROM admins WHERE telegram_id = %s", (user_id,))
    return cursor.fetchone() is not None

def get_admin_menu_keyboard():
    """Генерация клавиатуры для админ-панели"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["Добавить табак", "Добавить чай", "Редактировать позиции", "Выйти"]
    keyboard.add(*buttons)
    return keyboard

def get_availability_keyboard():
    """Клавиатура для выбора статуса наличия товара или отмены"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["В наличии", "Нет в наличии", "Отмена"]
    keyboard.add(*buttons)
    return keyboard

def get_items_keyboard(items):
    """Функция для динамической генерации кнопок с позициями и кнопкой 'Отмена'"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for item in items:
        name = item[2]
        button = KeyboardButton(name)
        keyboard.add(button)
    """Добавляем кнопку 'Отмена'"""
    cancel_button = KeyboardButton("Отмена")
    keyboard.add(cancel_button)
    return keyboard

def get_edit_delete_keyboard():
    """Клавиатура для выбора действия: Редактировать, Удалить или Отмена"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["Редактировать", "Удалить", "Отмена"]
    keyboard.add(*buttons)
    return keyboard

def get_edit_detail_keyboard():
    """Клавиатура для выбора детали редактирования или отмены"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["Название", "Описание", "Статус наличия", "Отмена"]
    keyboard.add(*buttons)
    return keyboard

def get_cancel_keyboard():
    """Клавиатура с кнопкой 'Отмена'"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    cancel_button = KeyboardButton("Отмена")
    keyboard.add(cancel_button)
    return keyboard

# Обработчик команды выхода из админ-панели
@dp.message_handler(lambda message: message.text == "Выйти", state="*")
async def admin_exit(message: types.Message, state: FSMContext):
    """Завершение сеанса админ-панели"""
    await state.finish()
    await message.answer("Вы вышли из админ-панели.", reply_markup=keyboard)

# Обработчик нажатия кнопки ⚙️ Админ панель
@dp.message_handler(lambda message: message.text == "⚙️ Админ панель", state="*")
async def admin_panel(message: types.Message, state: FSMContext):
    """Отображение админ-панели"""
    if is_admin(message.from_user.id):
        await message.answer("Добро пожаловать в админ-панель. Выберите действие:", reply_markup=get_admin_menu_keyboard())
        await AddItemStates.waiting_for_category.set()
    else:
        await message.answer("У вас нет доступа к админ-панели")

# Обработчик выбора категории для добавления товара
@dp.message_handler(state=AddItemStates.waiting_for_category)
async def choose_category(message: types.Message, state: FSMContext):
    """Обработка выбора действия в админ-панели"""
    if message.text == "Добавить табак":
        await state.update_data(category="табак")
        await message.answer("Введите название табака:", reply_markup=get_cancel_keyboard())
        await AddItemStates.waiting_for_name.set()
    elif message.text == "Добавить чай":
        await state.update_data(category="чай")
        await message.answer("Введите название чая:", reply_markup=get_cancel_keyboard())
        await AddItemStates.waiting_for_name.set()
    elif message.text == "Редактировать позиции":
        await select_item_for_edit_or_delete(message, state)
    elif message.text == "Выйти":
        await admin_exit(message, state)
    else:
        await message.answer("Пожалуйста, выберите действие из предложенных опций.")

# Обработчик добавления названия товара
@dp.message_handler(state=AddItemStates.waiting_for_name)
async def add_name(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_action(message, state)
        return
    """Ввод названия товара"""
    await state.update_data(name=message.text)
    await message.answer("Введите описание товара:", reply_markup=get_cancel_keyboard())
    await AddItemStates.waiting_for_description.set()

# Обработчик добавления описания товара
@dp.message_handler(state=AddItemStates.waiting_for_description)
async def add_description(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_action(message, state)
        return
    """Ввод описания товара"""
    await state.update_data(description=message.text)
    await message.answer("Товар в наличии?", reply_markup=get_availability_keyboard())
    await AddItemStates.waiting_for_availability.set()

# Обработчик добавления товара в базу данных
@dp.message_handler(state=AddItemStates.waiting_for_availability)
async def add_availability(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_action(message, state)
        return
    """Добавление товара в базу данных"""
    availability = message.text == "В наличии"
    data = await state.get_data()

    """Вставка товара в нужную таблицу"""
    if data["category"] == 'табак':
        cursor.execute(
            "INSERT INTO tobacco (name, flavor, available) VALUES (%s, %s, %s)",
            (data['name'], data['description'], availability)
        )
    elif data["category"] == 'чай':
        cursor.execute(
            "INSERT INTO tea (name, description, available) VALUES (%s, %s, %s)",
            (data['name'], data['description'], availability)
        )

    conn.commit()
    await message.answer("Товар успешно добавлен.")
    await message.answer("Вы вернулись в админ-панель. Выберите действие:", reply_markup=get_admin_menu_keyboard())
    await AddItemStates.waiting_for_category.set()

# Обработчик для редактирования или удаления позиций
@dp.message_handler(lambda message: message.text == "Редактировать позиции" or message.text == "Удалить позиции", state="*")
async def select_item_for_edit_or_delete(message: types.Message, state: FSMContext):
    """Сохранение действия и выбор позиции для редактирования/удаления"""
    action = message.text
    await state.update_data(action=action)

    """Запрос всех позиций из таблиц табака и чая"""
    cursor.execute(
        "SELECT 'tobacco' AS category, id, name FROM tobacco UNION SELECT 'tea' AS category, id, name FROM tea"
    )
    items = cursor.fetchall()

    if items:
        """Генерация клавиатуры для выбора позиции"""
        keyboard = get_items_keyboard(items)
        await message.answer("📋 Выберите позицию для редактирования или удаления:", reply_markup=keyboard)

        """Установка состояния ожидания выбора позиции"""
        await AddItemStates.waiting_for_selection.set()
    else:
        await message.answer("😔 _Нет доступных позиций._")

# Обработчик выбора позиций
@dp.message_handler(state=AddItemStates.waiting_for_selection)
async def handle_item_selection(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_action(message, state)
        return
    """Обработка выбора позиции для редактирования или удаления"""
    cursor.execute(
        "SELECT 'tobacco' AS category, id, name FROM tobacco UNION SELECT 'tea' AS category, id, name FROM tea"
    )
    items = cursor.fetchall()

    """Поиск выбранной позиции по имени кнопки"""
    selected_item = next((item for item in items if item[2] == message.text), None)

    if selected_item:
        """Сохранение данных о выбранной позиции"""
        await state.update_data(item_id=selected_item[1], category=selected_item[0])
        await message.answer(
            f"Вы выбрали {selected_item[2]}. Что вы хотите сделать?",
            reply_markup=get_edit_delete_keyboard()
        )
        await AddItemStates.waiting_for_edit_action.set()
    else:
        await message.answer("Неверный выбор. Попробуйте еще раз.")

# Обработчик редактирования или удаления позиции
@dp.message_handler(state=AddItemStates.waiting_for_edit_action)
async def handle_edit_or_delete_action(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_action(message, state)
        return
    action = message.text.lower()

    if action == "редактировать":
        """Предложить, что именно редактировать: название, описание или статус наличия"""
        await message.answer(
            "Что вы хотите редактировать?",
            reply_markup=get_edit_detail_keyboard()
        )
        await AddItemStates.waiting_for_edit_detail.set()
    elif action == "удалить":
        data = await state.get_data()
        item_id, category = data['item_id'], data['category']

        # Удаление позиции
        if category == 'tobacco':
            cursor.execute("DELETE FROM tobacco WHERE id = %s", (item_id,))
        else:
            cursor.execute("DELETE FROM tea WHERE id = %s", (item_id,))

        conn.commit()
        await message.answer("Позиция успешно удалена.", reply_markup=types.ReplyKeyboardRemove())
        await message.answer(
            "Вы вернулись в админ-панель. Выберите действие:",
            reply_markup=get_admin_menu_keyboard()
        )
        await AddItemStates.waiting_for_category.set()
    else:
        await message.answer(
            "Неверное действие. Пожалуйста, выберите *Редактировать* или *Удалить*.",
            reply_markup=get_edit_delete_keyboard()
        )

# Обработчик редактирования деталей позиции
@dp.message_handler(state=AddItemStates.waiting_for_edit_detail)
async def handle_edit_detail(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_action(message, state)
        return
    detail = message.text.lower()

    if detail == "название":
        await message.answer("Введите новое название:", reply_markup=get_cancel_keyboard())
        await AddItemStates.waiting_for_new_name.set()
    elif detail == "описание":
        await message.answer("Введите новое описание:", reply_markup=get_cancel_keyboard())
        await AddItemStates.waiting_for_new_description.set()
    elif detail == "статус наличия":
        await message.answer("Выберите статус наличия:", reply_markup=get_availability_keyboard())
        await AddItemStates.waiting_for_new_availability.set()
    else:
        await message.answer(
            "Неверный выбор. Пожалуйста, выберите *Название*, *Описание* или *Статус наличия*.",
            reply_markup=get_edit_detail_keyboard()
        )

# Обработчик изменения названия
@dp.message_handler(state=AddItemStates.waiting_for_new_name)
async def update_item_name(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_action(message, state)
        return
    new_name = message.text
    data = await state.get_data()
    item_id, category = data['item_id'], data['category']

    """Обновление названия в зависимости от категории"""
    if category == 'tobacco':
        cursor.execute("UPDATE tobacco SET name = %s WHERE id = %s", (new_name, item_id))
    else:
        cursor.execute("UPDATE tea SET name = %s WHERE id = %s", (new_name, item_id))

    conn.commit()
    await message.answer("Название успешно обновлено.", reply_markup=types.ReplyKeyboardRemove())
    await message.answer(
        "Вы вернулись в админ-панель. Выберите действие:",
        reply_markup=get_admin_menu_keyboard()
    )
    await AddItemStates.waiting_for_category.set()

# Обработчик изменения описания
@dp.message_handler(state=AddItemStates.waiting_for_new_description)
async def update_item_description(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_action(message, state)
        return
    new_description = message.text
    data = await state.get_data()
    item_id, category = data['item_id'], data['category']

    """Обновление описания в зависимости от категории"""
    if category == 'tobacco':
        cursor.execute("UPDATE tobacco SET flavor = %s WHERE id = %s", (new_description, item_id))
    else:
        cursor.execute("UPDATE tea SET description = %s WHERE id = %s", (new_description, item_id))

    conn.commit()
    await message.answer("Описание успешно обновлено.", reply_markup=types.ReplyKeyboardRemove())
    await message.answer(
        "Вы вернулись в админ-панель. Выберите действие:",
        reply_markup=get_admin_menu_keyboard()
    )
    await AddItemStates.waiting_for_category.set()

# Обработчик изменения статуса наличия
@dp.message_handler(state=AddItemStates.waiting_for_new_availability)
async def update_item_availability(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cancel_action(message, state)
        return
    availability = message.text == "В наличии"
    data = await state.get_data()
    item_id, category = data['item_id'], data['category']

    """Обновление статуса наличия в зависимости от категории"""
    if category == 'tobacco':
        cursor.execute("UPDATE tobacco SET available = %s WHERE id = %s", (availability, item_id))
    else:
        cursor.execute("UPDATE tea SET available = %s WHERE id = %s", (availability, item_id))

    conn.commit()
    await message.answer("Статус наличия успешно обновлен.", reply_markup=types.ReplyKeyboardRemove())
    await message.answer("Вы вернулись в админ-панель. Выберите действие:", reply_markup=get_admin_menu_keyboard())
    await AddItemStates.waiting_for_category.set()

# Обработчик команды 'Отмена' во время любого состояния
@dp.message_handler(lambda message: message.text == "Отмена", state="*")
async def cancel_action(message: types.Message, state: FSMContext):
    """Обработка команды 'Отмена' во время любого состояния"""
    await state.finish()
    await message.answer("Действие отменено.", reply_markup=get_admin_menu_keyboard())
    await AddItemStates.waiting_for_category.set()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
