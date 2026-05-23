import sys
import os
from typing import Dict
from urllib.parse import parse_qs, urlparse

import execjs

from constants import ZHIHU_URL

ZHIHU_SIGN_JS = None


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)


def sign(url: str, cookies: str) -> Dict:
    global ZHIHU_SIGN_JS
    if not ZHIHU_SIGN_JS:
        js_path = resource_path(os.path.join('libs', 'zhihu.js'))
        with open(js_path, mode='r', encoding='utf-8-sig') as f:
            ZHIHU_SIGN_JS = execjs.compile(f.read())
    return ZHIHU_SIGN_JS.call("get_sign", url, cookies)
