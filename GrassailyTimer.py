import sys
from pathlib import Path
import datetime
import json
import os
import sys
from PyQt6.QtWidgets import (QApplication, QGraphicsOpacityEffect, QLabel, QWidget, QPushButton,
                             QSlider, QVBoxLayout, QHBoxLayout, QLineEdit, QFileDialog)
from PyQt6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap, QImage, QIntValidator

def calculate_academic_days(start_year, num_courses):
    academic_days = 0
    for year in range(start_year, start_year + num_courses):
        semester1_start = datetime.date(year, 9, 1)
        semester1_end = datetime.date(year, 12, 31)
        academic_days += (semester1_end - semester1_start).days + 1

        semester2_start = datetime.date(year + 1, 1, 1)
        semester2_end = datetime.date(year + 1, 6, 30)
        academic_days += (semester2_end - semester2_start).days + 1

    return academic_days

def days_until_graduation(start_year, num_courses):
    today = datetime.date.today()
    graduation_year = start_year + num_courses
    graduation_date = datetime.date(graduation_year, 6, 30)
    return (graduation_date - today).days if today < graduation_date else 0

def calculate_progress(start_year, num_courses):
    today = datetime.date.today()
    total_academic_days = calculate_academic_days(start_year, num_courses)

    studied_days = 0
    for year in range(start_year, start_year + num_courses):
        semester1_start = datetime.date(year, 9, 1)
        semester1_end = datetime.date(year, 12, 31)
        if today >= semester1_start:
            studied_days += (min(today, semester1_end) - semester1_start).days + 1

        semester2_start = datetime.date(year + 1, 1, 1)
        semester2_end = datetime.date(year + 1, 6, 30)
        if today >= semester2_start:
            studied_days += (min(today, semester2_end) - semester2_start).days + 1

    total_progress = (studied_days / total_academic_days) * 100

    current_semester_start = datetime.date(today.year, 1, 1) if today.month >= 1 else datetime.date(today.year - 1, 9, 1)
    current_semester_end = datetime.date(today.year, 6, 30) if today.month >= 1 else datetime.date(today.year, 12, 31)
    semester_days = (current_semester_end - current_semester_start).days + 1
    semester_progress = (min((today - current_semester_start).days + 1, semester_days) / semester_days) * 100

    return total_progress, semester_progress

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_settings_path():
    if sys.platform == "win32":
        appdata_path = os.getenv('LOCALAPPDATA')
        if not appdata_path:
            appdata_path = os.path.expanduser('~')
        settings_dir = os.path.join(appdata_path, "GrassallyTimer")
    else:
        settings_dir = os.path.join(os.path.expanduser('~'), ".grassallytimer")
    os.makedirs(settings_dir, exist_ok=True)
    return os.path.join(settings_dir, "settings.json")

def get_images_dir():
    if sys.platform == "win32":
        images_dir = os.path.join(os.getenv("LOCALAPPDATA"), "GrassallyTimer", "images")
    else:
        images_dir = os.path.join(str(Path.home()), ".grassallytimer", "images")
    os.makedirs(images_dir, exist_ok=True)
    return images_dir

def get_desktop_path():
    if sys.platform == "win32":
        desktop_path = os.path.join(os.getenv("USERPROFILE"), "Desktop")
    else:
        desktop_path = os.path.join(str(Path.home()), "Desktop")
    return desktop_path

class TransparentWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.last_update_time = None
        self.cached_days_left = None
        self.cached_progress = None
        self.settings_file = get_settings_path()
        self.images_dir = get_images_dir()
        self.background_image = os.path.join(self.images_dir, "background_image.png")
        self.pin_icon_normal = resource_path("assets/pin_icon_normal.png")
        self.pin_icon_rotated = resource_path("assets/pin_icon_rotated.png")
        self.settings_icon = resource_path("assets/settings_icon.png")
        self.image_icon = resource_path("assets/image_icon.png")
        self.image_icon_delete = resource_path("assets/image_icon_delete.png")
        self.load_settings()
        self.is_expanded = False
        self.notification_label = None
        self.initUI()
        self.update_info()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_info)
        self.timer.start(600000)
        self.drag_position = QPoint()
        self.is_closing = False

    def initUI(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnBottomHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(self.window_x, self.window_y, self.window_width, self.window_height)

        self.background_opacity_effect = QGraphicsOpacityEffect()
        self.background_opacity_effect.setOpacity(self.opacity / 100.0)

        background_image_path = self.background_image.replace("\\", "/")

        self.background_widget = QWidget(self)
        self.background_widget.setGeometry(self.rect())
        self.background_widget.setStyleSheet(f"""
            background-image: url('{background_image_path}'); 
            background-repeat: no-repeat;
            background-position: center;
            background-size: contain;
            border-radius: 10px;
        """)
        self.background_widget.setGraphicsEffect(self.background_opacity_effect)
        self.background_widget.lower()

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(5)

        self.top_bar = QHBoxLayout(self)
        self.top_bar.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.background_button = QPushButton()
        self.background_button.setIcon(QIcon(QPixmap(self.image_icon)))
        self.background_button.setFixedSize(24, 24)
        self.background_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
        """)
        self.background_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.background_button.clicked.connect(self.change_background_image)
        self.top_bar.addWidget(self.background_button)

        self.pin_button = QPushButton()
        if self.is_locked:
            self.pin_button.setIcon(QIcon(QPixmap(self.pin_icon_rotated)))
        else:
            self.pin_button.setIcon(QIcon(QPixmap(self.pin_icon_normal)))
        self.pin_button.setFixedSize(24, 24)
        self.pin_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
        """)
        self.pin_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pin_button.clicked.connect(self.toggle_lock)
        self.top_bar.addWidget(self.pin_button)

        self.settings_button = QPushButton()
        self.settings_button.setIcon(QIcon(QPixmap(self.settings_icon)))
        self.settings_button.setFixedSize(24, 24)
        self.settings_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
        """)
        self.settings_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.settings_button.clicked.connect(self.toggle_settings)
        self.top_bar.addWidget(self.settings_button)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.label.setStyleSheet("color: white;")

        self.settings_container = QVBoxLayout()
        self.settings_container.setContentsMargins(0, 0, 0, 0)
        self.settings_container.setSpacing(5)
        self.settings_container.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.start_year_label = QLabel("Год начала:", self)
        self.start_year_label.setStyleSheet("color: white; border-radius: 10px; padding: 5px;")
        self.start_year_label.setVisible(False)

        self.start_year_input = QLineEdit(self)
        self.start_year_input.setStyleSheet("border-radius: 10px; padding: 5px;")
        self.start_year_input.setVisible(False)
        self.start_year_input.setText(str(self.start_year))

        self.start_year_input.setValidator(QIntValidator(1900, 2100, self))

        self.num_courses_label = QLabel("Курсы:", self)
        self.num_courses_label.setStyleSheet("color: white; border-radius: 10px; padding: 5px;")
        self.num_courses_label.setVisible(False)

        self.num_courses_input = QLineEdit(self)
        self.num_courses_input.setStyleSheet("border-radius: 10px; padding: 5px;")
        self.num_courses_input.setVisible(False)
        self.num_courses_input.setText(str(self.num_courses))

        self.num_courses_input.setValidator(QIntValidator(1, 6, self))

        self.update_input_fields()

        self.input_layout = QHBoxLayout()
        self.input_layout.setSpacing(10)

        self.settings_container.addLayout(self.input_layout)

        self.input_layout.addWidget(self.start_year_label)
        self.input_layout.addWidget(self.start_year_input)
        self.input_layout.addWidget(self.num_courses_label)
        self.input_layout.addWidget(self.num_courses_input)

        self.slider_label = QLabel("Прозрачность:")
        self.slider_label.setStyleSheet("color: white; border-radius: 10px; padding: 5px;")
        self.slider_label.setVisible(False)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(25)
        self.slider.setMaximum(60)
        self.slider.setValue(self.opacity)
        self.slider.setVisible(False)
        self.slider.valueChanged.connect(self.change_opacity)

        self.slider_group = QHBoxLayout()
        self.slider_group.setSpacing(10)

        self.settings_container.addLayout(self.slider_group)

        self.slider_group.addWidget(self.slider_label)
        self.slider_group.addWidget(self.slider)

        self.save_button = QPushButton("Сохранить")
        self.save_button.setVisible(False)
        self.save_button.setStyleSheet("border-radius: 10px; padding: 5px;")
        self.save_button.clicked.connect(self.save_settings_to_file)

        self.delete_exit_about_layout = QHBoxLayout()
        self.delete_exit_about_layout.setSpacing(10)

        self.delete_background_button = QPushButton()
        self.delete_background_button.setIcon(QIcon(QPixmap(self.image_icon_delete)))
        self.delete_background_button.setFixedSize(24, 24)
        self.delete_background_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
        """)
        self.delete_background_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.delete_background_button.setToolTip("Удалить фон")
        self.delete_background_button.setVisible(False)
        self.delete_background_button.clicked.connect(self.delete_background)

        self.exit_button = QPushButton("Закрыть программу")
        self.exit_button.setVisible(False)
        self.exit_button.setStyleSheet("border-radius: 10px; padding: 5px;")
        self.exit_button.clicked.connect(self.close)

        self.about_button = QPushButton("?")
        self.about_button.setFixedSize(24, 24)
        self.about_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
        """)
        self.about_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.about_button.setToolTip("Разработчик программы: Quvgard.")
        self.about_button.setVisible(False)

        self.delete_exit_about_layout.addWidget(self.delete_background_button)
        self.delete_exit_about_layout.addWidget(self.exit_button)
        self.delete_exit_about_layout.addWidget(self.about_button)

        self.settings_container.addWidget(self.save_button)
        self.settings_container.addLayout(self.delete_exit_about_layout)

        self.layout.addLayout(self.top_bar)
        self.layout.addWidget(self.label)
        self.layout.addLayout(self.settings_container)

        self.setStyleSheet(f"background-color: rgba(0, 0, 0, {self.opacity * 2.55}); border-radius: 10px;")

        self.setup_button_animations()

        self.notification_label = QLabel("Настройки сохранены", self)
        self.notification_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notification_label.setFont(QFont("Arial", 8))
        self.notification_label.setStyleSheet("""
                    background-color: rgba(0, 0, 0, 150);
                    color: white;
                    border-radius: 5px;
                    padding: 5px;
                """)
        self.notification_label.setFixedSize(200, 30)
        self.notification_label.move(10, 10)
        self.notification_label.hide()

        self.notification_opacity_effect = QGraphicsOpacityEffect(self.notification_label)
        self.notification_label.setGraphicsEffect(self.notification_opacity_effect)
        self.notification_opacity_effect.setOpacity(0.0)

    def setup_button_animations(self):
        buttons = [
            self.save_button,
            self.exit_button,
            self.settings_button,
            self.pin_button,
            self.background_button,
            self.delete_background_button,
        ]

        for button in buttons:
            button.pressed.connect(self.animate_button_press)
            button.released.connect(self.animate_button_release)

    def animate_button_press(self):
        button = self.sender()
        if not button:
            return

        self.animation = QPropertyAnimation(button, b"size")
        self.animation.setDuration(100)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        original_size = button.size()
        self.animation.setEndValue(QSize(original_size.width() - 4, original_size.height() - 4))
        self.animation.start()

        self.opacity_effect = QGraphicsOpacityEffect(button)
        button.setGraphicsEffect(self.opacity_effect)
        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_animation.setDuration(100)
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.7)
        self.opacity_animation.start()

        self.animation = QPropertyAnimation(button, b"pos")
        self.animation.setDuration(100)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.animation.setEndValue(button.pos() + QPoint(0, 2))
        self.animation.start()

    def animate_button_release(self):
        button = self.sender()
        if not button:
            return

        self.animation = QPropertyAnimation(button, b"size")
        self.animation.setDuration(100)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        original_size = button.size()
        self.animation.setEndValue(QSize(original_size.width() + 4, original_size.height() + 4))
        self.animation.start()

        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_animation.setDuration(100)
        self.opacity_animation.setStartValue(0.7)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.start()

        self.animation = QPropertyAnimation(button, b"pos")
        self.animation.setDuration(100)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.animation.setEndValue(button.pos() - QPoint(0, 2))
        self.animation.start()

    def show_notification(self, message):
        if not self.notification_label:
            return

        self.notification_label.setText(message)
        self.notification_label.move(10, 10)

        self.notification_animation = QPropertyAnimation(self.notification_opacity_effect, b"opacity")
        self.notification_animation.setDuration(500)
        self.notification_animation.setStartValue(0.0)
        self.notification_animation.setEndValue(0.8)
        self.notification_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.notification_animation.finished.connect(lambda: QTimer.singleShot(2000, self.hide_notification))

        self.notification_label.show()
        self.notification_animation.start()

    def hide_notification(self):
        if not self.notification_label:
            return

        self.notification_animation = QPropertyAnimation(self.notification_opacity_effect, b"opacity")
        self.notification_animation.setDuration(500)
        self.notification_animation.setStartValue(0.8)
        self.notification_animation.setEndValue(0.0)
        self.notification_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.notification_animation.finished.connect(self.notification_label.hide)

        self.notification_animation.start()

    def update_input_fields(self):
        self.start_year_input.setText(
            str(self.start_year) if self.start_year is not None and self.start_year != 0 else "")
        self.num_courses_input.setText(
            str(self.num_courses) if self.num_courses is not None and self.num_courses != 0 else "")

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as file:
                settings = json.load(file)
                self.start_year = settings.get("start_year", 2026) if settings.get("start_year", 0) != 0 else None
                self.num_courses = settings.get("num_courses", 4) if settings.get("num_courses", 0) != 0 else None
                self.opacity = settings.get("opacity", 30)
                self.is_locked = settings.get("is_locked", False)
                self.window_x = settings.get("window_x", 50)
                self.window_y = settings.get("window_y", 50)
                self.window_width = settings.get("window_width", 300)
                self.window_height = settings.get("window_height", 180)
        else:
            self.start_year = 0
            self.num_courses = 0
            self.opacity = 50
            self.is_locked = False
            self.window_x = 50
            self.window_y = 50
            self.window_width = 300
            self.window_height = 180

    def save_settings_to_file(self):
        try:
            start_year_text = self.start_year_input.text()
            num_courses_text = self.num_courses_input.text()

            start_year = int(start_year_text) if start_year_text else 0
            num_courses = int(num_courses_text) if num_courses_text else 0
        except ValueError:
            self.show_notification("Введите корректные числа")
            return

        if start_year != 0 and (start_year < 1900 or start_year > 2100):
            self.show_notification("Ошибка: год начала должен быть от 1900 до 2100")
            return

        if num_courses != 0 and (num_courses < 1 or num_courses > 6):
            self.show_notification("Ошибка: количество курсов должно быть от 1 до 6")
            return

        settings = {
            "start_year": start_year,
            "num_courses": num_courses,
            "opacity": self.opacity,
            "is_locked": self.is_locked,
            "window_x": self.x(),
            "window_y": self.y(),
            "window_width": 300,
            "window_height": 180
        }
        with open(self.settings_file, "w") as file:
            json.dump(settings, file)

        self.start_year = start_year if start_year != 0 else None
        self.num_courses = num_courses if num_courses != 0 else None

        self.last_update_time = None

        self.show_notification("Настройки сохранены")
        self.update_info()

    def update_info(self):
        if self.start_year is None or self.num_courses is None or self.start_year == 0 or self.num_courses == 0:
            self.label.setText("Настройте программу\n"
                               "перед использованием")
            return

        current_time = datetime.datetime.now()

        if self.last_update_time and (current_time - self.last_update_time).total_seconds() < 300:
            days_left = self.cached_days_left
            total_progress, semester_progress = self.cached_progress
        else:
            days_left = days_until_graduation(self.start_year, self.num_courses)
            total_progress, semester_progress = calculate_progress(self.start_year, self.num_courses)

            self.cached_days_left = days_left
            self.cached_progress = (total_progress, semester_progress)
            self.last_update_time = current_time

        self.label.setText(
            f"До выпуска: {days_left} дней\nПрогресс: {total_progress:.2f}%\nСеместр: {semester_progress:.2f}%"
        )

    def toggle_settings(self):
        self.is_expanded = not self.is_expanded

        self.animation = QPropertyAnimation(self, b"size")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        if self.is_expanded:
            self.animation.setEndValue(QSize(self.width(), 280))
        else:
            self.animation.setEndValue(QSize(self.width(), 180))

        self.animation.start()

        self.background_animation = QPropertyAnimation(self.background_widget, b"size")
        self.background_animation.setDuration(300)
        self.background_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        if self.is_expanded:
            self.background_animation.setEndValue(QSize(self.width(), 280))
        else:
            self.background_animation.setEndValue(QSize(self.width(), 180))

        self.background_animation.start()

        self.start_year_label.setVisible(self.is_expanded)
        self.start_year_input.setVisible(self.is_expanded)
        self.num_courses_label.setVisible(self.is_expanded)
        self.num_courses_input.setVisible(self.is_expanded)
        self.slider_label.setVisible(self.is_expanded)
        self.slider.setVisible(self.is_expanded)
        self.save_button.setVisible(self.is_expanded)
        self.delete_background_button.setVisible(self.is_expanded)
        self.exit_button.setVisible(self.is_expanded)
        self.about_button.setVisible(self.is_expanded)

        QApplication.processEvents()

    def toggle_lock(self):
        self.is_locked = not self.is_locked
        if self.is_locked:
            self.pin_button.setIcon(QIcon(QPixmap(self.pin_icon_rotated)))
        else:
            self.pin_button.setIcon(QIcon(QPixmap(self.pin_icon_normal)))

    def change_opacity(self, value):
        self.opacity = value
        self.setStyleSheet(f"background-color: rgba(0, 0, 0, {value * 2.55}); border-radius: 10px;")
        self.background_opacity_effect.setOpacity(value / 100.0)

    def change_background_image(self):
        desktop_path = get_desktop_path()

        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите фоновое изображение",
            desktop_path,
            "Images (*.png *.jpg *.bmp)"
        )
        if file_name:
            image = QImage(file_name)
            if image.isNull():
                self.show_notification("Не удалось загрузить изображение")
                return

            scaled_image = image.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)
            scaled_image.save(self.background_image)
            background_image_path = self.background_image.replace("\\", "/")
            self.background_widget.setStyleSheet(f"""
                background-image: url('{background_image_path}'); 
                background-repeat: no-repeat;
                background-position: center;
                background-size: contain;
                border-radius: 10px;
            """)

    def delete_background(self):
        if os.path.exists(self.background_image):
            os.remove(self.background_image)
            self.show_notification("Фоновое изображение удалено")

            self.background_widget.setStyleSheet("""
                    background-image: none;
                    border-radius: 10px;
                """)
        else:
            self.show_notification("Фоновое изображение отсутствует")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.is_locked:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.is_locked:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            screen_geometry = QApplication.primaryScreen().geometry()
            new_pos.setX(max(screen_geometry.left(), min(new_pos.x(), screen_geometry.right() - self.width())))
            new_pos.setY(max(screen_geometry.top(), min(new_pos.y(), screen_geometry.bottom() - self.height())))
            self.animation = QPropertyAnimation(self, b"pos")
            self.animation.setDuration(100)
            self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)
            self.animation.setEndValue(new_pos)
            self.animation.start()
            event.accept()

    def closeEvent(self, event):
        if self.is_closing:
            event.accept()
            return

        self.is_closing = True
        self.save_settings_to_file()

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.animation.finished.connect(self.finish_close)
        self.animation.start()

        event.ignore()

    def finish_close(self):
        QTimer.singleShot(100, QApplication.instance().quit)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = TransparentWidget()
    widget.show()
    sys.exit(app.exec())