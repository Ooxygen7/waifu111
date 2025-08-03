import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class User(BaseModel):
    """代表一个完整的用户实体，整合了多个表的数据。"""
    id: int = Field(..., alias='uid')
    
    # 来自 users 表
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    user_name: Optional[str] = None
    account_tier: int = 0
    remain_frequency: int = 0
    balance: float = 0.0
    conversations_count: int = Field(0, alias='conversations')
    
    # 来自 user_config 表
    nick: Optional[str] = None
    api: str
    character: str = Field(..., alias='char')
    preset: str
    stream: bool
    active_conversation_id: Optional[int] = Field(None, alias='conv_id')

    # 来自 user_sign 表
    last_sign_in: Optional[datetime.datetime] = Field(None, alias='last_sign')
    sign_in_count: int = Field(0, alias='sign_count')
    temporary_frequency: int = Field(0, alias='frequency')

    class Config:
        populate_by_name = True # 允许使用别名和字段名进行赋值

class DialogMessage(BaseModel):
    """代表对话中的一条消息。"""
    role: str
    turn: int
    raw_content: str
    processed_content: str
    message_id: Optional[int] = None
    created_at: datetime.datetime

class Conversation(BaseModel):
    """代表一个完整的私聊会话。"""
    id: int = Field(..., alias='conv_id')
    user_id: int
    character: str
    preset: str
    summaries: List[Dict[str, Any]] = Field(default_factory=list)
    turns: int = 0
    delete_mark: bool = False
    created_at: datetime.datetime
    updated_at: datetime.datetime
    
    # 动态加载的对话历史
    history: List[DialogMessage] = []

    class Config:
        populate_by_name = True

class Group(BaseModel):
    """代表一个群组。"""
    id: int
    name: str

class GroupConfig(BaseModel):
    """代表一个群组的配置。"""
    api: Optional[str] = None
    char: Optional[str] = None
    preset: Optional[str] = None