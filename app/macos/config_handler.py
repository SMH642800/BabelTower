# -*- coding: utf-8 -*-

import os
import sys
import toml


class ConfigHandler():
    DEFAULT_FONT_SIZE = 14
    DEFAULT_FONT_COLOR = "#FFFFFF"
    DEFAULT_CAPTURE_FREQUENCY = "標準 (2 秒)"
    DEFAULT_AUTO_RECAPTURE_STATE = 0
    DEFAULT_GOOGLE_CREDENTIAL_PATH = ""
    

    def __init__(self):
        if getattr(sys, 'frozen', False):
            # 应用程序被打包
            app_dir = sys._MEIPASS
            self.config_file_path = os.path.join(app_dir, "config.toml")
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            app_dir = os.path.dirname(os.path.dirname(current_dir))
            self.config_file_path = os.path.join(app_dir, "config.toml")

        self.config = self.read_config_file()


    def read_config_file(self):
        # 檢查是否有 config file
        if not os.path.exists(self.config_file_path):
            self._create_config_file()

        # 載入 config
        with open(self.config_file_path, "r") as config_file:
            config = toml.load(config_file)
        
        return config

    def _create_config_file(self):
        # 如果文件不存在，创建默认配置
        default_config = {
            "Settings": {
                "text_font_size": self.DEFAULT_FONT_SIZE,
                "text_font_color": self.DEFAULT_FONT_COLOR,
                "capture_frequency": self.DEFAULT_CAPTURE_FREQUENCY,
                "auto_recapture_state": self.DEFAULT_AUTO_RECAPTURE_STATE,
                "google_cloud_key_file_path": self.DEFAULT_GOOGLE_CREDENTIAL_PATH,
            },
        }
        with open(self.config_file_path, "w") as config_file:
            toml.dump(default_config, config_file)

    def set_font_size(self, new_font_size):
        self.config["Settings"]["text_font_size"] = new_font_size
        with open(self.config_file_path, 'w') as f:
            toml.dump(self.config, f)
    
    def set_font_color(self, new_font_color):
        self.config["Settings"]["text_font_color"] = new_font_color
        with open(self.config_file_path, 'w') as f:
            toml.dump(self.config, f)
    
    def set_capture_frequency(self, new_capture_frequency):
        self.config["Settings"]["capture_frequency"] = new_capture_frequency
        with open(self.config_file_path, 'w') as f:
            toml.dump(self.config, f)
            
    def set_auto_recapture_state(self, new_state):
        self.config["Settings"]["auto_recapture_state"] = new_state
        with open(self.config_file_path, 'w') as f:
            toml.dump(self.config, f)
    
    def set_google_credential_path(self, new_google_credential_path):
        self.config["Settings"]["google_cloud_key_file_path"] = new_google_credential_path
        with open(self.config_file_path, 'w') as f:
            toml.dump(self.config, f)

    def get_font_size(self):
        return self.config.get('Settings', {}).get('text_font_size', self.DEFAULT_FONT_SIZE)
    
    def get_font_color(self):
        return self.config.get('Settings', {}).get('text_font_color', self.DEFAULT_FONT_COLOR)
    
    def get_capture_frequency(self):
        return self.config.get('Settings', {}).get('capture_frequency', self.DEFAULT_CAPTURE_FREQUENCY)
    
    def get_auto_recapture_state(self):
        return self.config.get('Settings', {}).get('auto_recapture_state', self.DEFAULT_AUTO_RECAPTURE_STATE)
    
    def get_google_credential_path(self):
        return self.config.get('Settings', {}).get('google_cloud_key_file_path', self.DEFAULT_GOOGLE_CREDENTIAL_PATH)

