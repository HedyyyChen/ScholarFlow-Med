from typing import Optional
from pydantic import BaseModel, Field


class ZhihuContent(BaseModel):
    content_id: str = Field(default="")
    content_type: str = Field(default="")
    content_text: str = Field(default="")
    content_url: str = Field(default="")
    question_id: str = Field(default="")
    title: str = Field(default="")
    desc: str = Field(default="")
    created_time: int = Field(default=0)
    updated_time: int = Field(default=0)
    voteup_count: int = Field(default=0)
    comment_count: int = Field(default=0)
    source_keyword: str = Field(default="")
    user_id: str = Field(default="")
    user_link: str = Field(default="")
    user_nickname: str = Field(default="")
    user_avatar: str = Field(default="")
    user_url_token: str = Field(default="")


class ZhihuComment(BaseModel):
    comment_id: str = Field(default="")
    parent_comment_id: str = Field(default="")
    content: str = Field(default="")
    publish_time: int = Field(default=0)
    ip_location: Optional[str] = Field(default="")
    sub_comment_count: int = Field(default=0)
    like_count: int = Field(default=0)
    dislike_count: int = Field(default=0)
    content_id: str = Field(default="")
    content_type: str = Field(default="")
    user_id: str = Field(default="")
    user_link: str = Field(default="")
    user_nickname: str = Field(default="")
    user_avatar: str = Field(default="")

    model_config = {"extra": "ignore"}


class ZhihuCreator(BaseModel):
    user_id: str = Field(default="")
    user_link: str = Field(default="")
    user_nickname: str = Field(default="")
    user_avatar: str = Field(default="")
    url_token: str = Field(default="")
