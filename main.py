import sqlite3
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window

# Устанавливаем размер окна для удобства тестирования
Window.size = (400, 600)

# Создаём базу данных
def init_db():
    conn = sqlite3.connect('bar_inventory.db')
    c = conn.cursor()
    
    # Таблица для бутылок
    c.execute('''
        CREATE TABLE IF NOT EXISTS bottles (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            empty_weight REAL NOT NULL,
            total_volume REAL NOT NULL
        )
    ''')
    
    # Таблица для истории инвентаризации
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
    
    conn.commit()
    conn.close()

# Вспомогательная функция для показа уведомлений
def show_popup(title, message):
    popup = Popup(
        title=title,
        content=Label(text=message),
        size_hint=(0.8, 0.3)
    )
    popup.open()

# Экран: Добавление новой бутылки
class AddBottleScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Поля ввода
        self.name_input = self._create_input("Название бутылки")
        self.empty_weight_input = self._create_input("Вес пустой бутылки (г)")
        self.total_volume_input = self._create_input("Общий объём бутылки (мл)")
        
        # Кнопка сохранения
        save_btn = Button(text="Сохранить", size_hint_y=None, height=50)
        save_btn.bind(on_press=self.save_bottle)
        
        self.layout.add_widget(self.name_input)
        self.layout.add_widget(self.empty_weight_input)
        self.layout.add_widget(self.total_volume_input)
        self.layout.add_widget(save_btn)
        self.add_widget(self.layout)
    
    def _create_input(self, hint):
        from kivy.uix.textinput import TextInput
        return TextInput(hint_text=hint, multiline=False, input_type='number')
    
    def save_bottle(self, instance):
        try:
            name = self.name_input.text
            empty_weight = float(self.empty_weight_input.text)
            total_volume = float(self.total_volume_input.text)
            
            if not name:
                show_popup("Ошибка", "Введите название!")
                return
                
            conn = sqlite3.connect('bar_inventory.db')
            c = conn.cursor()
            c.execute(
                "INSERT INTO bottles (name, empty_weight, total_volume) VALUES (?, ?, ?)",
                (name, empty_weight, total_volume)
            )
            conn.commit()
            conn.close()
            
            show_popup("Успех", "Бутылка добавлена!")
            self.clear_inputs()
            
        except ValueError:
            show_popup("Ошибка", "Введите числа в вес/объём!")
    
    def clear_inputs(self):
        self.name_input.text = ""
        self.empty_weight_input.text = ""
        self.total_volume_input.text = ""

# ЭкРАН: Проведение инвентаризации (с удалением бутылок)
class InventoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Выбор бутылки
        self.bottle_spinner = self._create_spinner()
        self.layout.add_widget(self.bottle_spinner)
        
        # Ввод текущего веса
        self.current_weight_input = self._create_input("Текущий вес бутылки (г)")
        self.layout.add_widget(self.current_weight_input)
        
        # Кнопки
        btn_layout = BoxLayout(spacing=10)
        calc_btn = Button(text="Рассчитать объём", size_hint_y=None, height=50)
        calc_btn.bind(on_press=self.calculate_volume)
        save_btn = Button(text="Сохранить результат", size_hint_y=None, height=50)
        save_btn.bind(on_press=self.save_result)
        delete_btn = Button(text="Удалить бутылку", size_hint_y=None, height=50)
        delete_btn.bind(on_press=self.delete_bottle)
        
        btn_layout.add_widget(calc_btn)
        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(delete_btn)
        
        self.layout.add_widget(btn_layout)
        self.result_label = Label(text="Объём: -- мл", font_size=24)
        self.layout.add_widget(self.result_label)
        self.add_widget(self.layout)
    
    def _create_spinner(self):
        from kivy.uix.spinner import Spinner
        conn = sqlite3.connect('bar_inventory.db')
        c = conn.cursor()
        c.execute("SELECT id, name FROM bottles")
        bottles = c.fetchall()
        conn.close()
        
        values = [f"{b[0]} | {b[1]}" for b in bottles] if bottles else ["Нет бутылок"]
        return Spinner(text=values[0] if values else "Добавьте бутылку", values=values)
    
    def _create_input(self, hint):
        from kivy.uix.textinput import TextInput
        return TextInput(hint_text=hint, multiline=False, input_type='number')
    
    def calculate_volume(self, instance):
        try:
            if "Нет бутылок" in self.bottle_spinner.text:
                show_popup("Ошибка", "Сначала добавьте бутылку!")
                return
                
            bottle_id = int(self.bottle_spinner.text.split(" | ")[0])
            current_weight = float(self.current_weight_input.text)
            
            conn = sqlite3.connect('bar_inventory.db')
            c = conn.cursor()
            c.execute("SELECT empty_weight, total_volume FROM bottles WHERE id = ?", (bottle_id,))
            bottle_data = c.fetchone()
            conn.close()
            
            if not bottle_data:
                show_popup("Ошибка", "Бутылка не найдена!")
                return
                
            empty_weight, total_volume = bottle_data
            liquid_weight = current_weight - empty_weight
            
            # Упрощённый расчёт: 1 г жидкости = 1 мл
            current_volume = max(0, min(liquid_weight, total_volume))
            
            self.result_label.text = f"Объём: {round(current_volume, 1)} мл"
            self.current_volume = current_volume
            self.bottle_id = bottle_id
            
        except ValueError:
            show_popup("Ошибка", "Введите корректный вес!")
    
    def save_result(self, instance):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = sqlite3.connect('bar_inventory.db')
            c = conn.cursor()
            c.execute(
                "INSERT INTO inventory (bottle_id, timestamp, current_weight, current_volume) VALUES (?, ?, ?, ?)",
                (self.bottle_id, timestamp, float(self.current_weight_input.text), self.current_volume)
            )
            conn.commit()
            conn.close()
            show_popup("Успех", "Результат сохранён!")
        except AttributeError:
            show_popup("Ошибка", "Сначала рассчитайте объём!")
    
    # НОВАЯ ФУНКЦИЯ: Удаление бутылки
    def delete_bottle(self, instance):
        if "Нет бутылок" in self.bottle_spinner.text:
            show_popup("Ошибка", "Нет бутылок для удаления!")
            return
        
        try:
            bottle_id = int(self.bottle_spinner.text.split(" | ")[0])
        except ValueError:
            show_popup("Ошибка", "Выберите бутылку!")
            return

        # Создаем всплывающее окно подтверждения
        content = BoxLayout(orientation='vertical', padding=10)
        content.add_widget(Label(text="Удалить эту бутылку\nи всю историю по ней?"))
        
        btn_layout = BoxLayout(spacing=10)
        yes_btn = Button(text="Да", size_hint_x=0.5)
        no_btn = Button(text="Нет", size_hint_x=0.5)
        btn_layout.add_widget(yes_btn)
        btn_layout.add_widget(no_btn)
        
        content.add_widget(btn_layout)
        
        popup = Popup(
            title="Подтверждение удаления",
            content=content,
            size_hint=(0.8, 0.4)
        )
        
        def on_yes(instance):
            try:
                conn = sqlite3.connect('bar_inventory.db')
                c = conn.cursor()
                # Удаляем историю по бутылке
                c.execute("DELETE FROM inventory WHERE bottle_id = ?", (bottle_id,))
                # Удаляем саму бутылку
                c.execute("DELETE FROM bottles WHERE id = ?", (bottle_id,))
                conn.commit()
                conn.close()
                
                # Обновляем список бутылок
                self.layout.remove_widget(self.bottle_spinner)
                self.bottle_spinner = self._create_spinner()
                self.layout.add_widget(self.bottle_spinner, index=0)
                
                show_popup("Успех", "Бутылка удалена!")
                popup.dismiss()
            except Exception as e:
                show_popup("Ошибка", f"Не удалось удалить: {str(e)}")
        
        def on_no(instance):
            popup.dismiss()
        
        yes_btn.bind(on_press=on_yes)
        no_btn.bind(on_press=on_no)
        
        popup.open()

# Экран: История инвентаризации (с очисткой)
class HistoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20)
        
        # Кнопка очистки
        clear_btn = Button(
            text="Очистить историю", 
            size_hint_y=None, 
            height=50,
            background_color=(1, 0, 0, 1)  # Красная кнопка
        )
        clear_btn.bind(on_press=self.clear_history)
        self.layout.add_widget(clear_btn)
        
        # Контейнер для записей
        self.history_container = BoxLayout(orientation='vertical', spacing=5)
        self.layout.add_widget(self.history_container)
        
        self.update_history()
        self.add_widget(self.layout)
    
    def update_history(self):
        self.history_container.clear_widgets()
        
        conn = sqlite3.connect('bar_inventory.db')
        c = conn.cursor()
        c.execute('''
            SELECT inventory.timestamp, bottles.name, inventory.current_volume 
            FROM inventory
            JOIN bottles ON inventory.bottle_id = bottles.id
            ORDER BY inventory.timestamp DESC
            LIMIT 50
        ''')
        records = c.fetchall()
        conn.close()
        
        if not records:
            self.history_container.add_widget(Label(text="История пуста"))
            return
        
        for record in records:
            timestamp, name, volume = record
            self.history_container.add_widget(Label(
                text=f"{timestamp} | {name} | {volume} мл",
                size_hint_y=None,
                height=40,
                halign='left',
                valign='middle'
            ))
    
    # НОВАЯ ФУНКЦИЯ: Очистка истории
    def clear_history(self, instance):
        # Создаем всплывающее окно подтверждения
        content = BoxLayout(orientation='vertical', padding=10)
        content.add_widget(Label(text="Удалить ВСЮ историю инвентаризации?"))
        
        btn_layout = BoxLayout(spacing=10)
        yes_btn = Button(text="Да", size_hint_x=0.5, background_color=(1, 0, 0, 1))
        no_btn = Button(text="Нет", size_hint_x=0.5)
        btn_layout.add_widget(yes_btn)
        btn_layout.add_widget(no_btn)
        
        content.add_widget(btn_layout)
        
        popup = Popup(
            title="Подтверждение очистки",
            content=content,
            size_hint=(0.8, 0.4)
        )
        
        def on_yes(instance):
            try:
                conn = sqlite3.connect('bar_inventory.db')
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

# Менеджер экранов
class InventoryApp(App):
    def build(self):
        init_db()  # Инициализируем БД при запуске
        
        sm = ScreenManager()
        sm.add_widget(AddBottleScreen(name="add_bottle"))
        sm.add_widget(InventoryScreen(name="inventory"))
        sm.add_widget(HistoryScreen(name="history"))
        
        # Навигационное меню
        nav = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        
        # Функция для переключения экранов
        def switch_screen(name):
            print(f"ПЕРЕКЛЮЧЕНИЕ НА ЭКРАН: {name}")  # Отладочное сообщение
            sm.current = name

        for screen_name in ["add_bottle", "inventory", "history"]:
            btn = Button(text=screen_name.replace("_", " ").title())
            btn.bind(on_press=lambda x, name=screen_name: switch_screen(name))
            nav.add_widget(btn)
        
        root = BoxLayout(orientation='vertical')
        root.add_widget(sm)
        root.add_widget(nav)
        return root

if __name__ == "__main__":
    InventoryApp().run()