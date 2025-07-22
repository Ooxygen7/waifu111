/**
 * User Filtering Functionality
 * 用户筛选功能
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化筛选功能
    initUserFiltering();
});

/**
 * 初始化用户筛选功能
 */
function initUserFiltering() {
    const filterButton = document.querySelector('.filter-button');
    const filterDropdown = document.querySelector('.filter-dropdown');
    const filterOptions = document.querySelectorAll('.filter-option');
    const filterTags = document.querySelector('.filter-tags');
    const clearFiltersBtn = document.getElementById('clear-filters');
    const applyFiltersBtn = document.getElementById('apply-filters');
    
    if (!filterButton || !filterDropdown) {
        console.warn('筛选按钮或下拉菜单不存在');
        return;
    }
    
    // 存储当前选中的筛选条件
    const selectedFilters = {};
    
    // 从URL获取当前筛选条件
    const urlParams = new URLSearchParams(window.location.search);
    for (const [key, value] of urlParams.entries()) {
        if (key.startsWith('filter_')) {
            const filterKey = key.replace('filter_', '');
            selectedFilters[filterKey] = value;
            
            // 标记对应的选项为选中状态
            const option = document.querySelector(`.filter-option[data-key="${filterKey}"][data-value="${value}"]`);
            if (option) {
                option.classList.add('selected');
            }
        }
    }
    
    // 显示当前筛选标签
    updateFilterTags(selectedFilters);
    
    // 筛选按钮点击事件
    filterButton.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        console.log('筛选按钮被点击');
        
        // 简单地切换下拉菜单的显示状态
        if (filterDropdown.style.display === 'block') {
            filterDropdown.style.display = 'none';
            filterButton.classList.remove('active');
        } else {
            filterDropdown.style.display = 'block';
            filterButton.classList.add('active');
            
            // 确保下拉菜单在视口内
            const dropdownRect = filterDropdown.getBoundingClientRect();
            const viewportWidth = window.innerWidth;
            
            if (dropdownRect.right > viewportWidth) {
                filterDropdown.style.left = 'auto';
                filterDropdown.style.right = '0';
            }
        }
    });
    
    // 筛选选项点击事件
    filterOptions.forEach(option => {
        option.addEventListener('click', function() {
            const key = this.dataset.key;
            const value = this.dataset.value;
            
            // 切换选中状态
            this.classList.toggle('selected');
            
            // 同一组中只能选择一个选项
            if (this.classList.contains('selected')) {
                // 取消同组其他选项的选中状态
                document.querySelectorAll(`.filter-option[data-key="${key}"]`).forEach(opt => {
                    if (opt !== this) {
                        opt.classList.remove('selected');
                    }
                });
                
                // 更新选中的筛选条件
                selectedFilters[key] = value;
            } else {
                // 移除该筛选条件
                delete selectedFilters[key];
            }
            
            // 添加选择动画效果
            this.style.transform = 'scale(1.05)';
            setTimeout(() => {
                this.style.transform = '';
            }, 200);
        });
    });
    
    // 应用筛选按钮点击事件
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', function() {
            applyFilters(selectedFilters);
        });
    }
    
    // 清除筛选按钮点击事件
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', function() {
            // 清除所有选中状态
            filterOptions.forEach(option => {
                option.classList.remove('selected');
            });
            
            // 清空选中的筛选条件
            Object.keys(selectedFilters).forEach(key => {
                delete selectedFilters[key];
            });
            
            // 应用空筛选
            applyFilters({});
        });
    }
    
    // 点击页面其他区域关闭筛选下拉菜单
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.filter-container') && filterDropdown.style.display === 'block') {
            filterDropdown.style.display = 'none';
            filterButton.setAttribute('aria-expanded', 'false');
            filterButton.classList.remove('active');
        }
    });
    
    // 添加筛选标签点击事件
    if (filterTags) {
        filterTags.addEventListener('click', function(e) {
            const filterTag = e.target.closest('.filter-tag');
            if (filterTag) {
                const key = filterTag.dataset.key;
                
                if (key) {
                    // 移除该筛选条件
                    delete selectedFilters[key];
                    
                    // 取消对应选项的选中状态
                    document.querySelectorAll(`.filter-option[data-key="${key}"]`).forEach(opt => {
                        opt.classList.remove('selected');
                    });
                    
                    // 应用更新后的筛选
                    applyFilters(selectedFilters);
                }
            }
        });
    }
}

/**
 * 应用筛选条件
 * @param {Object} filters - 筛选条件对象
 */
function applyFilters(filters) {
    console.log('应用筛选条件:', filters);
    
    // 获取当前URL并移除现有的筛选参数
    const url = new URL(window.location.href);
    const params = url.searchParams;
    
    // 移除现有的筛选参数
    for (const key of [...params.keys()]) {
        if (key.startsWith('filter_')) {
            params.delete(key);
        }
    }
    
    // 添加新的筛选参数
    for (const [key, value] of Object.entries(filters)) {
        params.set(`filter_${key}`, value);
    }
    
    // 保留搜索词和排序参数
    const search = params.get('search') || '';
    const sort_by = params.get('sort_by') || 'create_at';
    const sort_order = params.get('sort_order') || 'desc';
    
    // 重置页码为1，因为筛选条件改变了
    params.set('page', '1');
    
    // 确保其他参数存在
    if (search) params.set('search', search);
    if (sort_by) params.set('sort_by', sort_by);
    if (sort_order) params.set('sort_order', sort_order);
    
    // 构建新的URL
    const newUrl = url.toString();
    console.log('跳转到新URL:', newUrl);
    
    // 跳转到筛选后的URL
    window.location.href = newUrl;
}

/**
 * 更新筛选标签显示
 * @param {Object} filters - 筛选条件对象
 */
function updateFilterTags(filters) {
    const filterTags = document.querySelector('.filter-tags');
    if (!filterTags) return;
    
    // 清空现有标签
    filterTags.innerHTML = '';
    
    // 如果没有筛选条件，则不显示标签
    if (Object.keys(filters).length === 0) return;
    
    // 添加筛选标签
    for (const [key, value] of Object.entries(filters)) {
        const tag = document.createElement('div');
        tag.className = 'filter-tag';
        tag.dataset.key = key;
        
        // 根据筛选类型设置标签文本
        let tagText = '';
        if (key === 'date') {
            switch (value) {
                case 'today': tagText = '今天注册'; break;
                case 'week': tagText = '本周注册'; break;
                case 'month': tagText = '本月注册'; break;
                case 'year': tagText = '今年注册'; break;
                default: tagText = `注册时间: ${value}`;
            }
        } else if (key === 'conversations') {
            switch (value) {
                case '0': tagText = '无对话'; break;
                case '1-10': tagText = '1-10次对话'; break;
                case '10+': tagText = '10+次对话'; break;
                case '50+': tagText = '50+次对话'; break;
                default: tagText = `对话数: ${value}`;
            }
        } else {
            tagText = `${key}: ${value}`;
        }
        
        tag.innerHTML = `
            ${tagText}
            <span class="filter-tag-close">✕</span>
        `;
        
        filterTags.appendChild(tag);
    }
}