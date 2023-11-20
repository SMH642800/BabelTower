import os
from google.cloud import vision_v1 as vision
from google.cloud import translate_v2 as translate
from google.oauth2 import service_account

class GoogleCloudClient:
    def __init__(self):
        self._client_vision = None
        self._client_translate = None
        self._credentials = None
        self._messsage = None

    def _set_google_vision(self):
        # 初始化 Google Cloud Vision API 客户端
        self._client_vision = vision.ImageAnnotatorClient()

    def _set_google_translation(self):
        # 初始化 Google Cloud Translation API 客户端
        self._client_translate = translate.Client()

    def _set_google_credentials(self, credentials):
        self._credentials = credentials

    def _set_message(self, message):
        self._messsage = message

    def get_google_vision(self):
        return self._client_vision
    
    def get_google_translation(self):
        return self._client_translate
    
    def get_google_credentials(self):
        return self._credentials
    
    def get_message(self):
        return self._messsage

    def check_google_credential(self, google_key_file_path):
        if os.path.exists(google_key_file_path):
            try:
                credentials = service_account.Credentials.from_service_account_file(google_key_file_path)

                # Create a client for Google Translation
                client_translate = translate.Client(credentials=credentials)
                translation = client_translate.translate('Hello', target_language='es')

                # 設置 GCP credentials
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_key_file_path

                # 初始化 google.vision 和 google.translation 和 google_credentials
                self._set_google_vision()
                self._set_google_translation()
                self._set_google_credentials(credentials)

                # set message info
                self._set_message("Google 憑證： <font color='green'>憑證有效</font> ")
            except Exception as e:
                self._client_vision = None
                self._client_translate = None
                self._credentials = None
                self._set_message("Google 憑證： <font color='red'>憑證無效</font> ")
        else:
            self._client_vision = None
            self._client_translate = None
            self._credentials = None
            self._set_message("Google 憑證： <font color='red'>尚未設置憑證</font> ")
