from flask import render_template
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        if session.get('user_role') != 'admin':
            flash('您没有权限访问此页面，请使用管理员账号登录', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def add_buttons_route(app):
    @app.route('/admin/buttons-demo')
    @admin_required
    def admin_buttons_demo():
        """按钮组件示例页面"""
        return render_template('admin_buttons_demo.html')