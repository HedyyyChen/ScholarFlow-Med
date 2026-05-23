import asyncio
import json
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urlencode

import httpx
from playwright.async_api import BrowserContext, Page

from constants import ZHIHU_URL, ZHIHU_ZHUANLAN_URL
from models import ZhihuComment, ZhihuContent
from extractor import ZhihuExtractor
from zhihu_sign import sign


class ZhiHuClient:

    def __init__(
        self,
        timeout=10,
        proxy=None,
        *,
        headers: Dict[str, str],
        cookie_dict: Dict[str, str],
    ):
        self.proxy = proxy
        self.timeout = timeout
        self.default_headers = headers
        self.cookie_dict = cookie_dict
        self._extractor = ZhihuExtractor()

    async def _pre_headers(self, url: str) -> Dict:
        d_c0 = self.cookie_dict.get("d_c0")
        if not d_c0:
            raise Exception("d_c0 not found in cookies")
        sign_res = sign(url, self.default_headers["cookie"])
        headers = self.default_headers.copy()
        headers['x-zst-81'] = sign_res["x-zst-81"]
        headers['x-zse-96'] = sign_res["x-zse-96"]
        return headers

    async def request(self, method, url, **kwargs) -> Union[str, Any]:
        return_response = kwargs.pop('return_response', False)
        async with httpx.AsyncClient(proxy=self.proxy) as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)
        if response.status_code == 404:
            return {}
        if response.status_code != 200:
            raise Exception(f"Request error: {response.status_code} {response.text}")
        if return_response:
            return response.text
        try:
            data = response.json()
            if data.get("error"):
                raise Exception(data.get("error", {}).get("message", "API error"))
            return data
        except json.JSONDecodeError:
            raise Exception(f"JSON decode error: {response.text}")

    async def get(self, uri: str, params=None, **kwargs) -> Union[Dict, str]:
        final_uri = uri
        if isinstance(params, dict):
            final_uri += '?' + urlencode(params)
        headers = await self._pre_headers(final_uri)
        base_url = ZHIHU_ZHUANLAN_URL if "/p/" in uri else ZHIHU_URL
        return await self.request(method="GET", url=base_url + final_uri, headers=headers, **kwargs)

    async def pong(self) -> bool:
        try:
            res = await self.get("/api/v4/me", {"include": "email"})
            if res.get("uid") and res.get("name"):
                return True
        except Exception:
            pass
        return False

    async def update_cookies(self, browser_context: BrowserContext):
        cookies = await browser_context.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        cookie_dict = {c['name']: c['value'] for c in cookies}
        self.default_headers["cookie"] = cookie_str
        self.cookie_dict = cookie_dict

    async def get_note_by_keyword(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
    ) -> List[ZhihuContent]:
        uri = "/api/v4/search_v3"
        params = {
            "t": "general",
            "q": keyword,
            "correction": 1,
            "offset": (page - 1) * page_size,
            "limit": page_size,
            "show_all_topics": 0,
            "search_source": "Filter",
        }
        search_res = await self.get(uri, params)
        return self._extractor.extract_contents_from_search(search_res)

    async def get_root_comments(
        self,
        content_id: str,
        content_type: str,
        offset: str = "",
        limit: int = 10,
        order_by: str = "score",
    ) -> Dict:
        uri = f"/api/v4/comment_v5/{content_type}s/{content_id}/root_comment"
        params = {"order": order_by, "offset": offset, "limit": limit}
        return await self.get(uri, params)

    async def get_note_all_comments(
        self,
        content: ZhihuContent,
        crawl_interval: float = 2.0,
        callback: Optional[Callable] = None,
    ) -> List[ZhihuComment]:
        result: List[ZhihuComment] = []
        is_end = False
        offset = ""
        limit = 10
        while not is_end:
            try:
                root_comment_res = await self.get_root_comments(
                    content.content_id, content.content_type, offset, limit
                )
            except Exception:
                break
            if not root_comment_res:
                break
            paging_info = root_comment_res.get("paging", {})
            is_end = paging_info.get("is_end", True)
            offset = self._extractor.extract_offset(paging_info)
            comments = self._extractor.extract_comments(content, root_comment_res.get("data", []))
            if not comments:
                break
            if callback:
                await callback(comments)
            result.extend(comments)
            await asyncio.sleep(crawl_interval)
        return result

    async def get_answer_info(self, question_id: str, answer_id: str) -> Optional[ZhihuContent]:
        uri = f"/api/v4/questions/{question_id}/answers/{answer_id}"
        params = {"include": "data[*].content,excerpt"}
        try:
            data = await self.get(uri, params)
            if not data:
                return None
            contents = self._extractor._extract_content_list([data])
            return contents[0] if contents else None
        except Exception:
            return None

    async def get_article_info(self, article_id: str) -> Optional[ZhihuContent]:
        uri = f"/api/v4/articles/{article_id}"
        try:
            data = await self.get(uri)
            if not data:
                return None
            contents = self._extractor._extract_content_list([data])
            return contents[0] if contents else None
        except Exception:
            return None

    async def get_video_info(self, video_id: str) -> Optional[ZhihuContent]:
        uri = f"/api/v4/zvideos/{video_id}"
        try:
            data = await self.get(uri)
            if not data:
                return None
            contents = self._extractor._extract_content_list([data])
            return contents[0] if contents else None
        except Exception:
            return None
