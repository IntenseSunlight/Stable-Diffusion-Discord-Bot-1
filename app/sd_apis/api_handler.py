from .abstract_api import AbstractAPI
from .a1111_api import A1111API
from .comfyUI_api import ComfyUIAPI
from typing import Optional

__all__ = ["Sd"]


class _Sd:
    def __init__(self, webui_url: Optional[str] = None, api_type: Optional[str] = None):
        if webui_url is not None:
            self.webui_url = webui_url

        if api_type is not None:
            self.api_type = api_type

        if webui_url and api_type:
            self.configure(webui_url, api_type)

    def api_configure(self, webui_url: str, api_type: str):
        self.webui_url = webui_url
        self.api_type = api_type

        if self.api_type == "a1111":
            self.api: AbstractAPI = A1111API(webui_url)
        elif self.api_type == "comfyUI":
            self.api: AbstractAPI = ComfyUIAPI(webui_url)
        else:
            raise ValueError(f"Invalid SD_API: {api_type}")

    def get_api_list(self):
        return ["a1111", "comfyUI"]


Sd = _Sd()
