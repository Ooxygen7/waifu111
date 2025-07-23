/**
 * 管理员按钮交互脚本
 * Admin Button Interactions Script
 */

document.addEventListener('DOMContentLoaded', function() {
  // 初始化按钮加载状态
  initLoadingButtons();
  
  // 初始化工具栏下拉菜单
  initToolbarDropdowns();
  
  // 初始化按钮波纹效果
  initRippleEffect();
  
  // 初始化按钮组切换
  initButtonGroupToggle();
});

/**
 * 初始化按钮加载状态
 */
function initLoadingButtons() {
  const loadingButtons = document.querySelectorAll('[data-loading]');
  
  loadingButtons.forEach(button => {
    button.addEventListener('click', function(event) {
      // 如果按钮已经处于加载状态，则不执行操作
      if (button.classList.contains('loading')) {
        return;
      }
      
      // 获取加载时间（毫秒）
      const loadingTime = button.getAttribute('data-loading-time') || 2000;
      
      // 添加加载状态
      button.classList.add('loading');
      button.disabled = true;
      
      // 保存原始文本
      const originalText = button.textContent;
      
      // 设置超时，恢复按钮状态
      setTimeout(() => {
        button.classList.remove('loading');
        button.disabled = false;
        button.textContent = originalText;
        
        // 触发加载完成事件
        const loadedEvent = new CustomEvent('button:loaded', {
          bubbles: true,
          detail: { button }
        });
        button.dispatchEvent(loadedEvent);
      }, parseInt(loadingTime));
      
      // 触发加载开始事件
      const loadingEvent = new CustomEvent('button:loading', {
        bubbles: true,
        detail: { button }
      });
      button.dispatchEvent(loadingEvent);
    });
  });
}

/**
 * 初始化工具栏下拉菜单
 */
function initToolbarDropdowns() {
  const dropdownButtons = document.querySelectorAll('.toolbar .dropdown-toggle');
  
  dropdownButtons.forEach(button => {
    const dropdownMenu = button.nextElementSibling;
    
    if (!dropdownMenu || !dropdownMenu.classList.contains('dropdown-menu')) {
      return;
    }
    
    // 点击按钮切换下拉菜单
    button.addEventListener('click', function(event) {
      event.preventDefault();
      event.stopPropagation();
      
      // 关闭其他打开的下拉菜单
      document.querySelectorAll('.toolbar .dropdown-menu.show').forEach(menu => {
        if (menu !== dropdownMenu) {
          menu.classList.remove('show');
          menu.previousElementSibling.setAttribute('aria-expanded', 'false');
        }
      });
      
      // 切换当前下拉菜单
      dropdownMenu.classList.toggle('show');
      button.setAttribute('aria-expanded', dropdownMenu.classList.contains('show'));
    });
    
    // 点击下拉菜单项
    dropdownMenu.querySelectorAll('.dropdown-item').forEach(item => {
      item.addEventListener('click', function() {
        dropdownMenu.classList.remove('show');
        button.setAttribute('aria-expanded', 'false');
      });
    });
  });
  
  // 点击页面其他区域关闭下拉菜单
  document.addEventListener('click', function(event) {
    if (!event.target.closest('.toolbar .dropdown-toggle') && 
        !event.target.closest('.toolbar .dropdown-menu')) {
      document.querySelectorAll('.toolbar .dropdown-menu.show').forEach(menu => {
        menu.classList.remove('show');
        menu.previousElementSibling.setAttribute('aria-expanded', 'false');
      });
    }
  });
}

/**
 * 初始化按钮波纹效果
 */
function initRippleEffect() {
  const buttons = document.querySelectorAll('.btn:not(.btn-link):not(.btn-text)');
  
  buttons.forEach(button => {
    button.addEventListener('mousedown', function(event) {
      const rect = button.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      
      const ripple = document.createElement('span');
      ripple.className = 'btn-ripple';
      ripple.style.left = `${x}px`;
      ripple.style.top = `${y}px`;
      
      button.appendChild(ripple);
      
      setTimeout(() => {
        ripple.remove();
      }, 600);
    });
  });
  
  // 添加波纹效果的CSS
  if (!document.getElementById('ripple-style')) {
    const style = document.createElement('style');
    style.id = 'ripple-style';
    style.textContent = `
      .btn {
        position: relative;
        overflow: hidden;
      }
      .btn-ripple {
        position: absolute;
        border-radius: 50%;
        background-color: rgba(255, 255, 255, 0.4);
        transform: scale(0);
        animation: ripple 0.6s linear;
        pointer-events: none;
      }
      .btn-secondary .btn-ripple {
        background-color: rgba(0, 0, 0, 0.1);
      }
      @keyframes ripple {
        to {
          transform: scale(4);
          opacity: 0;
        }
      }
    `;
    document.head.appendChild(style);
  }
}

/**
 * 初始化按钮组切换
 */
function initButtonGroupToggle() {
  const buttonGroups = document.querySelectorAll('.btn-group[data-toggle="buttons"]');
  
  buttonGroups.forEach(group => {
    const buttons = group.querySelectorAll('.btn');
    
    buttons.forEach(button => {
      button.addEventListener('click', function() {
        // 如果是单选模式
        if (group.getAttribute('data-toggle-type') === 'radio') {
          buttons.forEach(btn => {
            btn.classList.remove('active');
            btn.setAttribute('aria-pressed', 'false');
          });
          button.classList.add('active');
          button.setAttribute('aria-pressed', 'true');
        } 
        // 如果是复选模式
        else {
          button.classList.toggle('active');
          button.setAttribute('aria-pressed', button.classList.contains('active'));
        }
        
        // 触发选择改变事件
        const changeEvent = new CustomEvent('buttongroup:change', {
          bubbles: true,
          detail: { 
            group, 
            button,
            selected: Array.from(buttons).filter(btn => btn.classList.contains('active'))
          }
        });
        group.dispatchEvent(changeEvent);
      });
    });
  });
}