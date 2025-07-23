/**
 * Admin Modal Functionality
 * 管理员模态框功能
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化模态框功能
    initAdminModals();
});

/**
 * 初始化管理员模态框功能
 */
function initAdminModals() {
    // 获取所有模态框
    const modals = document.querySelectorAll('.modal');
    
    if (!modals.length) return;
    
    // 为每个模态框设置事件
    modals.forEach(modal => {
        // 获取关闭按钮
        const closeButtons = modal.querySelectorAll('.modal-close');
        const backdrop = modal.querySelector('.modal-backdrop');
        
        // 关闭按钮点击事件
        closeButtons.forEach(button => {
            button.addEventListener('click', function() {
                hideModal(modal);
            });
        });
        
        // 点击背景关闭模态框
        if (backdrop) {
            backdrop.addEventListener('click', function(e) {
                if (e.target === backdrop) {
                    hideModal(modal);
                }
            });
        }
    });
    
    // 添加ESC键关闭模态框
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const visibleModal = document.querySelector('.modal.show');
            if (visibleModal) {
                hideModal(visibleModal);
            }
        }
    });
    
    // 添加模态框样式
    addModalStyles();
}

/**
 * 显示模态框
 * @param {HTMLElement|string} modal - 模态框元素或ID
 */
function showModal(modal) {
    // 如果传入的是字符串ID，则获取对应元素
    if (typeof modal === 'string') {
        modal = document.getElementById(modal);
    }
    
    if (!modal) return;
    
    // 显示模态框
    modal.style.display = 'block';
    
    // 添加显示动画
    setTimeout(() => {
        modal.classList.add('show');
        
        // 设置焦点到第一个表单元素或关闭按钮
        const firstInput = modal.querySelector('input, select, textarea');
        if (firstInput) {
            firstInput.focus();
        } else {
            const closeButton = modal.querySelector('.modal-close');
            if (closeButton) {
                closeButton.focus();
            }
        }
    }, 10);
    
    // 设置ARIA属性
    modal.setAttribute('aria-hidden', 'false');
    
    // 禁止背景滚动
    document.body.classList.add('modal-open');
}

/**
 * 隐藏模态框
 * @param {HTMLElement|string} modal - 模态框元素或ID
 */
function hideModal(modal) {
    // 如果传入的是字符串ID，则获取对应元素
    if (typeof modal === 'string') {
        modal = document.getElementById(modal);
    }
    
    if (!modal) return;
    
    // 移除显示类
    modal.classList.remove('show');
    
    // 延迟隐藏，等待动画完成
    setTimeout(() => {
        modal.style.display = 'none';
        
        // 设置ARIA属性
        modal.setAttribute('aria-hidden', 'true');
        
        // 恢复背景滚动
        if (!document.querySelector('.modal.show')) {
            document.body.classList.remove('modal-open');
        }
    }, 300);
}

/**
 * 添加模态框样式
 */
function addModalStyles() {
    // 检查是否已存在样式
    if (document.getElementById('admin-modal-styles')) return;
    
    // 创建样式元素
    const style = document.createElement('style');
    style.id = 'admin-modal-styles';
    style.textContent = `
        /* 模态框开启时的body样式 */
        body.modal-open {
            overflow: hidden;
        }
        
        /* 模态框容器 */
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 1050;
            display: none;
            overflow: hidden;
            outline: 0;
        }
        
        /* 模态框背景 */
        .modal-backdrop {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(0, 0, 0, 0.5);
            z-index: 1040;
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        /* 模态框对话框 */
        .modal-dialog {
            position: relative;
            width: auto;
            margin: 1.75rem auto;
            max-width: 500px;
            pointer-events: none;
            transform: translateY(-50px);
            transition: transform 0.3s ease;
            z-index: 1050;
        }
        
        /* 模态框内容 */
        .modal-content {
            position: relative;
            display: flex;
            flex-direction: column;
            width: 100%;
            pointer-events: auto;
            background-color: var(--background-color);
            background-clip: padding-box;
            border: 1px solid var(--border-color);
            border-radius: 0.3rem;
            outline: 0;
            box-shadow: 0 0.25rem 0.5rem rgba(0, 0, 0, 0.1);
        }
        
        /* 模态框头部 */
        .modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        /* 模态框标题 */
        .modal-title {
            margin: 0;
            line-height: 1.5;
            font-size: 1.25rem;
            font-weight: 500;
        }
        
        /* 模态框关闭按钮 */
        .modal-close {
            padding: 0.5rem;
            margin: -0.5rem -0.5rem -0.5rem auto;
            background-color: transparent;
            border: 0;
            cursor: pointer;
            font-size: 1.5rem;
            font-weight: 700;
            line-height: 1;
            color: var(--text-secondary);
            opacity: 0.5;
            transition: opacity 0.15s;
        }
        
        .modal-close:hover {
            opacity: 1;
        }
        
        /* 模态框内容区域 */
        .modal-body {
            position: relative;
            flex: 1 1 auto;
            padding: 1rem;
        }
        
        /* 模态框底部 */
        .modal-footer {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding: 1rem;
            border-top: 1px solid var(--border-color);
            gap: 0.5rem;
        }
        
        /* 显示状态 */
        .modal.show .modal-backdrop {
            opacity: 1;
        }
        
        .modal.show .modal-dialog {
            transform: translateY(0);
        }
        
        /* 响应式调整 */
        @media (max-width: 576px) {
            .modal-dialog {
                margin: 0.5rem;
                max-width: calc(100% - 1rem);
            }
        }
        
        /* 深色模式适配 */
        [data-theme="dark"] .modal-content {
            background-color: var(--background-color);
            border-color: var(--border-color);
        }
        
        [data-theme="dark"] .modal-header,
        [data-theme="dark"] .modal-footer {
            border-color: var(--border-color);
        }
        
        [data-theme="dark"] .modal-close {
            color: var(--text-secondary);
        }
    `;
    
    // 添加到文档头部
    document.head.appendChild(style);
}

// 导出函数
window.showModal = showModal;
window.hideModal = hideModal;