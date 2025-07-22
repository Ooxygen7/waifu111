/**
 * Table Interactions
 * 表格交互功能
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化表格交互
    initTableInteractions();
});

/**
 * 初始化表格交互功能
 */
function initTableInteractions() {
    // 表格行悬停效果增强
    enhanceTableRowHover();
    
    // 初始化表格排序
    initTableSortable();
    
    // 初始化表格行点击
    initTableRowClick();
}

/**
 * 增强表格行悬停效果
 */
function enhanceTableRowHover() {
    const interactiveRows = document.querySelectorAll('.table-row-interactive');
    
    interactiveRows.forEach(row => {
        // 添加鼠标进入效果
        row.addEventListener('mouseenter', function() {
            // 添加高亮效果
            this.style.zIndex = '1';
            
            // 高亮用户头像
            const avatar = this.querySelector('.user-avatar');
            if (avatar) {
                avatar.style.transform = 'scale(1.1)';
            }
            
            // 高亮消息数量标签
            const messageCount = this.querySelector('.message-count');
            if (messageCount) {
                messageCount.style.transform = 'scale(1.1)';
            }
        });
        
        // 添加鼠标离开效果
        row.addEventListener('mouseleave', function() {
            // 恢复默认状态
            this.style.zIndex = '';
            
            // 恢复用户头像
            const avatar = this.querySelector('.user-avatar');
            if (avatar) {
                avatar.style.transform = '';
            }
            
            // 恢复消息数量标签
            const messageCount = this.querySelector('.message-count');
            if (messageCount) {
                messageCount.style.transform = '';
            }
        });
    });
}

/**
 * 初始化表格排序功能
 */
function initTableSortable() {
    const sortableHeaders = document.querySelectorAll('th.sortable');
    
    sortableHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const table = this.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const index = Array.from(this.parentNode.children).indexOf(this);
            const sortType = this.dataset.sort || 'text';
            
            // 切换排序方向
            const isAsc = !this.classList.contains('sort-asc');
            
            // 更新排序状态
            sortableHeaders.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
            this.classList.add(isAsc ? 'sort-asc' : 'sort-desc');
            
            // 排序行
            rows.sort((a, b) => {
                const cellA = a.querySelectorAll('td')[index];
                const cellB = b.querySelectorAll('td')[index];
                
                if (!cellA || !cellB) return 0;
                
                let valueA, valueB;
                
                // 根据排序类型获取值
                if (sortType === 'number') {
                    // 提取数字
                    valueA = parseInt(cellA.textContent.replace(/[^\d]/g, ''), 10) || 0;
                    valueB = parseInt(cellB.textContent.replace(/[^\d]/g, ''), 10) || 0;
                } else if (sortType === 'user') {
                    // 用户名排序
                    const userNameA = cellA.querySelector('.user-name');
                    const userNameB = cellB.querySelector('.user-name');
                    valueA = userNameA ? userNameA.textContent.trim() : '';
                    valueB = userNameB ? userNameB.textContent.trim() : '';
                } else {
                    // 默认文本排序
                    valueA = cellA.textContent.trim();
                    valueB = cellB.textContent.trim();
                }
                
                // 排序比较
                if (sortType === 'number') {
                    return isAsc ? valueA - valueB : valueB - valueA;
                } else {
                    return isAsc 
                        ? valueA.localeCompare(valueB, 'zh-CN') 
                        : valueB.localeCompare(valueA, 'zh-CN');
                }
            });
            
            // 应用排序动画
            rows.forEach((row, i) => {
                // 设置行的新位置
                row.style.transition = 'none';
                row.style.opacity = '0';
                row.style.transform = 'translateY(20px)';
                
                // 重新添加到表格
                tbody.appendChild(row);
                
                // 触发重绘
                void row.offsetHeight;
                
                // 添加动画
                setTimeout(() => {
                    row.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                    row.style.opacity = '1';
                    row.style.transform = 'translateY(0)';
                }, 50 * i); // 错开动画时间
            });
            
            // 添加排序完成提示
            const sortNotice = document.createElement('div');
            sortNotice.className = 'sort-notice';
            sortNotice.textContent = `已按${this.textContent.trim()}${isAsc ? '升序' : '降序'}排序`;
            sortNotice.style.position = 'absolute';
            sortNotice.style.top = '0';
            sortNotice.style.left = '50%';
            sortNotice.style.transform = 'translateX(-50%) translateY(-100%)';
            sortNotice.style.background = 'rgba(0,0,0,0.7)';
            sortNotice.style.color = 'white';
            sortNotice.style.padding = '8px 16px';
            sortNotice.style.borderRadius = '4px';
            sortNotice.style.zIndex = '100';
            sortNotice.style.opacity = '0';
            sortNotice.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            
            const tableContainer = table.closest('.table-container') || table.parentNode;
            tableContainer.style.position = 'relative';
            tableContainer.appendChild(sortNotice);
            
            // 显示提示
            setTimeout(() => {
                sortNotice.style.opacity = '1';
                sortNotice.style.transform = 'translateX(-50%) translateY(10px)';
                
                // 自动隐藏
                setTimeout(() => {
                    sortNotice.style.opacity = '0';
                    sortNotice.style.transform = 'translateX(-50%) translateY(-100%)';
                    
                    // 移除元素
                    setTimeout(() => {
                        sortNotice.remove();
                    }, 300);
                }, 2000);
            }, 100);
        });
    });
}

/**
 * 初始化表格行点击功能
 */
function initTableRowClick() {
    const interactiveRows = document.querySelectorAll('.table-row-interactive');
    
    interactiveRows.forEach(row => {
        row.addEventListener('click', function(e) {
            // 如果点击的是链接或按钮，不触发行点击
            if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON' || 
                e.target.closest('a') || e.target.closest('button')) {
                return;
            }
            
            // 获取用户ID
            const userIdElement = this.querySelector('.user-id');
            if (userIdElement) {
                const userId = userIdElement.textContent.replace('ID:', '').trim();
                
                // 显示用户详情
                showUserDetails(userId);
            }
        });
    });
}

/**
 * 显示用户详情
 * @param {string} userId - 用户ID
 */
function showUserDetails(userId) {
    // 创建模态框
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'userDetailModal';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-labelledby', 'userDetailModalTitle');
    modal.setAttribute('aria-hidden', 'true');
    
    // 模态框内容
    modal.innerHTML = `
        <div class="modal-dialog modal-dialog-centered" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="userDetailModalTitle">用户详情</h5>
                    <button type="button" class="close-modal" aria-label="关闭">
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <div class="modal-body">
                    <div class="user-detail-loading">
                        <div class="spinner"></div>
                        <p>加载用户数据...</p>
                    </div>
                    <div class="user-detail-content" style="display: none;">
                        <div class="user-detail-header">
                            <div class="user-detail-avatar">👤</div>
                            <div class="user-detail-info">
                                <h3 class="user-detail-name">加载中...</h3>
                                <div class="user-detail-id">ID: ${userId}</div>
                            </div>
                        </div>
                        <div class="user-detail-stats">
                            <div class="user-stat-item">
                                <div class="user-stat-value">-</div>
                                <div class="user-stat-label">总对话数</div>
                            </div>
                            <div class="user-stat-item">
                                <div class="user-stat-value">-</div>
                                <div class="user-stat-label">总消息数</div>
                            </div>
                            <div class="user-stat-item">
                                <div class="user-stat-value">-</div>
                                <div class="user-stat-label">最近活跃</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary close-modal">关闭</button>
                    <a href="/viewer/users/${userId}" class="btn btn-primary">查看详细资料</a>
                </div>
            </div>
        </div>
    `;
    
    // 添加到页面
    document.body.appendChild(modal);
    
    // 显示模态框
    setTimeout(() => {
        modal.classList.add('show');
        
        // 模拟加载数据
        setTimeout(() => {
            const loadingElement = modal.querySelector('.user-detail-loading');
            const contentElement = modal.querySelector('.user-detail-content');
            
            if (loadingElement && contentElement) {
                loadingElement.style.display = 'none';
                contentElement.style.display = 'block';
                
                // 更新用户名
                const nameElement = contentElement.querySelector('.user-detail-name');
                if (nameElement) {
                    // 这里应该是从后端获取数据，这里模拟一下
                    nameElement.textContent = `用户 ${userId}`;
                }
                
                // 更新统计数据
                const statValues = contentElement.querySelectorAll('.user-stat-value');
                if (statValues.length > 0) {
                    // 模拟数据
                    statValues[0].textContent = Math.floor(Math.random() * 50) + 1;
                    statValues[1].textContent = Math.floor(Math.random() * 500) + 10;
                    statValues[2].textContent = '今天';
                    
                    // 添加数字动画
                    animateNumbers('.user-stat-value', 1000, false);
                }
            }
        }, 1000);
    }, 10);
    
    // 关闭按钮事件
    const closeButtons = modal.querySelectorAll('.close-modal');
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            modal.classList.remove('show');
            setTimeout(() => {
                modal.remove();
            }, 300);
        });
    });
    
    // 点击背景关闭
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeButtons[0].click();
        }
    });
    
    // ESC键关闭
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.classList.contains('show')) {
            closeButtons[0].click();
        }
    });
}

// 添加模态框样式
if (!document.getElementById('modal-styles')) {
    const style = document.createElement('style');
    style.id = 'modal-styles';
    style.textContent = `
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1050;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.3s ease, visibility 0.3s ease;
        }
        
        .modal.show {
            opacity: 1;
            visibility: visible;
        }
        
        .modal-dialog {
            max-width: 500px;
            width: 100%;
            margin: 1.75rem auto;
            transform: translateY(-50px);
            transition: transform 0.3s ease;
        }
        
        .modal.show .modal-dialog {
            transform: translateY(0);
        }
        
        .modal-content {
            position: relative;
            background-color: #fff;
            border-radius: 0.5rem;
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
            overflow: hidden;
        }
        
        .modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem;
            border-bottom: 1px solid #e9ecef;
        }
        
        .modal-title {
            margin: 0;
            font-size: 1.25rem;
        }
        
        .close-modal {
            background: transparent;
            border: 0;
            font-size: 1.5rem;
            cursor: pointer;
            padding: 0.5rem;
            margin: -0.5rem;
            color: #6c757d;
        }
        
        .modal-body {
            padding: 1rem;
        }
        
        .modal-footer {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding: 1rem;
            border-top: 1px solid #e9ecef;
            gap: 0.5rem;
        }
        
        .user-detail-loading {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem 0;
        }
        
        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid rgba(0, 0, 0, 0.1);
            border-radius: 50%;
            border-top-color: #4facfe;
            animation: spin 1s linear infinite;
            margin-bottom: 1rem;
        }
        
        .user-detail-header {
            display: flex;
            align-items: center;
            margin-bottom: 1.5rem;
        }
        
        .user-detail-avatar {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            margin-right: 1rem;
        }
        
        .user-detail-name {
            margin: 0 0 0.25rem;
            font-size: 1.25rem;
        }
        
        .user-detail-id {
            color: #6c757d;
            font-size: 0.875rem;
        }
        
        .user-detail-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-top: 1.5rem;
        }
        
        .user-stat-item {
            text-align: center;
            padding: 1rem;
            background-color: #f8f9fa;
            border-radius: 0.5rem;
        }
        
        .user-stat-value {
            font-size: 1.5rem;
            font-weight: bold;
            margin-bottom: 0.25rem;
        }
        
        .user-stat-label {
            font-size: 0.875rem;
            color: #6c757d;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        @media (max-width: 576px) {
            .modal-dialog {
                margin: 0.5rem;
            }
            
            .user-detail-stats {
                grid-template-columns: 1fr;
            }
        }
    `;
    document.head.appendChild(style);
}