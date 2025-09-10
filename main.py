import sqlite3
import os
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

# Устанавливаем размер окна для удобства тестирования
Window.size = (400, 600)

# =============================
# 🎨 ЦВЕТОВЫЕ СХЕМЫ ДЛЯ КАТЕГОРИЙ
# =============================

CATEGORY_COLORS = {
    "Виски": (0.8, 0.6, 0.2, 1),      # Золотой
    "Водка": (0.9, 0.9, 0.9, 1),      # Серебристый
    "Ром": (0.6, 0.3, 0.1, 1),        # Коричневый
    "Текила": (0.9, 0.8, 0.2, 1),     # Желтый
    "Вино": (0.7, 0.1, 0.3, 1),       # Бордовый
    "Пиво": (1.0, 0.7, 0.2, 1),       # Оранжевый
    "Ликёр": (0.8, 0.4, 0.8, 1),      # Фиолетовый
    "Другое": (0.5, 0.5, 0.5, 1),     # Серый
    "Все категории": (0.3, 0.6, 0.9, 1) # Синий для фильтра
}

# =============================
# 🗃️ ФУНКЦИИ РАБОТЫ С БАЗОЙ ДАННЫХ
# =============================

def get_db_path():
    """Возвращает полный путь к файлу базы данных в папке проекта."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bar_inventory.db')

def init_db():
    """Инициализирует базу данных: создаёт таблицы, если их нет."""
    db_path = get_db_path()
    print(f"Инициализация БД: {db_path}")

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Таблица категорий
    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')

    # Предустановленные категории
    default_categories = [
        ("Виски",), ("Водка",), ("Ром",), ("Текила",),
        ("Вино",), ("Пиво",), ("Ликёр",), ("Другое",)
    ]
    c.executemany("INSERT OR IGNORE INTO categories (name) VALUES (?)", default_categories)

    # Таблица бутылок с внешним ключом на категорию
    c.execute('''
        CREATE TABLE IF NOT EXISTS bottles (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            empty_weight REAL NOT NULL,
            total_volume REAL NOT NULL,
            category_id INTEGER NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    ''')

    # Таблица истории инвентаризации
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY,
            bottle_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            current_weight REAL NOT NULL,
            current_volume REAL NOT NULL,
            FOREIGN KEY (bottle_id) REFERENCES bottles(id)
        )
    ''')

    # Индексы для ускорения запросов
    c.execute("CREATE INDEX IF NOT EXISTS idx_inventory_bottle_id ON inventory(bottle_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_inventory_timestamp ON inventory(timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_bottles_category ON bottles(category_id)")

    conn.commit()
    conn.close()

def get_all_categories():
    """Возвращает список всех категорий: [(id, name), ...]"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, name FROM categories ORDER BY name")
    categories = c.fetchall()
    conn.close()
    return categories

def get_bottles_with_filter(search_text="", category_filter=""):
    """Возвращает список бутылок с фильтрацией"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    query = '''
        SELECT bottles.id, bottles.name, categories.name, bottles.empty_weight, bottles.total_volume
        FROM bottles
        JOIN categories ON bottles.category_id = categories.id
    '''
    
    conditions = []
    params = []
    
    if search_text:
        conditions.append("bottles.name LIKE ?")
        params.append(f"%{search_text}%")
    
    if category_filter and category_filter != "Все категории":
        conditions.append("categories.name = ?")
        params.append(category_filter)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY bottles.name"
    
    c.execute(query, params)
    bottles = c.fetchall()
    conn.close()
    return bottles

def get_all_bottles_with_categories():
    """Возвращает список бутылок с именами категорий: [(id, name, category_name), ...]"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        SELECT bottles.id, bottles.name, categories.name
        FROM bottles
        JOIN categories ON bottles.category_id = categories.id
        ORDER BY bottles.name
    ''')
    bottles = c.fetchall()
    conn.close()
    return bottles

def get_bottle_by_id(bottle_id):
    """Возвращает данные бутылки по ID"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        SELECT bottles.id, bottles.name, bottles.empty_weight, bottles.total_volume, categories.name
        FROM bottles
        JOIN categories ON bottles.category_id = categories.id
        WHERE bottles.id = ?
    ''', (bottle_id,))
    bottle = c.fetchone()
    conn.close()
    return bottle

def update_bottle(bottle_id, name, empty_weight, total_volume, category_name):
    """Обновляет данные бутылки"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Получаем ID категории
    c.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
    category_id = c.fetchone()[0]
    
    c.execute('''
        UPDATE bottles 
        SET name = ?, empty_weight = ?, total_volume = ?, category_id = ?
        WHERE id = ?
    ''', (name, empty_weight, total_volume, category_id, bottle_id))
    
    conn.commit()
    conn.close()

def export_inventory_to_excel():
    """Экспортирует историю инвентаризации в Excel-файл 'inventory_export.xlsx' в папке проекта."""
    try:
        from openpyxl import Workbook
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('''
            SELECT inventory.timestamp, bottles.name, categories.name, inventory.current_volume 
            FROM inventory
            JOIN bottles ON inventory.bottle_id = bottles.id
            JOIN categories ON bottles.category_id = categories.id
            ORDER BY inventory.timestamp DESC
        ''')
        records = c.fetchall()
        conn.close()

        wb = Workbook()
        ws = wb.active
        ws.title = "История инвентаризации"
        ws.append(["Дата и время", "Название", "Категория", "Объём (мл)"])

        for record in records:
            ws.append(record)

        export_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory_export.xlsx')
        wb.save(export_path)

        return export_path

    except Exception as e:
        print(f"Ошибка экспорта в Excel: {e}")
        return None

# =============================
# 🧩 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================

def show_popup(title, message):
    """Показывает всплывающее окно с заголовком и сообщением."""
    popup = Popup(
        title=title,
        content=Label(text=message, halign='center', valign='middle'),
        size_hint=(0.8, 0.3)
    )
    popup.open()

# =============================
# 🎨 КАРТОЧКА БУТЫЛКИ
# =============================

class BottleCard(BoxLayout):
    def __init__(self, bottle_id, name, category, empty_weight, total_volume, on_edit=None, on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(120)
        self.padding = dp(10)
        self.spacing = dp(5)
        
        # Фон с цветом категории
        with self.canvas.before:
            color = CATEGORY_COLORS.get(category, CATEGORY_COLORS["Другое"])
            Color(*color)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)
        
        # Заголовок с названием и категорией
        header = BoxLayout(size_hint_y=None, height=dp(30))
        name_label = Label(
            text=f"[b]{name}[/b]",
            markup=True,
            halign='left',
            text_size=(None, None)
        )
        category_label = Label(
            text=f"[i]{category}[/i]",
            markup=True,
            halign='right',
            color=(0, 0, 0, 1)
        )
        header.add_widget(name_label)
        header.add_widget(category_label)
        
        # Параметры
        params = BoxLayout(size_hint_y=None, height=dp(25))
        params.add_widget(Label(
            text=f"Пустая: {empty_weight}г",
            font_size=dp(12),
            halign='left'
        ))
        params.add_widget(Label(
            text=f"Объём: {total_volume}мл",
            font_size=dp(12),
            halign='right'
        ))
        
        # Кнопки действий
        buttons = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
        
        edit_btn = Button(
            text="✏️",
            size_hint_x=None,
            width=dp(40),
            background_color=(0.3, 0.6, 0.9, 1)
        )
        if on_edit:
            edit_btn.bind(on_press=lambda x: on_edit(bottle_id))
        
        delete_btn = Button(
            text="🗑️",
            size_hint_x=None,
            width=dp(40),
            background_color=(0.9, 0.3, 0.3, 1)
        )
        if on_delete:
            delete_btn.bind(on_press=lambda x: on_delete(bottle_id))
        
        spacer = Widget()
        
        buttons.add_widget(spacer)
        buttons.add_widget(edit_btn)
        buttons.add_widget(delete_btn)
        
        self.add_widget(header)
        self.add_widget(params)
        self.add_widget(buttons)
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

# =============================
# 🖥️ ЭКРАН: ДОБАВЛЕНИЕ/РЕДАКТИРОВАНИЕ БУТЫЛКИ
# =============================

class AddEditBottleScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_edit_mode = False
        self.edit_bottle_id = None
        self.layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))

        # Заголовок
        self.title_label = Label(text="Добавить бутылку", font_size=dp(20), size_hint_y=None, height=dp(40))
        self.layout.add_widget(self.title_label)

        # Поля ввода
        self.name_input = TextInput(hint_text="Название бутылки", multiline=False, size_hint_y=None, height=dp(40))
        self.empty_weight_input = TextInput(hint_text="Вес пустой бутылки (г)", multiline=False, input_filter='float', size_hint_y=None, height=dp(40))
        self.total_volume_input = TextInput(hint_text="Общий объём бутылки (мл)", multiline=False, input_filter='float', size_hint_y=None, height=dp(40))

        # Выпадающий список категорий
        categories = get_all_categories()
        category_names = [cat[1] for cat in categories]
        self.category_spinner = Spinner(text=category_names[0] if category_names else "Другое", values=category_names, size_hint_y=None, height=dp(40))

        # Кнопка сохранения
        self.save_btn = Button(text="Сохранить", size_hint_y=None, height=dp(50), background_color=(0.3, 0.7, 0.3, 1))
        self.save_btn.bind(on_press=self.save_bottle)

        # Добавляем виджеты
        self.layout.add_widget(self.name_input)
        self.layout.add_widget(self.empty_weight_input)
        self.layout.add_widget(self.total_volume_input)
        self.layout.add_widget(Label(text="Категория:", size_hint_y=None, height=dp(30)))
        self.layout.add_widget(self.category_spinner)
        self.layout.add_widget(self.save_btn)
        self.add_widget(self.layout)

    def set_edit_mode(self, bottle_id):
        """Переводит экран в режим редактирования"""
        self.is_edit_mode = True
        self.edit_bottle_id = bottle_id
        self.title_label.text = "Редактировать бутылку"
        self.save_btn.text = "Обновить"
        
        # Загружаем данные бутылки
        bottle = get_bottle_by_id(bottle_id)
        if bottle:
            self.name_input.text = bottle[1]
            self.empty_weight_input.text = str(bottle[2])
            self.total_volume_input.text = str(bottle[3])
            self.category_spinner.text = bottle[4]

    def set_add_mode(self):
        """Переводит экран в режим добавления"""
        self.is_edit_mode = False
        self.edit_bottle_id = None
        self.title_label.text = "Добавить бутылку"
        self.save_btn.text = "Сохранить"
        self.clear_inputs()

    def save_bottle(self, instance):
        """Сохраняет или обновляет бутылку в базу данных."""
        try:
            name = self.name_input.text.strip()
            empty_weight = float(self.empty_weight_input.text)
            total_volume = float(self.total_volume_input.text)

            if not name:
                show_popup("Ошибка", "Введите название бутылки!")
                return

            # Получаем ID выбранной категории
            selected_category_name = self.category_spinner.text
            categories = get_all_categories()
            category_id = next((cat[0] for cat in categories if cat[1] == selected_category_name), None)

            if category_id is None:
                show_popup("Ошибка", "Категория не найдена!")
                return

            db_path = get_db_path()
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            if self.is_edit_mode and self.edit_bottle_id:
                # Обновляем существующую бутылку
                c.execute('''
                    UPDATE bottles 
                    SET name = ?, empty_weight = ?, total_volume = ?, category_id = ?
                    WHERE id = ?
                ''', (name, empty_weight, total_volume, category_id, self.edit_bottle_id))
                message = "Бутылка обновлена!"
            else:
                # Добавляем новую бутылку
                c.execute(
                    "INSERT INTO bottles (name, empty_weight, total_volume, category_id) VALUES (?, ?, ?, ?)",
                    (name, empty_weight, total_volume, category_id)
                )
                message = "Бутылка добавлена!"
            
            conn.commit()
            conn.close()

            show_popup("Успех", message)
            self.clear_inputs()

        except ValueError:
            show_popup("Ошибка", "Введите корректные числа для веса и объёма!")
        except Exception as e:
            show_popup("Ошибка", f"Не удалось сохранить: {str(e)}")

    def clear_inputs(self):
        """Очищает поля ввода."""
        self.name_input.text = ""
        self.empty_weight_input.text = ""
        self.total_volume_input.text = ""
        categories = get_all_categories()
        category_names = [cat[1] for cat in categories]
        if category_names:
            self.category_spinner.text = category_names[0]

# =============================
# 📊 ЭКРАН: ИНВЕНТАРИЗАЦИЯ
# =============================

class InventoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        self.bottle_id = None
        self.current_volume = None

        # Заголовок
        self.layout.add_widget(Label(text="Инвентаризация", font_size=dp(20), size_hint_y=None, height=dp(40)))

        # Фильтры
        filter_layout = BoxLayout(size_hint_y=None, height=dp(80), spacing=dp(5), orientation='vertical')
        
        # Поиск
        search_layout = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
        self.search_input = TextInput(hint_text="Поиск по названию...", multiline=False)
        search_btn = Button(text="🔍", size_hint_x=None, width=dp(40))
        search_btn.bind(on_press=self.apply_filters)
        search_layout.add_widget(self.search_input)
        search_layout.add_widget(search_btn)
        filter_layout.add_widget(search_layout)
        
        # Фильтр по категории
        category_layout = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
        categories = ["Все категории"] + [cat[1] for cat in get_all_categories()]
        self.category_filter = Spinner(text="Все категории", values=categories)
        self.category_filter.bind(text=self.apply_filters)
        category_layout.add_widget(Label(text="Категория:", size_hint_x=None, width=dp(80)))
        category_layout.add_widget(self.category_filter)
        filter_layout.add_widget(category_layout)
        
        self.layout.add_widget(filter_layout)

        # Список бутылок (в ScrollView)
        self.scroll_view = ScrollView(size_hint=(1, 0.4))
        self.bottles_container = BoxLayout(orientation='vertical', spacing=dp(5), size_hint_y=None)
        self.bottles_container.bind(minimum_height=self.bottles_container.setter('height'))
        self.scroll_view.add_widget(self.bottles_container)
        self.layout.add_widget(self.scroll_view)

        # Выбранный элемент и ввод веса
        self.selected_label = Label(text="Выберите бутылку", size_hint_y=None, height=dp(30))
        self.layout.add_widget(self.selected_label)

        # Ввод текущего веса
        weight_layout = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
        self.current_weight_input = TextInput(
            hint_text="Текущий вес бутылки (г)",
            multiline=False,
            input_filter='float'
        )
        weight_layout.add_widget(self.current_weight_input)
        self.layout.add_widget(weight_layout)

        # Кнопки
        btn_layout = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(50))
        calc_btn = Button(text="Рассчитать объём", background_color=(0.3, 0.6, 0.9, 1))
        calc_btn.bind(on_press=self.calculate_volume)
        save_btn = Button(text="Сохранить результат", background_color=(0.3, 0.7, 0.3, 1))
        save_btn.bind(on_press=self.save_result)
        btn_layout.add_widget(calc_btn)
        btn_layout.add_widget(save_btn)
        self.layout.add_widget(btn_layout)

        # Результат
        self.result_label = Label(text="Объём: -- мл", font_size=dp(24))
        self.layout.add_widget(self.result_label)

        self.add_widget(self.layout)
        self.load_bottles()

    def on_enter(self):
        """Обновляет список бутылок при входе на экран."""
        self.load_bottles()

    def load_bottles(self):
        """Загружает список бутылок с фильтрами"""
        self.bottles_container.clear_widgets()
        
        search_text = self.search_input.text.strip()
        category_filter = self.category_filter.text
        
        bottles = get_bottles_with_filter(search_text, category_filter)
        
        if not bottles:
            self.bottles_container.add_widget(Label(text="Бутылки не найдены", size_hint_y=None, height=dp(40)))
            return
        
        for bottle in bottles:
            bottle_id, name, category, empty_weight, total_volume = bottle
            card = BottleCard(
                bottle_id=bottle_id,
                name=name,
                category=category,
                empty_weight=empty_weight,
                total_volume=total_volume,
                on_edit=self.edit_bottle,
                on_delete=self.delete_bottle
            )
            self.bottles_container.add_widget(card)

    def apply_filters(self, *args):
        """Применяет фильтры и перезагружает список"""
        self.load_bottles()

    def select_bottle(self, bottle_id):
        """Выбирает бутылку для инвентаризации"""
        bottle = get_bottle_by_id(bottle_id)
        if bottle:
            self.bottle_id = bottle_id
            self.selected_label.text = f"Выбрано: {bottle[1]} ({bottle[4]})"

    def edit_bottle(self, bottle_id):
        """Открывает экран редактирования бутылки"""
        app = App.get_running_app()
        add_edit_screen = app.root.get_screen('add_edit_bottle')
        add_edit_screen.set_edit_mode(bottle_id)
        app.root.current = 'add_edit_bottle'

    def delete_bottle(self, bottle_id):
        """Удаляет бутылку с подтверждением"""
        # Подтверждение
        content = BoxLayout(orientation='vertical', padding=dp(10))
        content.add_widget(Label(text="Удалить эту бутылку\nи всю историю по ней?"))

        btn_layout = BoxLayout(spacing=dp(10))
        yes_btn = Button(text="Да", size_hint_x=0.5, background_color=(1, 0, 0, 1))
        no_btn = Button(text="Нет", size_hint_x=0.5)
        btn_layout.add_widget(yes_btn)
        btn_layout.add_widget(no_btn)
        content.add_widget(btn_layout)

        popup = Popup(title="Подтверждение удаления", content=content, size_hint=(0.8, 0.4))

        def on_yes(instance):
            try:
                db_path = get_db_path()
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("DELETE FROM inventory WHERE bottle_id = ?", (bottle_id,))
                c.execute("DELETE FROM bottles WHERE id = ?", (bottle_id,))
                conn.commit()
                conn.close()

                self.load_bottles()
                show_popup("Успех", "Бутылка удалена!")
                popup.dismiss()
            except Exception as e:
                show_popup("Ошибка", f"Не удалось удалить: {str(e)}")

        def on_no(instance):
            popup.dismiss()

        yes_btn.bind(on_press=on_yes)
        no_btn.bind(on_press=on_no)
        popup.open()

    def calculate_volume(self, instance):
        """Рассчитывает текущий объём жидкости по весу."""
        try:
            if not hasattr(self, 'bottle_id') or self.bottle_id is None:
                show_popup("Ошибка", "Сначала выберите бутылку!")
                return

            current_weight = float(self.current_weight_input.text)

            # Получаем данные бутылки
            db_path = get_db_path()
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT empty_weight, total_volume FROM bottles WHERE id = ?", (self.bottle_id,))
            bottle_data = c.fetchone()
            conn.close()

            if not bottle_data:
                show_popup("Ошибка", "Бутылка не найдена!")
                return

            empty_weight, total_volume = bottle_data
            liquid_weight = current_weight - empty_weight
            current_volume = max(0, min(liquid_weight, total_volume))  # Ограничиваем диапазон

            self.result_label.text = f"Объём: {round(current_volume, 1)} мл"
            self.current_volume = current_volume

        except ValueError:
            show_popup("Ошибка", "Введите корректный вес!")
        except Exception as e:
            show_popup("Ошибка", f"Расчёт не удался: {str(e)}")

    def save_result(self, instance):
        """Сохраняет результат инвентаризации в базу."""
        if self.bottle_id is None or self.current_volume is None:
            show_popup("Ошибка", "Сначала рассчитайте объём!")
            return

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db_path = get_db_path()
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute(
                "INSERT INTO inventory (bottle_id, timestamp, current_weight, current_volume) VALUES (?, ?, ?, ?)",
                (self.bottle_id, timestamp, float(self.current_weight_input.text), self.current_volume)
            )
            conn.commit()
            conn.close()
            show_popup("Успех", "Результат сохранён!")

        except Exception as e:
            show_popup("Ошибка", f"Не удалось сохранить: {str(e)}")

# =============================
# 📜 ЭКРАН: ИСТОРИЯ + ЭКСПОРТ В EXCEL
# =============================

class HistoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=dp(20))

        # Заголовок
        self.layout.add_widget(Label(text="История инвентаризации", font_size=dp(20), size_hint_y=None, height=dp(40)))

        # Верхняя панель: кнопки
        top_panel = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(10))
        
        # Кнопка очистки истории
        clear_btn = Button(text="Очистить историю", background_color=(1, 0, 0, 1))
        clear_btn.bind(on_press=self.clear_history)
        top_panel.add_widget(clear_btn)

        # Кнопка экспорта в Excel
        export_btn = Button(text="Экспорт в Excel", background_color=(0, 0.5, 1, 1))
        export_btn.bind(on_press=self.export_to_excel)
        top_panel.add_widget(export_btn)

        self.layout.add_widget(top_panel)

        # ScrollView для истории
        scroll_view = ScrollView(size_hint=(1, 0.85))
        self.history_container = BoxLayout(orientation='vertical', spacing=dp(5), size_hint_y=None)
        self.history_container.bind(minimum_height=self.history_container.setter('height'))
        scroll_view.add_widget(self.history_container)
        self.layout.add_widget(scroll_view)

        self.add_widget(self.layout)
        self.update_history()  # Первый раз загружаем историю

    def on_enter(self):
        """Обновляет историю при входе на экран."""
        self.update_history()

    def update_history(self):
        """Обновляет список записей в истории."""
        self.history_container.clear_widgets()

        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('''
            SELECT inventory.timestamp, bottles.name, categories.name, inventory.current_volume 
            FROM inventory
            JOIN bottles ON inventory.bottle_id = bottles.id
            JOIN categories ON bottles.category_id = categories.id
            ORDER BY inventory.timestamp DESC
            LIMIT 100
        ''')
        records = c.fetchall()
        conn.close()

        if not records:
            self.history_container.add_widget(Label(text="История пуста", size_hint_y=None, height=dp(40)))
            return

        for record in records:
            timestamp, name, category, volume = record
            # Карточка истории с цветовой схемой категории
            card = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(80), padding=dp(10))
            
            # Фон с цветом категории
            with card.canvas.before:
                color = CATEGORY_COLORS.get(category, CATEGORY_COLORS["Другое"])
                Color(*color)
                card.rect = Rectangle(pos=card.pos, size=card.size)
            card.bind(pos=lambda instance, value: setattr(instance.rect, 'pos', instance.pos))
            card.bind(size=lambda instance, value: setattr(instance.rect, 'size', instance.size))
            
            # Текст истории
            entry = Label(
                text=f"[b]{timestamp}[/b]\n{name} ({category}) — {volume} мл",
                markup=True,
                size_hint_y=None,
                height=dp(60),
                halign='left',
                valign='middle',
                text_size=(self.width - dp(40), None)
            )
            card.add_widget(entry)
            self.history_container.add_widget(card)

    def clear_history(self, instance):
        """Очищает всю историю инвентаризации (с подтверждением)."""
        content = BoxLayout(orientation='vertical', padding=dp(10))
        content.add_widget(Label(text="Удалить ВСЮ историю инвентаризации?"))

        btn_layout = BoxLayout(spacing=dp(10))
        yes_btn = Button(text="Да", size_hint_x=0.5, background_color=(1, 0, 0, 1))
        no_btn = Button(text="Нет", size_hint_x=0.5)
        btn_layout.add_widget(yes_btn)
        btn_layout.add_widget(no_btn)
        content.add_widget(btn_layout)

        popup = Popup(title="Подтверждение очистки", content=content, size_hint=(0.8, 0.4))

        def on_yes(instance):
            try:
                db_path = get_db_path()
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("DELETE FROM inventory")
                conn.commit()
                conn.close()
                self.update_history()
                show_popup("Успех", "История очищена!")
                popup.dismiss()
            except Exception as e:
                show_popup("Ошибка", f"Не удалось очистить: {str(e)}")

        def on_no(instance):
            popup.dismiss()

        yes_btn.bind(on_press=on_yes)
        no_btn.bind(on_press=on_no)
        popup.open()

    def export_to_excel(self, instance):
        """Экспортирует историю в Excel-файл и показывает путь к нему."""
        export_path = export_inventory_to_excel()
        if export_path:
            show_popup("Экспорт завершён", f"Файл сохранён:\n{export_path}")
        else:
            show_popup("Ошибка", "Не удалось экспортировать в Excel.")

# =============================
# 🎮 ОСНОВНОЙ КЛАСС ПРИЛОЖЕНИЯ
# =============================

class InventoryApp(App):
    def build(self):
        """Строит интерфейс приложения: экраны + навигация."""
        init_db()  # Инициализируем БД при запуске

        sm = ScreenManager()
        sm.add_widget(AddEditBottleScreen(name="add_edit_bottle"))
        sm.add_widget(InventoryScreen(name="inventory"))
        sm.add_widget(HistoryScreen(name="history"))

        # Навигационное меню
        nav = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50))

        def switch_screen(name):
            sm.current = name

        for screen_name in ["add_edit_bottle", "inventory", "history"]:
            btn = Button(text=screen_name.replace("_", " ").replace("edit", "редактировать").title())
            btn.bind(on_press=lambda x, name=screen_name: switch_screen(name))
            nav.add_widget(btn)

        root = BoxLayout(orientation='vertical')
        root.add_widget(sm)
        root.add_widget(nav)
        return root

# =============================
# ▶️ ЗАПУСК ПРИЛОЖЕНИЯ
# =============================

if __name__ == "__main__":
    # Отладочная информация
    db_path = get_db_path()
    print("="*50)
    print(f"Файл базы данных: {db_path}")
    print(f"Папка проекта: {os.path.dirname(os.path.abspath(__file__))}")
    print("="*50)

    InventoryApp().run()