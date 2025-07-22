/**
 * 对话搜索和排序功能
 */

// 搜索结果高亮显示
function highlightSearchResults() {
  const searchParam = new URLSearchParams(window.location.search).get('search');
  if (!searchParam) return;
  
  // 需要高亮的元素选择器
  const elementsToHighlight = [
    '.conversation-user-name',
    '.conversation-user-id',
    '.character-badge',
    '.summary-content'
  ];
  
  // 创建正则表达式，不区分大小写
  const regex = new RegExp(`(${searchParam.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  
  // 遍历所有需要高亮的元素
  elementsToHighlight.forEach(selector => {
    document.querySelectorAll(selector).forEach(element => {
      // 跳过已经包含HTML标签的内容
      if (/<[a-z][\s\S]*>/i.test(element.innerHTML) && !element.classList.contains('summary-content')) return;
      
      // 替换文本为高亮版本
      element.innerHTML = element.textContent.replace(regex, '<span class="search-highlight">$1</span>');
    });
  });
  
  // 添加高亮动画效果
  setTimeout(() => {
    const highlights = document.querySelectorAll('.search-highlight');
    highlights.forEach((highlight, index) => {
      // 错开动画开始时间，创造波浪效果
      setTimeout(() => {
        highlight.style.animation = 'highlight-pulse 2s infinite';
      }, index * 100);
    });
  }, 500);
}

// 添加搜索加载状态
function initSearchLoadingState() {
  const searchForm = document.querySelector('.search-form');
  const searchInput = document.querySelector('.search-input');
  
  if (!searchForm || !searchInput) return;
  
  // 创建加载指示器
  const loadingIndicator = document.createElement('div');
  loadingIndicator.className = 'search-loading';
  searchForm.appendChild(loadingIndicator);
  
  // 表单提交时显示加载状态
  searchForm.addEventListener('submit', () => {
    if (searchInput.value.trim()) {
      loadingIndicator.classList.add('active');
      // 禁用搜索按钮，防止重复提交
      const searchButton = searchForm.querySelector('.search-button');
      if (searchButton) {
        searchButton.disabled = true;
        searchButton.textContent = '搜索中...';
        searchButton.classList.add('loading');
      }
    }
  });
}

// 初始化排序下拉菜单的动画效果
function initSortDropdownAnimation() {
  const sortDropdown = document.getElementById('sortDropdown');
  const sortMenu = document.getElementById('sortMenu');
  
  if (!sortDropdown || !sortMenu) return;
  
  // 添加动画类
  sortMenu.classList.add('animate-dropdown');
  
  // 点击排序选项时添加动画效果
  const sortItems = sortMenu.querySelectorAll('.sort-item');
  sortItems.forEach(item => {
    item.addEventListener('click', function(e) {
      // 添加点击波纹效果
      const ripple = document.createElement('span');
      ripple.className = 'sort-item-ripple';
      ripple.style.left = (e.offsetX) + 'px';
      ripple.style.top = (e.offsetY) + 'px';
      this.appendChild(ripple);
      
      // 动画结束后移除元素
      setTimeout(() => {
        ripple.remove();
      }, 600);
    });
  });
}

// 添加当前排序状态指示
function updateSortingIndicators() {
  const urlParams = new URLSearchParams(window.location.search);
  const sortBy = urlParams.get('sort_by');
  const sortOrder = urlParams.get('sort_order');
  
  if (!sortBy) return;
  
  // 更新排序下拉按钮文本
  const sortDropdown = document.getElementById('sortDropdown');
  if (sortDropdown) {
    const sortNames = {
      'conv_id': '对话ID',
      'user_id': '用户',
      'character': '角色',
      'turns': '轮次',
      'create_at': '创建时间',
      'update_at': '更新时间'
    };
    
    const orderIcon = sortOrder === 'asc' ? '↑' : '↓';
    const sortName = sortNames[sortBy] || sortBy;
    
    // 更新排序按钮文本，显示当前排序方式
    const buttonContent = `
      <span class="filter-button-icon">↕️</span>
      ${sortName} ${orderIcon}
    `;
    
    // 保留原始的下拉箭头
    const arrowSpan = sortDropdown.querySelector('.dropdown-arrow');
    if (arrowSpan) {
      sortDropdown.innerHTML = buttonContent;
      sortDropdown.appendChild(arrowSpan);
    } else {
      sortDropdown.innerHTML = buttonContent + '<span class="dropdown-arrow">▼</span>';
    }
  }
  
  // 添加排序状态标签
  const filterContainer = document.querySelector('.filter-container');
  if (filterContainer && sortBy) {
    const existingTag = document.querySelector('.sort-status-tag');
    if (!existingTag) {
      const sortNames = {
        'conv_id': '对话ID',
        'user_id': '用户',
        'character': '角色',
        'turns': '轮次',
        'create_at': '创建时间',
        'update_at': '更新时间'
      };
      
      const orderText = sortOrder === 'asc' ? '升序' : '降序';
      const sortName = sortNames[sortBy] || sortBy;
      
      const sortTag = document.createElement('div');
      sortTag.className = 'filter-tag sort-status-tag';
      sortTag.innerHTML = `
        按${sortName}${orderText}
        <a href="${window.location.pathname}${window.location.search.replace(/[?&]sort_by=[^&]*(&sort_order=[^&]*)?/g, '')}" 
           class="filter-tag-close" aria-label="清除排序">✕</a>
      `;
      
      // 在搜索框后面插入排序标签
      const searchContainer = document.querySelector('.search-container');
      if (searchContainer && searchContainer.nextElementSibling) {
        filterContainer.insertBefore(sortTag, searchContainer.nextElementSibling);
      } else {
        filterContainer.appendChild(sortTag);
      }
    }
  }
}

// 初始化清除按钮功能
function initClearButton() {
  const searchInput = document.querySelector('.search-input');
  const clearButton = document.querySelector('.clear-button');
  
  if (!searchInput || !clearButton) return;
  
  // 输入框有内容时显示清除按钮
  searchInput.addEventListener('input', () => {
    clearButton.style.display = searchInput.value ? 'flex' : 'none';
  });
  
  // 初始状态
  clearButton.style.display = searchInput.value ? 'flex' : 'none';
  
  // 添加清除按钮动画效果
  clearButton.addEventListener('mouseenter', () => {
    clearButton.style.transform = 'scale(1.1)';
  });
  
  clearButton.addEventListener('mouseleave', () => {
    clearButton.style.transform = '';
  });
}

// 添加过滤标签动画效果
function initFilterTagAnimations() {
  const filterTags = document.querySelectorAll('.filter-tag');
  
  filterTags.forEach(tag => {
    tag.addEventListener('mouseenter', () => {
      tag.style.transform = 'translateY(-2px)';
    });
    
    tag.addEventListener('mouseleave', () => {
      tag.style.transform = '';
    });
  });
}

// 页面加载完成后初始化所有功能
document.addEventListener('DOMContentLoaded', () => {
  highlightSearchResults();
  initSearchLoadingState();
  initSortDropdownAnimation();
  updateSortingIndicators();
  initClearButton();
  initFilterTagAnimations();
});