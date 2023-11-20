# -*- coding: utf-8 -*-

import os
import sys
import shutil
from PySide6.QtCore import QStandardPaths, QUrl, Signal, QRect, QPoint, QPropertyAnimation, QEasingCurve, Property, QThread
from PySide6.QtGui import QFont, Qt, QDesktopServices, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel, QComboBox, QPushButton, QFrame, QColorDialog, QFileDialog, QMessageBox, QCheckBox

from config_handler import *
from google_credentials import *


class CheckGoogleCredentialThread(QThread):
    google_credential_checked = Signal(str)

    def __init__(self, config_handler, google_credential):
        super().__init__()
        self.config_handler = config_handler
        self.google_credential = google_credential

    def run(self):
        google_key_file_path = self.config_handler.get_google_credential_path()
        self.google_credential.check_google_credential(google_key_file_path)
        message = self.google_credential.get_message()
        self.google_credential_checked.emit(message)
        

# 創建 slide toggle check box
class SlideToggle(QCheckBox):
    def __init__(
        self,
        width = 54,
        height = 24,
        bg_color = "#777",
        circle_color = "#DDD",
        active_color = "#00BCff",
        animation_curve = QEasingCurve.Linear
    ):
        QCheckBox.__init__(self)

        # SET DEFALT PARAMETERS
        self.setFixedSize(width, height)
        self.setCursor(Qt.PointingHandCursor)

        # COLORS
        self._bg_color = bg_color
        self._circle_color = circle_color
        self._active_color = active_color

        # CREATE ANIMATION
        self._circle_position = 3
        self._circle_radius = height / 2 - 2  # 圆圈的半径
        self.animation = QPropertyAnimation(self, b"circle_position", self)
        self.animation.setEasingCurve(animation_curve)
        self.animation.setDuration(150)

        # CONNECT STATE CHANGED
        self.stateChanged.connect(self.start_transition)

    # CREATE NEW SET AND GET PROPERTIE
    @Property(float)
    def circle_position(self):
        return self._circle_position
    
    @circle_position.setter
    def circle_position(self, pos):
        self._circle_position = pos
        self.update()

    def start_transition(self, value):
        self.animation.stop()
        if value:
            self.animation.setEndValue(self.width() - 2 * self._circle_radius - 3)
        else:
            self.animation.setEndValue(3)

        # START ANIMATION
        self.animation.start()

    # SET NEW HIT AREA
    def hitButton(self, pos: QPoint):
        return self.contentsRect().contains(pos)

    def paintEvent (self, e):
        # SET PAINTER
        p = QPainter (self)
        p.setRenderHint(QPainter.Antialiasing)

        # SET AS NO PEN
        p. setPen(Qt.NoPen)

        # DRAW RECTANGLE
        rect = QRect(0, 0, self.width(), self.height())

        # CHECH IF IS CHECKED
        if not self.isChecked():
            # DRAW BG
            p.setBrush(QColor(self._bg_color))
            p.drawRoundedRect(0, 0, rect.width(), self.height(), self.height() / 2, self.height() / 2)

            # DRAW CIRCLE
            circle_x = self._circle_position
            circle_y = (self.height() - 2 * self._circle_radius) / 2  # 垂直居中
            p.setBrush(QColor(self._circle_color))
            p.drawEllipse(circle_x, circle_y, 2 * self._circle_radius, 2 * self._circle_radius)
        else:
            # DRAW BG
            p.setBrush(QColor(self._active_color))
            p.drawRoundedRect(0, 0, rect.width(), self.height(), self.height() / 2, self.height() / 2)

            # DRAW CIRCLE
            circle_x = self._circle_position
            circle_y = (self.height() - 2 * self._circle_radius) / 2  # 垂直居中
            p.setBrush(QColor(self._circle_color))
            p.drawEllipse(circle_x, circle_y, 2 * self._circle_radius, 2 * self._circle_radius)

        # END DRAW
        p.end()


# 创建一个新的类以用于设置窗口
class SettingsWindow(QDialog):
    # Create a custom signal for closed event
    setting_window_closed = Signal()

    # create a custom signal for update google credential state in main window
    update_google_credential_state = Signal()

    def __init__(self, config_handler: ConfigHandler, google_credential: GoogleCloudClient, main_window_screen):
        super().__init__()

        # set app's pwd
        if getattr(sys, 'frozen', False):
            # 应用程序被打包
            self.app_dir_path = sys._MEIPASS
        else:
            # 一般開發狀態
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.app_dir_path = os.path.dirname(os.path.dirname(current_dir))

        # 設定 setting window 字體大小
        self._font_size = 16

        # 讀取 config file
        self.config_handler = config_handler

        # import google credential module
        self.google_credential = google_credential

        # screen info
        self.main_window_screen = main_window_screen

        # # Set the window opacity
        self.setWindowOpacity(0.99)

        # 設置參數
        self._text_font_size = self.config_handler.get_font_size()
        self._text_font_color = self.config_handler.get_font_color()
        self._text_font_color_name = self._text_font_color
        self._frequency = self.config_handler.get_capture_frequency()
        self._auto_recapture_state = self.config_handler.get_auto_recapture_state()
        # self._google_credentials = self.config_handler.get_google_credential_path()

        # 设置窗口标题和属性
        self.setWindowTitle("設定")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)  # 使设置窗口始终位于顶层
        self.setFixedSize(300, 220)  # 視窗大小 300 x 220

        # Calculate the position to center the window on the main window's screen
        setting_window_geometry = self.main_window_screen.geometry()
        self.setGeometry(
            setting_window_geometry.left() + (setting_window_geometry.width() - self.width()) / 2,
            setting_window_geometry.top() + setting_window_geometry.height() // 4,
            self.width(),
            self.height()
        )

        # Create a top-level layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Create the tab widget for switch pages
        tabs = QTabWidget()
        tabs.addTab(self.create_text_settings(), "文字")
        tabs.addTab(self.create_recognition_settings(), "擷取")
        tabs.addTab(self.create_system_settings(), "系統")
        tabs.addTab(self.create_about_page(), "關於")
        tabs.setStyleSheet("QTabBar::tab { font-size: 14px; }")  # set tabs font size: 14px
 
        layout.addWidget(tabs)

        # start check google credential state thread
        self.check_google_credential_thread = CheckGoogleCredentialThread(self.config_handler, self.google_credential)
        self.check_google_credential_thread.google_credential_checked.connect(self.update_google_credential_state_label)
        self.check_google_credential_thread.start()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            event.ignore()  # 阻止 ESC 鍵事件傳播

    def create_text_settings(self):
        # 创建一个用于文本设置的 QWidget
        text_settings = QWidget()

        # set font size to 14px
        text_font = QFont()
        text_font.setPointSize(14)
        text_font.setBold(True) # 設置粗體

        # 创建文本大小下拉框
        text_size_label = QLabel("字體大小 ")
        text_size_label.setFont(text_font)
        text_size_combo = QComboBox()
        #text_size_combo.setFixedWidth(80)
        for text_size in range(10, 25, 2):
            text_size_combo.addItem(str(text_size))
        text_size_combo.setCurrentText(str(self._text_font_size))  # 設置文本字體大小
        text_size_combo.currentTextChanged.connect(self.update_text_size)

        # 创建文本颜色按钮以及預覽顏色
        text_color_label = QLabel("字體顏色 ")
        text_color_label.setFont(text_font)

        text_color_button = QPushButton("選擇顏色")
        #text_color_button.setFixedWidth(70)
        # 使用样式表自定义按钮的外观
        text_color_button.setStyleSheet(
            "QPushButton {"
            "    background-color: rgba(0, 0, 0, 0);"
            "    color: rgb(58, 134, 255);"
            "    border: 2px solid rgb(58, 134, 255);"
            "    border-radius: 8px;"
            "    padding: 3px;"
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

        text_color_button.clicked.connect(self.choose_text_color)

        self.text_color_show = QLabel()
        self.text_color_show.setFixedSize(55, 25)  # 設置預覽顏色的範圍大小
        self.text_color_show.setStyleSheet(
            'border: 2px solid lightgray;'  # 邊框線條顏色
            'border-radius: 5px;'  # 邊框圓角
            f'background-color: {self._text_font_color};'  # 設置背景顏色
        )
        self.color_name = QLabel()
        self.color_name.setText(self._text_font_color_name)  # 設置顏色名稱
        self.color_name.setStyleSheet(f'color: {self._text_font_color_name}; qproperty-alignment: AlignCenter;')
        color_name_font = QFont()
        color_name_font.setPointSize(16)
        color_name_font.setBold(True) # 設置粗體
        self.color_name.setFont(color_name_font)

        # 创建 text_size 水平布局
        text_size_layout = QHBoxLayout()
        # 添加一个占位符来距离左边至少 10px
        text_size_layout.addSpacing(10)
        # 将文本大小标签和下拉框添加到水平布局
        text_size_layout.addWidget(text_size_label)
        # 添加一个60px的空白空間
        text_size_layout.addSpacing(5)
        text_size_layout.addWidget(text_size_combo)
        # 添加一个60px的空白空間
        text_size_layout.addSpacing(10)

        # 创建 text_color 水平布局
        text_color_layout = QHBoxLayout()
        # 添加一个占位符来距离左边至少 10px
        text_color_layout.addSpacing(10)
        # 将文本大小标签和下拉框添加到水平布局
        text_color_layout.addWidget(text_color_label)
        # 添加一个60px的空白空間
        #text_color_layout.addSpacing(40)
        text_color_layout.addWidget(text_color_button)
         # 添加一个60px的空白空間
        text_color_layout.addSpacing(10)

        # 创建 color_show 水平布局
        color_show_layout = QHBoxLayout()
        # 添加一个占位符来距离左边至少 10px
        color_show_layout.addSpacing(12)
        # 将文本大小标签和下拉框添加到水平布局
        color_show_layout.addWidget(self.text_color_show)
        # 添加一个60px的空白空間
        color_show_layout.addSpacing(45)
        color_show_layout.addWidget(self.color_name)
        # 添加一个60px的空白空間
        color_show_layout.addSpacing(10)

        # Create a vertical layout
        layout = QVBoxLayout()

        # Add the horizontal button layout to the vertical layout
        layout.addLayout(text_size_layout)
        layout.addLayout(text_color_layout)
        layout.addSpacing(5)
        layout.addLayout(color_show_layout)

        # 设置水平布局作为文本设置的布局
        text_settings.setLayout(layout)

        return text_settings

    def create_recognition_settings(self):
        # 创建一个用于辨识设置的 QWidget
        recognition_settings = QWidget()

        # Create a vertical layout for the recognition settings
        vbox = QVBoxLayout()

        # Create a horizontal layout for the frequency label and combo
        frequency_layout = QHBoxLayout()

        # Create a horizontal layout for the checkbox and label
        checkbox_layout = QHBoxLayout()

        frequency_label = QLabel("擷取頻率 ")

        # set font size to 14px
        label_font = QFont()
        label_font.setPointSize(14)
        label_font.setBold(True) # 設置粗體
        frequency_label.setFont(label_font)

        # 建立辨識頻率的下拉式選單
        frequency_combo = QComboBox()
        frequency_combo.addItem("高 (1 秒)")
        frequency_combo.addItem("標準 (2 秒)")
        frequency_combo.addItem("慢 (3 秒)")
        frequency_combo.addItem("非常慢 (5 秒)")
        match self._frequency:
            case "高 (1 秒)":
                frequency_combo.setCurrentIndex(0)  

            case "標準 (2 秒)":
                frequency_combo.setCurrentIndex(1)  

            case "慢 (3 秒)":
                frequency_combo.setCurrentIndex(2)  

            case "非常慢 (5 秒)":
                frequency_combo.setCurrentIndex(3)  

        frequency_combo.currentIndexChanged.connect(self.update_recognition_frequency)

        # set auto recapture check box
        auto_recapture_check_box = SlideToggle()
        auto_recapture_check_box.setChecked(self._auto_recapture_state)
        auto_recapture_check_box.stateChanged.connect(self.update_auto_recapture_state)

        check_box_label = QLabel("截圖後自動繼續擷取")
        check_box_label.setFont(label_font)

        # Add the label and combo to the horizontal layout
        frequency_layout.addWidget(frequency_label)
        frequency_layout.addWidget(frequency_combo)

        # Add the label and checkbox to the horizontal layout
        checkbox_layout.addSpacing(3)
        checkbox_layout.addWidget(auto_recapture_check_box)
        checkbox_layout.addSpacing(28)
        checkbox_layout.addWidget(check_box_label)

        # Add the horizontal layout and the check box to the vertical layout
        vbox.addStretch(1)
        vbox.addLayout(frequency_layout)
        vbox.addSpacing(15)
        vbox.addLayout(checkbox_layout)
        vbox.addStretch(1)

        # add all widget
        recognition_settings.setLayout(vbox)

        return recognition_settings

    def create_system_settings(self):
        # 创建一个用于系統设置的 QWidget
        system_settings = QWidget()

        # set button font size to 14px
        button_font = QFont()
        button_font.setPointSize(14)
        button_font.setBold(True) # 設置粗體

        # set label font size to 14px
        label_font = QFont()
        label_font.setPointSize(12)
        label_font.setBold(True) # 設置粗體

        # 创建一个按钮以设置 Google 凭证
        self.set_credentials_button = QPushButton("")
        self.set_credentials_button.setFont(button_font)
        self.set_credentials_button.clicked.connect(self.set_google_credentials)
        # 使用样式表自定义按钮的外观
        self.set_credentials_button.setStyleSheet(
            "QPushButton {"
            "    background-color: rgba(0, 0, 0, 0);"
            "    color: rgb(58, 134, 255);"
            "    border: 3px solid rgb(58, 134, 255);"
            "    border-radius: 8px;"
            "    padding: 3px;"
            "}"
            "QPushButton:hover {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #488EF7, stop: 1 #3478F6);"
            "    border: none; "
            "    color: white;"
            "}"
            "QPushButton:pressed {"
            "    background-color: QLinearGradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #3879E3, stop: 1 #2D66EA);"
            "    border: none;"
            "    color: white;"
            "}"
        )

        # create a label to show google_credential state
        self.google_credential_state = QLabel("")
        self.google_credential_state.setFont(label_font)
        self.google_credential_state.setStyleSheet(
            "QLabel { qproperty-alignment: AlignCenter; } "  # 文字置中
        )

        # 創建如何取得google憑證連結
        new_file_path = os.path.join(self.app_dir_path, "html/sub-google-api.html")
        self.credentials_link = QLabel(f'<a href="file://{new_file_path}">如何取得 Google 憑證？</a>')
        self.credentials_link.setFont(label_font)    
        self.credentials_link.setStyleSheet(
            "QLabel { qproperty-alignment: AlignCenter; } "  # 文字置中
        )
        self.credentials_link.setOpenExternalLinks(True)  # 允許外部連結
        self.credentials_link.linkActivated.connect(self.open_google_credential_settings_link)

        # 将小部件添加到系統设置布局
        layout = QVBoxLayout()
        layout.addSpacing(15)  
        layout.addWidget(self.set_credentials_button)
        layout.addWidget(self.google_credential_state)
        layout.addWidget(self.credentials_link)
        layout.addSpacing(15) 
        system_settings.setLayout(layout)

        return system_settings
    
    def update_google_credential_state_label(self, message):
        # 設置 google 憑證狀態
        self.google_credential_state.setText(message)

        # send signal that make main windows update status
        self.update_google_credential_state.emit()

        # 設置 google 憑證 button 的顯示文字
        successed_message = "憑證有效"
        failed_message = "憑證無效"
        not_set_message = "尚未設置憑證"
        if successed_message in self.google_credential.get_message():
            self.set_credentials_button.setText("更新 Google 憑證")
        if failed_message in self.google_credential.get_message():
            self.set_credentials_button.setText("更新 Google 憑證")
        if not_set_message in self.google_credential.get_message():
            self.set_credentials_button.setText("設定 Google 憑證")

        # close check_google_credential state thread
        self.check_google_credential_thread.quit()
        self.check_google_credential_thread.wait()
    
    def open_google_credential_settings_link(self, url):
        # 使用 QDesktopServices 打開 URL
        QDesktopServices.openUrl(QUrl(url))

    def create_about_page(self):
        # 创建一个用于“关于”页面的 QWidget
        about_page = QWidget()

        # set font size to 14px
        label_font = QFont()
        label_font.setPointSize(14)
        label_font.setBold(True) # 設置粗體

        # 建立版本訊息、作者名稱
        version_label = QLabel(f"版本: ver0.1.0")
        author_label = QLabel("作者: Hsieh Meng-Hao")

        # 創建使用說明連結、Github連結
        manual_file_path = os.path.join(self.app_dir_path, "html/manual.html")
        github_file_path = os.path.join(self.app_dir_path, "html/githublink.html")
        self.manual_link = QLabel(f'<a href="file://{manual_file_path}"><span> &lt; </span>使用說明<span> &gt; </span></a>')
        self.github_link = QLabel(f'<a href="file://{github_file_path}"><span> &lt; </span>GitHub<span> &gt; </span></a>')
        self.manual_link.setFont(label_font)
        self.github_link.setFont(label_font)
        self.manual_link.setOpenExternalLinks(True)  # 允許外部連結
        self.manual_link.linkActivated.connect(self.open_manual_link)
        self.github_link.setOpenExternalLinks(True)  # 允許外部連結
        self.github_link.linkActivated.connect(self.open_github_website_link)

        # 創建一條水平線以隔開 label
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setLineWidth(1.5)  # 設置線條寬度為 2px

        # 将小部件添加到“关于”页面布局
        layout = QVBoxLayout()
        layout.addWidget(version_label)
        layout.addWidget(author_label)
        layout.addWidget(line)
        layout.addWidget(self.manual_link)
        layout.addWidget(self.github_link)
        about_page.setLayout(layout)

        return about_page
    
    def open_manual_link(self, url):
        # 使用 QDesktopServices 打開 URL
        QDesktopServices.openUrl(QUrl(url))

    def open_github_website_link(self, url):
        # 使用 QDesktopServices 打開 URL
        QDesktopServices.openUrl(QUrl(url))

    def update_text_size(self, selected_font_size):
        # 更新文本字體大小
        self._text_font_size = int(selected_font_size)
        
        # 保存用户设置到JSON配置文件
        self.config_handler.set_font_size(self._text_font_size)
        
    def choose_text_color(self):
        # 打开颜色对话框，并根据用户的选择设置文本颜色
        color = QColorDialog.getColor()
        hex_color = ""  # 初始化 hex_color 為空字符串
        if color.isValid():
            name = color.name().upper()
            self.color_name.setText(name)

            # 將選定的顏色轉換為十六進位格式
            hex_color = color.name()

            # 更新 color_name 的字體顏色
            self.color_name.setStyleSheet(f'color: {hex_color};')

            # 更新 text_color_show 的背景顏色
            self.text_color_show.setStyleSheet(
                'border: 2px solid lightgray;'  # 邊框線條顏色
                'border-radius: 5px;'  # 邊框圓角
                f'background-color: {hex_color};' # 更新顏色
            )

            # 保存用户设置到 TOML 配置文件
            self._text_font_color = hex_color.upper()
            self.config_handler.set_font_color(self._text_font_color)

    def update_recognition_frequency(self, selected_frequency):
        # 更新偵測的頻率
        match selected_frequency:
            case 0:
                self._frequency = "高 (1 秒)"

            case 1:
                self._frequency = "標準 (2 秒)"

            case 2:
                self._frequency = "慢 (3 秒)" 

            case 3:
                self._frequency = "非常慢 (5 秒)" 
        
        # 保存用户设置到 TOML 配置文件
        self.config_handler.set_capture_frequency(self._frequency)

    def update_auto_recapture_state(self, value):
        self._auto_recapture_state = value
        self.config_handler.set_auto_recapture_state(value)

    def set_google_credentials(self):
        # 打开一个文件对话框，让用户选择 Google 凭证文件
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("JSON Files (*.json)")
        file_dialog.setViewMode(QFileDialog.ViewMode.List)
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        file_dialog.setWindowTitle("Choose Google's Credential File")
        
        # 设置初始目录（在这里设置为用户主目录）
        initial_directory = QStandardPaths.writableLocation(QStandardPaths.HomeLocation)
        file_dialog.setDirectory(initial_directory)

        # 获取所选文件路径并根据文件路径设置 Google 凭证
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                credentials_file = selected_files[0]  # 获取第一个选择的文件

                # 获取当前脚本所在的目录
                new_file_path = os.path.join(self.app_dir_path, os.path.basename(credentials_file))
                print(new_file_path)
                
                previous_file_path = self.config_handler.get_google_credential_path()
                if os.path.exists(previous_file_path):
                    os.remove(previous_file_path)  # 如果文件已存在，先删除它

                # 將 google 憑證文件複製到 app 資料夾底下
                try:
                    shutil.copy(credentials_file, new_file_path)
                    # 保存用户设置到 TOML 配置文件
                    self.config_handler.set_google_credential_path(new_file_path)
                except Exception as e:
                    pass

                # 檢查 google 憑證是否能正常使用
                google_key_file_path = self.config_handler.get_google_credential_path()
                self.google_credential.check_google_credential(google_key_file_path)

                # create a messagebox to show the google credential state
                msg_box = QMessageBox()
                msg_box.setWindowTitle("Information")
                if self.google_credential.get_google_vision() and self.google_credential.get_google_translation():
                    new_file_path = os.path.join(self.app_dir_path , "img/messagebox/info.png")
                    customIcon = QPixmap(new_file_path)  # 加载图标
                    msg_box.setIconPixmap(customIcon)
                    msg_box.setText("已成功設置 Google 憑證！")
                    msg_box.exec()
                    
                    # 更新設置 google 憑證 button 的文字
                    self.set_credentials_button.setText("更新 Google 憑證")

                    # 更新 google 憑證狀態的文字
                    message = self.google_credential.get_message()
                    self.google_credential_state.setText(message)
                else:
                    new_file_path = os.path.join(self.app_dir_path , "img/messagebox/warning.png")
                    customIcon = QPixmap(new_file_path)  # 加载图标
                    msg_box.setIconPixmap(customIcon)
                    msg_box.setText("設置 Google 憑證失敗！\n可能是該 Google 憑證無法使用 或 無法將該 Google 憑證檔案複製至應用程式資料夾底下作為使用！")
                    msg_box.exec()

                    # 更新 google 憑證狀態的文字
                    message = self.google_credential.get_message()
                    self.google_credential_state.setText(message)

                    not_set_message = "尚未設置憑證"
                    if not_set_message in message:
                        self.set_credentials_button.setText("設定 Google 憑證")
                    else:
                        self.set_credentials_button.setText("更新 Google 憑證")


    def closeEvent(self, event):
        self.setting_window_closed.emit()
        event.accept()


