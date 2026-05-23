import os
import sys
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from parsel import Selector

from constants import ZHIHU_URL, ZHIHU_ZHUANLAN_URL, ANSWER_NAME, ARTICLE_NAME, VIDEO_NAME
from models import ZhihuContent, ZhihuComment, ZhihuCreator


def extract_text_from_html(html_content: str) -> str:
    if not html_content:
        return ""
    selector = Selector(text=html_content)
    text = selector.xpath('string(.)').get(default='').strip()
    return text


class ZhihuExtractor:

    def extract_contents_from_search(self, json_data: Dict) -> List[ZhihuContent]:
        if not json_data:
            return []
        search_result = json_data.get("data", [])
        search_result = [s_item for s_item in search_result if s_item.get("type") in ['search_result', 'zvideo']]
        return self._extract_content_list([sr_item.get("object") for sr_item in search_result if sr_item.get("object")])

    def _extract_content_list(self, content_list: List[Dict]) -> List[ZhihuContent]:
        if not content_list:
            return []
        res = []
        for content in content_list:
            if content.get("type") == ANSWER_NAME:
                res.append(self._extract_answer_content(content))
            elif content.get("type") == ARTICLE_NAME:
                res.append(self._extract_article_content(content))
            elif content.get("type") == VIDEO_NAME:
                res.append(self._extract_zvideo_content(content))
        return res

    def _extract_answer_content(self, answer: Dict) -> ZhihuContent:
        res = ZhihuContent()
        res.content_id = str(answer.get("id", ""))
        res.content_type = answer.get("type", "")
        res.content_text = extract_text_from_html(answer.get("content", ""))
        question = answer.get("question") or {}
        res.question_id = str(question.get("id", ""))
        res.content_url = f"{ZHIHU_URL}/question/{res.question_id}/answer/{res.content_id}"
        res.title = extract_text_from_html(answer.get("title", ""))
        res.desc = extract_text_from_html(answer.get("description", "") or answer.get("excerpt", ""))
        res.created_time = answer.get("created_time", 0)
        res.updated_time = answer.get("updated_time", 0)
        res.voteup_count = answer.get("voteup_count", 0)
        res.comment_count = answer.get("comment_count", 0)
        author = self._extract_author(answer.get("author"))
        res.user_id = author.user_id
        res.user_link = author.user_link
        res.user_nickname = author.user_nickname
        res.user_url_token = author.url_token
        return res

    def _extract_article_content(self, article: Dict) -> ZhihuContent:
        res = ZhihuContent()
        res.content_id = str(article.get("id", ""))
        res.content_type = article.get("type", "")
        res.content_text = extract_text_from_html(article.get("content", ""))
        res.content_url = f"{ZHIHU_ZHUANLAN_URL}/p/{res.content_id}"
        res.title = extract_text_from_html(article.get("title", ""))
        res.desc = extract_text_from_html(article.get("excerpt", ""))
        res.created_time = article.get("created_time", 0) or article.get("created", 0)
        res.updated_time = article.get("updated_time", 0) or article.get("updated", 0)
        res.voteup_count = article.get("voteup_count", 0)
        res.comment_count = article.get("comment_count", 0)
        author = self._extract_author(article.get("author"))
        res.user_id = author.user_id
        res.user_link = author.user_link
        res.user_nickname = author.user_nickname
        res.user_url_token = author.url_token
        return res

    def _extract_zvideo_content(self, zvideo: Dict) -> ZhihuContent:
        res = ZhihuContent()
        res.content_id = str(zvideo.get("id", ""))
        res.content_type = zvideo.get("type", "")
        res.title = extract_text_from_html(zvideo.get("title", ""))
        res.desc = extract_text_from_html(zvideo.get("description", ""))
        if "video" in zvideo and isinstance(zvideo.get("video"), dict):
            res.content_url = f"{ZHIHU_URL}/zvideo/{res.content_id}"
            res.created_time = zvideo.get("published_at", 0) or 0
            res.updated_time = zvideo.get("updated_at", 0) or 0
        else:
            res.content_url = zvideo.get("video_url", "")
            res.created_time = zvideo.get("created_at", 0) or 0
        res.voteup_count = zvideo.get("voteup_count", 0) or 0
        res.comment_count = zvideo.get("comment_count", 0) or 0
        author = self._extract_author(zvideo.get("author"))
        res.user_id = author.user_id
        res.user_link = author.user_link
        res.user_nickname = author.user_nickname
        res.user_url_token = author.url_token
        return res

    @staticmethod
    def _extract_author(author: Dict) -> ZhihuCreator:
        res = ZhihuCreator()
        if not author:
            return res
        if not author.get("id"):
            author = author.get("member") or {}
        res.user_id = str(author.get("id", ""))
        res.user_link = f"{ZHIHU_URL}/people/{author.get('url_token', '')}"
        res.user_nickname = author.get("name", "")
        res.user_avatar = author.get("avatar_url", "")
        res.url_token = author.get("url_token", "")
        return res

    def extract_comments(self, page_content: ZhihuContent, comments: List[Dict]) -> List[ZhihuComment]:
        if not comments:
            return []
        res = []
        for comment in comments:
            if comment.get("type") != "comment":
                continue
            res.append(self._extract_comment(page_content, comment))
        return res

    def _extract_comment(self, page_content: ZhihuContent, comment: Dict) -> ZhihuComment:
        res = ZhihuComment()
        res.comment_id = str(comment.get("id", ""))
        res.parent_comment_id = str(comment.get("reply_comment_id", ""))
        res.content = extract_text_from_html(comment.get("content", ""))
        res.publish_time = comment.get("created_time", 0)
        res.ip_location = self._extract_ip_location(comment.get("comment_tag", []))
        res.sub_comment_count = comment.get("child_comment_count", 0)
        res.like_count = comment.get("like_count", 0) or 0
        res.dislike_count = comment.get("dislike_count", 0) or 0
        res.content_id = page_content.content_id
        res.content_type = page_content.content_type
        author = self._extract_author(comment.get("author"))
        res.user_id = author.user_id
        res.user_link = author.user_link
        res.user_nickname = author.user_nickname
        return res

    @staticmethod
    def _extract_ip_location(comment_tags: List[Dict]) -> str:
        if not comment_tags:
            return ""
        for ct in comment_tags:
            if ct.get("type") == "ip_info":
                return ct.get("text", "")
        return ""

    @staticmethod
    def extract_offset(paging_info: Dict) -> str:
        next_url = paging_info.get("next")
        if not next_url:
            return ""
        parsed_url = urlparse(next_url)
        query_params = parse_qs(parsed_url.query)
        offset = query_params.get('offset', [""])[0]
        return offset

    @staticmethod
    def judge_zhihu_url(url: str) -> str:
        if "/answer/" in url:
            return ANSWER_NAME
        elif "/p/" in url:
            return ARTICLE_NAME
        elif "/zvideo/" in url:
            return VIDEO_NAME
        return ""
