import os
import sys
import json
import logging
from datetime import datetime
from functools import wraps
from flask import Flask, session, redirect, url_for, request, flash

def setup_app_logging():
    """
    为app.py设置专门的日志配置：只输出到控制台，不输出到文件
    """
    app_logger = logging.getLogger(__name__)
    app_logger.setLevel(logging.DEBUG)
    app_logger.handlers = []
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    app_logger.addHandler(console_handler)
    app_logger.propagate = False
    return app_logger

app_logger = setup_app_logging()

def get_config():
    config_path = os.environ.get("CONFIG_PATH")
    if not config_path or not os.path.exists(config_path):
        app_logger.error("配置文件不存在")
        return {"WEB_PW": "123456", "VIEWER_PW": "viewer123", "ADMIN": [7007822593]}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            return {
                "WEB_PW": config.get("WEB_PW", "123456"),
                "VIEWER_PW": config.get("VIEWER_PW", "viewer123"),
                "ADMIN": config.get("ADMIN", [7007822593]),
            }
    except Exception as e:
        app_logger.error(f"读取配置文件失败: {str(e)}")
        return {"WEB_PW": "123456", "VIEWER_PW": "viewer123", "ADMIN": [7007822593]}

def get_admin_ids():
    """获取管理员ID列表"""
    config = get_config()
    return config["ADMIN"]

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" not in session:
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" not in session:
            return redirect(url_for("auth.login", next=request.url))
        if session.get("user_role") != "admin":
            flash("您没有权限访问此页面，请使用管理员账号登录", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def viewer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" not in session:
            return redirect(url_for("auth.login", next=request.url))
        if session.get("user_role") != "viewer":
            flash("您没有权限访问此页面，请使用浏览者账号登录", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def format_datetime(timestamp):
    """格式化时间戳"""
    if timestamp:
        if isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        return str(timestamp)
    return "未知"

def format_large_number(n):
    """格式化大数字，转换为K, M, B等单位"""
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)

def highlight_search_keyword(text, keyword):
    import re
    if not keyword:
        return text
    return re.sub(f"(?i)({re.escape(keyword)})", r"<mark>\1</mark>", text)

def create_app():
    # 添加项目根目录到Python路径
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.append(project_root)

    app = Flask(__name__, template_folder='templates', static_folder='static')

    # 设置密钥
    app.secret_key = "cyberwaifu_admin_secret_key"

    # 设置数据库路径
    db_path = os.path.join(project_root, "data", "data.db")
    os.environ["DB_PATH"] = db_path

    # 设置配置文件路径
    config_local_path = os.path.join(project_root, "config", "config_local.json")
    config_path = os.path.join(project_root, "config", "config.json")
    if os.path.exists(config_local_path):
        os.environ["CONFIG_PATH"] = config_local_path
    elif os.path.exists(config_path):
        os.environ["CONFIG_PATH"] = config_path
    else:
        print(f"警告: 配置文件不存在，请检查 {config_local_path} 或 {config_path}")

    # 注册Jinja2过滤器和上下文处理器
    @app.context_processor
    def inject_moment():
        def moment():
            return datetime.now()
        return dict(moment=moment, max=max, min=min, range=range)

    app.jinja_env.filters["format_datetime"] = format_datetime
    app.jinja_env.filters["format_large_number"] = format_large_number
    app.jinja_env.filters["highlight_search_keyword"] = highlight_search_keyword

    # 注册蓝图
    from .blueprints.auth import auth_bp
    from .blueprints.admin import admin_bp
    from .blueprints.viewer import viewer_bp
    from .blueprints.api import api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(viewer_bp)
    app.register_blueprint(api_bp)

    return app