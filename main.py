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

# Устанавливаем размер окна для удобства тестирования
Window.size = (400, 600)


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
# 🖥️ ЭКРАН: ДОБАВЛЕНИЕ БУТЫЛКИ
# =============================

class AddBottleScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        # Поля ввода
        self.name_input = TextInput(hint_text="Название бутылки", multiline=False)
        self.empty_weight_input = TextInput(hint_text="Вес пустой бутылки (г)", multiline=False, input_filter='float')
        self.total_volume_input = TextInput(hint_text="Общий объём бутылки (мл)", multiline=False, input_filter='float')

        # Выпадающий список категорий
        categories = get_all_categories()
        category_names = [cat[1] for cat in categories]
        self.category_spinner = Spinner(text=category_names[0] if category_names else "Другое", values=category_names)

        # Кнопка сохранения
        save_btn = Button(text="Сохранить", size_hint_y=None, height=50)
        save_btn.bind(on_press=self.save_bottle)

        # Добавляем виджеты
        self.layout.add_widget(self.name_input)
        self.layout.add_widget(self.empty_weight_input)
        self.layout.add_widget(self.total_volume_input)
        self.layout.add_widget(Label(text="Категория:", size_hint_y=None, height=30))
        self.layout.add_widget(self.category_spinner)
        self.layout.add_widget(save_btn)
        self.add_widget(self.layout)

    def save_bottle(self, instance):
        """Сохраняет новую бутылку в базу данных."""
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

            # Сохраняем в БД
            db_path = get_db_path()
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute(
                "INSERT INTO bottles (name, empty_weight, total_volume, category_id) VALUES (?, ?, ?, ?)",
                (name, empty_weight, total_volume, category_id)
            )
            conn.commit()
            conn.close()

            show_popup("Успех", "Бутылка добавлена!")
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


# =============================
# 📊 ЭКРАН: ИНВЕНТАРИЗАЦИЯ
# =============================

class InventoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.bottle_id = None
        self.current_volume = None

        # Заголовок выбора
        self.layout.add_widget(Label(text="Выберите бутылку:", size_hint_y=None, height=30))

        # Создаём спиннер (сначала пустой или с данными)
        self.bottle_spinner = self._create_bottle_spinner()
        self.layout.add_widget(self.bottle_spinner)

        # Ввод текущего веса
        self.current_weight_input = TextInput(
            hint_text="Текущий вес бутылки (г)",
            multiline=False,
            input_filter='float'
        )
        self.layout.add_widget(self.current_weight_input)

        # Кнопки
        btn_layout = BoxLayout(spacing=10, size_hint_y=None, height=50)
        calc_btn = Button(text="Рассчитать объём")
        calc_btn.bind(on_press=self.calculate_volume)
        save_btn = Button(text="Сохранить результат")
        save_btn.bind(on_press=self.save_result)
        delete_btn = Button(text="Удалить бутылку", background_color=(1, 0, 0, 1))
        delete_btn.bind(on_press=self.delete_bottle)

        btn_layout.add_widget(calc_btn)
        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(delete_btn)
        self.layout.add_widget(btn_layout)

        # Результат
        self.result_label = Label(text="Объём: -- мл", font_size=24)
        self.layout.add_widget(self.result_label)

        self.add_widget(self.layout)

    def on_enter(self):
        """Обновляет список бутылок при входе на экран."""
        # Удаляем старый спиннер
        if hasattr(self, 'bottle_spinner') and self.bottle_spinner in self.layout.children:
            self.layout.remove_widget(self.bottle_spinner)
        # Создаём новый
        self.bottle_spinner = self._create_bottle_spinner()
        # Вставляем на место — после заголовка "Выберите бутылку"
        # Индекс: 1, потому что первый виджет — это Label "Выберите бутылку"
        self.layout.add_widget(self.bottle_spinner, index=len(self.layout.children) - 4)

    def _create_bottle_spinner(self):
        """Создаёт выпадающий список бутылок с категориями."""
        bottles = get_all_bottles_with_categories()
        if not bottles:
            return Spinner(text="Нет бутылок", values=["Нет бутылок"])

        values = [f"{b[0]} | {b[1]} ({b[2]})" for b in bottles]
        return Spinner(text=values[0], values=values)

    def calculate_volume(self, instance):
        """Рассчитывает текущий объём жидкости по весу."""
        try:
            if self.bottle_spinner.text == "Нет бутылок":
                show_popup("Ошибка", "Сначала добавьте бутылку!")
                return

            # Извлекаем ID бутылки
            bottle_info = self.bottle_spinner.text.split(" | ")[0]
            bottle_id = int(bottle_info)

            current_weight = float(self.current_weight_input.text)

            # Получаем данные бутылки
            db_path = get_db_path()
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT empty_weight, total_volume FROM bottles WHERE id = ?", (bottle_id,))
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
            self.bottle_id = bottle_id

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

    def delete_bottle(self, instance):
        """Удаляет бутылку и всю её историю (с подтверждением)."""
        if self.bottle_spinner.text == "Нет бутылок":
            show_popup("Ошибка", "Нет бутылок для удаления!")
            return

        try:
            bottle_info = self.bottle_spinner.text.split(" | ")[0]
            bottle_id = int(bottle_info)
        except:
            show_popup("Ошибка", "Выберите бутылку!")
            return

        # Подтверждение
        content = BoxLayout(orientation='vertical', padding=10)
        content.add_widget(Label(text="Удалить эту бутылку\nи всю историю по ней?"))

        btn_layout = BoxLayout(spacing=10)
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

                # Обновляем список бутылок
                self.layout.remove_widget(self.bottle_spinner)
                self.bottle_spinner = self._create_bottle_spinner()
                self.layout.add_widget(self.bottle_spinner, index=len(self.layout.children) - 4)

                show_popup("Успех", "Бутылка удалена!")
                popup.dismiss()
            except Exception as e:
                show_popup("Ошибка", f"Не удалось удалить: {str(e)}")

        def on_no(instance):
            popup.dismiss()

        yes_btn.bind(on_press=on_yes)
        no_btn.bind(on_press=on_no)
        popup.open()


# =============================
# 📜 ЭКРАН: ИСТОРИЯ + ЭКСПОРТ В EXCEL
# =============================

class HistoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20)

        # Верхняя панель: кнопки
        top_panel = BoxLayout(size_hint_y=None, height=60, spacing=10)
        
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
        self.history_container = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
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
            self.history_container.add_widget(Label(text="История пуста", size_hint_y=None, height=40))
            return

        for record in records:
            timestamp, name, category, volume = record
            entry = Label(
                text=f"{timestamp}\n{name} ({category}) — {volume} мл",
                size_hint_y=None,
                height=60,
                halign='left',
                valign='middle',
                text_size=(self.width - 40, None)
            )
            self.history_container.add_widget(entry)

    def clear_history(self, instance):
        """Очищает всю историю инвентаризации (с подтверждением)."""
        content = BoxLayout(orientation='vertical', padding=10)
        content.add_widget(Label(text="Удалить ВСЮ историю инвентаризации?"))

        btn_layout = BoxLayout(spacing=10)
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
        sm.add_widget(AddBottleScreen(name="add_bottle"))
        sm.add_widget(InventoryScreen(name="inventory"))
        sm.add_widget(HistoryScreen(name="history"))

        # Навигационное меню
        nav = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)

        def switch_screen(name):
            sm.current = name

        for screen_name in ["add_bottle", "inventory", "history"]:
            btn = Button(text=screen_name.replace("_", " ").title())
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