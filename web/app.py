from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import sys
import os
import json
import time
import logging
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# 设置正确的数据库路径
db_path = os.path.join(project_root, 'data', 'data.db')
os.environ['DB_PATH'] = db_path

# 设置配置文件路径，优先使用config_local.json
config_local_path = os.path.join(project_root, 'config', 'config_local.json')
config_path = os.path.join(project_root, 'config', 'config.json')

# 检查config_local.json是否存在，如果存在则使用它，否则使用config.json
if os.path.exists(config_local_path):
    os.environ['CONFIG_PATH'] = config_local_path
elif os.path.exists(config_path):
    os.environ['CONFIG_PATH'] = config_path
else:
    print(f"警告: 配置文件不存在，请检查 {config_local_path} 或 {config_path}")

def setup_app_logging():
    """
    为app.py设置专门的日志配置：只输出到控制台，不输出到文件
    """
    # 获取当前模块的logger
    app_logger = logging.getLogger(__name__)
    app_logger.setLevel(logging.DEBUG)
    
    # 清除可能存在的handlers
    app_logger.handlers = []
    
    # 只添加控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # 设置日志格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    app_logger.addHandler(console_handler)
    
    # 防止日志传播到根logger（避免重复输出和文件记录）
    app_logger.propagate = False
    
    return app_logger

# 设置app专用的日志配置
app_logger = setup_app_logging()

from utils import db_utils as db
from utils import LLM_utils as llm
import asyncio
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'cyberwaifu_admin_secret_key'

# 加载配置文件获取Web密码
def get_web_password():
    config_path = os.environ.get('CONFIG_PATH')
    if not config_path or not os.path.exists(config_path):
        app_logger.error("配置文件不存在")
        return "123456"  # 默认密码
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get("WEB_PW", "123456")
    except Exception as e:
        app_logger.error(f"读取配置文件失败: {str(e)}")
        return "123456"  # 默认密码

# 登录验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# 添加moment函数到Jinja2模板上下文
@app.context_processor
def inject_moment():
    def moment():
        return datetime.now()
    return dict(moment=moment)

def format_datetime(timestamp):
    """格式化时间戳"""
    if timestamp:
        try:
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            return str(timestamp)
        except:
            return str(timestamp)
    return '未知'

app.jinja_env.filters['format_datetime'] = format_datetime

def highlight_search_keyword(text, keyword):
    import re
    if not keyword:
        return text
    # 使用re.IGNORECASE进行不区分大小写的匹配
    return re.sub(f'(?i)({re.escape(keyword)})', r'<mark>\1</mark>', text)

app.jinja_env.filters['highlight_search_keyword'] = highlight_search_keyword

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if 'logged_in' in session:
        return redirect(url_for('index'))
    
    error = None
    if request.method == 'POST':
        password = request.form.get('password')
        correct_password = get_web_password()
        
        if password == correct_password:
            session['logged_in'] = True
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            error = '密码错误'
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    """登出"""
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """主页 - 显示统计信息"""
    # 获取统计数据
    stats = {}
    
    # 基础统计
    stats['total_users'] = db.query_db('SELECT COUNT(*) FROM users')[0][0] if db.query_db('SELECT COUNT(*) FROM users') else 0
    stats['total_conversations'] = db.query_db('SELECT COUNT(*) FROM conversations')[0][0] if db.query_db('SELECT COUNT(*) FROM conversations') else 0
    stats['total_dialogs'] = db.query_db('SELECT COUNT(*) FROM dialogs')[0][0] if db.query_db('SELECT COUNT(*) FROM dialogs') else 0
    
    # Token统计
    total_tokens = db.query_db('SELECT SUM(input_tokens), SUM(output_tokens) FROM users')
    if total_tokens and total_tokens[0] and total_tokens[0][0]:
        stats['total_input_tokens'] = total_tokens[0][0] or 0
        stats['total_output_tokens'] = total_tokens[0][1] or 0
    else:
        stats['total_input_tokens'] = 0
        stats['total_output_tokens'] = 0
    stats['total_tokens'] = stats['total_input_tokens'] + stats['total_output_tokens']
    
    # 今日统计
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 今日新增对话数
    today_conversations = db.query_db("SELECT COUNT(*) FROM conversations WHERE date(create_at) = ?", (today,))
    stats['today_conversations'] = today_conversations[0][0] if today_conversations else 0
    
    # 今日新增消息数
    today_dialogs = db.query_db("SELECT COUNT(*) FROM dialogs WHERE date(created_at) = ?", (today,))
    stats['today_dialogs'] = today_dialogs[0][0] if today_dialogs else 0
    
    # 今日新增群聊消息数
    today_group_dialogs = db.query_db("SELECT COUNT(*) FROM group_dialogs WHERE date(create_at) = ?", (today,))
    stats['today_group_dialogs'] = today_group_dialogs[0][0] if today_group_dialogs else 0
    
    # 今日消耗token数 (估算：基于今日对话数的比例)
    if stats['total_dialogs'] > 0:
        today_ratio = stats['today_dialogs'] / stats['total_dialogs']
        stats['today_input_tokens'] = int(stats['total_input_tokens'] * today_ratio)
        stats['today_output_tokens'] = int(stats['total_output_tokens'] * today_ratio)
        stats['today_total_tokens'] = stats['today_input_tokens'] + stats['today_output_tokens']
    else:
        stats['today_input_tokens'] = 0
        stats['today_output_tokens'] = 0
        stats['today_total_tokens'] = 0
    
    # Token使用统计
    token_stats = db.query_db('SELECT SUM(input_tokens) as input_total, SUM(output_tokens) as output_total FROM users')
    if token_stats and token_stats[0]:
        stats['total_input_tokens'] = token_stats[0][0] or 0
        stats['total_output_tokens'] = token_stats[0][1] or 0
    else:
        stats['total_input_tokens'] = 0
        stats['total_output_tokens'] = 0
    
    # 今日最活跃用户 (按消息数排序)
    active_users = db.query_db("""
        SELECT u.uid, u.user_name, u.first_name, u.last_name, COUNT(d.id) as message_count
        FROM users u
        JOIN conversations c ON u.uid = c.user_id
        JOIN dialogs d ON c.conv_id = d.conv_id
        WHERE date(d.created_at) = ?
        GROUP BY u.uid, u.user_name, u.first_name, u.last_name
        ORDER BY message_count DESC
        LIMIT 5
    """, (today,))
    stats['active_users'] = active_users or []
    
    # 今日最活跃群组 (按消息数排序)
    active_groups = db.query_db("""
        SELECT g.group_id, g.group_name, COUNT(*) as message_count
        FROM groups g
        JOIN group_dialogs gd ON g.group_id = gd.group_id
        WHERE date(gd.create_at) = ?
        GROUP BY g.group_id, g.group_name
        ORDER BY message_count DESC
        LIMIT 5
    """, (today,))
    stats['active_groups'] = active_groups or []
    
    # 获取时间粒度参数
    time_range = request.args.get('time_range', '7d')  # 默认7天
    
    # 根据时间粒度设置查询参数
    if time_range == '30d':
        days_back = 30
        user_date_format = "date(create_at)"
        user_group_format = "date(create_at)"
        dialog_date_format = "date(created_at)"
        dialog_group_format = "date(created_at)"
        group_date_format = "date(create_at)"
        group_group_format = "date(create_at)"
    elif time_range == '7d':
        days_back = 7
        user_date_format = "date(create_at)"
        user_group_format = "date(create_at)"
        dialog_date_format = "date(created_at)"
        dialog_group_format = "date(created_at)"
        group_date_format = "date(create_at)"
        group_group_format = "date(create_at)"
    elif time_range == '1d':
        days_back = 1
        user_date_format = "strftime('%H:00', create_at)"
        user_group_format = "strftime('%H', create_at)"
        dialog_date_format = "strftime('%H:00', created_at)"
        dialog_group_format = "strftime('%H', created_at)"
        group_date_format = "strftime('%H:00', create_at)"
        group_group_format = "strftime('%H', create_at)"
    else:
        days_back = 7
        user_date_format = "date(create_at)"
        user_group_format = "date(create_at)"
        dialog_date_format = "date(created_at)"
        dialog_group_format = "date(created_at)"
        group_date_format = "date(create_at)"
        group_group_format = "date(create_at)"
    
    # 用户增长趋势
    if time_range == '1d':
        user_growth = db.query_db(f"""
            SELECT strftime('%H:00', create_at) as date, COUNT(*) as count
            FROM users
            WHERE date(create_at) = date('now')
            GROUP BY strftime('%H', create_at)
            ORDER BY strftime('%H', create_at)
        """)
    else:
        user_growth = db.query_db(f"""
            SELECT {user_date_format} as date, COUNT(*) as count
            FROM users
            WHERE date(create_at) >= date('now', '-{days_back} days')
            GROUP BY {user_group_format}
            ORDER BY {user_group_format}
        """)
    stats['user_growth'] = user_growth or []
    
    # 对话活跃度趋势
    if time_range == '1d':
        dialog_trend = db.query_db(f"""
            SELECT strftime('%H:00', created_at) as date, COUNT(*) as count
            FROM dialogs
            WHERE date(created_at) = date('now')
            GROUP BY strftime('%H', created_at)
            ORDER BY strftime('%H', created_at)
        """)
    else:
        dialog_trend = db.query_db(f"""
            SELECT {dialog_date_format} as date, COUNT(*) as count
            FROM dialogs
            WHERE date(created_at) >= date('now', '-{days_back} days')
            GROUP BY {dialog_group_format}
            ORDER BY {dialog_group_format}
        """)
    stats['dialog_trend'] = dialog_trend or []
    
    # Token消耗趋势 (基于对话数估算)
    token_trend = []
    for item in dialog_trend:
        if stats['total_dialogs'] > 0:
            ratio = item[1] / stats['total_dialogs']
            estimated_tokens = int((stats['total_input_tokens'] + stats['total_output_tokens']) * ratio)
        else:
            estimated_tokens = 0
        token_trend.append((item[0], estimated_tokens))
    stats['token_trend'] = token_trend
    
    # 群聊活跃度趋势
    if time_range == '1d':
        group_trend = db.query_db(f"""
            SELECT strftime('%H:00', create_at) as date, COUNT(*) as count
            FROM group_dialogs
            WHERE date(create_at) = date('now')
            GROUP BY strftime('%H', create_at)
            ORDER BY strftime('%H', create_at)
        """)
    else:
        group_trend = db.query_db(f"""
            SELECT {group_date_format} as date, COUNT(*) as count
            FROM group_dialogs
            WHERE date(create_at) >= date('now', '-{days_back} days')
            GROUP BY {group_group_format}
            ORDER BY {group_group_format}
        """)
    stats['group_trend'] = group_trend or []
    
    # 传递时间粒度参数给模板
    stats['time_range'] = time_range
    
    return render_template('index.html', stats=stats)

@app.route('/users')
@login_required
def users():
    """用户管理页面"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    search_term = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'create_at')
    sort_order = request.args.get('sort_order', 'desc')

    query = 'SELECT * FROM users'
    params = []
    if search_term:
        query += ' WHERE uid LIKE ? OR user_name LIKE ? OR first_name LIKE ? OR last_name LIKE ?'
        search_param = f'%{search_term}%'
        params.extend([search_param, search_param, search_param, search_param])

    if sort_by and sort_order:
        query += f' ORDER BY {sort_by} {sort_order}'

    query += ' LIMIT ? OFFSET ?'
    params.extend([per_page, offset])

    users_data = db.query_db(query, tuple(params))

    count_query = 'SELECT COUNT(*) FROM users'
    count_params = []
    if search_term:
        count_query += ' WHERE uid LIKE ? OR user_name LIKE ? OR first_name LIKE ? OR last_name LIKE ?'
        count_params.extend([search_param, search_param, search_param, search_param])

    total_result = db.query_db(count_query, tuple(count_params))
    total_users = total_result[0][0] if total_result else 0
    total_pages = (total_users + per_page - 1) // per_page

    users_list = []
    if users_data:
        columns = ['uid', 'first_name', 'last_name', 'user_name', 'create_at', 'conversations', 
                  'dialog_turns', 'update_at', 'input_tokens', 'output_tokens', 'account_tier', 
                  'remain_frequency', 'balance']
        for row in users_data:
            user_dict = {columns[i]: row[i] for i in range(len(columns))}
            users_list.append(user_dict)

    def next_sort_order(column):
        if column == sort_by:
            return 'asc' if sort_order == 'desc' else 'desc'
        return 'desc'

    return render_template('users.html', users=users_list, page=page, total_pages=total_pages, 
                         format_datetime=format_datetime, search_term=search_term, 
                         sort_by=sort_by, sort_order=sort_order, next_sort_order=next_sort_order)

@app.route('/conversations')
@login_required
def conversations():
    """对话管理页面"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str).strip()
    sort_by = request.args.get('sort', 'update_at')
    order = request.args.get('order', 'desc')
    per_page = 20
    offset = (page - 1) * per_page
    
    # 允许的排序字段
    allowed_sort_fields = ['conv_id', 'user_id', 'character', 'preset', 'turns', 'create_at', 'update_at']
    if sort_by not in allowed_sort_fields:
        sort_by = 'update_at'
    
    # 确保排序方向安全
    order = 'ASC' if order.lower() == 'asc' else 'DESC'
    
    # 使用JOIN查询获取用户信息
    query = '''
        SELECT c.id, c.conv_id, c.user_id, c.character, c.preset, c.summary, 
               c.create_at, c.update_at, c.delete_mark, c.turns,
               u.first_name, u.last_name, u.user_name
        FROM conversations c
        LEFT JOIN users u ON c.user_id = u.uid
    '''
    params = []
    
    # 添加搜索条件
    if search:
        # 模糊搜索用户名、用户姓名、用户ID
        query += ''' WHERE (u.user_name LIKE ? OR 
                           u.first_name LIKE ? OR 
                           u.last_name LIKE ? OR 
                           CAST(c.user_id AS TEXT) LIKE ?)'''
        search_param = f'%{search}%'
        params.extend([search_param, search_param, search_param, search_param])
    
    query += f' ORDER BY c.{sort_by} {order} LIMIT ? OFFSET ?'
    params.extend([per_page, offset])
    
    conversations_data = db.query_db(query, tuple(params))
    
    # 计算总数
    count_query = 'SELECT COUNT(*) FROM conversations c LEFT JOIN users u ON c.user_id = u.uid'
    count_params = []
    if search:
        count_query += ''' WHERE (u.user_name LIKE ? OR 
                                 u.first_name LIKE ? OR 
                                 u.last_name LIKE ? OR 
                                 CAST(c.user_id AS TEXT) LIKE ?)'''
        search_param = f'%{search}%'
        count_params.extend([search_param, search_param, search_param, search_param])
    
    total_result = db.query_db(count_query, tuple(count_params))
    total_conversations = total_result[0][0] if total_result else 0
    total_pages = (total_conversations + per_page - 1) // per_page
    
    # 转换为字典格式
    conversations_list = []
    if conversations_data:
        columns = ['id', 'conv_id', 'user_id', 'character', 'preset', 'summary', 
                  'create_at', 'update_at', 'delete_mark', 'turns',
                  'first_name', 'last_name', 'user_name']
        for row in conversations_data:
            conv_dict = {columns[i]: row[i] for i in range(len(columns))}
            conversations_list.append(conv_dict)
    
    return render_template('conversations.html', conversations=conversations_list, 
                         page=page, total_pages=total_pages, search=search, 
                         sort_by=sort_by, order=order.lower(), format_datetime=format_datetime)

@app.route('/dialogs/<int:conv_id>')
@login_required
def dialogs(conv_id):
    """查看对话详情"""
    # 获取对话信息
    conversation_data = db.query_db(
        'SELECT * FROM conversations WHERE conv_id = ?', (conv_id,)
    )
    
    if not conversation_data:
        return "对话不存在", 404
    
    # 转换对话信息为字典
    conv_columns = ['id', 'conv_id', 'user_id', 'character', 'preset', 'summary', 'create_at', 'update_at', 'delete_mark', 'turns']
    conversation = {conv_columns[i]: conversation_data[0][i] for i in range(len(conv_columns))}
    
    # 获取搜索关键词
    search_keyword = request.args.get('search', '').strip()
    
    # 根据是否有搜索关键词决定查询方式
    if search_keyword:
        # 搜索模式：在对话消息中搜索关键词
        dialogs_data = db.query_db(
            '''SELECT * FROM dialogs 
               WHERE conv_id = ? AND (
                   raw_content LIKE ? OR 
                   processed_content LIKE ?
               ) 
               ORDER BY turn_order ASC''',
            (conv_id, f'%{search_keyword}%', f'%{search_keyword}%')
        )
    else:
        # 正常模式：获取所有对话消息
        dialogs_data = db.query_db(
            'SELECT * FROM dialogs WHERE conv_id = ? ORDER BY turn_order ASC',
            (conv_id,)
        )
    
    # 转换对话消息为字典格式
    dialogs_list = []
    if dialogs_data:
        dialog_columns = ['id', 'conv_id', 'role', 'raw_content', 'turn_order', 'created_at', 'processed_content', 'msg_id']
        for row in dialogs_data:
            dialog_dict = {dialog_columns[i]: row[i] for i in range(len(dialog_columns))}
            dialogs_list.append(dialog_dict)
    
    return render_template('dialogs.html', conversation=conversation, 
                         dialogs=dialogs_list, format_datetime=format_datetime,
                         search_keyword=search_keyword)

@app.route('/groups')
@login_required
def groups():
    """群组管理页面"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    search_term = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'update_time')
    sort_order = request.args.get('sort_order', 'desc')
    
    # 允许的排序字段
    allowed_sort_fields = ['group_id', 'group_name', 'call_count', 'api', 'char', 'preset', 'rate', 
                          'input_token', 'output_token', 'active', 'update_time']
    if sort_by not in allowed_sort_fields:
        sort_by = 'update_time'
    
    # 确保排序方向安全
    sort_order = 'ASC' if sort_order.lower() == 'asc' else 'DESC'
    
    query = 'SELECT * FROM groups'
    params = []
    if search_term:
        query += ' WHERE group_id LIKE ? OR group_name LIKE ? OR members_list LIKE ? OR api LIKE ? OR char LIKE ? OR preset LIKE ?'
        search_param = f'%{search_term}%'
        params.extend([search_param, search_param, search_param, search_param, search_param, search_param])
    
    query += f' ORDER BY {sort_by} {sort_order}'
    query += ' LIMIT ? OFFSET ?'
    params.extend([per_page, offset])
    
    groups_data = db.query_db(query, tuple(params))
    
    # 获取总数
    count_query = 'SELECT COUNT(*) FROM groups'
    count_params = []
    if search_term:
        count_query += ' WHERE group_id LIKE ? OR group_name LIKE ? OR members_list LIKE ? OR api LIKE ? OR char LIKE ? OR preset LIKE ?'
        count_params.extend([search_param, search_param, search_param, search_param, search_param, search_param])
    
    total_result = db.query_db(count_query, tuple(count_params))
    total_groups = total_result[0][0] if total_result else 0
    total_pages = (total_groups + per_page - 1) // per_page
    
    # 转换为字典格式
    groups_list = []
    if groups_data:
        columns = ['group_id', 'members_list', 'call_count', 'keywords', 'active', 'api', 'char', 
                  'preset', 'input_token', 'group_name', 'update_time', 'rate', 'output_token', 'disabled_topics']
        for row in groups_data:
            group_dict = {columns[i]: row[i] for i in range(len(columns))}
            groups_list.append(group_dict)
    
    def next_sort_order(column):
        if column == sort_by:
            return 'asc' if sort_order == 'DESC' else 'desc'
        return 'desc'
    
    return render_template('groups.html', groups=groups_list, page=page, total_pages=total_pages,
                         format_datetime=format_datetime, search_term=search_term,
                         sort_by=sort_by, sort_order=sort_order, next_sort_order=next_sort_order)

@app.route('/group_dialogs/<group_id>')
@login_required
def group_dialogs(group_id):
    # 转换group_id为整数（支持负数）
    try:
        group_id = int(group_id)
    except ValueError:
        return "Invalid group ID", 400
    """查看群组对话"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str).strip()
    per_page = 50
    offset = (page - 1) * per_page
    
    # 获取群组信息
    group_data = db.query_db('SELECT * FROM groups WHERE group_id = ?', (group_id,))
    
    if not group_data:
        return "群组不存在", 404
    
    # 转换群组信息为字典
    group_columns = ['group_id', 'members_list', 'call_count', 'keywords', 'active', 'api', 'char', 
                    'preset', 'input_token', 'group_name', 'update_time', 'rate', 'output_token', 'disabled_topics']
    group = {group_columns[i]: group_data[0][i] for i in range(len(group_columns))}
    
    # 根据是否有搜索条件构建查询
    if search:
        # 搜索模式：搜索用户消息内容
        dialogs_data = db.query_db(
            'SELECT * FROM group_dialogs WHERE group_id = ? AND msg_text LIKE ? ORDER BY create_at DESC LIMIT ? OFFSET ?',
            (group_id, f'%{search}%', per_page, offset)
        )
        
        total_result = db.query_db(
            'SELECT COUNT(*) FROM group_dialogs WHERE group_id = ? AND msg_text LIKE ?', 
            (group_id, f'%{search}%')
        )
    else:
        # 正常模式：显示所有对话
        dialogs_data = db.query_db(
            'SELECT * FROM group_dialogs WHERE group_id = ? ORDER BY create_at DESC LIMIT ? OFFSET ?',
            (group_id, per_page, offset)
        )
        
        total_result = db.query_db(
            'SELECT COUNT(*) FROM group_dialogs WHERE group_id = ?', (group_id,)
        )
    
    total_dialogs = total_result[0][0] if total_result else 0
    total_pages = (total_dialogs + per_page - 1) // per_page
    
    # 转换对话数据为字典格式
    dialogs_list = []
    if dialogs_data:
        # 根据数据库实际字段顺序映射
        dialog_columns = ['group_id', 'msg_user', 'trigger_type', 'msg_text', 'msg_user_name', 
                         'msg_id', 'raw_response', 'processed_response', 'delete_mark', 'group_name', 'create_at']
        for row in dialogs_data:
            dialog_dict = {dialog_columns[i]: row[i] for i in range(len(dialog_columns))}
            dialogs_list.append(dialog_dict)
    
    return render_template('group_dialogs.html', group=group, dialogs=dialogs_list,
                         page=page, total_pages=total_pages, search=search, format_datetime=format_datetime)

@app.route('/api/message_page/<group_id>/<msg_id>')
@login_required
def get_message_page(group_id, msg_id):
    """获取指定消息所在的页码"""
    try:
        group_id = int(group_id)
    except ValueError:
        return jsonify({'error': 'Invalid group ID'}), 400
    
    per_page = 50
    
    # 获取该消息的创建时间
    msg_data = db.query_db(
        'SELECT create_at FROM group_dialogs WHERE group_id = ? AND msg_id = ?',
        (group_id, msg_id)
    )
    
    if not msg_data:
        return jsonify({'error': 'Message not found'}), 404
    
    msg_create_at = msg_data[0][0]
    
    # 计算在该消息之后创建的消息数量（因为按create_at DESC排序）
    count_result = db.query_db(
        'SELECT COUNT(*) FROM group_dialogs WHERE group_id = ? AND create_at > ?',
        (group_id, msg_create_at)
    )
    
    messages_after = count_result[0][0] if count_result else 0
    page = (messages_after // per_page) + 1
    
    return jsonify({'page': page})

@app.route('/api/user/<int:user_id>')
@login_required
def api_user_detail(user_id):
    """获取用户详细信息API"""
    user_data = db.query_db('SELECT * FROM users WHERE uid = ?', (user_id,))
    
    if not user_data:
        return jsonify({'error': '用户不存在'}), 404
    
    user_config_data = db.query_db('SELECT * FROM user_config WHERE uid = ?', (user_id,))
    conversations_count_data = db.query_db('SELECT COUNT(*) FROM conversations WHERE user_id = ?', (user_id,))
    conversations_count = conversations_count_data[0][0] if conversations_count_data else 0
    
    # 转换为字典格式
    user_columns = ['uid', 'first_name', 'last_name', 'user_name', 'create_at', 'conversations', 
                   'dialog_turns', 'update_at', 'input_tokens', 'output_tokens', 'account_tier', 
                   'remain_frequency', 'balance']
    user_dict = {user_columns[i]: user_data[0][i] for i in range(len(user_columns))}
    
    user_config_dict = None
    if user_config_data:
        config_columns = ['uid', 'char', 'api', 'preset', 'conv_id', 'stream', 'nick']
        user_config_dict = {config_columns[i]: user_config_data[0][i] for i in range(len(config_columns))}
    
    return jsonify({
        'user': user_dict,
        'config': user_config_dict,
        'conversations_count': conversations_count
    })

@app.route('/search')
@login_required
def search():
    """全局搜索页面"""
    query = request.args.get('q', '')
    
    if not query:
        return render_template('search.html', results={}, query='', format_datetime=format_datetime)
    
    results = {
        'dialogs': [],
        'users': [],
        'groups': [],
        'conversations': []
    }
    
    # 搜索私聊对话消息
    dialogs_data = db.query_db(
        'SELECT d.*, c.character, c.user_id, u.user_name, u.first_name, u.last_name FROM dialogs d LEFT JOIN conversations c ON d.conv_id = c.conv_id LEFT JOIN users u ON c.user_id = u.uid WHERE d.raw_content LIKE ? OR d.processed_content LIKE ? ORDER BY d.created_at DESC',
        (f'%{query}%', f'%{query}%')
    )
    if dialogs_data:
        dialog_columns = ['id', 'conv_id', 'role', 'raw_content', 'turn_order', 'created_at', 'processed_content', 'msg_id', 'character', 'user_id', 'user_name', 'first_name', 'last_name']
        for row in dialogs_data:
            dialog_dict = {dialog_columns[i]: row[i] for i in range(len(dialog_columns))}
            # 构建用户姓名
            first_name = dialog_dict.get('first_name', '') or ''
            last_name = dialog_dict.get('last_name', '') or ''
            dialog_dict['user_name'] = f"{first_name} {last_name}".strip() or dialog_dict.get('user_name', '未设置')
            dialog_dict['type'] = 'private'  # 标记为私聊消息
            results['dialogs'].append(dialog_dict)
    
    # 搜索群聊消息内容
    group_dialogs_data = db.query_db(
        'SELECT gd.group_id, gd.msg_user, gd.trigger_type, gd.msg_text, gd.msg_user_name, gd.msg_id, gd.raw_response, gd.processed_response, gd.delete_mark, gd.group_name, gd.create_at, g.group_name as groups_group_name, ROW_NUMBER() OVER (ORDER BY gd.create_at DESC) as id FROM group_dialogs gd LEFT JOIN groups g ON gd.group_id = g.group_id WHERE gd.msg_text LIKE ? OR gd.raw_response LIKE ? OR gd.processed_response LIKE ? ORDER BY gd.create_at DESC',
        (f'%{query}%', f'%{query}%', f'%{query}%')
    )
    if group_dialogs_data:
        group_dialog_columns = ['group_id', 'msg_user', 'trigger_type', 'msg_text', 'msg_user_name', 'msg_id', 'raw_response', 'processed_response', 'delete_mark', 'group_name', 'create_at', 'groups_group_name', 'id']
        for row in group_dialogs_data:
            group_dialog_dict = {group_dialog_columns[i]: row[i] for i in range(len(group_dialog_columns))}
            # 使用 groups 表的 group_name 作为主要群组名，如果没有则使用 group_dialogs 表的 group_name
            group_dialog_dict['group_name'] = group_dialog_dict.get('groups_group_name') or group_dialog_dict.get('group_name') or '未知群组'
            group_dialog_dict['type'] = 'group'  # 标记为群聊消息
            results['dialogs'].append(group_dialog_dict)
    
    # 搜索用户信息
    users_data = db.query_db(
        'SELECT u.uid, u.first_name, u.last_name, u.user_name, u.create_at, u.conversations as conversations_orig, u.dialog_turns as dialog_turns_orig, u.update_at, u.input_tokens, u.output_tokens, u.account_tier, u.remain_frequency, u.balance, COUNT(DISTINCT c.conv_id) as conversations, SUM(CASE WHEN d.id IS NOT NULL THEN 1 ELSE 0 END) as dialog_turns FROM users u LEFT JOIN conversations c ON u.uid = c.user_id LEFT JOIN dialogs d ON c.conv_id = d.conv_id WHERE u.user_name LIKE ? OR u.first_name LIKE ? OR u.last_name LIKE ? OR CAST(u.uid AS TEXT) LIKE ? GROUP BY u.uid ORDER BY u.create_at DESC',
        (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%')
    )
    if users_data:
        user_columns = ['uid', 'first_name', 'last_name', 'user_name', 'create_at', 'conversations_orig', 
                       'dialog_turns_orig', 'update_at', 'input_tokens', 'output_tokens', 'account_tier', 
                       'remain_frequency', 'balance', 'conversations', 'dialog_turns']
        for row in users_data:
            user_dict = {user_columns[i]: row[i] for i in range(len(user_columns))}
            results['users'].append(user_dict)
    
    # 搜索群组信息
    groups_data = db.query_db(
        'SELECT g.group_id, g.group_name, g.char, g.call_count, g.active, g.update_time, COUNT(DISTINCT gd.msg_id) as dialog_count FROM groups g LEFT JOIN group_dialogs gd ON g.group_id = gd.group_id WHERE g.group_name LIKE ? OR CAST(g.group_id AS TEXT) LIKE ? GROUP BY g.group_id ORDER BY g.update_time DESC',
        (f'%{query}%', f'%{query}%')
    )
    if groups_data:
        group_columns = ['group_id', 'group_name', 'char', 'call_count', 'active', 'update_time', 'dialog_count']
        for row in groups_data:
            group_dict = {group_columns[i]: row[i] for i in range(len(group_columns))}
            results['groups'].append(group_dict)
    
    # 搜索对话记录
    conversations_data = db.query_db(
        'SELECT c.conv_id, c.user_id, c.character, c.preset, c.summary, c.create_at, c.update_at, u.user_name, u.first_name, u.last_name, COUNT(d.id) as turns FROM conversations c LEFT JOIN users u ON c.user_id = u.uid LEFT JOIN dialogs d ON c.conv_id = d.conv_id WHERE c.character LIKE ? OR c.preset LIKE ? OR c.summary LIKE ? OR u.user_name LIKE ? OR u.first_name LIKE ? OR u.last_name LIKE ? OR CAST(c.user_id AS TEXT) LIKE ? GROUP BY c.conv_id ORDER BY c.update_at DESC',
        (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%')
    )
    if conversations_data:
        conversation_columns = ['conv_id', 'user_id', 'character', 'preset', 'summary', 'create_at', 'update_at', 'user_name', 'first_name', 'last_name', 'turns']
        for row in conversations_data:
            conv_dict = {conversation_columns[i]: row[i] for i in range(len(conversation_columns))}
            results['conversations'].append(conv_dict)
    
    return render_template('search.html', results=results, query=query, format_datetime=format_datetime)

@app.route('/api/user/<int:user_id>/update', methods=['POST'])
@login_required
def api_user_update(user_id):
    """更新用户信息API"""
    try:
        data = request.get_json()
        
        # 更新用户基本信息
        user_updates = []
        user_params = []
        
        if 'user_name' in data:
            user_updates.append('user_name = ?')
            user_params.append(data['user_name'])
        if 'first_name' in data:
            user_updates.append('first_name = ?')
            user_params.append(data['first_name'])
        if 'last_name' in data:
            user_updates.append('last_name = ?')
            user_params.append(data['last_name'])
        if 'account_tier' in data:
            user_updates.append('account_tier = ?')
            user_params.append(data['account_tier'])
        if 'balance' in data:
            user_updates.append('balance = ?')
            user_params.append(data['balance'])
        if 'remain_frequency' in data:
            user_updates.append('remain_frequency = ?')
            user_params.append(data['remain_frequency'])
        
        if user_updates:
            user_params.append(user_id)
            user_sql = f"UPDATE users SET {', '.join(user_updates)}, update_at = datetime('now') WHERE uid = ?"
            db.revise_db(user_sql, tuple(user_params))
        
        # 更新用户配置信息
        config_updates = []
        config_params = []
        
        if 'char' in data:
            config_updates.append('char = ?')
            config_params.append(data['char'])
        if 'api' in data:
            config_updates.append('api = ?')
            config_params.append(data['api'])
        if 'preset' in data:
            config_updates.append('preset = ?')
            config_params.append(data['preset'])
        if 'stream' in data:
            config_updates.append('stream = ?')
            config_params.append(data['stream'])
        if 'nick' in data:
            config_updates.append('nick = ?')
            config_params.append(data['nick'])
        
        if config_updates:
            # 检查用户配置是否存在
            existing_config = db.query_db('SELECT uid FROM user_config WHERE uid = ?', (user_id,))
            
            if existing_config:
                # 更新现有配置
                config_params.append(user_id)
                config_sql = f"UPDATE user_config SET {', '.join(config_updates)} WHERE uid = ?"
                db.revise_db(config_sql, tuple(config_params))
            else:
                # 创建新配置
                config_columns = ['uid'] + [col.split(' = ?')[0] for col in config_updates]
                config_values = [user_id] + config_params
                placeholders = ', '.join(['?'] * len(config_values))
                config_sql = f"INSERT INTO user_config ({', '.join(config_columns)}) VALUES ({placeholders})"
                db.revise_db(config_sql, tuple(config_values))
        
        return jsonify({'success': True, 'message': '用户信息更新成功'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/groups/<group_id>', methods=['PUT'])
@login_required
def api_group_update(group_id):
    """更新群组信息API"""
    try:
        # 将group_id转换为整数，支持负数
        try:
            group_id = int(group_id)
        except ValueError:
            return jsonify({'success': False, 'message': '无效的群组ID'}), 400
            
        data = request.get_json()
        
        # 检查群组是否存在
        existing_group = db.query_db('SELECT group_id FROM groups WHERE group_id = ?', (group_id,))
        if not existing_group:
            return jsonify({'success': False, 'message': '群组不存在'}), 404
        
        # 更新群组信息
        updates = []
        params = []
        
        if 'group_name' in data:
            updates.append('group_name = ?')
            params.append(data['group_name'])
        if 'active' in data:
            updates.append('active = ?')
            params.append(int(data['active']))
        if 'char' in data:
            updates.append('char = ?')
            params.append(data['char'])
        if 'api' in data:
            updates.append('api = ?')
            params.append(data['api'])
        if 'preset' in data:
            updates.append('preset = ?')
            params.append(data['preset'])
        if 'rate' in data:
            updates.append('rate = ?')
            params.append(float(data['rate']) if data['rate'] else None)
        if 'members_list' in data:
            updates.append('members_list = ?')
            params.append(data['members_list'])
        if 'keywords' in data:
            updates.append('keywords = ?')
            params.append(data['keywords'])
        if 'disabled_topics' in data:
            updates.append('disabled_topics = ?')
            params.append(data['disabled_topics'])
        
        if updates:
            params.append(group_id)
            
            sql = f"UPDATE groups SET {', '.join(updates)} WHERE group_id = ?"
            db.revise_db(sql, tuple(params))
            
            return jsonify({'success': True, 'message': '群组信息更新成功'})
        else:
            return jsonify({'success': False, 'message': '没有提供要更新的字段'}), 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# 配置文件管理路由
@app.route('/config')
@login_required
def config_management():
    """配置文件管理页面"""
    return render_template('config.html')

@app.route('/api/config/list')
@login_required
def api_config_list():
    """获取配置文件列表"""
    try:
        import os
        import json
        
        # 动态获取项目根目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(current_dir)  # 上一级目录
        config_dirs = {
            'characters': os.path.join(base_path, 'characters'),
            'config': os.path.join(base_path, 'config'),
            'prompts': os.path.join(base_path, 'prompts')
        }
        
        result = {}
        
        for category, dir_path in config_dirs.items():
            files = []
            if os.path.exists(dir_path):
                for filename in os.listdir(dir_path):
                    if filename.endswith('.json'):
                        file_path = os.path.join(dir_path, filename)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = json.load(f)
                            files.append({
                                'name': filename,
                                'path': file_path,
                                'size': os.path.getsize(file_path),
                                'modified': os.path.getmtime(file_path)
                            })
                        except Exception as e:
                            files.append({
                                'name': filename,
                                'path': file_path,
                                'error': str(e)
                            })
            result[category] = files
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/read')
@login_required
def api_config_read():
    """读取配置文件内容"""
    try:
        file_path = request.args.get('path')
        if not file_path:
            return jsonify({'error': '缺少文件路径参数'}), 400
        
        # 安全检查：确保文件路径在允许的目录内
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(current_dir)  # 上一级目录
        allowed_dirs = ['characters', 'config', 'prompts']
        
        is_allowed = False
        for allowed_dir in allowed_dirs:
            if file_path.startswith(os.path.join(base_path, allowed_dir)):
                is_allowed = True
                break
        
        if not is_allowed:
            return jsonify({'error': '不允许访问此路径'}), 403
        
        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        return jsonify({
            'content': content,
            'path': file_path,
            'name': os.path.basename(file_path)
        })
    except json.JSONDecodeError as e:
        return jsonify({'error': f'JSON格式错误: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/save', methods=['POST'])
@login_required
def api_config_save():
    """保存配置文件"""
    try:
        data = request.get_json()
        file_path = data.get('path')
        content = data.get('content')
        
        if not file_path or content is None:
            return jsonify({'error': '缺少必要参数'}), 400
        
        # 安全检查
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(current_dir)  # 上一级目录
        allowed_dirs = ['characters', 'config', 'prompts']
        
        is_allowed = False
        for allowed_dir in allowed_dirs:
            if file_path.startswith(os.path.join(base_path, allowed_dir)):
                is_allowed = True
                break
        
        if not is_allowed:
            return jsonify({'error': '不允许访问此路径'}), 403
        
        # 验证JSON格式
        try:
            json.dumps(content)
        except Exception as e:
            return jsonify({'error': f'JSON格式无效: {str(e)}'}), 400
        
        # 备份原文件
        if os.path.exists(file_path):
            backup_path = file_path + '.backup'
            import shutil
            shutil.copy2(file_path, backup_path)
        
        # 保存新内容
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        
        return jsonify({'success': True, 'message': '文件保存成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/create', methods=['POST'])
@login_required
def api_config_create():
    """创建新配置文件"""
    try:
        data = request.get_json()
        category = data.get('category')  # characters, config, prompts
        filename = data.get('filename')
        content = data.get('content', {})
        
        if not category or not filename:
            return jsonify({'error': '缺少必要参数'}), 400
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(current_dir)  # 上一级目录
        allowed_categories = ['characters', 'config', 'prompts']
        
        if category not in allowed_categories:
            return jsonify({'error': '无效的分类'}), 400
        
        file_path = os.path.join(base_path, category, filename)
        
        if os.path.exists(file_path):
            return jsonify({'error': '文件已存在'}), 409
        
        # 验证JSON格式
        try:
            json.dumps(content)
        except Exception as e:
            return jsonify({'error': f'JSON格式无效: {str(e)}'}), 400
        
        # 创建文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        
        return jsonify({'success': True, 'message': '文件创建成功', 'path': file_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/delete', methods=['POST'])
@login_required
def api_config_delete():
    """删除配置文件"""
    try:
        data = request.get_json()
        file_path = data.get('path')
        
        if not file_path:
            return jsonify({'error': '缺少文件路径参数'}), 400
        
        # 安全检查
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(current_dir)  # 上一级目录
        allowed_dirs = ['characters', 'config', 'prompts']
        
        is_allowed = False
        for allowed_dir in allowed_dirs:
            if file_path.startswith(os.path.join(base_path, allowed_dir)):
                is_allowed = True
                break
        
        if not is_allowed:
            return jsonify({'error': '不允许访问此路径'}), 403
        
        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404
        
        # 创建备份
        backup_path = file_path + '.deleted.' + str(int(time.time()))
        import shutil
        shutil.move(file_path, backup_path)
        
        return jsonify({'success': True, 'message': '文件删除成功', 'backup': backup_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate_summary', methods=['POST'])
@login_required
def api_generate_summary():
    """生成对话摘要"""
    try:
        # 添加详细的请求日志
        app_logger.info(f"收到生成摘要请求，Content-Type: {request.content_type}")
        app_logger.info(f"请求数据: {request.get_data(as_text=True)}")
        
        # 检查Content-Type
        if not request.is_json:
            app_logger.error(f"请求不是JSON格式，Content-Type: {request.content_type}")
            return jsonify({'error': '请求必须是JSON格式'}), 400
        
        data = request.get_json()
        if data is None:
            app_logger.error("无法解析JSON数据")
            return jsonify({'error': '无法解析JSON数据'}), 400
            
        conversation_id = data.get('conversation_id')
        app_logger.info(f"解析到的conversation_id: {conversation_id}")
        
        if not conversation_id:
            return jsonify({'error': '缺少对话ID参数'}), 400
        
        # 调用异步生成摘要函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            summary = loop.run_until_complete(llm.LLM.generate_summary(conversation_id))
        finally:
            loop.close()
        
        if summary:
            # 更新数据库中的摘要
            db.revise_db('UPDATE conversations SET summary = ? WHERE conv_id = ?', (summary, conversation_id))
            return jsonify({'success': True, 'summary': summary})
        else:
            return jsonify({'error': '生成摘要失败'}), 500
            
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'生成摘要时发生错误: {str(e)}'}), 500

@app.route('/api/edit_message', methods=['POST'])
@login_required
def edit_message():
    """编辑消息的processed_content"""
    try:
        data = request.get_json()
        dialog_id = data.get('dialog_id')
        new_content = data.get('content', '').strip()
        
        if not dialog_id:
            return jsonify({'error': '缺少消息ID'}), 400
            
        # 更新数据库中的processed_content
        db.revise_db(
            'UPDATE dialogs SET processed_content = ? WHERE id = ?',
            (new_content, dialog_id)
        )
        
        return jsonify({'success': True, 'message': '消息内容已更新'})
        
    except Exception as e:
        app_logger.error(f"编辑消息失败: {str(e)}")
        return jsonify({'error': f'编辑消息失败: {str(e)}'}), 500

if __name__ == '__main__':
    app_logger.info("启动Web管理界面，地址: http://0.0.0.0:8081")
    app.run(debug=False, host='0.0.0.0', port=8081, use_reloader=False)