# -*- coding: utf-8 -*-

import io
import os
import sys
import cv2
import mss
import mss.tools
import html
import numpy as np 
import pygetwindow as gw
from io import BytesIO
from PIL import Image,ImageGrab
from multiprocessing import freeze_support
from PySide6.QtGui import QPalette, QColor, QFontMetrics, QIcon, QPixmap
from PySide6.QtWidgets import QMainWindow, QMessageBox, QApplication, QPushButton, QHBoxLayout, QWidget, QScrollArea
from PySide6.QtCore import Signal, QTimer, QSize, Property, QObject, QEasingCurve, QPropertyAnimation, Qt, Signal, Slot


from settings import *
from config_handler import *
from google_credentials import *

import time


# set GCP parameters
client_vision = None
client_translate = None


# create icon scale signal
class IconScaler(QObject):
    icon_size_changed = Signal(QSize)

    def __init__(self):
        super().__init__()
        self._icon_size = QSize(32, 32)

    @Property(QSize, notify=icon_size_changed)
    def icon_size(self):
        return self._icon_size

    @icon_size.setter
    def icon_size(self, size):
        self._icon_size = size
        self.icon_size_changed.emit(size)

# create button scale class and add the animations when cursor hover、press、release the button
class ScalableButton(QPushButton):
    def __init__(self, name, icon_path, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.icon_path = icon_path
        self.icon_scaler = IconScaler()
        self.is_pressed = False

        # create a property animation
        self.animation = QPropertyAnimation(self.icon_scaler, b"icon_size")
        self.animation.setDuration(200)  # animation duration (milliseconds)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)  # use an appropriate easing curve

        # connect the 'icon_size_changed' signal to update the icon size of the button
        self.icon_scaler.icon_size_changed.connect(self.updateIconSize)

        # connect the 'pressed' signal and 'released' signal to execute the shrink and restore operations
        self.pressed.connect(self.onButtonPressed)
        self.released.connect(self.onButtonReleased)

        self.setObjectName(name)

        self.createIcon(icon_path)

    def createIcon(self, path):
        # create an icon
        icon = QIcon(path)

        # set the icon to the button
        self.setIcon(icon)

        # set the initial icon size
        self.setIconSize(self.icon_scaler.icon_size)

    def onButtonPressed(self):
        # when the mouse presses the button, shrink the icon and change it to a new icon if available
        self.animateIconSize(QSize(28, 28))
        self.is_pressed = True

    def onButtonReleased(self):
        # upon releasing the mouse button, restore the original icon size.
        self.is_pressed = False
        self.createIcon(self.icon_path)
        self.animateIconSize(QSize(40, 40))

    def enterEvent(self, event):
        # when the mouse enters the button block, enlarge the icon
        if not self.is_pressed: 
            self.animateIconSize(QSize(40, 40))

    def leaveEvent(self, event):
        # upon mouse leaving the button, restore the original icon size
        if not self.is_pressed: 
            self.animateIconSize(QSize(32, 32))

    def animateIconSize(self, target_size):
        self.animation.setStartValue(self.icon_scaler.icon_size)
        self.animation.setEndValue(target_size)
        self.animation.start()

    def updateIconSize(self, size):
        self.setIconSize(size)


class ScreenshotWindow(QMainWindow):
    mouse_release = Signal(int, int, int, int)

    def __init__(self, main_window_screen):
        super().__init__()

        if getattr(sys, 'frozen', False):
            # 应用程序被打包
            self.app_dir = sys._MEIPASS
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.app_dir = os.path.dirname(os.path.dirname(current_dir))

        # screen info
        self.main_window_screen = main_window_screen
        
        # initial screenshot region window
        self.initUI()

        # mouse event
        self.mouse_press_position = None
        self.mouse_tracking_position = None
        self.mouse_release_position = None
        self.mouse_is_pressed = False

    def initUI(self):
        self.setWindowTitle("Screenshot")
        self.setWindowFlags(Qt.FramelessWindowHint)

        # Set the window background color to black
        capture_window_palette = QPalette()
        capture_window_palette.setColor(QPalette.Window, QColor(0, 0, 0))
        self.setPalette(capture_window_palette)

        # Set the window opacity
        self.setWindowOpacity(0.4)
        
        # Use the stored screen for this window
        self.move(self.main_window_screen.geometry().topLeft())

        # setting the geometry of window
        screen_geometry = self.main_window_screen.geometry()

        # set x, y coordinate & width, height
        start_x_position = screen_geometry.left()
        start_y_position = screen_geometry.top()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        self.setGeometry(start_x_position, start_y_position, screen_width, screen_height)

        self.setCursor(Qt.CrossCursor)

        # plot the border of the window
        self.screenshot_region_frame = QFrame(self)
        self.screenshot_region_frame.setStyleSheet('QFrame {background-color:  rgba(180, 180, 180, 150); }')
        self.screenshot_region_frame.hide()

        layout = QHBoxLayout()
        layout.addWidget(self.screenshot_region_frame)

        container_widget = QWidget(self)
        container_widget.setLayout(layout)

        self.setCentralWidget(container_widget)

    def set_frame_to_disapper(self):
        self.screenshot_region_frame.show()
        self.screenshot_region_frame.setGeometry(0, 0, 0, 0)

        # take a whole screenshot first
        app_window = gw.getWindowsWithTitle("Screenshot")
        if app_window:
            app_window = app_window[0]
            # get windows coordinates info
            left, top, right, bottom = app_window.left, app_window.top, app_window.right, app_window.bottom

            # use mss fuction to take a screenshot
            with mss.mss() as sct:
                for monitor in sct.monitors:
                    if monitor['left'] == left and monitor['top'] == top and monitor['width'] == abs(left-right) and monitor['height'] == abs(top-bottom):
                        sct_img = sct.grab(monitor)
                        screenshot_path = os.path.join(self.app_dir, "screenshot.png")
                        mss.tools.to_png(sct_img.rgb, sct_img.size, output=screenshot_path)
                        break

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            screenshot_path = os.path.join(self.app_dir, "screenshot.png")
            if os.path.exists(screenshot_path):
                os.remove(screenshot_path)
            self.mouse_release.emit(0, 0, 0, 0)  # Emit the signal
            self.close()
            event.ignore()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_press_position = event.pos()
            self.mouse_is_pressed = True
            
            # show the paint frame and set it to invisible at first
            self.set_frame_to_disapper()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_release_position = event.pos()
            self.setCursor(Qt.ArrowCursor)  # change back to arrow cursor
            self.mouse_is_pressed = False
            self.close()

            # Emit the custom signal with coordinates
            if self.mouse_press_position and self.mouse_release_position:
                # Get the screen where the screenshot window is displayed
                screen = self.screen()
                scale_factor = screen.devicePixelRatio()

                # set the correct number after scale
                x1, y1 = self.mouse_press_position.x()*scale_factor, self.mouse_press_position.y()*scale_factor
                x2, y2 = self.mouse_release_position.x()*scale_factor, self.mouse_release_position.y()*scale_factor
                self.mouse_release.emit(x1, y1, x2, y2)  # Emit the signal

    def mouseMoveEvent(self, event):
        if self.mouse_is_pressed:
            self.mouse_tracking_position = event.pos()
            self.plot_screenshot_region()

    def plot_screenshot_region(self):
        if self.mouse_press_position and self.mouse_tracking_position:
            x = min(self.mouse_press_position.x(), self.mouse_tracking_position.x())
            y = min(self.mouse_press_position.y(), self.mouse_tracking_position.y())
            width = abs(self.mouse_tracking_position.x() - self.mouse_press_position.x())
            height = abs(self.mouse_tracking_position.y() - self.mouse_press_position.y()) 

            # adjust border lines position
            self.screenshot_region_frame.setGeometry(x, y, width, height)


class MainMenuWindow(QMainWindow):
    def __init__(self, config_handler: ConfigHandler, google_credential: GoogleCloudClient):
        global client_vision, client_translate

        if getattr(sys, 'frozen', False):
            # application is in packaged
            app_dir = sys._MEIPASS
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            app_dir = os.path.dirname(os.path.dirname(current_dir))

        self.app_dir = app_dir

        super().__init__()

        # get the screen info that main_window stay on
        self.main_window_screen = None

        # read config file
        self.config_handler = config_handler

        self.google_credential = google_credential

        # set private member
        self._label_font_size = 12
        self._frequency = ""
        self._auto_recaputre_state = None
        self.pause_capture = False
        self.result_1 = ""
        self.result_2 = ""

        # set up the 'resume_capture' timer
        self.resume_capture_timer = QTimer(self)
        self.resume_capture_timer.setSingleShot(True)
        self.resume_capture_timer.timeout.connect(self.start_capture)

        # set action_button countdown
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.update_countdown_text)
        self.countdown = 0 

        # Set the title
        self.setWindowTitle("Babel Tower")

        # Set the window background color to black
        main_window_palette = QPalette()
        main_window_palette.setColor(QPalette.Window, QColor(10, 10, 10))
        self.setPalette(main_window_palette)

        # Set the window opacity
        self.setWindowOpacity(0.95)

        # Set the window geometry
        screen_geometry = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geometry.x() + (screen_geometry.width() // 3) * 2, 
                         screen_geometry.y() + screen_geometry.height() // 4,
                         screen_geometry.width() // 4.5, screen_geometry.height() // 2)
    
        # Create a button to add the screen capture window
        new_file_path = os.path.join(self.app_dir, "img/ui/add_capture_window.png")
        self.add_window_button = ScalableButton("add_window_button", new_file_path)
        self.add_window_button.setToolTip("新增螢幕擷取視窗")
        self.add_window_button.setStyleSheet(
            "QPushButton {"
            "    background-color: rgba(0, 0, 0, 0);"
            "    color: rgb(58, 134, 255);"
            "    border-radius: 8px;"
            "}"
            "QPushButton:hover {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #488EF7, stop: 1 #3478F6);"
            "    border: none;"
            "    color: white;"
            "}"
            "QPushButton:pressed {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #3879E3, stop: 1 #2D66EA);"
            "    border: none;"
            "    color: white;"
            "}"
        )
        self.add_window_button.setMinimumSize(44, 44)  # Set the minimum size for the button to ensure the icon fits
        self.add_window_button.clicked.connect(self.add_or_check_screen_capture_window)

        # Create a capturing button to start screen capture
        new_file_path = os.path.join(self.app_dir, "img/ui/record_button_start.svg")
        self.action_button = ScalableButton("action_button", new_file_path)
        self.action_button.setToolTip("開始擷取畫面")
        self.action_button.setStyleSheet(
            "QPushButton {"
            "    background-color: rgba(0, 0, 0, 0);"
            "    color: rgb(58, 134, 255);"
            "    border-radius: 8px;"
            "    font-size: 30px;"
            "    font-weight: bold;"
            "}"
            "QPushButton:hover {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #488EF7, stop: 1 #3478F6);"
            "    border: none;"
            "    color: white;"
            "}"
            "QPushButton:pressed {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #3879E3, stop: 1 #2D66EA);"
            "    border: none;"
            "    color: white;"
            "}"
        )
        self.action_button.setMinimumSize(44, 44)  # Set the minimum size for the button to ensure the icon fits
        self.action_button.clicked.connect(self.toggle_capture)
        self.capturing = False  # Track capturing state

        # Create a button to capture the screenshot
        new_file_path = os.path.join(self.app_dir, "img/ui/screenshot_button.png")
        self.screenshot_button = ScalableButton("add_window_button", new_file_path)
        self.screenshot_button.setToolTip("螢幕截圖")
        self.screenshot_button.setStyleSheet(
            "QPushButton {"
            "    background-color: rgba(0, 0, 0, 0);"
            "    color: rgb(58, 134, 255);"
            "    border-radius: 8px;"
            "}"
            "QPushButton:hover {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #488EF7, stop: 1 #3478F6);"
            "    border: none;"
            "    color: white;"
            "}"
            "QPushButton:pressed {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #3879E3, stop: 1 #2D66EA);"
            "    border: none;"
            "    color: white;"
            "}"
        )
        self.screenshot_button.setMinimumSize(44, 44)  # Set the minimum size for the button to ensure the icon fits

        # set timer for delay process the capture_screenshot function
        self.screenshot_timer = QTimer(self)
        self.screenshot_timer.timeout.connect(self.show_screenshot_window)
        self.screenshot_button.clicked.connect(self.delayed_process_screenshot_function)

        # Create a button to pin the window on the toppest
        new_file_path = os.path.join(self.app_dir, "img/ui/pin_button_disable.png")
        self.pin_button = ScalableButton("pin_button", new_file_path)
        self.pin_button.setToolTip("取消釘選")
        self.pin_button.setStyleSheet(
            "QPushButton {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #3879E3, stop: 1 #2D66EA);"
            "    border-radius: 8px;"
            "}"
            "QPushButton:hover {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #488EF7, stop: 1 #3478F6);"
            "}"
            "QPushButton:pressed {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #3879E3, stop: 1 #2D66EA);"
            "}"
        )
        self.pin_button.setMinimumSize(44, 44)  # Set the minimum size for the button to ensure the icon fits
        self.pin_button.clicked.connect(self.pin_on_top)
        self.is_pined = True  # Track pining state

        # Create a button to clear label text
        new_file_path = os.path.join(self.app_dir, "img/ui/cleanup_button.png")
        self.clear_text_button = ScalableButton("clear_text_button", new_file_path)
        self.clear_text_button.setToolTip("清空文本")
        self.clear_text_button.setStyleSheet(
            "QPushButton {"
            "    background-color: rgba(0, 0, 0, 0);"
            "    border-radius: 8px;"
            "}"
            "QPushButton:hover {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #EB6777, stop: 1 #E63F46);"
            "    border: none;"
            "    color: white;"
            "}"
            "QPushButton:pressed {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #6E2C35, stop: 1 #6D181A);"
            "    border: none;"
            "    color: white;"
            "}"
        )
        self.clear_text_button.setMinimumSize(44, 44)  # Set the minimum size for the button to ensure the icon fits
        self.clear_text_button.clicked.connect(self.clear_label_text)

        # Create a button to open settings window
        new_file_path = os.path.join(self.app_dir, "img/ui/settings_button.svg")
        self.settings_button = ScalableButton("settings_button", new_file_path)
        self.settings_button.setToolTip("設定")
        self.settings_button.setStyleSheet(
            "QPushButton {"
            "    background-color: rgba(0, 0, 0, 0);"
            "    color: rgb(58, 134, 255);"
            "    border-radius: 8px;"
            "}"
            "QPushButton:hover {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #488EF7, stop: 1 #3478F6);"
            "    border: none;"
            "    color: white;"
            "}"
            "QPushButton:pressed {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #3879E3, stop: 1 #2D66EA);"
            "    border: none;"
            "    color: white;"
            "}"
        )

        self.settings_button.setMinimumSize(44, 44)  # Set the minimum size for the button to ensure the icon fits
        self.settings_button.clicked.connect(self.show_settings)

        # create a horizontal line to separate the label block and the button block
        self.line = QFrame()
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)
        self.line.setLineWidth(1)  # set line width to 2px

        # create a QLabel for displaying OCR recognized text
        self.ocr_label = QLabel("  原 文：", self)
        self.ocr_label.setAutoFillBackground(False)  # set the background color to be transparent
        self.ocr_label.setStyleSheet("color: white;")  # set text color to white
        self.ocr_text_label = QLabel("", self)
        self.ocr_text_label.setStyleSheet("background-color: rgb(50, 50, 50); border-radius: 10px;")
        self.ocr_text_label.setAutoFillBackground(True)  # set the background color to be transparent
        self.ocr_text_label.setContentsMargins(10, 10, 10, 10)  # set the left, right, top, and bottom margins to 10px
        self.ocr_text_label.setWordWrap(True)  # enable automatic word wrapping
        self.ocr_text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # set text in label which can selected by users
        self.ocr_text_label.setCursor(Qt.IBeamCursor)  # set cursor style to selected cursor style

        # Create a scroll area
        ocr_scroll_area = QScrollArea()
        ocr_scroll_area.setWidgetResizable(True)

        # remove the frame/border
        ocr_scroll_area.setFrameShape(QScrollArea.NoFrame)
        ocr_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Set the label as the widget for the scroll area
        ocr_scroll_area.setWidget(self.ocr_text_label)

        # create a QLabel for displaying translated text
        self.translation_label = QLabel("  翻 譯：", self)
        self.translation_label.setStyleSheet("color: white;")  
        self.translation_label.setAutoFillBackground(False)  
        self.translation_text_label = QLabel("", self)
        self.translation_text_label.setAutoFillBackground(True)  
        self.translation_text_label.setStyleSheet("background-color: rgb(50, 50, 50); border-radius: 10px;")
        self.translation_text_label.setContentsMargins(10, 10, 10, 10)  
        self.translation_text_label.setWordWrap(True)  
        self.translation_text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  
        self.translation_text_label.setCursor(Qt.IBeamCursor)  

        # Create a scroll area
        transaltion_scroll_area = QScrollArea()
        transaltion_scroll_area.setWidgetResizable(True)

        # Remove the frame/border
        transaltion_scroll_area.setFrameShape(QScrollArea.NoFrame)
        transaltion_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Set the label as the widget for the scroll area
        transaltion_scroll_area.setWidget(self.translation_text_label)

        # set the font size and weight for ocr_label and translation_label
        font = QFont()
        font.setPointSize(12)
        font.setBold(True) # 設置粗體
        self.ocr_label.setFont(font)
        self.translation_label.setFont(font)

        # Calculate the height based on font size
        # Set the height of ocr_label, translation_label
        font_metrics = QFontMetrics(font)
        label_height = font_metrics.height()
        self.ocr_label.setFixedHeight(label_height)
        self.translation_label.setFixedHeight(label_height)

        # read the 'text_font_size' parameter from the configuration file
        text_font_size = self.config_handler.get_font_size()
        self.update_text_font_size(text_font_size)

        # read the 'text_font_color' parameter from the configuration file
        text_font_color = self.config_handler.get_font_color()
        self.update_text_font_color(text_font_color)

        # read the 'capture_frequency' parameter from the configuration file
        frequency = self.config_handler.get_capture_frequency()
        self.update_recognition_frequency(frequency)

        # read the 'auto_capture_state' parameter from the configuration file
        state = self.config_handler.get_auto_recapture_state()
        self.update_auto_capture_state(state)

        # Create a vertical layout
        layout = QVBoxLayout()

        # create a horizontal layout for function buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_window_button)
        button_layout.addWidget(self.action_button)
        button_layout.addWidget(self.screenshot_button)
        button_layout.addWidget(self.pin_button)
        button_layout.addStretch(1) 
        button_layout.addWidget(self.clear_text_button)
        button_layout.addWidget(self.settings_button)

        # Add the horizontal button layout and system state layout to the vertical layout
        layout.addLayout(button_layout)
        # layout.addLayout(system_state_layout)

        # Add the horizontal line to the vertical layout to seperate the system_state_layout and ocr_label
        layout.addWidget(self.line)

        # Add ocr_label and translation_label to the layout
        layout.addWidget(self.ocr_label)
        layout.addWidget(ocr_scroll_area)
        layout.addWidget(self.translation_label)
        layout.addWidget(transaltion_scroll_area)

        # Create a QWidget as a container for the layout
        widget = QWidget(self)
        widget.setLayout(layout)

        # Add the QWidget to the main window
        self.setCentralWidget(widget)

        # set window flags to keep it always on top
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        # Initialize the attribute
        self.screen_capture_window = None 

        # set timer for messagebox delayed show
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.show_message_box)

        # check if it's the first time using the app
        if self.config_handler.get_google_credential_path() != "":
            # set up Google_Credential_key as an OS environment variable
            google_key_file_path = self.config_handler.get_google_credential_path()
            self.google_credential.check_google_credential(google_key_file_path)

            if not self.update_google_credential_state():
                # set timer for messagebox delayed show
                self.timer = QTimer(self)
                self.timer.timeout.connect(self.show_message_box)
                self.delayed_show_message_box()
        else:      
            # set timer for messagebox delayed show
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.show_message_box)
            self.delayed_show_message_box()

            # set only setting button enabled
            for button in [self.add_window_button, self.action_button, self.screenshot_button, self.pin_button, self.clear_text_button]:
                button.setEnabled(False)

    def update_google_credential_state(self):
        global client_vision, client_translate

        # check google vision and google translation is setted or not
        if self.google_credential.get_google_vision() and self.google_credential.get_google_translation():
            client_vision = self.google_credential.get_google_vision()
            client_translate = self.google_credential.get_google_translation()

            for button in [self.add_window_button, self.action_button, self.screenshot_button, self.pin_button, self.clear_text_button]:
                button.setEnabled(True)

            return True
        else: 
            for button in [self.add_window_button, self.action_button, self.screenshot_button, self.pin_button, self.clear_text_button]:
                button.setEnabled(False)

            return False

    def delayed_show_message_box(self):
        # start a timer to display a message box after a certain delay
        self.timer.start(500)  # set the delay time to 0.5 seconds (500 milliseconds)

    def show_message_box(self):
        # 停止计时器
        self.timer.stop()
        
        new_file_path = os.path.join(self.app_dir, "img/index/Babel_Tower.png")
        customIcon = QPixmap(new_file_path)  # set icon image
        customIcon = customIcon.scaled(128, 128)

        # create messagebox
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Welcome ! ")
        msg_box.setIconPixmap(customIcon)
        msg_box.setText("歡迎使用「Babel Tower」！ \n"
            "\n在使用此應用程式之前，請至 【設定】 > 【系統】 > 【設置 Google 憑證】 "
            "，上傳已申請的 Google 憑證。")

        # set the message box to always display on top
        msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
        msg_box.exec()
        
    def toggle_capture(self):
        if self.capturing:
            self.stop_capture()
        else:
            self.start_capture()

    def minimize_all_open_windows(self):
        self.setWindowFlags(Qt.WindowStaysOnBottomHint)

        # check if a screen capture window is already open
        if hasattr(self, 'screen_capture_window') and self.screen_capture_window:
            self.screen_capture_window.setWindowFlags(Qt.WindowStaysOnBottomHint)

    def restore_all_windows(self):
        # restore the main window after capturing the screenshot
        self.setWindowFlag(Qt.WindowStaysOnBottomHint, False)
        if self.is_pined:
            self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.show()

        # check if a screen capture window is already open
        if hasattr(self, 'screen_capture_window') and self.screen_capture_window:
            # restore the screen capture window after capturing the screenshot
            self.screen_capture_window.setWindowFlag(Qt.WindowStaysOnBottomHint, False)
            self.screen_capture_window.showNormal()
            if self.is_pined:
                self.screen_capture_window.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.screen_capture_window.show()

    def delayed_process_screenshot_function(self):
        # check screen capture is working or not
        if self.capturing:
            self.stop_capture()
            self.pause_capture = True

        if self.pause_capture:
            self.countdown_timer.stop()
            self.resume_capture_timer.stop()
            for button in [self.add_window_button,self.action_button, self.pin_button, self.clear_text_button, self.settings_button]:
                button.setEnabled(False)
            
        self.minimize_all_open_windows()

        # start timer to delay process the screenshot function
        self.screenshot_timer.start(300)  # delay 0.3 seconds

    def show_screenshot_window(self):
        # stop screenshot_timer
        self.screenshot_timer.stop()

        # Get the main window's screen based on its current position
        self.main_window_screen = QApplication.screenAt(self.mapToGlobal(self.rect().topLeft()))

        if self.main_window_screen is not None:
            self.screenshot_window = ScreenshotWindow(self.main_window_screen)
            # Connect the custom signal to a slot in MainWindow
            self.screenshot_window.mouse_release.connect(self.capture_screenshot)
            self.screenshot_window.show()

    @Slot(int, int, int, int)
    def capture_screenshot(self, x1, y1, x2, y2):
        # get screenshot_path
        screenshot_path = os.path.join(self.app_dir, "screenshot.png")

        self.restore_all_windows()

        if os.path.exists(screenshot_path):
            # open screenshot image and change image_color into gray
            with Image.open(screenshot_path) as img:
                # crop the image region
                crop_box = (x1, y1, x2, y2)
                cropped_img = img.crop(crop_box)

                img_gray = cropped_img.convert("L")
                img_bytes = BytesIO()
                img_gray.save(img_bytes, format="PNG")
                image_data = img_bytes.getvalue()

            # use Google Cloud Vision API to perform OCR task
            image = vision_v1.Image(content=image_data)
            response = client_vision.text_detection(image=image)
            texts = response.text_annotations

            # extract recognized text
            if texts:
                detected_text = texts[0].description

                # set up displaying the OCR results on the interface
                self.ocr_text_label.setText(f'{detected_text}')

                # concatenate all the sentences together
                sentence = detected_text.replace("\n", "")

                # split the text into individual lines based on line breaks
                lines = detected_text.splitlines()
                translated_lines = []

                # Google 翻譯
                target_language = "zh-TW"  # replace this with the desired target language code (e.g., English --> en, Traditional Chinese --> zh-TW)
                
                # First scenario: separated sentences
                for line in lines:
                    # translate
                    translated_line = client_translate.translate(line, target_language=target_language)
                    # Unescape HTML entities
                    unescape_translated_text = html.unescape(translated_line["translatedText"])
                    # join to list
                    translated_lines.append(unescape_translated_text)
                self.result_1 = "<br>".join(translated_lines)

                # Second scenario: The text to recognize is a complete paragraph that has been split into multiple lines due to its length too long
                translated_sentence = client_translate.translate(sentence, target_language=target_language)
                unescape_translated_sentence = html.unescape(translated_sentence["translatedText"])
                self.result_2 = unescape_translated_sentence

                # set it to HTML format
                font_size = self._label_font_size
                result_1_html = f"<span style='font-size: {font_size}pt'>{self.result_1}</span>"
                result_2_html = f"<span style='font-size: {font_size}pt'>{self.result_2}</span>"
                separator_line = "<hr style='border-width: 2px; border-style: solid; width: 100%; margin-top: 5px; margin-bottom: 5px;'>"

                # combine both results and display them on the interface
                final_result = f"{result_1_html}{separator_line}{result_2_html}"
                self.translation_text_label.setText(final_result)
            else:
                pass

            # delete screenshot image after ocr complete
            os.remove(screenshot_path)

        # if screen_capture_window is exsited
        if hasattr(self, 'screen_capture_window') and self.screen_capture_window:
            if self.pause_capture:
                if self._auto_recaputre_state == 2:
                    # resume screen capture after countdown 5 seconds
                    self.resume_capture_timer.start(5000)

                    # set action_button text into countdown timer
                    self.countdown = 5
                    self.action_button.setIcon(QIcon())
                    self.update_countdown_text()
                    self.countdown_timer.start(1000)
                else:
                    self.pause_capture = False
                    for button in [self.add_window_button,self.action_button, self.screenshot_button, self.pin_button, self.clear_text_button, self.settings_button]:
                        button.setEnabled(True)

    def update_countdown_text(self):
        self.countdown -= 1
        if self.countdown >= 0:
            self.action_button.setText(str(self.countdown + 1))
        else:
            self.countdown_timer.stop()
            self.action_button.setEnabled(True)
            self.screenshot_button.setEnabled(True)

    def pin_on_top(self):
        if self.is_pined:
            self.is_pined = False 
            new_file_path = os.path.join(self.app_dir, "img/ui/pin_button_enable.png")
            self.pin_button.createIcon(new_file_path)
            self.pin_button.setToolTip("釘選在最上層")
            self.pin_button.setStyleSheet(
                "QPushButton {"
                "    background-color: rgba(0, 0, 0, 0);"
                "    border-radius: 8px;"
                "}"
                "QPushButton:hover {"
                "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #488EF7, stop: 1 #3478F6);"
                "}"
                "QPushButton:pressed {"
                "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #3879E3, stop: 1 #2D66EA);"
                "}"
            )

            # remove the topest flag from the main_window
            self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
            self.show()

            
            # remove the topest flag from the screen_capture_window if it exits
            if hasattr(self, 'screen_capture_window') and self.screen_capture_window:
                self.screen_capture_window.setWindowFlag(Qt.WindowStaysOnTopHint, False)
                self.screen_capture_window.show()
        else:
            self.is_pined = True 
            new_file_path = os.path.join(self.app_dir, "img/ui/pin_button_disable.png")
            self.pin_button.createIcon(new_file_path)
            self.pin_button.setToolTip("取消釘選")
            self.pin_button.setStyleSheet(
                "QPushButton {"
                "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #3879E3, stop: 1 #2D66EA);"
                "    border-radius: 8px;"
                "}"
                "QPushButton:hover {"
                "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #488EF7, stop: 1 #3478F6);"
                "}"
                "QPushButton:pressed {"
                "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #3879E3, stop: 1 #2D66EA);"
                "}"
            )

            # restore the topest flag back to main_window
            self.setWindowFlag(Qt.WindowStaysOnTopHint)
            self.show()
            
            # if the screen_capture_window exists, restore the topest flag as well
            if hasattr(self, 'screen_capture_window') and self.screen_capture_window:
                self.screen_capture_window.setWindowFlags(Qt.WindowStaysOnTopHint)
                self.screen_capture_window.show()

    def clear_label_text(self):
        self.ocr_text_label.setText("")
        self.translation_text_label.setText("")
        self.result_1 = ""
        self.result_2 = ""

    def show_settings(self):
        # if the screen_capture_window exists, disabled it as well
        if hasattr(self, 'screen_capture_window') and self.screen_capture_window:
            self.screen_capture_window.setWindowFlag(Qt.WindowStaysOnTopHint, False)
            self.screen_capture_window.show()
            self.screen_capture_window.setDisabled(True)

        self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
        self.show()
        self.setDisabled(True)  # disabled main_window

        # Get the main window's screen based on its current position
        self.main_window_screen = QApplication.screenAt(self.mapToGlobal(self.rect().topLeft()))

        self.settings_window = SettingsWindow(self.config_handler, self.google_credential, self.main_window_screen)

        # set icon for settings dialog
        ico_path = os.path.join(self.app_dir, "img\\icon\\settings_icon.png")
        self.settings_window.setWindowIcon(QIcon(ico_path))

        self.settings_window.update_google_credential_state.connect(self.update_google_credential_state)
        self.settings_window.setting_window_closed.connect(self.set_main_and_capture_window_frame_window_back)
        self.settings_window.exec()

        self.setDisabled(False)  # enabled main_window
        if self.is_pined:
            # restore the topest flag for the main_capture_window
            self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.show()
    
        if hasattr(self, 'screen_capture_window') and self.screen_capture_window:
            self.screen_capture_window.setDisabled(False)
            if self.is_pined:
                # restore the topest flag for the screen_capture_window
                self.screen_capture_window.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            self.screen_capture_window.show()

    def update_text_font_size(self, new_font_size):
        # update the new font size to ocr_text_label and translation_text_label
        font = QFont()
        font.setPointSize(new_font_size)
        font.setBold(True) # 設置粗體
        self.ocr_text_label.setFont(font)
        self.translation_text_label.setFont(font)

        # check label test is cleared or not
        if self.result_1 != "":
            # Update text font size using HTML style
            updated_html = f"<span style='font-size: {new_font_size}pt'>{self.result_1}</span>" \
                        f"<hr style='border-width: 2px; border-style: solid; width: 100%; margin-top: 5px; margin-bottom: 5px;'>" \
                        f"<span style='font-size: {new_font_size}pt'>{self.result_2}</span>"
            self.translation_text_label.setText(updated_html)

        # Update private member: _label_font_size
        self._label_font_size = new_font_size

    def update_text_font_color(self, new_font_color):
        # update the new font color to ocr_text_label and translation_text_label
        self.ocr_text_label.setStyleSheet(f"background-color: rgb(50, 50, 50); border-radius: 10px; color: {new_font_color};")
        self.translation_text_label.setStyleSheet(f"background-color: rgb(50, 50, 50); border-radius: 10px; color: {new_font_color};")

    def update_recognition_frequency(self, new_frequency):
        # Update Frequency
        self._frequency = new_frequency

    def update_auto_capture_state(self, state):
        self._auto_recaputre_state = state

    def add_or_check_screen_capture_window(self):
        # Check if a screen capture window is already open
        if hasattr(self, 'screen_capture_window') and self.screen_capture_window:
            # set window back to normale state
            self.screen_capture_window.showNormal()
            self.screen_capture_window.setWindowFlags(Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
            if self.is_pined:
                self.screen_capture_window.setWindowFlag(Qt.WindowStaysOnTopHint)
            else:
                self.screen_capture_window.setWindowFlag(Qt.WindowStaysOnTopHint, False)
            
            self.screen_capture_window.show()

            QMessageBox.warning(self, "Warning", "你已經開啟擷取視窗了!")
        else:
            # Get the main window's screen based on its current position
            self.main_window_screen = QApplication.screenAt(self.mapToGlobal(self.rect().topLeft()))

            # Create and show the screen capture window
            self.screen_capture_window = ScreenCaptureWindow(self.main_window_screen)

            # set icon for screen capture window
            ico_path = os.path.join(self.app_dir, "img\\icon\\capture_icon.png")
            self.screen_capture_window.setWindowIcon(QIcon(ico_path))

            self.screen_capture_window.closed.connect(self.handle_screen_capture_window_closed)
            self.screen_capture_window.setWindowFlags(Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
            if self.is_pined:
                self.screen_capture_window.setWindowFlag(Qt.WindowStaysOnTopHint)
            self.screen_capture_window.show()

            self.add_window_button.setStyleSheet(
                "QPushButton {"
                "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #488EF7, stop: 1 #3478F6);"
                "    color: rgb(58, 134, 255);"
                "    border-radius: 8px;"
                "}"
                "QPushButton:hover {"
                "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #488EF7, stop: 1 #3478F6);"
                "    border: none;"
                "    color: white;"
                "}"
                "QPushButton:pressed {"
                "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #3879E3, stop: 1 #2D66EA);"
                "    border: none;"
                "    color: white;"
                "}"
            )
        
    def start_capture(self):
        if hasattr(self, 'screen_capture_window') and self.screen_capture_window:
            self.capturing = True 
            self.pause_capture = False
            
            new_file_path = os.path.join(self.app_dir, "img/ui/record_button_stop.png")
            self.action_button.createIcon(new_file_path)
            self.action_button.setText("")
            self.action_button.setToolTip("停止擷取畫面")
            self.action_button.setStyleSheet(
                "QPushButton {"
                "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #EB6777, stop: 1 #E63F46);"
                "    border-radius: 8px;"
                "    font-size: 30px;"
                "    font-weight: bold;"
                "}"
                "QPushButton:hover {"
                "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #EB6777, stop: 1 #E63F46);"
                "    border: none;"
                "    color: white;"
                "}"
                "QPushButton:pressed {"
                "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #6E2C35, stop: 1 #6D181A);"
                "    border: none;"
                "    color: white;"
                "}"
            )

            self.action_button.clicked.disconnect()
            self.action_button.clicked.connect(self.stop_capture)

            self.screen_capture_window.start_capture()

            for button in [self.add_window_button, self.pin_button, self.clear_text_button, self.settings_button]:
                button.setEnabled(False)

            self.screen_capture_window.setWindowFlag(Qt.WindowStaysOnTopHint, False)
            self.screen_capture_window.show()
        else:
            # create messagebox
            QMessageBox.warning(self, "Warning", "你尚未開啟擷取視窗!")

    def stop_capture(self):
        if hasattr(self, 'screen_capture_window') and self.screen_capture_window:
            self.capturing = False
            new_file_path = os.path.join(self.app_dir, "img/ui/record_button_start.svg")
            self.action_button.createIcon(new_file_path)
            self.action_button.setToolTip("開始擷取畫面")
            self.action_button.setStyleSheet(
                "QPushButton {"
                "    background-color: rgba(0, 0, 0, 0);"
                "    color: rgb(58, 134, 255);"
                "    border-radius: 8px;"
                "    font-size: 30px;"
                "    font-weight: bold;"
                "}"
                "QPushButton:hover {"
                "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #488EF7, stop: 1 #3478F6);"
                "    border: none;"
                "    color: white;"
                "}"
                "QPushButton:pressed {"
                "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #3879E3, stop: 1 #2D66EA);"
                "    border: none;"
                "    color: white;"
                "}"
            )

            self.action_button.clicked.disconnect()
            self.action_button.clicked.connect(self.toggle_capture)

            self.screen_capture_window.stop_capture()

            for button in [self.add_window_button, self.screenshot_button, self.pin_button, self.clear_text_button, self.settings_button]:
                button.setEnabled(True)

            self.screen_capture_window.setWindowFlags(Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
            if self.is_pined:
                self.screen_capture_window.setWindowFlag(Qt.WindowStaysOnTopHint)
            self.screen_capture_window.show()

    def set_main_and_capture_window_frame_window_back(self):
        # update the new configuration settings
        text_font_size = self.config_handler.get_font_size()
        text_font_color = self.config_handler.get_font_color()
        frequency = self.config_handler.get_capture_frequency()
        state = self.config_handler.get_auto_recapture_state()
        self.update_text_font_size(text_font_size)
        self.update_text_font_color(text_font_color)
        self.update_recognition_frequency(frequency)
        self.update_auto_capture_state(state)
        self.update_google_credential_state()

    def handle_screen_capture_window_closed(self):
        # Slot to handle the screen capture window being closed
        self.screen_capture_window = None

        self.pause_capture = False

        self.countdown_timer.stop()
        self.resume_capture_timer.stop()

        for button in [self.add_window_button,self.action_button, self.screenshot_button, self.pin_button, self.clear_text_button, self.settings_button]:
            button.setEnabled(True)

        # set the add_window_button back to normal
        self.add_window_button.setStyleSheet(
            "QPushButton {"
            "    background-color: (0, 0, 0, 0);"
            "    color: rgb(58, 134, 255);"
            "    border-radius: 8px;"
            "}"
            "QPushButton:hover {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #488EF7, stop: 1 #3478F6);"
            "    border: none;"
            "    color: white;"
            "}"
            "QPushButton:pressed {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #3879E3, stop: 1 #2D66EA);"
            "    border: none;"
            "    color: white;"
            "}"
        )

        # set the action_button back to start state
        new_file_path = os.path.join(self.app_dir, "img/ui/record_button_start.svg")
        self.action_button.createIcon(new_file_path)
        self.action_button.setText("")
        self.action_button.setToolTip("開始擷取畫面")
        self.action_button.setStyleSheet(
            "QPushButton {"
            "    background-color: rgba(0, 0, 0, 0);"
            "    color: rgb(58, 134, 255);"
            "    border-radius: 8px;"
            "    font-size: 30px;"
            "    font-weight: bold;"
            "}"
            "QPushButton:hover {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #488EF7, stop: 1 #3478F6);"
            "    border: none;"
            "    color: white;"
            "}"
            "QPushButton:pressed {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #3879E3, stop: 1 #2D66EA);"
            "    border: none;"
            "    color: white;"
            "}"
        )

    def get_frequncy(self):
        return self._frequency

    def closeEvent(self, event):
        # Check if the screen_capture_window is open and close it
        if self.screen_capture_window is not None:
            self.screen_capture_window.close()
        
        event.accept()

class ScreenCaptureWindow(QMainWindow):
    # Define a custom signal
    closed = Signal()
  
    def __init__(self, main_window_screen):
        super().__init__()

        # screen info
        self.main_window_screen = main_window_screen

        # declare a variable to store the previously recognized image
        self.previous_image = None

        # define variables to store the current screen scaling factor and correct the xy-coordinate offset for the current window
        self.scale_factor = 1.0
        self.monitor_modify_x = 0.0
        self.monitor_modify_y = 0.0

        # define variables to store the monitor information for the current window
        self.monitor = None

        # define boolen value record window is out of border or not
        self.is_found_monitor = False
  
        # set the title
        self.setWindowTitle("擷取視窗")

        # Set the window background color to black
        capture_window_palette = QPalette()
        capture_window_palette.setColor(QPalette.Window, QColor(40, 40, 40))
        self.setPalette(capture_window_palette)

        # set the window's transparency
        self.setWindowOpacity(0.7)

        # create a horizontal layout manager
        layout = QHBoxLayout()

        # setting the geometry of window
        screen_geometry = self.main_window_screen.geometry()

        # set x, y coordinate & width, height
        start_x_position = screen_geometry.left() + screen_geometry.width() // 4
        start_y_position = screen_geometry.top() + screen_geometry.height() // 2
        screen_width = screen_geometry.width() // 3
        screen_height = screen_geometry.height() // 4
        self.setGeometry(start_x_position, start_y_position, screen_width, screen_height)

        # plot the border of the window
        self.border_frame = QFrame(self)
        self.border_frame.setFrameShape(QFrame.Box)
        self.border_frame.setStyleSheet('QFrame { border: 3px solid red; border-radius: 10px;}')

        # add border lines to the layout manager
        layout.addWidget(self.border_frame)

        # create a widget to contain the layout manager
        container_widget = QWidget(self)
        container_widget.setLayout(layout)

        self.setCentralWidget(container_widget)
        
        # capture the countdown timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.capture_screen)

    def showEvent(self, event):
        # adjust the border position immediately after the window is displayed
        super().showEvent(event)
        self.adjustBorderPosition()

    def resizeEvent(self, event):
        # adjust the position of the border lines when the window size changes
        super().resizeEvent(event)
        self.adjustBorderPosition()

    def adjustBorderPosition(self):
        # get the newest window's height and width
        new_width = self.width()
        new_height = self.height()

        # adjust border lines shows position
        self.border_frame.setGeometry(0, 0, new_width, new_height)

    def get_monitor_info(self):
        # Get the screen where the screenshot window is displayed
        screen = self.screen()
        # get the ration of screen settings in windows system
        self.scale_factor = screen.devicePixelRatio()
        
        # use mss module to get the display of screen_capture_window which stayed on
        app_window = gw.getWindowsWithTitle("擷取視窗")
        if app_window:
            app_window = app_window[0]

            # get screen_capture_window top-left coordinate
            left, top = app_window.left, app_window.top

            # set a flag to check monitor is founded or not
            self.is_found_monitor = False

            # use mss to capture screen
            with mss.mss() as sct:
                # create a dictionary to save the distance with "left - monitor['left']" for every monitor
                over_border_distance_list = {}

                for monitor in sct.monitors[1:]:
                    # save the distance in dictionary with [distance] = monitor
                    distance = abs(left - monitor['left'])
                    over_border_distance_list[distance] = monitor

                    if monitor['left'] < left and monitor['top'] <= top:
                        distance_x, distance_y = left-monitor['left'], top-monitor['top']
                        if distance_x < monitor['width'] and distance_y < monitor['height']:
                            # modify the correct cropped coordinate
                            self.monitor_modify_x = (0.0 - monitor['left'])
                            self.monitor_modify_y = (0.0 - monitor['top'])

                            # save monitor info in self parameter
                            self.monitor = monitor

                            self.is_found_monitor = True                                
                            break

                    if self.is_found_monitor:
                        break

                if not self.is_found_monitor:
                    # get the closet display
                    min_distance = min(over_border_distance_list.keys())
                    closest_monitor = over_border_distance_list[min_distance]

                    # save monitor info in self parameter
                    self.monitor = closest_monitor

                    # modify the correct cropped coordinate
                    self.monitor_modify_x = (0.0 - closest_monitor['left'])
                    self.monitor_modify_y = (0.0 - closest_monitor['top'])
    
    def start_capture(self):
        self.previous_image = None  # clear the previous_image content before start capture

        # get the monitor info which capture_window stay on
        self.get_monitor_info()

        match main_window.get_frequncy():
            case "高 (1 秒)":
                self.timer.start(1000)  # Capture every 1000 milliseconds (1 second)

            case "標準 (2 秒)":
                self.timer.start(2000)  # Capture every 2000 milliseconds (2 second)

            case "慢 (3 秒)":
                self.timer.start(3000)  # Capture every 3000 milliseconds (3 second)

            case "非常慢 (5 秒)":
                self.timer.start(5000)  # Capture every 5000 milliseconds (5 second)

        # change the window opacity and border lines
        self.setWindowOpacity(0)
        self.border_frame.hide()

    def stop_capture(self):
        self.timer.stop()

        # restore window opacity and border lines
        self.setWindowOpacity(0.7)
        self.border_frame.show()

        # switch back to a frame window
        self.setWindowFlags(Qt.Window)
        self.show()

    def capture_screen(self):
        if self.isVisible():
            # get top-left and bottom-right coordinate, and modify right cropped values
            if self.is_found_monitor:
                x1 = (self.geometry().x() + self.monitor_modify_x) * self.scale_factor
            else:
                x1 = 0
            y1 = (self.geometry().y() + self.monitor_modify_y) * self.scale_factor
            x2 = (self.geometry().x() + self.geometry().width() + self.monitor_modify_x) * self.scale_factor
            y2 = (self.geometry().y() + self.geometry().height()+ self.monitor_modify_y) * self.scale_factor
            
            with mss.mss() as sct:
                # use mss module to grab whole region of monitor first
                sct_img = sct.grab(self.monitor)
                # Create the PIL Image
                pil_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                # crop the region
                screenshot = pil_img.crop((x1, y1, x2, y2))
    
            # compare image similarity before each OCR execution
            if self.is_similar_to_previous(screenshot):
                pass
            else:
                # Perform OCR using Google Cloud Vision on the screenshot
                self.perform_ocr(screenshot)

    def is_similar_to_previous(self, current_image):
        # compare the current image with the previously captured image for similarity
        if self.previous_image is not None:
            # convert a PIL image to OpenCV format
            previous_cv = cv2.cvtColor(np.array(self.previous_image), cv2.COLOR_RGB2BGR)
            current_cv = cv2.cvtColor(np.array(current_image), cv2.COLOR_RGB2BGR)

            # comparing images similarity
            result = cv2.matchTemplate(current_cv, previous_cv, cv2.TM_CCOEFF_NORMED)

            # get the maximum matching value
            max_similarity = np.max(result)

            if max_similarity == 1.0:
                check_result = cv2.matchTemplate(previous_cv, current_cv, cv2.TM_CCOEFF_NORMED)
                check_max_similarity = np.max(check_result)

                if check_max_similarity == 0.0:
                    return False # not similar to the previous image
                else:
                    return True # similar to the previous image
            else:
                # set the similarity threshold value
                similarity_threshold = 0.95

                if max_similarity >= similarity_threshold:
                    return True  # not similar to the previous image
                else:
                    return False  # similar to the previous image

    def closeEvent(self, event):
        # Stop the timer when the screen capture window is closed
        self.timer.stop()
        event.accept()
        self.closed.emit()  # Emit the signal when the window is closed

    def perform_ocr(self, screenshot):
        global client_vision, client_translate

        # save the current image as the previously captured image
        self.previous_image = screenshot.copy()

        # convert a PIL image to OpenCV format
        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        # convert the image to grayscale
        gray_image = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2GRAY)

        # convert grayscale image in OpenCV format to PIL format
        binary_image_pil = Image.fromarray(gray_image)

        # Save the screenshot to an in-memory buffer as a PNG image
        binary_image_buffer = io.BytesIO()
        binary_image_pil.save(binary_image_buffer, format='PNG')
        screenshot_bytes = binary_image_buffer.getvalue()

        # use Google Cloud Vision API to perform OCR
        image = vision_v1.Image(content=screenshot_bytes)
        response = client_vision.text_detection(image=image)
        texts = response.text_annotations

        # extract the recognized text
        if texts:
            detected_text = texts[0].description

            # set recognized text to main_window's ocr_text_label
            main_window.ocr_text_label.setText(detected_text)
 
            # merge the text lines into complete sentences
            lines = detected_text.replace("\n", "")

            # Google Cloud Translation
            target_language = "zh-TW"  # replace this with the desired target language code (e.g., English --> en, Traditional Chinese --> zh-TW)
            translated_lines = client_translate.translate(lines, target_language=target_language)

            # Unescape HTML entities
            unescape_translated_text = html.unescape(translated_lines["translatedText"])
            main_window.translation_text_label.setText(unescape_translated_text)  # 完全不以句點和問號為換行分界點
        else:
            pass


if __name__ == "__main__":

    # read config file class
    config_handler = ConfigHandler()
    config_handler.read_config_file()

    # create a instance of google_credentials's class
    google_credential = GoogleCloudClient()

    freeze_support()

    # create pyside6 app
    App = QApplication(sys.argv)

    # Create the screen capture window and the main capturing control window
    main_window = MainMenuWindow(config_handler, google_credential)

    # set icon for application
    if getattr(sys, 'frozen', False):
        app_dir = sys._MEIPASS
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    ico_path = os.path.join(app_dir, "Babel_Tower_windowOS.ico")
    main_window.setWindowIcon(QIcon(ico_path))

    # Show the windows
    main_window.show()
    
    # start the app
    sys.exit(App.exec())
  