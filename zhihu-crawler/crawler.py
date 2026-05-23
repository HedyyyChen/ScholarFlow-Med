import asyncio
import os
import sys
from typing import List, Optional
from urllib.parse import urlparse

from playwright.async_api import (
    BrowserContext,
    async_playwright,
)

from constants import ZHIHU_URL, ANSWER_NAME, ARTICLE_NAME, VIDEO_NAME
from models import ZhihuContent
from client import ZhiHuClient
from extractor import ZhihuExtractor
from login import ZhiHuLogin


class ZhihuCrawler:

    def __init__(self):
        self.index_url = ZHIHU_URL
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        self._extractor = ZhihuExtractor()
        self.browser_context: Optional[BrowserContext] = None
        self.zhihu_client: Optional[ZhiHuClient] = None
        self.context_page = None
        self._playwright_stack = None

    async def start(self):
        self._playwright_stack = async_playwright()
        playwright = await self._playwright_stack.start()
        chromium = playwright.chromium

        user_data_dir = os.path.join(os.getcwd(), "browser_data", "zhihu_user_data_dir")
        self.browser_context = await chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            accept_downloads=True,
            headless=False,
            viewport={"width": 1920, "height": 1080},
            user_agent=self.user_agent,
        )

        self.context_page = await self.browser_context.new_page()
        await self.context_page.goto(self.index_url, wait_until="domcontentloaded")

        self.zhihu_client = await self._create_client()

        if not await self.zhihu_client.pong():
            login_obj = ZhiHuLogin(
                browser_context=self.browser_context,
                context_page=self.context_page,
            )
            success = await login_obj.login_by_qrcode()
            if not success:
                await self.close()
                return False
            await self.zhihu_client.update_cookies(self.browser_context)

        await self.context_page.goto(
            f"{self.index_url}/search?q=test&search_source=Guess&utm_content=search_hot&type=content"
        )
        await asyncio.sleep(5)
        await self.zhihu_client.update_cookies(self.browser_context)
        return True

    async def _create_client(self) -> ZhiHuClient:
        cookies = await self.browser_context.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        cookie_dict = {c['name']: c['value'] for c in cookies}
        return ZhiHuClient(
            headers={
                "accept": "*/*",
                "accept-language": "zh-CN,zh;q=0.9",
                "cookie": cookie_str,
                "priority": "u=1, i",
                "referer": f"{ZHIHU_URL}/search?q=python&type=content",
                "user-agent": self.user_agent,
                "x-api-version": "3.0.91",
                "x-app-za": "OS=Web",
                "x-requested-with": "fetch",
                "x-zse-93": "101_3_3.0",
            },
            cookie_dict=cookie_dict,
        )

    async def search(self, keyword: str, max_notes: int = 20, sleep_sec: float = 2.0) -> List[ZhihuContent]:
        all_contents: List[ZhihuContent] = []
        page = 1

        while len(all_contents) < max_notes:
            try:
                content_list = await self.zhihu_client.get_note_by_keyword(keyword=keyword, page=page)
                if not content_list:
                    break
                for content in content_list:
                    content.source_keyword = keyword
                    all_contents.append(content)
                    if len(all_contents) >= max_notes:
                        break
                page += 1
                await asyncio.sleep(sleep_sec)
            except Exception as e:
                raise Exception(f"第 {page} 页出错: {e}")

        return all_contents

    async def get_comments_for_contents(self, contents: List[ZhihuContent], sleep_sec: float = 2.0):
        all_comments = []
        for i, content in enumerate(contents):
            try:
                comments = await self.zhihu_client.get_note_all_comments(
                    content=content,
                    crawl_interval=sleep_sec,
                )
                all_comments.extend(comments)
            except Exception as e:
                pass
        return all_comments

    async def get_detail(self, url: str, sleep_sec: float = 2.0) -> Optional[ZhihuContent]:
        note_type = self._extractor.judge_zhihu_url(url)
        try:
            if note_type == ANSWER_NAME:
                parsed = urlparse(url)
                path_parts = parsed.path.strip('/').split('/')
                question_id = path_parts[1]
                answer_id = path_parts[3]
                result = await self.zhihu_client.get_answer_info(question_id, answer_id)
            elif note_type == ARTICLE_NAME:
                article_id = url.split("/")[-1]
                result = await self.zhihu_client.get_article_info(article_id)
            elif note_type == VIDEO_NAME:
                video_id = url.split("/")[-1]
                result = await self.zhihu_client.get_video_info(video_id)
            else:
                return None
            return result
        except Exception as e:
            raise Exception(f"获取详情失败: {e}")

    async def close(self):
        if self.browser_context:
            await self.browser_context.close()
        if self._playwright_stack:
            await self._playwright_stack.__aexit__(None, None, None)
