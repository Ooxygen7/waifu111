/**
 * 模态框交互增强脚本
 * Modal Dialog Enhancement Script
 */

document.addEventListener('DOMContentLoaded', function() {
  // 获取模态框元素
  const modal = document.getElementById('messageDetailModal');
  if (!modal) return;
  
  const closeModal = document.getElementById('closeModal');
  const closeModalBtn = document.getElementById('closeModalBtn');
  const modalOverlay = document.querySelector('.modal-overlay');
  const modalContainer = document.querySelector('.modal-container');
  
  // 关闭模态框的函数
  function hideModal() {
    modal.classList.add('modal-closing');
    
    // 添加关闭动画
    setTimeout(() => {
      modal.style.display = 'none';
      document.body.classList.remove('modal-open');
      modal.classList.remove('modal-closing');
      
      // 恢复焦点到之前的元素
      if (lastFocusedElement) {
        lastFocusedElement.focus();
      }
    }, 200);
  }
  
  // 打开模态框的函数
  let lastFocusedElement;
  
  function showModal(container) {
    // 保存当前焦点元素
    lastFocusedElement = document.activeElement;
    
    const dialogId = container.dataset.dialogId;
    const rawContent = container.dataset.rawContent;
    const processedContent = container.dataset.processedContent;
    const turn = container.dataset.turn;
    const time = container.dataset.time;
    const msgId = container.dataset.msgId || '';
    const role = container.dataset.role === 'user' ? '用户' : 'AI助手';
    
    // 填充模态框内容
    document.getElementById('modal-role').textContent = role;
    document.getElementById('modal-role').className = 'tag ' + (role === '用户' ? 'primary' : 'success');
    document.getElementById('modal-turn').textContent = turn;
    document.getElementById('modal-time').textContent = time;
    document.getElementById('modal-msg-id').textContent = msgId || '无';
    
    // 设置原始内容和处理后内容
    const rawContentEl = document.getElementById('modal-raw-content');
    const processedContentEl = document.getElementById('modal-processed-content');
    
    // 原始内容保持纯文本显示，不进行任何HTML渲染
    rawContentEl.textContent = rawContent;
    rawContentEl.classList.add('raw-text');
    
    // 处理后内容可以进行语法高亮
    processedContentEl.textContent = processedContent;
    
    // 只对处理后的内容进行代码块高亮
    highlightCodeBlocks(processedContentEl);
    
    // 显示模态框
    modal.style.display = 'block';
    document.body.classList.add('modal-open');
    
    // 设置焦点到关闭按钮
    setTimeout(() => {
      closeModal.focus();
    }, 100);
  }
  
  // 代码块高亮函数
  function highlightCodeBlocks(container) {
    const content = container.textContent;
    
    // 检测是否包含常见的代码模式
    const codePatterns = [
      { pattern: /\b(function|const|let|var|if|else|for|while|return|import|export|class)\b/, language: 'javascript' },
      { pattern: /\b(def|class|import|from|if|elif|else|for|while|return|try|except)\b/, language: 'python' },
      { pattern: /<\/?[a-z][\s\S]*>/i, language: 'html' },
      { pattern: /\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\b/i, language: 'sql' },
      { pattern: /\{[\s\S]*\}|\[[\s\S]*\]/, language: 'json' }
    ];
    
    // 检查内容是否匹配任何代码模式
    let detectedLanguage = '';
    for (const { pattern, language } of codePatterns) {
      if (pattern.test(content)) {
        detectedLanguage = language;
        break;
      }
    }
    
    // 如果检测到代码，添加语法高亮类
    if (detectedLanguage) {
      container.classList.add('code-block');
      container.setAttribute('data-language', detectedLanguage);
      
      // 添加语言标签
      const languageTag = document.createElement('div');
      languageTag.className = 'language-tag';
      languageTag.textContent = detectedLanguage;
      container.parentNode.insertBefore(languageTag, container);
      
      // 简单的语法高亮 (这里只是基础实现，实际项目中可以使用 highlight.js 等库)
      applyBasicSyntaxHighlighting(container, detectedLanguage);
    }
  }
  
  // 简单的语法高亮实现
  function applyBasicSyntaxHighlighting(container, language) {
    let html = container.textContent;
    
    // 根据不同语言应用不同的高亮规则
    switch (language) {
      case 'javascript':
        // 关键字高亮
        html = html.replace(/\b(function|const|let|var|if|else|for|while|return|import|export|class|new|this|true|false|null|undefined)\b/g, '<span class="syntax-keyword">$1</span>');
        // 字符串高亮
        html = html.replace(/(["'`])(.*?)\1/g, '<span class="syntax-string">$1$2$1</span>');
        // 注释高亮
        html = html.replace(/(\/\/.*)/g, '<span class="syntax-comment">$1</span>');
        break;
        
      case 'python':
        // 关键字高亮
        html = html.replace(/\b(def|class|import|from|if|elif|else|for|while|return|try|except|as|with|in|not|and|or|True|False|None)\b/g, '<span class="syntax-keyword">$1</span>');
        // 字符串高亮
        html = html.replace(/(["'])(.*?)\1/g, '<span class="syntax-string">$1$2$1</span>');
        // 注释高亮
        html = html.replace(/(#.*)/g, '<span class="syntax-comment">$1</span>');
        break;
        
      case 'html':
        // 标签高亮
        html = html.replace(/(&lt;[^&]*&gt;)/g, '<span class="syntax-tag">$1</span>');
        // 属性高亮
        html = html.replace(/(\s[a-zA-Z-]+)=["']([^"']*)["']/g, '<span class="syntax-attr">$1</span>=<span class="syntax-string">"$2"</span>');
        break;
        
      case 'json':
        // 键高亮
        html = html.replace(/(".*?")(?=\s*:)/g, '<span class="syntax-key">$1</span>');
        // 值高亮
        html = html.replace(/:\s*(".*?")/g, ': <span class="syntax-string">$1</span>');
        // 数字高亮
        html = html.replace(/:\s*([0-9]+)/g, ': <span class="syntax-number">$1</span>');
        // 布尔值高亮
        html = html.replace(/:\s*(true|false)/g, ': <span class="syntax-keyword">$1</span>');
        break;
    }
    
    // 更新容器内容
    container.innerHTML = html;
  }
  
  // 关闭按钮点击事件
  if (closeModal) closeModal.addEventListener('click', hideModal);
  if (closeModalBtn) closeModalBtn.addEventListener('click', hideModal);
  if (modalOverlay) modalOverlay.addEventListener('click', hideModal);
  
  // 键盘支持 - ESC键关闭模态框
  document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape' && modal.style.display === 'block') {
      hideModal();
    }
  });
  
  // 消息气泡点击事件
  document.querySelectorAll('.message-bubble').forEach(bubble => {
    bubble.addEventListener('click', function() {
      const container = this.closest('.message-bubble-container');
      showModal(container);
    });
    
    // 键盘支持 - 回车键或空格键点击消息
    bubble.addEventListener('keydown', function(event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        const container = this.closest('.message-bubble-container');
        showModal(container);
      }
    });
  });
  
  // 模态框内的焦点陷阱
  if (modal) {
    modal.addEventListener('keydown', function(event) {
      if (event.key === 'Tab') {
        // 获取模态框内所有可聚焦元素
        const focusableElements = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];
        
        // 如果按下Shift+Tab且当前焦点在第一个元素上，则移动到最后一个元素
        if (event.shiftKey && document.activeElement === firstElement) {
          event.preventDefault();
          lastElement.focus();
        }
        // 如果按下Tab且当前焦点在最后一个元素上，则移动到第一个元素
        else if (!event.shiftKey && document.activeElement === lastElement) {
          event.preventDefault();
          firstElement.focus();
        }
      }
    });
  }
  
  // 复制按钮功能
  function addCopyButtons() {
    const contentBoxes = document.querySelectorAll('.content-box');
    
    contentBoxes.forEach(box => {
      // 创建复制按钮
      const copyBtn = document.createElement('button');
      copyBtn.className = 'copy-btn';
      copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
      copyBtn.setAttribute('aria-label', '复制内容');
      copyBtn.setAttribute('title', '复制到剪贴板');
      
      // 添加按钮到内容框
      box.style.position = 'relative';
      box.appendChild(copyBtn);
      
      // 添加点击事件
      copyBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        
        // 获取内容
        const pre = box.querySelector('pre');
        const textToCopy = pre.textContent;
        
        // 复制到剪贴板
        navigator.clipboard.writeText(textToCopy).then(() => {
          // 显示成功提示
          copyBtn.innerHTML = '<i class="fas fa-check"></i>';
          copyBtn.classList.add('copied');
          
          // 恢复原始图标
          setTimeout(() => {
            copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
            copyBtn.classList.remove('copied');
          }, 2000);
        }).catch(err => {
          console.error('复制失败:', err);
          copyBtn.innerHTML = '<i class="fas fa-times"></i>';
          copyBtn.classList.add('copy-error');
          
          setTimeout(() => {
            copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
            copyBtn.classList.remove('copy-error');
          }, 2000);
        });
      });
    });
  }
  
  // 当模态框显示时添加复制按钮
  const modalObserver = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
      if (mutation.attributeName === 'style' && modal.style.display === 'block') {
        addCopyButtons();
      }
    });
  });
  
  modalObserver.observe(modal, { attributes: true });
});