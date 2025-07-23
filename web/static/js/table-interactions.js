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
    
    // 注意：表格行点击功能已移至专门的页面JS文件中处理
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