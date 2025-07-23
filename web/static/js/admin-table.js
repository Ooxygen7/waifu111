/**
 * Admin Table Components
 * 管理员表格组件功能
 * 
 * 这个文件提供了管理员页面表格组件的交互功能，包括：
 * - 表格排序
 * - 表格过滤
 * - 表格分页
 * - 响应式表格行为
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有表格功能
    initAdminTables();
});

/**
 * 初始化管理员表格功能
 */
function initAdminTables() {
    // 初始化表格排序
    initTableSorting();
    
    // 初始化表格过滤
    initTableFiltering();
    
    // 初始化表格行交互
    initTableRowInteractions();
    
    // 初始化响应式表格
    initResponsiveTables();
    
    // 初始化表格分页
    initPaginationNavigation();
    
    // 添加表格可访问性支持
    enhanceTableAccessibility();
    
    // 转换Bootstrap表格为新样式
    convertBootstrapTables();
}

/**
 * 转换Bootstrap表格为新样式
 * 这个函数将现有的Bootstrap表格转换为新的样式
 */
function convertBootstrapTables() {
    // 查找所有表格
    const tables = document.querySelectorAll('table.table:not(.admin-table)');
    
    tables.forEach(table => {
        // 添加新的表格类
        table.classList.add('admin-table');
        
        // 处理表格行
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            if (row.classList.contains('table-row-interactive')) {
                row.classList.add('admin-table-row-interactive');
            }
        });
        
        // 处理表格容器
        const tableContainer = table.closest('.table-container');
        if (tableContainer) {
            tableContainer.classList.add('admin-table-container');
        }
        
        // 处理响应式表格
        if (table.closest('.table-responsive')) {
            table.closest('.table-responsive').classList.add('admin-table-responsive');
        }
        
        // 处理表格头部排序
        const sortableHeaders = table.querySelectorAll('th.sortable');
        sortableHeaders.forEach(header => {
            const sortLink = header.querySelector('.sort-link');
            if (sortLink) {
                sortLink.setAttribute('role', 'button');
                if (!sortLink.getAttribute('aria-label')) {
                    sortLink.setAttribute('aria-label', `排序按 ${sortLink.textContent.trim()}`);
                }
            }
        });
        
        // 处理分页容器
        const paginationContainer = table.closest('.card-body')?.querySelector('.pagination-container');
        if (paginationContainer) {
            paginationContainer.classList.add('admin-pagination-container');
            
            // 处理分页项
            const pageItems = paginationContainer.querySelectorAll('.page-item');
            pageItems.forEach(item => {
                item.classList.add('admin-page-item');
            });
            
            // 处理分页信息
            const paginationInfo = paginationContainer.querySelector('.pagination-info');
            if (paginationInfo) {
                paginationInfo.classList.add('admin-pagination-info');
            }
            
            // 处理分页控件
            const pagination = paginationContainer.querySelector('.pagination');
            if (pagination) {
                pagination.classList.add('admin-pagination');
            }
        }
    });
}

/**
 * 初始化表格排序功能
 */
function initTableSorting() {
    const sortableHeaders = document.querySelectorAll('.admin-table th.sortable, .table th.sortable');
    
    sortableHeaders.forEach(header => {
        const sortLink = header.querySelector('.sort-link');
        if (!sortLink) return;
        
        sortLink.addEventListener('click', function(e) {
            e.preventDefault();
            
            const table = header.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const index = Array.from(header.parentNode.children).indexOf(header);
            const sortType = header.dataset.sort || 'text';
            
            // 获取当前排序方向
            let currentDirection = '';
            if (header.classList.contains('sort-asc')) {
                currentDirection = 'asc';
            } else if (header.classList.contains('sort-desc')) {
                currentDirection = 'desc';
            }
            
            // 切换排序方向
            const isAsc = currentDirection !== 'asc';
            
            // 更新排序状态
            sortableHeaders.forEach(h => {
                h.classList.remove('sort-asc', 'sort-desc');
                const indicator = h.querySelector('.sort-indicator');
                if (indicator) {
                    indicator.classList.remove('sort-asc', 'sort-desc');
                    indicator.classList.add('sort-both');
                    
                    // 更新SVG图标（如果存在）
                    const svg = indicator.querySelector('svg');
                    if (svg) {
                        svg.classList.remove('sort-asc', 'sort-desc');
                        svg.classList.add('sort-both');
                    }
                }
            });
            
            header.classList.add(isAsc ? 'sort-asc' : 'sort-desc');
            const indicator = header.querySelector('.sort-indicator');
            if (indicator) {
                indicator.classList.remove('sort-both');
                indicator.classList.add(isAsc ? 'sort-asc' : 'sort-desc');
                
                // 更新SVG图标（如果存在）
                const svg = indicator.querySelector('svg');
                if (svg) {
                    svg.classList.remove('sort-both');
                    svg.classList.add(isAsc ? 'sort-asc' : 'sort-desc');
                    
                    // 更新SVG路径
                    const polyline = svg.querySelector('polyline');
                    if (polyline) {
                        polyline.setAttribute('points', isAsc ? '18 15 12 9 6 15' : '6 9 12 15 18 9');
                    }
                } else {
                    // 如果没有SVG，使用文本指示器
                    indicator.textContent = isAsc ? '↑' : '↓';
                }
            }
            
            // 排序行
            rows.sort((a, b) => {
                const cellA = a.querySelectorAll('td')[index];
                const cellB = b.querySelectorAll('td')[index];
                
                if (!cellA || !cellB) return 0;
                
                let valueA, valueB;
                
                // 根据排序类型获取值
                if (sortType === 'number') {
                    // 提取数字
                    valueA = parseFloat(cellA.textContent.replace(/[^\d.-]/g, '')) || 0;
                    valueB = parseFloat(cellB.textContent.replace(/[^\d.-]/g, '')) || 0;
                } else if (sortType === 'date') {
                    // 日期排序
                    valueA = new Date(cellA.textContent.trim()).getTime() || 0;
                    valueB = new Date(cellB.textContent.trim()).getTime() || 0;
                } else {
                    // 默认文本排序
                    valueA = cellA.textContent.trim();
                    valueB = cellB.textContent.trim();
                }
                
                // 排序比较
                if (sortType === 'number' || sortType === 'date') {
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
                row.style.opacity = '0.5';
                row.style.transform = 'translateY(10px)';
                
                // 重新添加到表格
                tbody.appendChild(row);
                
                // 触发重绘
                void row.offsetHeight;
                
                // 添加动画
                setTimeout(() => {
                    row.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                    row.style.opacity = '1';
                    row.style.transform = 'translateY(0)';
                }, 30 * i); // 错开动画时间
            });
            
            // 添加排序完成提示
            showSortNotification(table, header.textContent.trim(), isAsc);
            
            // 添加可访问性通知
            const liveRegion = document.getElementById('sort-live-region') || createLiveRegion('sort-live-region');
            liveRegion.textContent = `表格已按${header.textContent.trim()}${isAsc ? '升序' : '降序'}排序`;
            
            // 清除通知
            setTimeout(() => {
                liveRegion.textContent = '';
            }, 2000);
        });
    });
}

/**
 * 创建实时区域用于可访问性通知
 * @param {string} id - 元素ID
 * @returns {HTMLElement} - 创建的实时区域元素
 */
function createLiveRegion(id) {
    const liveRegion = document.createElement('div');
    liveRegion.id = id;
    liveRegion.setAttribute('aria-live', 'polite');
    liveRegion.setAttribute('aria-atomic', 'true');
    liveRegion.className = 'sr-only';
    document.body.appendChild(liveRegion);
    return liveRegion;
}

/**
 * 显示排序通知
 */
function showSortNotification(table, columnName, isAsc) {
    const sortNotice = document.createElement('div');
    sortNotice.className = 'sort-notice';
    sortNotice.textContent = `已按${columnName}${isAsc ? '升序' : '降序'}排序`;
    sortNotice.setAttribute('role', 'status');
    sortNotice.setAttribute('aria-live', 'polite');
    
    // 设置样式
    Object.assign(sortNotice.style, {
        position: 'absolute',
        top: '0',
        left: '50%',
        transform: 'translateX(-50%) translateY(-100%)',
        background: 'var(--primary-color)',
        color: 'white',
        padding: '8px 16px',
        borderRadius: 'var(--border-radius-md)',
        zIndex: '100',
        opacity: '0',
        transition: 'opacity 0.3s ease, transform 0.3s ease',
        boxShadow: 'var(--shadow-md)'
    });
    
    const tableContainer = table.closest('.table-container, .admin-table-container') || table.parentNode;
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
}

/**
 * 初始化表格过滤功能
 */
function initTableFiltering() {
    const filterButtons = document.querySelectorAll('.filter-button');
    
    filterButtons.forEach(button => {
        const dropdown = button.nextElementSibling;
        if (!dropdown || !dropdown.classList.contains('filter-dropdown')) return;
        
        // 点击按钮显示/隐藏下拉菜单
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // 切换下拉菜单显示状态
            const isVisible = dropdown.style.display === 'block';
            
            // 先关闭所有打开的下拉菜单
            document.querySelectorAll('.filter-dropdown').forEach(menu => {
                menu.style.display = 'none';
                const btn = menu.previousElementSibling;
                if (btn && btn.classList.contains('filter-button')) {
                    btn.classList.remove('active');
                    btn.setAttribute('aria-expanded', 'false');
                }
            });
            
            // 如果当前菜单之前不是显示状态，则显示它
            if (!isVisible) {
                dropdown.style.display = 'block';
                dropdown.style.animation = 'filter-dropdown-fade-in 0.2s ease-out forwards';
                button.classList.add('active');
                button.setAttribute('aria-expanded', 'true');
                
                // 确保下拉菜单在视口内
                const dropdownRect = dropdown.getBoundingClientRect();
                const viewportWidth = window.innerWidth;
                
                if (dropdownRect.right > viewportWidth) {
                    dropdown.style.left = 'auto';
                    dropdown.style.right = '0';
                }
            }
        });
        
        // 添加键盘导航支持
        button.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
    });
    
    // 点击页面其他区域关闭下拉菜单
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.filter-container')) {
            document.querySelectorAll('.filter-dropdown').forEach(dropdown => {
                dropdown.style.display = 'none';
                const button = dropdown.previousElementSibling;
                if (button && button.classList.contains('filter-button')) {
                    button.classList.remove('active');
                    button.setAttribute('aria-expanded', 'false');
                }
            });
        }
    });
    
    // 初始化过滤选项点击事件
    const filterOptions = document.querySelectorAll('.filter-option');
    filterOptions.forEach(option => {
        option.addEventListener('click', function() {
            this.classList.toggle('selected');
            
            // 添加选择动画效果
            this.style.transform = 'scale(1.05)';
            setTimeout(() => {
                this.style.transform = '';
            }, 200);
            
            // 添加波纹效果
            const ripple = document.createElement('span');
            ripple.className = 'filter-option-ripple';
            ripple.style.position = 'absolute';
            ripple.style.top = '0';
            ripple.style.left = '0';
            ripple.style.width = '100%';
            ripple.style.height = '100%';
            ripple.style.backgroundColor = 'rgba(255, 255, 255, 0.3)';
            ripple.style.borderRadius = 'inherit';
            ripple.style.opacity = '0';
            ripple.style.transform = 'scale(0)';
            ripple.style.animation = 'filter-option-ripple 0.6s ease-out';
            
            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
        
        // 添加键盘导航支持
        option.setAttribute('tabindex', '0');
        option.setAttribute('role', 'checkbox');
        option.setAttribute('aria-checked', option.classList.contains('selected') ? 'true' : 'false');
        
        option.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
                this.setAttribute('aria-checked', this.classList.contains('selected') ? 'true' : 'false');
            }
        });
    });
    
    // 添加CSS动画样式
    if (!document.getElementById('filter-animations-style')) {
        const style = document.createElement('style');
        style.id = 'filter-animations-style';
        style.textContent = `
            @keyframes filter-option-ripple {
                0% {
                    transform: scale(0);
                    opacity: 1;
                }
                100% {
                    transform: scale(4);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * 初始化表格行交互
 */
function initTableRowInteractions() {
    const interactiveRows = document.querySelectorAll('.admin-table-row-interactive, .table-row-interactive');
    
    interactiveRows.forEach(row => {
        // 添加点击事件
        row.addEventListener('click', function(e) {
            // 如果点击的是按钮或链接，不触发行点击事件
            if (e.target.closest('a, button, .btn')) return;
            
            // 获取行的数据ID
            const rowId = this.dataset.id;
            if (!rowId) return;
            
            // 获取详情页URL
            const detailUrl = this.dataset.url;
            if (detailUrl) {
                window.location.href = detailUrl;
            }
            
            // 添加点击波纹效果
            const ripple = document.createElement('div');
            ripple.className = 'table-row-ripple';
            ripple.style.position = 'absolute';
            ripple.style.width = '20px';
            ripple.style.height = '20px';
            ripple.style.borderRadius = '50%';
            ripple.style.backgroundColor = 'rgba(79, 172, 254, 0.3)';
            ripple.style.transform = 'scale(0)';
            ripple.style.animation = 'ripple 0.6s linear';
            ripple.style.left = e.clientX - this.getBoundingClientRect().left + 'px';
            ripple.style.top = e.clientY - this.getBoundingClientRect().top + 'px';
            
            this.style.overflow = 'hidden';
            this.style.position = 'relative';
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
        
        // 添加键盘导航支持
        row.setAttribute('tabindex', '0');
        row.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                
                // 模拟点击事件
                const clickEvent = new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    view: window
                });
                this.dispatchEvent(clickEvent);
            }
        });
        
        // 添加鼠标进入效果
        row.addEventListener('mouseenter', function() {
            // 添加高亮效果
            this.style.zIndex = '1';
            
            // 高亮操作按钮
            const actionButtons = this.querySelectorAll('.btn-icon, .btn-sm');
            actionButtons.forEach(btn => {
                btn.style.opacity = '1';
                btn.style.transform = 'scale(1.05)';
            });
        });
        
        // 添加鼠标离开效果
        row.addEventListener('mouseleave', function() {
            // 恢复默认状态
            this.style.zIndex = '';
            
            // 恢复操作按钮
            const actionButtons = this.querySelectorAll('.btn-icon, .btn-sm');
            actionButtons.forEach(btn => {
                btn.style.opacity = '';
                btn.style.transform = '';
            });
        });
    });
    
    // 添加CSS动画样式
    if (!document.getElementById('table-row-animations-style')) {
        const style = document.createElement('style');
        style.id = 'table-row-animations-style';
        style.textContent = `
            @keyframes ripple {
                0% {
                    transform: scale(0);
                    opacity: 1;
                }
                100% {
                    transform: scale(40);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * 初始化响应式表格
 */
function initResponsiveTables() {
    // 检查是否需要应用响应式表格
    const tables = document.querySelectorAll('.admin-table-responsive-sm table, .table-responsive-sm table');
    
    tables.forEach(table => {
        // 获取表头
        const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
        
        // 为每个单元格添加data-label属性
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            cells.forEach((cell, index) => {
                if (index < headers.length) {
                    cell.setAttribute('data-label', headers[index]);
                }
            });
        });
        
        // 添加响应式类
        table.classList.add('admin-table-stack-sm');
    });
    
    // 监听窗口大小变化
    window.addEventListener('resize', function() {
        const isMobile = window.innerWidth < 768;
        
        // 在移动视图下添加额外的可访问性支持
        if (isMobile) {
            tables.forEach(table => {
                if (!table.classList.contains('admin-table-stack-sm')) {
                    table.classList.add('admin-table-stack-sm');
                }
            });
        } else {
            tables.forEach(table => {
                if (table.classList.contains('admin-table-stack-sm') && 
                    !table.closest('.admin-table-responsive-sm') && 
                    !table.closest('.table-responsive-sm')) {
                    table.classList.remove('admin-table-stack-sm');
                }
            });
        }
    });
}

/**
 * 初始化分页导航
 */
function initPaginationNavigation() {
    const paginationItems = document.querySelectorAll('.page-item, .admin-page-item');
    
    paginationItems.forEach(item => {
        // 添加点击波纹效果
        item.addEventListener('click', function(e) {
            // 如果是禁用状态或当前页，不添加效果
            if (this.classList.contains('disabled') || this.classList.contains('active')) return;
            
            // 创建波纹元素
            const ripple = document.createElement('span');
            ripple.className = 'page-ripple';
            this.appendChild(ripple);
            
            // 动画结束后移除元素
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
        
        // 添加键盘导航支持
        if (!item.hasAttribute('tabindex')) {
            item.setAttribute('tabindex', '0');
        }
        
        item.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                
                // 如果是链接，模拟点击
                const link = this.querySelector('a');
                if (link) {
                    link.click();
                } else {
                    this.click();
                }
            }
        });
    });
}

/**
 * 增强表格可访问性
 */
function enhanceTableAccessibility() {
    // 为表格添加ARIA属性
    const tables = document.querySelectorAll('.admin-table, .table');
    
    tables.forEach(table => {
        // 如果表格没有caption，添加一个隐藏的caption
        if (!table.querySelector('caption')) {
            const caption = document.createElement('caption');
            caption.className = 'sr-only';
            caption.textContent = '数据表格';
            table.prepend(caption);
        }
        
        // 为表格添加role属性
        if (!table.hasAttribute('role')) {
            table.setAttribute('role', 'grid');
        }
        
        // 为表头行添加role属性
        const headerRow = table.querySelector('thead tr');
        if (headerRow && !headerRow.hasAttribute('role')) {
            headerRow.setAttribute('role', 'row');
        }
        
        // 为表头单元格添加role属性
        const headerCells = table.querySelectorAll('thead th');
        headerCells.forEach(cell => {
            if (!cell.hasAttribute('role')) {
                cell.setAttribute('role', 'columnheader');
            }
            
            // 如果是可排序的，添加aria-sort属性
            if (cell.classList.contains('sortable')) {
                if (cell.classList.contains('sort-asc')) {
                    cell.setAttribute('aria-sort', 'ascending');
                } else if (cell.classList.contains('sort-desc')) {
                    cell.setAttribute('aria-sort', 'descending');
                } else {
                    cell.setAttribute('aria-sort', 'none');
                }
            }
        });
        
        // 为表格行添加role属性
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            if (!row.hasAttribute('role')) {
                row.setAttribute('role', 'row');
            }
        });
        
        // 为表格单元格添加role属性
        const cells = table.querySelectorAll('tbody td');
        cells.forEach(cell => {
            if (!cell.hasAttribute('role')) {
                cell.setAttribute('role', 'gridcell');
            }
        });
    });
    
    // 为分页导航添加ARIA属性
    const paginationContainers = document.querySelectorAll('.pagination-container, .admin-pagination-container');
    
    paginationContainers.forEach(container => {
        const pagination = container.querySelector('.pagination, .admin-pagination');
        if (!pagination) return;
        
        // 设置ARIA属性
        pagination.setAttribute('role', 'navigation');
        pagination.setAttribute('aria-label', '分页导航');
        
        // 为页码项添加可访问性支持
        const pageItems = pagination.querySelectorAll('.page-item, .admin-page-item');
        pageItems.forEach(item => {
            // 如果是当前页
            if (item.classList.contains('active')) {
                item.setAttribute('aria-current', 'page');
            }
        });
    });
}