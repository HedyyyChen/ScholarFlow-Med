import asyncio
import csv
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
from typing import List

from models import ZhihuContent, ZhihuComment
from crawler import ZhihuCrawler
from login import set_log_func as _set_login_log

_log_callback = None

def log(msg):
    if _log_callback:
        _log_callback(msg)
    else:
        print(msg)

def set_log_callback(callback):
    global _log_callback
    _log_callback = callback

def save_contents_to_csv(contents: List[ZhihuContent], output_dir: str):
    filepath = os.path.join(output_dir, "contents.csv")
    fieldnames = [
        "content_id", "content_type", "title", "content_text", "content_url",
        "question_id", "desc", "voteup_count", "comment_count",
        "created_time", "updated_time",
        "user_id", "user_nickname", "user_link", "source_keyword",
    ]
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in contents:
            writer.writerow({
                "content_id": c.content_id,
                "content_type": c.content_type,
                "title": c.title,
                "content_text": c.content_text,
                "content_url": c.content_url,
                "question_id": c.question_id,
                "desc": c.desc,
                "voteup_count": c.voteup_count,
                "comment_count": c.comment_count,
                "created_time": c.created_time,
                "updated_time": c.updated_time,
                "user_id": c.user_id,
                "user_nickname": c.user_nickname,
                "user_link": c.user_link,
                "source_keyword": c.source_keyword,
            })
    return filepath


def save_comments_to_csv(comments: List[ZhihuComment], output_dir: str):
    filepath = os.path.join(output_dir, "comments.csv")
    fieldnames = [
        "comment_id", "content_id", "content", "publish_time", "ip_location",
        "like_count", "dislike_count", "user_id", "user_nickname", "user_link",
    ]
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in comments:
            writer.writerow({
                "comment_id": c.comment_id,
                "content_id": c.content_id,
                "content": c.content,
                "publish_time": c.publish_time,
                "ip_location": c.ip_location,
                "like_count": c.like_count,
                "dislike_count": c.dislike_count,
                "user_id": c.user_id,
                "user_nickname": c.user_nickname,
                "user_link": c.user_link,
            })
    return filepath


class ZhihuCrawlerGUI:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("知乎数据爬虫工具 v1.0")
        self.root.geometry("620x560")
        self.root.resizable(False, False)
        self.crawler = None
        self.output_dir = ""
        self._build_ui()
        set_log_callback(self._log)
        _set_login_log(self._log)

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="知乎数据爬虫工具", font=("", 16, "bold")).pack(pady=(0, 10))

        mode_frame = ttk.LabelFrame(main_frame, text="爬取模式", padding=8)
        mode_frame.pack(fill=tk.X, pady=5)
        self.mode_var = tk.StringVar(value="search")
        ttk.Radiobutton(mode_frame, text="关键词搜索", variable=self.mode_var, value="search",
                        command=self._on_mode_change).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="详情页爬取", variable=self.mode_var, value="detail",
                        command=self._on_mode_change).pack(side=tk.LEFT, padx=10)

        keyword_frame = ttk.LabelFrame(main_frame, text="搜索关键词", padding=8)
        keyword_frame.pack(fill=tk.X, pady=5)
        self.keyword_var = tk.StringVar()
        self.keyword_entry = ttk.Entry(keyword_frame, textvariable=self.keyword_var, font=("", 11))
        self.keyword_entry.pack(fill=tk.X)

        url_frame = ttk.LabelFrame(main_frame, text="知乎链接（详情页模式）", padding=8)
        url_frame.pack(fill=tk.X, pady=5)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, font=("", 11))
        self.url_entry.pack(fill=tk.X)

        settings_frame = ttk.LabelFrame(main_frame, text="爬取设置", padding=8)
        settings_frame.pack(fill=tk.X, pady=5)
        row1 = ttk.Frame(settings_frame)
        row1.pack(fill=tk.X)
        ttk.Label(row1, text="爬取数量:").pack(side=tk.LEFT)
        self.max_notes_var = tk.StringVar(value="10")
        ttk.Entry(row1, textvariable=self.max_notes_var, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Label(row1, text="条").pack(side=tk.LEFT)
        ttk.Label(row1, text="  请求间隔:").pack(side=tk.LEFT)
        self.sleep_var = tk.StringVar(value="2")
        ttk.Entry(row1, textvariable=self.sleep_var, width=5).pack(side=tk.LEFT, padx=5)
        ttk.Label(row1, text="秒").pack(side=tk.LEFT)

        self.start_btn = ttk.Button(main_frame, text="🚀 开始爬取", command=self._on_start)
        self.start_btn.pack(fill=tk.X, pady=8)

        status_frame = ttk.LabelFrame(main_frame, text="状态日志", padding=5)
        status_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = scrolledtext.ScrolledText(status_frame, height=10, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self._on_mode_change()

    def _on_mode_change(self):
        mode = self.mode_var.get()
        if mode == "search":
            self.keyword_entry.config(state="normal")
            self.url_entry.config(state="disabled")
        else:
            self.keyword_entry.config(state="disabled")
            self.url_entry.config(state="normal")

    def _log(self, msg):
        def _append():
            self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
            self.log_text.see(tk.END)
        self.root.after(0, _append)

    def _on_start(self):
        mode = self.mode_var.get()
        if mode == "search" and not self.keyword_var.get().strip():
            messagebox.showwarning("提示", "请输入搜索关键词")
            return
        if mode == "detail" and not self.url_var.get().strip():
            messagebox.showwarning("提示", "请输入知乎链接")
            return

        try:
            max_notes = int(self.max_notes_var.get())
            sleep_sec = float(self.sleep_var.get())
        except ValueError:
            messagebox.showwarning("提示", "请填写正确的数字")
            return

        self.start_btn.config(state="disabled")
        self.log_text.delete(1.0, tk.END)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = os.path.join(os.getcwd(), "output", timestamp)
        os.makedirs(self.output_dir, exist_ok=True)

        if mode == "search":
            thread = threading.Thread(target=self._run_search, args=(
                self.keyword_var.get().strip(), max_notes, sleep_sec
            ), daemon=True)
        else:
            thread = threading.Thread(target=self._run_detail, args=(
                self.url_var.get().strip(), sleep_sec
            ), daemon=True)
        thread.start()
        self._poll_thread(thread)

    def _run_search(self, keyword, max_notes, sleep_sec):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._do_search(keyword, max_notes, sleep_sec))
        except Exception as e:
            log(f"[错误] {e}")
        finally:
            self._finish()

    def _run_detail(self, url, sleep_sec):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._do_detail(url, sleep_sec))
        except Exception as e:
            log(f"[错误] {e}")
        finally:
            self._finish()

    async def _do_search(self, keyword, max_notes, sleep_sec):
        self.crawler = ZhihuCrawler()
        log("[步骤1] 正在启动浏览器...")
        success = await self.crawler.start()
        if not success or not self.crawler.zhihu_client:
            log("[错误] 浏览器启动或登录失败")
            return

        log(f"[步骤2] 开始搜索关键词: {keyword}")
        contents = await self.crawler.search(keyword, max_notes=max_notes, sleep_sec=sleep_sec)
        log(f"[步骤2] 搜索完成，获取 {len(contents)} 条内容")

        if contents:
            filepath = save_contents_to_csv(contents, self.output_dir)
            log(f"[保存] 内容已保存: {filepath}")

        log(f"[步骤3] 开始获取评论...")
        comments = await self.crawler.get_comments_for_contents(contents, sleep_sec=sleep_sec)
        log(f"[步骤3] 评论获取完成，共 {len(comments)} 条")

        if comments:
            filepath = save_comments_to_csv(comments, self.output_dir)
            log(f"[保存] 评论已保存: {filepath}")

        log(f"[完成] 共爬取 {len(contents)} 条内容，{len(comments)} 条评论")
        log(f"[完成] 输出目录: {self.output_dir}")
        await self.crawler.close()

    async def _do_detail(self, url, sleep_sec):
        self.crawler = ZhihuCrawler()
        log("[步骤1] 正在启动浏览器...")
        success = await self.crawler.start()
        if not success or not self.crawler.zhihu_client:
            log("[错误] 浏览器启动或登录失败")
            return

        log(f"[步骤2] 开始获取详情: {url}")
        content = await self.crawler.get_detail(url, sleep_sec=sleep_sec)
        if content:
            filepath = save_contents_to_csv([content], self.output_dir)
            log(f"[保存] 内容已保存: {filepath}")

            log(f"[步骤3] 开始获取评论...")
            comments = await self.crawler.get_comments_for_contents([content], sleep_sec=sleep_sec)
            log(f"[步骤3] 评论获取完成，共 {len(comments)} 条")

            if comments:
                filepath = save_comments_to_csv(comments, self.output_dir)
                log(f"[保存] 评论已保存: {filepath}")

            log(f"[完成] 共爬取 1 条内容，{len(comments)} 条评论")
        else:
            log("[完成] 未获取到内容")
        log(f"[完成] 输出目录: {self.output_dir}")
        await self.crawler.close()

    def _poll_thread(self, thread):
        if thread.is_alive():
            self.root.after(200, lambda: self._poll_thread(thread))

    def _finish(self):
        self.root.after(0, lambda: self.start_btn.config(state="normal"))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ZhihuCrawlerGUI()
    app.run()
