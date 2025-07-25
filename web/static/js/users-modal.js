/**
 * Users Modal Interactions
 * 用户管理页面模态框交互功能
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化用户详情模态框
    initUserDetailModal();
    
    // 初始化用户编辑模态框
    initUserEditModal();
    
    // 绑定详情按钮事件
    bindDetailButtons();
    
    // 绑定编辑按钮事件
    bindEditButtons();
});

/**
 * 初始化用户详情模态框样式
 */
function initUserDetailModal() {
    // 检查是否已存在模态框样式
    if (!document.getElementById('user-detail-modal-styles')) {
        const style = document.createElement('style');
        style.id = 'user-detail-modal-styles';
        style.textContent = `
            .modal-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(135deg, rgba(0, 0, 0, 0.8) 0%, rgba(0, 20, 40, 0.9) 100%);
                backdrop-filter: blur(10px);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
                opacity: 0;
                visibility: hidden;
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .modal-overlay.show {
                opacity: 1;
                visibility: visible;
            }
            
            .user-detail-modal {
                background: linear-gradient(145deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                border: 1px solid rgba(0, 255, 255, 0.3);
                border-radius: 20px;
                box-shadow: 
                    0 25px 50px rgba(0, 0, 0, 0.5),
                    0 0 0 1px rgba(255, 255, 255, 0.1),
                    inset 0 1px 0 rgba(255, 255, 255, 0.2);
                width: 90%;
                max-width: 700px;
                max-height: 90vh;
                overflow: hidden;
                transform: translateY(-30px) scale(0.95);
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
            }
            
            .user-detail-modal::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 2px;
                background: linear-gradient(90deg, #00ffff, #0080ff, #8000ff, #ff0080, #ff8000, #ffff00);
                background-size: 300% 100%;
                animation: techGlow 3s linear infinite;
            }
            
            @keyframes techGlow {
                0% { background-position: 0% 50%; }
                100% { background-position: 300% 50%; }
            }
            
            .modal-overlay.show .user-detail-modal {
                transform: translateY(0) scale(1);
            }
            
            .user-detail-modal-header {
                padding: 24px 28px;
                border-bottom: 1px solid rgba(0, 255, 255, 0.2);
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: linear-gradient(135deg, rgba(0, 255, 255, 0.1) 0%, rgba(0, 128, 255, 0.1) 100%);
                position: relative;
                overflow: hidden;
            }
            
            .user-detail-modal-header::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
                animation: headerScan 2s ease-in-out infinite;
            }
            
            @keyframes headerScan {
                0% { left: -100%; }
                100% { left: 100%; }
            }
            
            .user-detail-modal-title {
                margin: 0;
                font-size: 20px;
                font-weight: 700;
                color: #00ffff;
                text-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
                letter-spacing: 1px;
                position: relative;
                z-index: 1;
            }
            
            .user-detail-modal-close {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: #00ffff;
                cursor: pointer;
                padding: 10px;
                border-radius: 12px;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                backdrop-filter: blur(10px);
                position: relative;
                z-index: 1;
                min-width: 44px;
                height: 44px;
                flex-shrink: 0;
            }
            
            .user-detail-modal-close:hover {
                background: rgba(0, 255, 255, 0.2);
                border-color: #00ffff;
                box-shadow: 0 0 20px rgba(0, 255, 255, 0.4);
                transform: scale(1.1);
            }
            
            .user-detail-modal-body {
                padding: 28px;
                overflow-y: auto;
                max-height: calc(90vh - 160px);
                scrollbar-width: thin;
                scrollbar-color: #00ffff rgba(255, 255, 255, 0.1);
            }
            
            .user-detail-modal-body::-webkit-scrollbar {
                width: 8px;
            }
            
            .user-detail-modal-body::-webkit-scrollbar-track {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
            
            .user-detail-modal-body::-webkit-scrollbar-thumb {
                background: linear-gradient(180deg, #00ffff, #0080ff);
                border-radius: 4px;
            }
            
            .user-detail-modal-loading {
                text-align: center;
                padding: 60px 20px;
                color: #00ffff;
            }
            
            .user-detail-modal-spinner {
                width: 50px;
                height: 50px;
                border: 3px solid rgba(0, 255, 255, 0.3);
                border-top: 3px solid #00ffff;
                border-radius: 50%;
                animation: techSpin 1s linear infinite;
                margin: 0 auto 20px;
                box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
            }
            
            @keyframes techSpin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .user-detail-modal-content {
                display: none;
            }
            
            .user-detail-modal-profile {
                display: flex;
                align-items: flex-start;
                margin-bottom: 28px;
                padding: 24px;
                background: linear-gradient(135deg, rgba(0, 255, 255, 0.05) 0%, rgba(0, 128, 255, 0.05) 100%);
                border: 1px solid rgba(0, 255, 255, 0.2);
                border-radius: 16px;
                position: relative;
                overflow: hidden;
            }
            
            .user-detail-modal-profile::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(45deg, transparent 30%, rgba(0, 255, 255, 0.1) 50%, transparent 70%);
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            
            .user-detail-modal-profile:hover::before {
                opacity: 1;
            }
            
            .user-detail-modal-avatar {
                width: 80px;
                height: 80px;
                background: linear-gradient(135deg, #00ffff 0%, #0080ff 50%, #8000ff 100%);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-right: 24px;
                color: white;
                flex-shrink: 0;
                box-shadow: 
                    0 0 30px rgba(0, 255, 255, 0.4),
                    inset 0 0 20px rgba(255, 255, 255, 0.2);
                position: relative;
                z-index: 1;
            }
            
            .user-detail-modal-avatar::before {
                content: '';
                position: absolute;
                top: -2px;
                left: -2px;
                right: -2px;
                bottom: -2px;
                background: linear-gradient(45deg, #00ffff, #0080ff, #8000ff, #ff0080);
                border-radius: 50%;
                z-index: -1;
                animation: avatarGlow 2s linear infinite;
            }
            
            @keyframes avatarGlow {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .user-detail-modal-info {
                flex: 1;
                position: relative;
                z-index: 1;
            }
            
            .user-detail-modal-name {
                margin: 0 0 12px 0;
                font-size: 24px;
                font-weight: 700;
                color: #00ffff;
                text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);
            }
            
            .user-detail-modal-id {
                color: rgba(255, 255, 255, 0.7);
                font-size: 14px;
                margin-bottom: 16px;
                font-family: 'Courier New', monospace;
                background: rgba(0, 255, 255, 0.1);
                padding: 4px 8px;
                border-radius: 6px;
                display: inline-block;
            }
            
            .user-detail-modal-meta {
                margin-bottom: 8px;
                font-size: 14px;
                color: rgba(255, 255, 255, 0.8);
                display: flex;
                align-items: center;
            }
            
            .user-detail-modal-meta span {
                color: #00ffff;
                font-weight: 500;
                margin-left: 8px;
            }
            
            .user-detail-modal-stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                gap: 16px;
                margin-bottom: 28px;
            }
            
            .user-detail-modal-stat {
                text-align: center;
                padding: 20px 16px;
                background: linear-gradient(135deg, rgba(0, 255, 255, 0.1) 0%, rgba(0, 128, 255, 0.1) 100%);
                border: 1px solid rgba(0, 255, 255, 0.3);
                border-radius: 12px;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }
            
            .user-detail-modal-stat::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(0, 255, 255, 0.2), transparent);
                transition: left 0.5s ease;
            }
            
            .user-detail-modal-stat:hover {
                transform: translateY(-4px);
                box-shadow: 0 10px 30px rgba(0, 255, 255, 0.2);
                border-color: #00ffff;
            }
            
            .user-detail-modal-stat:hover::before {
                left: 100%;
            }
            
            .user-detail-modal-stat-value {
                font-size: 24px;
                font-weight: 700;
                color: #00ffff;
                margin-bottom: 8px;
                text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);
                position: relative;
                z-index: 1;
            }
            
            .user-detail-modal-stat-label {
                font-size: 12px;
                color: rgba(255, 255, 255, 0.7);
                text-transform: uppercase;
                letter-spacing: 1px;
                position: relative;
                z-index: 1;
            }
            
            .user-detail-modal-footer {
                padding: 24px 28px;
                border-top: 1px solid rgba(0, 255, 255, 0.2);
                display: flex;
                justify-content: flex-end;
                gap: 16px;
                background: linear-gradient(135deg, rgba(0, 255, 255, 0.05) 0%, rgba(0, 128, 255, 0.05) 100%);
            }
            
            .user-detail-modal-btn {
                padding: 12px 24px;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
                text-transform: uppercase;
                letter-spacing: 1px;
                white-space: nowrap;
            }
            
            .user-detail-modal-btn::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
                transition: left 0.5s ease;
            }
            
            .user-detail-modal-btn:hover::before {
                left: 100%;
            }
            
            .user-detail-modal-btn-secondary {
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%);
                color: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            .user-detail-modal-btn-secondary:hover {
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.2) 0%, rgba(255, 255, 255, 0.1) 100%);
                border-color: rgba(255, 255, 255, 0.4);
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
            }
            
            .user-detail-modal-btn-primary {
                background: linear-gradient(135deg, #00ffff 0%, #0080ff 100%);
                border: 1px solid #00ffff;
                color: #000;
                font-weight: 700;
            }
            
            .user-detail-modal-btn-primary:hover {
                background: linear-gradient(135deg, #0080ff 0%, #8000ff 100%);
                border-color: #0080ff;
                transform: translateY(-2px);
                box-shadow: 0 10px 25px rgba(0, 255, 255, 0.3);
                color: #fff;
            }
            
            @media (max-width: 576px) {
                .user-detail-modal {
                    width: 95%;
                    margin: 20px;
                }
                
                .user-detail-modal-stats {
                    grid-template-columns: repeat(2, 1fr);
                }
                
                .user-detail-modal-profile {
                    flex-direction: column;
                    text-align: center;
                }
                
                .user-detail-modal-avatar {
                    margin-right: 0;
                    margin-bottom: 20px;
                }
                
                .user-detail-modal-footer {
                    flex-direction: column;
                }
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * 初始化用户编辑模态框样式
 */
function initUserEditModal() {
    // 检查是否已存在编辑模态框样式
    if (!document.getElementById('user-edit-modal-styles')) {
        const style = document.createElement('style');
        style.id = 'user-edit-modal-styles';
        style.textContent = `
            .user-edit-modal {
                background: linear-gradient(145deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                border: 1px solid rgba(0, 255, 255, 0.3);
                border-radius: 20px;
                box-shadow: 
                    0 25px 50px rgba(0, 0, 0, 0.5),
                    0 0 0 1px rgba(255, 255, 255, 0.1),
                    inset 0 1px 0 rgba(255, 255, 255, 0.2);
                width: 90%;
                max-width: 600px;
                max-height: 90vh;
                overflow: hidden;
                transform: translateY(-30px) scale(0.95);
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
            }
            
            .user-edit-modal::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 2px;
                background: linear-gradient(90deg, #ff8000, #ffff00, #00ffff, #0080ff, #8000ff, #ff0080);
                background-size: 300% 100%;
                animation: editGlow 3s linear infinite;
            }
            
            @keyframes editGlow {
                0% { background-position: 0% 50%; }
                100% { background-position: 300% 50%; }
            }
            
            .modal-overlay.show .user-edit-modal {
                transform: translateY(0) scale(1);
            }
            
            .user-edit-modal-header {
                padding: 24px 28px;
                border-bottom: 1px solid rgba(255, 128, 0, 0.2);
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: linear-gradient(135deg, rgba(255, 128, 0, 0.1) 0%, rgba(255, 255, 0, 0.1) 100%);
                position: relative;
                overflow: hidden;
            }
            
            .user-edit-modal-header::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
                animation: editHeaderScan 2s ease-in-out infinite;
            }
            
            @keyframes editHeaderScan {
                0% { left: -100%; }
                100% { left: 100%; }
            }
            
            .user-edit-modal-title {
                margin: 0;
                font-size: 20px;
                font-weight: 700;
                color: #ff8000;
                text-shadow: 0 0 10px rgba(255, 128, 0, 0.5);
                letter-spacing: 1px;
                position: relative;
                z-index: 1;
            }
            
            .user-edit-modal-close {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: #ff8000;
                cursor: pointer;
                padding: 10px;
                border-radius: 12px;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                backdrop-filter: blur(10px);
                position: relative;
                z-index: 1;
                min-width: 44px;
                height: 44px;
                flex-shrink: 0;
            }
            
            .user-edit-modal-close:hover {
                background: rgba(255, 128, 0, 0.2);
                border-color: #ff8000;
                box-shadow: 0 0 20px rgba(255, 128, 0, 0.4);
                transform: scale(1.1);
            }
            
            .user-edit-modal-body {
                padding: 28px;
                overflow-y: auto;
                max-height: calc(90vh - 160px);
                scrollbar-width: thin;
                scrollbar-color: #ff8000 rgba(255, 255, 255, 0.1);
            }
            
            .user-edit-modal-body::-webkit-scrollbar {
                width: 8px;
            }
            
            .user-edit-modal-body::-webkit-scrollbar-track {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
            
            .user-edit-modal-body::-webkit-scrollbar-thumb {
                background: linear-gradient(180deg, #ff8000, #ffff00);
                border-radius: 4px;
            }
            
            .user-edit-form {
                display: grid;
                gap: 20px;
            }
            
            .form-group {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            
            .form-group.form-row {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 16px;
            }
            
            .form-label {
                font-size: 14px;
                font-weight: 600;
                color: #ff8000;
                text-transform: uppercase;
                letter-spacing: 1px;
                text-shadow: 0 0 5px rgba(255, 128, 0, 0.3);
            }
            
            .form-input {
                padding: 12px 16px;
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
                border: 1px solid rgba(255, 128, 0, 0.3);
                border-radius: 10px;
                color: #fff;
                font-size: 14px;
                transition: all 0.3s ease;
                backdrop-filter: blur(10px);
            }
            
            .form-input:focus {
                outline: none;
                border-color: #ff8000;
                box-shadow: 0 0 20px rgba(255, 128, 0, 0.3);
                background: linear-gradient(135deg, rgba(255, 128, 0, 0.1) 0%, rgba(255, 255, 0, 0.05) 100%);
            }
            
            .form-input::placeholder {
                color: rgba(255, 255, 255, 0.5);
            }
            
            .form-select {
                padding: 12px 16px;
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
                border: 1px solid rgba(255, 128, 0, 0.3);
                border-radius: 10px;
                color: #fff;
                font-size: 14px;
                transition: all 0.3s ease;
                backdrop-filter: blur(10px);
                cursor: pointer;
            }
            
            .form-select:focus {
                outline: none;
                border-color: #ff8000;
                box-shadow: 0 0 20px rgba(255, 128, 0, 0.3);
            }
            
            .form-select option {
                background: #1a1a2e;
                color: #fff;
            }
            
            .user-edit-modal-footer {
                padding: 24px 28px;
                border-top: 1px solid rgba(255, 128, 0, 0.2);
                display: flex;
                justify-content: flex-end;
                gap: 16px;
                background: linear-gradient(135deg, rgba(255, 128, 0, 0.05) 0%, rgba(255, 255, 0, 0.05) 100%);
            }
            
            .user-edit-modal-btn {
                padding: 12px 24px;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
                text-transform: uppercase;
                letter-spacing: 1px;
                white-space: nowrap;
            }
            
            .user-edit-modal-btn::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
                transition: left 0.5s ease;
            }
            
            .user-edit-modal-btn:hover::before {
                left: 100%;
            }
            
            .user-edit-modal-btn-cancel {
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%);
                color: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            .user-edit-modal-btn-cancel:hover {
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.2) 0%, rgba(255, 255, 255, 0.1) 100%);
                border-color: rgba(255, 255, 255, 0.4);
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
            }
            
            .user-edit-modal-btn-save {
                background: linear-gradient(135deg, #ff8000 0%, #ffff00 100%);
                border: 1px solid #ff8000;
                color: #000;
                font-weight: 700;
            }
            
            .user-edit-modal-btn-save:hover {
                background: linear-gradient(135deg, #ffff00 0%, #00ffff 100%);
                border-color: #ffff00;
                transform: translateY(-2px);
                box-shadow: 0 10px 25px rgba(255, 128, 0, 0.3);
                color: #000;
            }
            
            .user-edit-modal-btn-save:disabled {
                opacity: 0.5;
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
            }
            
            .form-error {
                color: #ff4444;
                font-size: 12px;
                margin-top: 4px;
                text-shadow: 0 0 5px rgba(255, 68, 68, 0.3);
            }
            
            .form-success {
                color: #44ff44;
                font-size: 12px;
                margin-top: 4px;
                text-shadow: 0 0 5px rgba(68, 255, 68, 0.3);
            }
            
            @media (max-width: 576px) {
                .user-edit-modal {
                    width: 95%;
                    margin: 20px;
                }
                
                .form-group.form-row {
                    grid-template-columns: 1fr;
                }
                
                .user-edit-modal-footer {
                    flex-direction: column;
                }
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * 绑定详情按钮事件
 */
function bindDetailButtons() {
    // 绑定表格中的详情按钮
    const detailButtons = document.querySelectorAll('.view-user-btn');
    console.log('找到详情按钮数量:', detailButtons.length);
    
    detailButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            console.log('详情按钮被点击');
            
            // 添加按钮点击效果
            this.classList.add('btn-clicked');
            setTimeout(() => {
                this.classList.remove('btn-clicked');
            }, 300);
            
            const userId = this.getAttribute('data-uid');
            if (userId) {
                console.log('用户ID:', userId);
                showUserDetailModal(userId);
            }
        });
    });
    
    // 添加按钮点击动画样式
    if (!document.getElementById('button-animations-style')) {
        const style = document.createElement('style');
        style.id = 'button-animations-style';
        style.textContent = `
            .btn-clicked {
                animation: button-pulse 0.3s ease;
            }
            
            @keyframes button-pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.2); }
                100% { transform: scale(1); }
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * 绑定编辑按钮事件
 */
function bindEditButtons() {
    // 绑定表格中的编辑按钮
    const editButtons = document.querySelectorAll('.edit-user-btn');
    console.log('找到编辑按钮数量:', editButtons.length);
    
    editButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            console.log('编辑按钮被点击');
            
            // 添加按钮点击效果
            this.classList.add('btn-clicked');
            setTimeout(() => {
                this.classList.remove('btn-clicked');
            }, 300);
            
            const userId = this.getAttribute('data-uid');
            if (userId) {
                console.log('编辑用户ID:', userId);
                showUserEditModal(userId);
            }
        });
    });
}

/**
 * 显示用户详情模态框
 * @param {string} userId - 用户ID
 */
function showUserDetailModal(userId) {
    // 检查是否已存在模态框，如果存在则先移除
    const existingModal = document.querySelector('.modal-overlay');
    if (existingModal) {
        existingModal.remove();
    }
    
    // 创建模态框
    const modalOverlay = document.createElement('div');
    modalOverlay.className = 'modal-overlay';
    modalOverlay.setAttribute('role', 'dialog');
    modalOverlay.setAttribute('aria-modal', 'true');
    modalOverlay.setAttribute('aria-labelledby', 'user-detail-modal-title');
    
    modalOverlay.innerHTML = `
        <div class="user-detail-modal">
            <div class="user-detail-modal-header">
                <h2 class="user-detail-modal-title" id="user-detail-modal-title">用户详情</h2>
                <button class="user-detail-modal-close" aria-label="关闭">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
            <div class="user-detail-modal-body">
                <div class="user-detail-modal-loading">
                    <div class="user-detail-modal-spinner"></div>
                    <p>加载用户数据...</p>
                </div>
                <div class="user-detail-modal-content">
                    <div class="user-detail-modal-profile">
                        <div class="user-detail-modal-avatar">
                            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                                <circle cx="12" cy="7" r="4"></circle>
                            </svg>
                        </div>
                        <div class="user-detail-modal-info">
                            <h3 class="user-detail-modal-name">加载中...</h3>
                            <div class="user-detail-modal-id">ID: ${userId}</div>
                            <div class="user-detail-modal-meta">用户名: <span class="user-detail-modal-username">-</span></div>
                            <div class="user-detail-modal-meta">姓名: <span class="user-detail-modal-fullname">-</span></div>
                            <div class="user-detail-modal-meta">昵称: <span class="user-detail-modal-nick">-</span></div>
                            <div class="user-detail-modal-meta">当前角色: <span class="user-detail-modal-char">-</span></div>
                            <div class="user-detail-modal-meta">API配置: <span class="user-detail-modal-api">-</span></div>
                            <div class="user-detail-modal-meta">预设: <span class="user-detail-modal-preset">-</span></div>
                            <div class="user-detail-modal-meta">流式传输: <span class="user-detail-modal-stream">-</span></div>
                            <div class="user-detail-modal-meta">注册时间: <span class="user-detail-modal-date">-</span></div>
                            <div class="user-detail-modal-meta">最后更新: <span class="user-detail-modal-update">-</span></div>
                        </div>
                    </div>
                    <div class="user-detail-modal-stats">
                        <div class="user-detail-modal-stat">
                            <div class="user-detail-modal-stat-value">-</div>
                            <div class="user-detail-modal-stat-label">总对话数</div>
                        </div>
                        <div class="user-detail-modal-stat">
                            <div class="user-detail-modal-stat-value">-</div>
                            <div class="user-detail-modal-stat-label">总消息数</div>
                        </div>
                        <div class="user-detail-modal-stat">
                            <div class="user-detail-modal-stat-value">-</div>
                            <div class="user-detail-modal-stat-label">输入Token</div>
                        </div>
                        <div class="user-detail-modal-stat">
                            <div class="user-detail-modal-stat-value">-</div>
                            <div class="user-detail-modal-stat-label">输出Token</div>
                        </div>
                        <div class="user-detail-modal-stat">
                            <div class="user-detail-modal-stat-value">-</div>
                            <div class="user-detail-modal-stat-label">总Token数</div>
                        </div>
                        <div class="user-detail-modal-stat">
                            <div class="user-detail-modal-stat-value">-</div>
                            <div class="user-detail-modal-stat-label">账户等级</div>
                        </div>
                        <div class="user-detail-modal-stat">
                            <div class="user-detail-modal-stat-value">-</div>
                            <div class="user-detail-modal-stat-label">剩余次数</div>
                        </div>
                        <div class="user-detail-modal-stat">
                            <div class="user-detail-modal-stat-value">-</div>
                            <div class="user-detail-modal-stat-label">余额</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="user-detail-modal-footer">
                <button class="user-detail-modal-btn user-detail-modal-btn-secondary user-detail-modal-close">关闭</button>
                <a href="/conversations?search=${userId}" class="user-detail-modal-btn user-detail-modal-btn-primary">查看对话记录</a>
            </div>
        </div>
    `;
    
    document.body.appendChild(modalOverlay);
    
    // 显示模态框
    setTimeout(() => {
        modalOverlay.classList.add('show');
        
        // 调用API获取用户详情
        fetch(`/api/user/${userId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('获取用户信息失败');
                }
                return response.json();
            })
            .then(data => {
                const loadingElement = modalOverlay.querySelector('.user-detail-modal-loading');
                const contentElement = modalOverlay.querySelector('.user-detail-modal-content');
                
                if (loadingElement && contentElement) {
                    loadingElement.style.display = 'none';
                    contentElement.style.display = 'block';
                    
                    const user = data.user;
                    const config = data.config || {};
                    
                    // 计算总token数
                    const totalTokens = (user.input_tokens || 0) + (user.output_tokens || 0);
                    
                    // 格式化日期
                    const formatDate = (dateStr) => {
                        if (!dateStr) return '未知';
                        return new Date(dateStr).toLocaleString('zh-CN');
                    };
                    
                    // 获取用户显示名称
                    const userName = user.first_name || user.last_name ? 
                        `${user.first_name || ''} ${user.last_name || ''}`.trim() : 
                        (user.user_name || '未知用户');
                    
                    const fullName = user.first_name || user.last_name ? 
                        `${user.first_name || ''} ${user.last_name || ''}`.trim() : 
                        '未设置';
                    
                    // 更新用户基本信息
                    modalOverlay.querySelector('.user-detail-modal-name').textContent = userName;
                    modalOverlay.querySelector('.user-detail-modal-username').textContent = user.user_name || '未设置';
                    modalOverlay.querySelector('.user-detail-modal-fullname').textContent = fullName;
                    modalOverlay.querySelector('.user-detail-modal-nick').textContent = config.nick || '未设置';
                    modalOverlay.querySelector('.user-detail-modal-char').textContent = config.char || '未设置';
                    modalOverlay.querySelector('.user-detail-modal-api').textContent = config.api || '未设置';
                    modalOverlay.querySelector('.user-detail-modal-preset').textContent = config.preset || '未设置';
                    modalOverlay.querySelector('.user-detail-modal-stream').textContent = config.stream === 'yes' ? '开启' : (config.stream === 'no' ? '关闭' : '未设置');
                    modalOverlay.querySelector('.user-detail-modal-date').textContent = formatDate(user.create_at);
                    modalOverlay.querySelector('.user-detail-modal-update').textContent = formatDate(user.update_at);
                    
                    // 更新统计数据
                    const statValues = modalOverlay.querySelectorAll('.user-detail-modal-stat-value');
                    if (statValues.length >= 8) {
                        statValues[0].textContent = user.conversations || 0;
                        statValues[1].textContent = user.dialog_turns || 0;
                        statValues[2].textContent = user.input_tokens || 0;
                        statValues[3].textContent = user.output_tokens || 0;
                        statValues[4].textContent = totalTokens;
                        statValues[5].textContent = user.account_tier || '未设置';
                        statValues[6].textContent = user.remain_frequency || 0;
                        statValues[7].textContent = user.balance || 0;
                    }
                }
            })
            .catch(error => {
                console.error('获取用户信息失败:', error);
                const loadingElement = modalOverlay.querySelector('.user-detail-modal-loading');
                if (loadingElement) {
                    loadingElement.innerHTML = '<p class="error">获取用户信息失败，请稍后重试</p>';
                }
            });
    }, 10);
    
    // 关闭按钮事件
    const closeButtons = modalOverlay.querySelectorAll('.user-detail-modal-close');
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            modalOverlay.classList.remove('show');
            setTimeout(() => {
                modalOverlay.remove();
            }, 300);
        });
    });
    
    // 点击背景关闭
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) {
            closeButtons[0].click();
        }
    });
    
    // ESC键关闭
    const escHandler = function(e) {
        if (e.key === 'Escape') {
            closeButtons[0].click();
            document.removeEventListener('keydown', escHandler);
        }
    };
    
    document.addEventListener('keydown', escHandler);
}

/**
 * 显示用户编辑模态框
 * @param {string} userId - 用户ID
 */
function showUserEditModal(userId) {
    // 检查是否已存在模态框，如果存在则先移除
    const existingModal = document.querySelector('.modal-overlay');
    if (existingModal) {
        existingModal.remove();
    }
    
    // 创建模态框
    const modalOverlay = document.createElement('div');
    modalOverlay.className = 'modal-overlay';
    modalOverlay.setAttribute('role', 'dialog');
    modalOverlay.setAttribute('aria-modal', 'true');
    modalOverlay.setAttribute('aria-labelledby', 'user-edit-modal-title');
    
    modalOverlay.innerHTML = `
        <div class="user-edit-modal">
            <div class="user-edit-modal-header">
                <h2 class="user-edit-modal-title" id="user-edit-modal-title">编辑用户信息</h2>
                <button class="user-edit-modal-close" aria-label="关闭">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
            <div class="user-edit-modal-body">
                <form class="user-edit-form" id="user-edit-form">
                    <input type="hidden" id="edit-user-id" value="${userId}">
                    
                    <div class="form-group">
                        <label class="form-label" for="edit-user-name">用户名</label>
                        <input type="text" class="form-input" id="edit-user-name" placeholder="请输入用户名" readonly>
                        <div class="form-error" id="edit-user-name-error"></div>
                    </div>
                    
                    <div class="form-group form-row">
                        <div>
                            <label class="form-label" for="edit-first-name">名字</label>
                            <input type="text" class="form-input" id="edit-first-name" placeholder="请输入名字">
                            <div class="form-error" id="edit-first-name-error"></div>
                        </div>
                        <div>
                            <label class="form-label" for="edit-last-name">姓氏</label>
                            <input type="text" class="form-input" id="edit-last-name" placeholder="请输入姓氏">
                            <div class="form-error" id="edit-last-name-error"></div>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label" for="edit-account-tier">账户等级</label>
                        <select class="form-select" id="edit-account-tier">
                            <option value="">请选择账户等级</option>
                            <option value="普通">普通</option>
                            <option value="高级">高级</option>
                            <option value="VIP">VIP</option>
                            <option value="管理员">管理员</option>
                        </select>
                        <div class="form-error" id="edit-account-tier-error"></div>
                    </div>
                    
                    <div class="form-group form-row">
                        <div>
                            <label class="form-label" for="edit-remain-frequency">剩余次数</label>
                            <input type="number" class="form-input" id="edit-remain-frequency" placeholder="请输入剩余次数" min="0">
                            <div class="form-error" id="edit-remain-frequency-error"></div>
                        </div>
                        <div>
                            <label class="form-label" for="edit-balance">余额</label>
                            <input type="number" class="form-input" id="edit-balance" placeholder="请输入余额" min="0" step="0.01">
                            <div class="form-error" id="edit-balance-error"></div>
                        </div>
                    </div>
                    
                    <div class="form-group form-row">
                        <div>
                            <label class="form-label" for="edit-role">角色</label>
                            <input type="text" class="form-input" id="edit-role" placeholder="请输入角色">
                            <div class="form-error" id="edit-role-error"></div>
                        </div>
                        <div>
                            <label class="form-label" for="edit-preset">预设</label>
                            <input type="text" class="form-input" id="edit-preset" placeholder="请输入预设">
                            <div class="form-error" id="edit-preset-error"></div>
                        </div>
                    </div>
                    
                    <div class="form-group form-row">
                        <div>
                            <label class="form-label" for="edit-api-key">API密钥</label>
                            <input type="text" class="form-input" id="edit-api-key" placeholder="请输入API密钥">
                            <div class="form-error" id="edit-api-key-error"></div>
                        </div>
                        <div>
                            <label class="form-label" for="edit-model">模型</label>
                            <input type="text" class="form-input" id="edit-model" placeholder="请输入模型">
                            <div class="form-error" id="edit-model-error"></div>
                        </div>
                    </div>
                </form>
            </div>
            <div class="user-edit-modal-footer">
                <button class="user-edit-modal-btn user-edit-modal-btn-cancel user-edit-modal-close">取消</button>
                <button class="user-edit-modal-btn user-edit-modal-btn-save" id="save-user-btn">保存</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modalOverlay);
    
    // 显示模态框
    setTimeout(() => {
        modalOverlay.classList.add('show');
        
        // 调用API获取用户详情
        fetch(`/api/user/${userId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('获取用户信息失败');
                }
                return response.json();
            })
            .then(data => {
                const user = data.user;
                const config = data.config || {};
                
                // 填充表单数据
                document.getElementById('edit-user-name').value = user.user_name || '';
                document.getElementById('edit-first-name').value = user.first_name || '';
                document.getElementById('edit-last-name').value = user.last_name || '';
                document.getElementById('edit-account-tier').value = user.account_tier || '';
                document.getElementById('edit-remain-frequency').value = user.remain_frequency || 0;
                document.getElementById('edit-balance').value = user.balance || 0;
                document.getElementById('edit-role').value = config.char || '';
                document.getElementById('edit-preset').value = config.preset || '';
                document.getElementById('edit-api-key').value = config.api || '';
                document.getElementById('edit-model').value = config.nick || '';
            })
            .catch(error => {
                console.error('获取用户信息失败:', error);
                alert('获取用户信息失败，请稍后重试');
                modalOverlay.querySelector('.user-edit-modal-close').click();
            });
    }, 10);
    
    // 保存按钮事件
    const saveButton = modalOverlay.querySelector('#save-user-btn');
    saveButton.addEventListener('click', function(e) {
        e.preventDefault();
        saveUserData(userId, modalOverlay);
    });
    
    // 关闭按钮事件
    const closeButtons = modalOverlay.querySelectorAll('.user-edit-modal-close');
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            modalOverlay.classList.remove('show');
            setTimeout(() => {
                modalOverlay.remove();
            }, 300);
        });
    });
    
    // 点击背景关闭
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) {
            closeButtons[0].click();
        }
    });
    
    // ESC键关闭
    const escHandler = function(e) {
        if (e.key === 'Escape') {
            closeButtons[0].click();
            document.removeEventListener('keydown', escHandler);
        }
    };
    
    document.addEventListener('keydown', escHandler);
}

/**
 * 保存用户数据
 * @param {string} userId - 用户ID
 * @param {HTMLElement} modalOverlay - 模态框元素
 */
function saveUserData(userId, modalOverlay) {
    const saveButton = modalOverlay.querySelector('#save-user-btn');
    const form = modalOverlay.querySelector('#user-edit-form');
    
    // 清除之前的错误信息
    const errorElements = modalOverlay.querySelectorAll('.form-error');
    errorElements.forEach(el => el.textContent = '');
    
    // 禁用保存按钮
    saveButton.disabled = true;
    saveButton.textContent = '保存中...';
    
    // 收集表单数据
    const formData = {
        user_id: userId,
        first_name: document.getElementById('edit-first-name').value.trim(),
        last_name: document.getElementById('edit-last-name').value.trim(),
        account_tier: document.getElementById('edit-account-tier').value,
        remain_frequency: parseInt(document.getElementById('edit-remain-frequency').value) || 0,
        balance: parseFloat(document.getElementById('edit-balance').value) || 0,
        config: {
            role: document.getElementById('edit-role').value.trim(),
            preset: document.getElementById('edit-preset').value.trim(),
            api_key: document.getElementById('edit-api-key').value.trim(),
            model: document.getElementById('edit-model').value.trim()
        }
    };
    
    // 发送更新请求
    fetch(`/api/user/${userId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => Promise.reject(err));
        }
        return response.json();
    })
    .then(data => {
        // 显示成功消息
        const successMessage = document.createElement('div');
        successMessage.className = 'form-success';
        successMessage.textContent = '用户信息更新成功！';
        successMessage.style.textAlign = 'center';
        successMessage.style.marginBottom = '16px';
        
        form.insertBefore(successMessage, form.firstChild);
        
        // 2秒后关闭模态框并刷新页面
        setTimeout(() => {
            modalOverlay.querySelector('.user-edit-modal-close').click();
            window.location.reload();
        }, 2000);
    })
    .catch(error => {
        console.error('保存用户信息失败:', error);
        
        // 显示错误信息
        if (error.errors) {
            // 显示字段级错误
            Object.keys(error.errors).forEach(field => {
                const errorElement = document.getElementById(`edit-${field.replace('_', '-')}-error`);
                if (errorElement) {
                    errorElement.textContent = error.errors[field];
                }
            });
        } else {
            // 显示通用错误
            const errorMessage = document.createElement('div');
            errorMessage.className = 'form-error';
            errorMessage.textContent = error.message || '保存失败，请稍后重试';
            errorMessage.style.textAlign = 'center';
            errorMessage.style.marginBottom = '16px';
            
            form.insertBefore(errorMessage, form.firstChild);
        }
    })
    .finally(() => {
        // 恢复保存按钮
        saveButton.disabled = false;
        saveButton.textContent = '保存';
    });
}

/**
 * 数字动画效果（简化版）
 * @param {HTMLElement} element - 包含数字的元素
 */
function animateNumber(element) {
    const finalValue = parseInt(element.textContent.replace(/,/g, ''), 10);
    if (isNaN(finalValue)) return;
    
    // 直接显示最终值，不使用动画
    element.textContent = finalValue;
}