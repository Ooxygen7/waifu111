/**
 * Admin Pagination Components
 * 管理员分页组件功能
 * 
 * 这个文件提供了管理员页面分页组件的交互功能，包括：
 * - 分页导航增强
 * - 分页跳转功能
 * - 分页可访问性支持
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化分页功能
    initAdminPagination();
});

/**
 * 初始化管理员分页功能
 */
function initAdminPagination() {
    // 初始化分页导航
    initPaginationNavigation();
    
    // 初始化分页跳转
    initPaginationJump();
    
    // 添加分页可访问性支持
    enhancePaginationAccessibility();
}

/**
 * 初始化分页导航
 */
function initPaginationNavigation() {
    const paginationItems = document.querySelectorAll('.page-item');
    
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
    });
}

/**
 * 初始化分页跳转功能
 */
function initPaginationJump() {
    const pageGotoForms = document.querySelectorAll('.page-goto');
    
    pageGotoForms.forEach(form => {
        const input = form.querySelector('.page-goto-input');
        const button = form.querySelector('.page-goto-btn');
        
        if (!input || !button) return;
        
        // 按钮点击事件
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const pageNum = parseInt(input.value);
            if (isNaN(pageNum) || pageNum < 1) {
                // 输入无效
                input.classList.add('invalid');
                setTimeout(() => {
                    input.classList.remove('invalid');
                }, 1000);
                return;
            }
            
            // 构建跳转URL
            const url = new URL(window.location.href);
            url.searchParams.set('page', pageNum);
            window.location.href = url.toString();
        });
        
        // 输入框回车事件
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                button.click();
            }
        });
    });
}

/**
 * 增强分页可访问性
 */
function enhancePaginationAccessibility() {
    const paginationContainers = document.querySelectorAll('.pagination-container');
    
    paginationContainers.forEach(container => {
        const pagination = container.querySelector('.pagination');
        if (!pagination) return;
        
        // 设置ARIA属性
        pagination.setAttribute('role', 'navigation');
        pagination.setAttribute('aria-label', '分页导航');
        
        // 为页码项添加可访问性支持
        const pageItems = pagination.querySelectorAll('.page-item');
        pageItems.forEach(item => {
            // 如果是当前页
            if (item.classList.contains('active')) {
                item.setAttribute('aria-current', 'page');
            }
            
            // 添加键盘导航支持
            item.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.click();
                }
            });
        });
    });
}