/**
 * 通用搜索功能
 */

// 初始化搜索框增强功能
function initSearchEnhancements() {
  const searchForms = document.querySelectorAll('.search-form');
  
  searchForms.forEach(form => {
    const searchInput = form.querySelector('.search-input');
    const clearButton = form.querySelector('.clear-button');
    const searchButton = form.querySelector('.search-button');
    
    if (!searchInput) return;
    
    // 添加搜索输入框动画效果
    searchInput.addEventListener('focus', () => {
      searchInput.parentElement.classList.add('search-focused');
    });
    
    searchInput.addEventListener('blur', () => {
      searchInput.parentElement.classList.remove('search-focused');
    });
    
    // 如果有清除按钮，初始化其功能
    if (clearButton) {
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
      
      // 点击清除按钮时清空输入框并提交表单
      clearButton.addEventListener('click', (e) => {
        e.preventDefault();
        searchInput.value = '';
        form.submit();
      });
    }
    
    // 添加搜索按钮动画效果
    if (searchButton) {
      searchButton.addEventListener('mouseenter', () => {
        searchButton.classList.add('hover');
      });
      
      searchButton.addEventListener('mouseleave', () => {
        searchButton.classList.remove('hover');
      });
    }
    
    // 表单提交时显示加载状态
    form.addEventListener('submit', () => {
      if (searchInput.value.trim()) {
        // 创建并显示加载指示器
        let loadingIndicator = form.querySelector('.search-loading');
        
        if (!loadingIndicator) {
          loadingIndicator = document.createElement('div');
          loadingIndicator.className = 'search-loading';
          form.appendChild(loadingIndicator);
        }
        
        loadingIndicator.classList.add('active');
        
        // 禁用搜索按钮，防止重复提交
        if (searchButton) {
          searchButton.disabled = true;
          const originalText = searchButton.innerHTML;
          searchButton.innerHTML = '<span class="loading-spinner"></span> 搜索中...';
          
          // 存储原始文本以便恢复
          searchButton.dataset.originalText = originalText;
        }
      }
    });
  });
}

// 高亮搜索结果
function highlightSearchResults() {
  // 从URL获取搜索参数
  const urlParams = new URLSearchParams(window.location.search);
  const searchParam = urlParams.get('search');
  
  if (!searchParam) return;
  
  // 需要高亮的元素选择器（根据页面类型调整）
  const elementsToHighlight = [
    '.user-name', '.user-id', '.user-info', 
    '.conversation-user-name', '.conversation-user-id', '.character-badge', '.summary-content',
    '.table-cell', '.table-data', '.data-text'
  ];
  
  // 创建正则表达式，不区分大小写
  const regex = new RegExp(`(${searchParam.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  
  // 遍历所有需要高亮的元素
  elementsToHighlight.forEach(selector => {
    document.querySelectorAll(selector).forEach(element => {
      // 跳过已经包含复杂HTML标签的内容
      if (/<(?!span class="search-highlight")[a-z][\s\S]*>/i.test(element.innerHTML)) return;
      
      // 替换文本为高亮版本
      const originalText = element.textContent;
      const highlightedText = originalText.replace(regex, '<span class="search-highlight">$1</span>');
      
      // 只有当文本实际发生变化时才更新DOM
      if (highlightedText !== originalText) {
        element.innerHTML = highlightedText;
      }
    });
  });
  
  // 添加高亮动画效果
  setTimeout(() => {
    const highlights = document.querySelectorAll('.search-highlight');
    highlights.forEach((highlight, index) => {
      // 错开动画开始时间，创造波浪效果
      setTimeout(() => {
        highlight.style.animation = 'highlight-pulse 2s infinite';
      }, index * 50);
    });
  }, 300);
}

// 初始化过滤标签动画效果
function initFilterTagAnimations() {
  const filterTags = document.querySelectorAll('.filter-tag');
  
  filterTags.forEach(tag => {
    tag.addEventListener('mouseenter', () => {
      tag.style.transform = 'translateY(-2px)';
    });
    
    tag.addEventListener('mouseleave', () => {
      tag.style.transform = '';
    });
    
    // 添加点击波纹效果
    tag.addEventListener('click', (e) => {
      const ripple = document.createElement('span');
      ripple.className = 'filter-tag-ripple';
      ripple.style.left = (e.offsetX) + 'px';
      ripple.style.top = (e.offsetY) + 'px';
      tag.appendChild(ripple);
      
      // 动画结束后移除元素
      setTimeout(() => {
        ripple.remove();
      }, 600);
    });
  });
}

// 页面加载完成后初始化所有功能
document.addEventListener('DOMContentLoaded', () => {
  initSearchEnhancements();
  highlightSearchResults();
  initFilterTagAnimations();
});