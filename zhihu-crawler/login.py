import asyncio
import base64
import tempfile
import os
from typing import Optional

from playwright.async_api import BrowserContext, Page

_log_func = None

def set_log_func(func):
    global _log_func
    _log_func = func

def log(msg):
    if _log_func:
        _log_func(msg)
    else:
        print(msg)


class ZhiHuLogin:

    def __init__(
        self,
        browser_context: BrowserContext,
        context_page: Page,
    ):
        self.browser_context = browser_context
        self.context_page = context_page

    async def check_login_state(self) -> bool:
        current_cookie = await self.browser_context.cookies()
        cookie_dict = {c['name']: c['value'] for c in current_cookie}
        if cookie_dict.get("z_c0"):
            return True
        return False

    async def login_by_qrcode(self):
        log("[登录] 正在打开知乎登录页面...")
        try:
            await self.context_page.goto(
                "https://www.zhihu.com/signin",
                wait_until="networkidle",
                timeout=30000
            )
        except Exception as e:
            log(f"[登录] 页面加载超时，尝试继续: {e}")

        await asyncio.sleep(3)

        qrcode_img_selector = "canvas.Qrcode-qrcode"
        qrcode_found = False
        for i in range(30):
            base64_qrcode_img = await self._find_qrcode_img_from_canvas(
                self.context_page,
                canvas_selector=qrcode_img_selector
            )
            if base64_qrcode_img:
                qrcode_found = True
                self._show_qrcode(base64_qrcode_img)
                break
            login_canvas = await self.context_page.query_selector(".Login-qrcode")
            if not login_canvas:
                await asyncio.sleep(1)
                continue
            await asyncio.sleep(1)
            log(f"[登录] 等待二维码加载... ({i+1}/30)")

        if not qrcode_found:
            log("[登录] 未能检测到二维码，请直接在弹出的浏览器窗口中手动扫码登录")
            log("[登录] 等待登录状态...")

        log("[登录] 请使用手机知乎 APP 扫码登录...")
        log("[登录] 等待中...（最多等待5分钟）")

        for i in range(300):
            if await self.check_login_state():
                log("[登录] 登录成功！")
                return True
            if i % 30 == 0 and i > 0:
                log(f"[登录] 已等待 {i} 秒，继续等待...")
            await asyncio.sleep(1)

        log("[登录] 登录超时（5分钟），请重试")
        return False

    @staticmethod
    async def _find_qrcode_img_from_canvas(page: Page, canvas_selector: str) -> str:
        try:
            canvas_element = await page.query_selector(canvas_selector)
            if not canvas_element:
                return ""
            base64_image = await canvas_element.evaluate("""
                (canvas) => {
                    return canvas.toDataURL('image/png');
                }
            """)
            return base64_image
        except Exception:
            return ""

    @staticmethod
    def _show_qrcode(qrcode_base64: str):
        try:
            header, encoded = qrcode_base64.split(",", 1)
            data = base64.b64decode(encoded)
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False, dir='.') as f:
                f.write(data)
                temp_path = f.name

            try:
                from PIL import Image
                img = Image.open(temp_path)
                img.show()
                log("[登录] 二维码已打开（图片查看器），请扫码")
            except ImportError:
                log(f"[登录] 二维码已保存到: {os.path.abspath(temp_path)}")
                log(f"[登录] 请打开该文件查看二维码并扫码")
            except Exception:
                log(f"[登录] 二维码已保存到: {os.path.abspath(temp_path)}")
                log(f"[登录] 请打开该文件查看二维码并扫码")
        except Exception as e:
            log(f"[登录] 二维码显示失败: {e}")
