/**
 * 排序功能增强
 */

// 初始化排序下拉菜单的动画效果
function initSortDropdownAnimation() {
  const sortDropdowns = document.querySelectorAll('.sort-dropdown');
  
  sortDropdowns.forEach(dropdown => {
    const button = dropdown.querySelector('.filter-button');
    const menu = dropdown.querySelector('.sort-menu');
    
    if (!button || !menu) return;
    
    // 添加动画类
    menu.classList.add('animate-dropdown');
    
    // 点击按钮切换菜单显示状态
    button.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      
      const isExpanded = menu.classList.toggle('show');
      button.setAttribute('aria-expanded', isExpanded);
      
      // 添加按钮点击波纹效果
      const ripple = document.createElement('span');
      ripple.className = 'button-ripple';
      ripple.style.left = (e.offsetX) + 'px';
      ripple.style.top = (e.offsetY) + 'px';
      button.appendChild(ripple);
      
      // 动画结束后移除元素
      setTimeout(() => {
        ripple.remove();
      }, 600);
      
      // 关闭其他打开的下拉菜单
      document.querySelectorAll('.sort-menu.show').forEach(openMenu => {
        if (openMenu !== menu) {
          openMenu.classList.remove('show');
          const openButton = openMenu.closest('.sort-dropdown').querySelector('.filter-button');
          if (openButton) {
            openButton.setAttribute('aria-expanded', 'false');
          }
        }
      });
    });
    
    // 点击排序选项时添加动画效果
    const sortItems = menu.querySelectorAll('.sort-item');
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
      
      // 添加键盘导航支持
      item.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          item.click();
        }
      });
    });
  });
  
  // 点击外部关闭排序菜单
  document.addEventListener('click', (e) => {
    document.querySelectorAll('.sort-dropdown').forEach(dropdown => {
      const button = dropdown.querySelector('.filter-button');
      const menu = dropdown.querySelector('.sort-menu');
      
      if (button && menu && !dropdown.contains(e.target)) {
        menu.classList.remove('show');
        button.setAttribute('aria-expanded', 'false');
      }
    });
  });
  
  // 添加键盘导航支持
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.sort-menu.show').forEach(menu => {
        menu.classList.remove('show');
        const button = menu.closest('.sort-dropdown').querySelector('.filter-button');
        if (button) {
          button.setAttribute('aria-expanded', 'false');
        }
      });
    }
  });
}

// 添加当前排序状态指示
function updateSortingIndicators() {
  const urlParams = new URLSearchParams(window.location.search);
  const sortBy = urlParams.get('sort_by');
  const sortOrder = urlParams.get('sort_order');
  
  if (!sortBy) return;
  
  // 更新排序下拉按钮文本
  const sortDropdowns = document.querySelectorAll('.sort-dropdown');
  
  sortDropdowns.forEach(dropdown => {
    const button = dropdown.querySelector('.filter-button');
    if (!button) return;
    
    const sortNames = {
      'conv_id': '对话ID',
      'user_id': '用户',
      'character': '角色',
      'turns': '轮次',
      'create_at': '创建时间',
      'update_at': '更新时间',
      'name': '名称',
      'id': 'ID',
      'date': '日期',
      'status': '状态'
    };
    
    const orderIcon = sortOrder === 'asc' ? '↑' : '↓';
    const sortName = sortNames[sortBy] || sortBy;
    
    // 更新排序按钮文本，显示当前排序方式
    const buttonContent = `
      <span class="filter-button-icon">↕️</span>
      ${sortName} ${orderIcon}
    `;
    
    // 保留原始的下拉箭头
    const arrowSpan = button.querySelector('.dropdown-arrow');
    if (arrowSpan) {
      button.innerHTML = buttonContent;
      button.appendChild(arrowSpan);
    } else {
      button.innerHTML = buttonContent + '<span class="dropdown-arrow">▼</span>';
    }
  });
  
  // 添加排序状态标签
  const filterContainers = document.querySelectorAll('.filter-container');
  
  filterContainers.forEach(container => {
    if (!container || !sortBy) return;
    
    const existingTag = container.querySelector('.sort-status-tag');
    if (!existingTag) {
      const sortNames = {
        'conv_id': '对话ID',
        'user_id': '用户',
        'character': '角色',
        'turns': '轮次',
        'create_at': '创建时间',
        'update_at': '更新时间',
        'name': '名称',
        'id': 'ID',
        'date': '日期',
        'status': '状态'
      };
      
      const orderText = sortOrder === 'asc' ? '升序' : '降序';
      const sortName = sortNames[sortBy] || sortBy;
      
      const sortTag = document.createElement('div');
      sortTag.className = 'filter-tag sort-status-tag';
      
      // 构建清除排序的URL
      const currentUrl = new URL(window.location.href);
      currentUrl.searchParams.delete('sort_by');
      currentUrl.searchParams.delete('sort_order');
      
      sortTag.innerHTML = `
        按${sortName}${orderText}
        <a href="${currentUrl.toString()}" 
           class="filter-tag-close" aria-label="清除排序">✕</a>
      `;
      
      // 在搜索框后面插入排序标签
      const searchContainer = container.querySelector('.search-container');
      if (searchContainer && searchContainer.nextElementSibling) {
        container.insertBefore(sortTag, searchContainer.nextElementSibling);
      } else {
        container.appendChild(sortTag);
      }
    }
  });
}

// 页面加载完成后初始化所有功能
document.addEventListener('DOMContentLoaded', () => {
  initSortDropdownAnimation();
  updateSortingIndicators();
});