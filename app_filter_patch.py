@app.route('/viewer/users')
@viewer_required
def viewer_users():
    """浏览者用户列表页面（排除管理员和群聊）"""
    admin_ids = get_admin_ids()
    admin_ids_str = ','.join(map(str, admin_ids))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    search_term = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'create_at')
    sort_order = request.args.get('sort_order', 'desc')

    # 处理筛选参数
    filter_params = {}
    filter_date = request.args.get('filter_date')
    filter_conversations = request.args.get('filter_conversations')
    
    query = f'SELECT * FROM users WHERE uid NOT IN ({admin_ids_str})'
    params = []
    
    # 添加搜索条件
    if search_term:
        query += ' AND (uid LIKE ? OR user_name LIKE ? OR first_name LIKE ? OR last_name LIKE ?)'
        search_param = f'%{search_term}%'
        params.extend([search_param, search_param, search_param, search_param])

    # 添加日期筛选条件
    if filter_date:
        filter_params['filter_date'] = filter_date
        if filter_date == 'today':
            query += " AND date(create_at) = date('now')"
        elif filter_date == 'week':
            query += " AND date(create_at) >= date('now', '-7 days')"
        elif filter_date == 'month':
            query += " AND date(create_at) >= date('now', '-30 days')"
        elif filter_date == 'year':
            query += " AND date(create_at) >= date('now', '-365 days')"

    # 添加对话数筛选条件
    if filter_conversations:
        filter_params['filter_conversations'] = filter_conversations
        if filter_conversations == '0':
            query += " AND (conversations = 0 OR conversations IS NULL)"
        elif filter_conversations == '1-10':
            query += " AND conversations BETWEEN 1 AND 10"
        elif filter_conversations == '10+':
            query += " AND conversations > 10"
        elif filter_conversations == '50+':
            query += " AND conversations > 50"

    # 添加排序条件
    if sort_by and sort_order:
        query += f' ORDER BY {sort_by} {sort_order}'

    # 添加分页
    query += ' LIMIT ? OFFSET ?'
    params.extend([per_page, offset])

    users_data = db.query_db(query, tuple(params))

    # 计算总数
    count_query = f'SELECT COUNT(*) FROM users WHERE uid NOT IN ({admin_ids_str})'
    count_params = []
    
    # 添加搜索条件到计数查询
    if search_term:
        count_query += ' AND (uid LIKE ? OR user_name LIKE ? OR first_name LIKE ? OR last_name LIKE ?)'
        count_params.extend([search_param, search_param, search_param, search_param])

    # 添加日期筛选条件到计数查询
    if filter_date:
        if filter_date == 'today':
            count_query += " AND date(create_at) = date('now')"
        elif filter_date == 'week':
            count_query += " AND date(create_at) >= date('now', '-7 days')"
        elif filter_date == 'month':
            count_query += " AND date(create_at) >= date('now', '-30 days')"
        elif filter_date == 'year':
            count_query += " AND date(create_at) >= date('now', '-365 days')"

    # 添加对话数筛选条件到计数查询
    if filter_conversations:
        if filter_conversations == '0':
            count_query += " AND (conversations = 0 OR conversations IS NULL)"
        elif filter_conversations == '1-10':
            count_query += " AND conversations BETWEEN 1 AND 10"
        elif filter_conversations == '10+':
            count_query += " AND conversations > 10"
        elif filter_conversations == '50+':
            count_query += " AND conversations > 50"

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

    return render_template('viewer_users.html', users=users_list, page=page, total_pages=total_pages, 
                         format_datetime=format_datetime, search_term=search_term, 
                         sort_by=sort_by, sort_order=sort_order, next_sort_order=next_sort_order, 
                         per_page=per_page, total_users=total_users, filter_params=filter_params)