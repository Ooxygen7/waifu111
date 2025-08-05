from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    REAL,
    ForeignKey,
    PrimaryKeyConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    conv_id = Column(Text, nullable=False)
    user_id = Column(Integer, nullable=False)
    character = Column(Text, nullable=False)
    preset = Column(Text, nullable=False)
    summary = Column(Text)
    create_at = Column(Text)
    update_at = Column(Text)
    delete_mark = Column(Text)
    turns = Column(Integer)


class DialogSummary(Base):
    __tablename__ = "dialog_summary"
    conv_id = Column(Text, nullable=False, primary_key=True)
    summary_area = Column(Text, nullable=False, primary_key=True)
    content = Column(Text, nullable=False)


class Dialog(Base):
    __tablename__ = "dialogs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    conv_id = Column(Text, nullable=False)
    role = Column(Text, nullable=False)
    raw_content = Column(Text, nullable=False)
    turn_order = Column(Integer, nullable=False)
    created_at = Column(Text, nullable=False)
    processed_content = Column(Text)
    msg_id = Column(Integer)


class GroupDialog(Base):
    __tablename__ = "group_dialogs"
    id = Column(Integer, primary_key=True, autoincrement=True) # Assuming id is the primary key
    group_id = Column(Integer)
    msg_user = Column(Integer)
    trigger_type = Column(Text)
    msg_text = Column(Text)
    msg_user_name = Column(Text)
    msg_id = Column(Integer)
    raw_response = Column(Text)
    processed_response = Column(Text)
    delete_mark = Column(Text)
    group_name = Column(Text)
    create_at = Column(Text)


class GroupUserConversation(Base):
    __tablename__ = "group_user_conversations"
    id = Column(Integer, primary_key=True, autoincrement=True) # Assuming a surrogate primary key
    user_id = Column(Integer)
    group_id = Column(Integer)
    user_name = Column(Text)
    conv_id = Column(Text)
    delete_mark = Column(Integer)
    create_at = Column(Text)
    update_at = Column(Text)
    turns = Column(Integer)
    group_name = Column(Text)


class GroupUserDialog(Base):
    __tablename__ = "group_user_dialogs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    conv_id = Column(Text)
    role = Column(Text)
    raw_content = Column(Text)
    turn_order = Column(Integer)
    created_at = Column(Text)
    processed_content = Column(Text)


class Group(Base):
    __tablename__ = "groups"
    group_id = Column(Integer, primary_key=True)
    members_list = Column(Text)
    call_count = Column(Integer)
    keywords = Column(Text)
    active = Column(Integer)
    api = Column(Text)
    char = Column(Text)
    preset = Column(Text)
    input_token = Column(Integer)
    group_name = Column(Text)
    update_time = Column(Text)
    rate = Column(REAL)
    output_token = Column(Integer)
    disabled_topics = Column(Text)
    allowed_topics = Column(Text)


class UserConfig(Base):
    __tablename__ = "user_config"
    uid = Column(Integer, primary_key=True)
    char = Column(Text)
    api = Column(Text)
    preset = Column(Text)
    conv_id = Column(Text)
    stream = Column(Text)
    nick = Column(Text)


class UserSign(Base):
    __tablename__ = "user_sign"
    user_id = Column(Integer, primary_key=True)
    last_sign = Column(Text)
    sign_count = Column(Integer)
    frequency = Column(Integer)


class User(Base):
    __tablename__ = "users"
    uid = Column(Integer, primary_key=True)
    first_name = Column(Text)
    last_name = Column(Text)
    user_name = Column(Text)
    create_at = Column(Text)
    conversations = Column(Integer)
    dialog_turns = Column(Integer)
    update_at = Column(Text)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    account_tier = Column(Integer)
    remain_frequency = Column(Integer)
    balance = Column(REAL)


class UserProfile(Base):
    __tablename__ = "user_profiles"
    user_id = Column(Integer, nullable=False)
    group_id = Column(Integer, nullable=False)
    profile_json = Column(Text)
    last_updated = Column(Text)
    __table_args__ = (PrimaryKeyConstraint("user_id", "group_id"),)