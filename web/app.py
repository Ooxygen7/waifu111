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
    
    # 用户统计
    stats['total_users'] = db.query_db('SELECT COUNT(*) FROM users')[0][0] if db.query_db('SELECT COUNT(*) FROM users') else 0
    stats['total_conversations'] = db.query_db('SELECT COUNT(*) FROM conversations')[0][0] if db.query_db('SELECT COUNT(*) FROM conversations') else 0
    stats['total_dialogs'] = db.query_db('SELECT COUNT(*) FROM dialogs')[0][0] if db.query_db('SELECT COUNT(*) FROM dialogs') else 0
    stats['total_groups'] = db.query_db('SELECT COUNT(*) FROM groups')[0][0] if db.query_db('SELECT COUNT(*) FROM groups') else 0
    
    # 今日活跃统计
    today = datetime.now().strftime('%Y-%m-%d')
    today_result = db.query_db("SELECT COUNT(*) FROM dialogs WHERE date(created_at) = ?", (today,))
    stats['today_dialogs'] = today_result[0][0] if today_result else 0
    
    # Token使用统计
    token_stats = db.query_db('SELECT SUM(input_tokens) as input_total, SUM(output_tokens) as output_total FROM users')
    if token_stats and token_stats[0]:
        stats['total_input_tokens'] = token_stats[0][0] or 0
        stats['total_output_tokens'] = token_stats[0][1] or 0
    else:
        stats['total_input_tokens'] = 0
        stats['total_output_tokens'] = 0
    
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
    
    # 获取对话消息
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
                         dialogs=dialogs_list, format_datetime=format_datetime)

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
    
    # 搜索对话消息
    dialogs_data = db.query_db(
        'SELECT d.*, c.character, c.user_id FROM dialogs d LEFT JOIN conversations c ON d.conv_id = c.conv_id WHERE d.raw_content LIKE ? OR d.processed_content LIKE ? ORDER BY d.created_at DESC LIMIT 50',
        (f'%{query}%', f'%{query}%')
    )
    if dialogs_data:
        dialog_columns = ['dialog_id', 'conv_id', 'role', 'raw_content', 'processed_content', 'turn_order', 'created_at', 'character', 'user_id']
        for row in dialogs_data:
            dialog_dict = {dialog_columns[i]: row[i] for i in range(len(dialog_columns))}
            results['dialogs'].append(dialog_dict)
    
    # 搜索用户信息
    users_data = db.query_db(
        'SELECT u.uid, u.first_name, u.last_name, u.user_name, u.create_at, u.conversations as conversations_orig, u.dialog_turns as dialog_turns_orig, u.update_at, u.input_tokens, u.output_tokens, u.account_tier, u.remain_frequency, u.balance, COUNT(DISTINCT c.conv_id) as conversations, SUM(CASE WHEN d.id IS NOT NULL THEN 1 ELSE 0 END) as dialog_turns FROM users u LEFT JOIN conversations c ON u.uid = c.user_id LEFT JOIN dialogs d ON c.conv_id = d.conv_id WHERE u.user_name LIKE ? OR u.first_name LIKE ? OR u.last_name LIKE ? OR CAST(u.uid AS TEXT) LIKE ? GROUP BY u.uid ORDER BY u.create_at DESC LIMIT 50',
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
        'SELECT g.group_id, g.group_name, g.char, g.call_count, g.active, g.update_time, COUNT(DISTINCT gd.msg_id) as dialog_count FROM groups g LEFT JOIN group_dialogs gd ON g.group_id = gd.group_id WHERE g.group_name LIKE ? OR CAST(g.group_id AS TEXT) LIKE ? GROUP BY g.group_id ORDER BY g.update_time DESC LIMIT 50',
        (f'%{query}%', f'%{query}%')
    )
    if groups_data:
        group_columns = ['group_id', 'group_name', 'char', 'call_count', 'active', 'update_time', 'dialog_count']
        for row in groups_data:
            group_dict = {group_columns[i]: row[i] for i in range(len(group_columns))}
            results['groups'].append(group_dict)
    
    # 搜索对话记录
    conversations_data = db.query_db(
        'SELECT c.conv_id, c.user_id, c.character, c.preset, c.summary, c.create_at, c.update_at, u.user_name, u.first_name, u.last_name, COUNT(d.id) as turns FROM conversations c LEFT JOIN users u ON c.user_id = u.uid LEFT JOIN dialogs d ON c.conv_id = d.conv_id WHERE c.character LIKE ? OR c.preset LIKE ? OR c.summary LIKE ? OR u.user_name LIKE ? OR u.first_name LIKE ? OR u.last_name LIKE ? OR CAST(c.user_id AS TEXT) LIKE ? GROUP BY c.conv_id ORDER BY c.update_at DESC LIMIT 50',
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

@app.route('/api/groups/<int:group_id>', methods=['PUT'])
@login_required
def api_group_update(group_id):
    """更新群组信息API"""
    try:
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
            # 添加更新时间
            updates.append('update_time = datetime(\'now\')')
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
        
        base_path = '/Volumes/samsung/project/cyberwaifu_bot'
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
        base_path = '/Volumes/samsung/project/cyberwaifu_bot'
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
        base_path = '/Volumes/samsung/project/cyberwaifu_bot'
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
        
        base_path = '/Volumes/samsung/project/cyberwaifu_bot'
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
        base_path = '/Volumes/samsung/project/cyberwaifu_bot'
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
        data = request.get_json()
        conversation_id = data.get('conversation_id')
        
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

if __name__ == '__main__':
    app_logger.info("启动Web管理界面，地址: http://0.0.0.0:8081")
    app.run(debug=False, host='0.0.0.0', port=8081, use_reloader=False)