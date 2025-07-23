# 示例页面路由
@app.route('/admin/sample')
@admin_required
def admin_sample():
    """示例页面 - 展示页面头部和主内容区域布局"""
    return render_template('admin_sample.html')