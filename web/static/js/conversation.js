/**
 * 对话列表交互功能
 */

// 初始化对话摘要展开/收起功能
function initSummaryToggle() {
  const summaryElements = document.querySelectorAll('.conversation-summary');
  
  summaryElements.forEach(summary => {
    const content = summary.querySelector('.summary-content');
    if (!content) return;
    
    // 检查内容是否需要截断
    const needsTruncation = content.scrollHeight > 80;
    
    if (needsTruncation) {
      // 创建展开/收起按钮
      const toggleButton = document.createElement('button');
      toggleButton.className = 'conversation-summary-toggle';
      toggleButton.textContent = '展开';
      toggleButton.setAttribute('aria-expanded', 'false');
      toggleButton.setAttribute('aria-controls', `summary-${summary.dataset.id}`);
      
      summary.appendChild(toggleButton);
      
      // 添加点击事件
      toggleButton.addEventListener('click', (e) => {
        e.preventDefault();
        const isExpanded = summary.classList.toggle('expanded');
        toggleButton.textContent = isExpanded ? '收起' : '展开';
        toggleButton.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
        
        // 添加点击波纹效果
        const ripple = document.createElement('span');
        ripple.className = 'ripple';
        ripple.style.left = (e.offsetX) + 'px';
        ripple.style.top = (e.offsetY) + 'px';
        toggleButton.appendChild(ripple);
        
        // 动画结束后移除元素
        setTimeout(() => {
          ripple.remove();
        }, 600);
      });
    }
  });
}

// 初始化对话卡片悬停效果
function initConversationCardHover() {
  const cards = document.querySelectorAll('.conversation-card');
  
  cards.forEach(card => {
    // 添加鼠标进入动画
    card.addEventListener('mouseenter', () => {
      card.classList.add('hover');
      
      // 为徽章添加动画效果
      const badges = card.querySelectorAll('.character-badge, .turns-badge');
      badges.forEach((badge, index) => {
        setTimeout(() => {
          badge.style.transform = 'translateY(-2px)';
        }, index * 50);
      });
    });
    
    // 添加鼠标离开动画
    card.addEventListener('mouseleave', () => {
      card.classList.remove('hover');
      
      // 重置徽章动画
      const badges = card.querySelectorAll('.character-badge, .turns-badge');
      badges.forEach((badge) => {
        badge.style.transform = '';
      });
    });
  });
}

// 初始化对话操作按钮
function initActionButtons() {
  const actionButtons = document.querySelectorAll('.conversation-action-btn');
  
  actionButtons.forEach(button => {
    // 添加点击波纹效果
    button.addEventListener('click', (e) => {
      // 如果按钮有确认属性，显示确认对话框
      if (button.dataset.confirm) {
        if (!confirm(button.dataset.confirm)) {
          e.preventDefault();
          return;
        }
      }
      
      // 添加点击波纹效果
      const ripple = document.createElement('span');
      ripple.className = 'ripple';
      ripple.style.left = (e.offsetX) + 'px';
      ripple.style.top = (e.offsetY) + 'px';
      button.appendChild(ripple);
      
      // 动画结束后移除元素
      setTimeout(() => {
        ripple.remove();
      }, 600);
    });
    
    // 添加键盘焦点样式
    button.addEventListener('focus', () => {
      button.classList.add('focus');
    });
    
    button.addEventListener('blur', () => {
      button.classList.remove('focus');
    });
  });
}

// 初始化对话时间格式化
function initTimeFormatting() {
  const timeElements = document.querySelectorAll('.conversation-time');
  
  if (typeof moment === 'undefined') return;
  
  timeElements.forEach(timeEl => {
    const timeText = timeEl.textContent;
    
    // 查找时间文本中的日期
    const dateRegex = /(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/g;
    const matches = timeText.match(dateRegex);
    
    if (matches) {
      matches.forEach(match => {
        const formattedTime = moment(match).fromNow();
        timeEl.innerHTML = timeEl.innerHTML.replace(match, `<span title="${match}">${formattedTime}</span>`);
      });
    }
  });
}

// 初始化对话摘要动画效果
function initSummaryAnimations() {
  const summaries = document.querySelectorAll('.conversation-summary');
  
  summaries.forEach(summary => {
    // 添加鼠标悬停效果
    summary.addEventListener('mouseenter', () => {
      summary.style.backgroundColor = 'rgba(79, 172, 254, 0.05)';
    });
    
    summary.addEventListener('mouseleave', () => {
      summary.style.backgroundColor = '';
    });
  });
}

// 页面加载完成后初始化所有功能
document.addEventListener('DOMContentLoaded', () => {
  initSummaryToggle();
  initConversationCardHover();
  initActionButtons();
  initTimeFormatting();
  initSummaryAnimations();
});