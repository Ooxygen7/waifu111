/**
 * Content Layout
 * 内容布局功能
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化内容布局
    initContentLayout();
});

/**
 * 初始化内容布局
 */
function initContentLayout() {
    // 添加内容块动画效果
    animateContentBlocks();
    
    // 监听窗口大小变化
    window.addEventListener('resize', handleContentResize);
    
    // 初始调用一次
    handleContentResize();
}

/**
 * 处理内容区域大小变化
 */
function handleContentResize() {
    const width = window.innerWidth;
    const contentCards = document.querySelectorAll('.content-cards');
    
    contentCards.forEach(container => {
        // 根据窗口大小调整卡片网格
        if (width < 576) {
            container.style.gridTemplateColumns = '1fr';
        } else if (width < 768) {
            container.style.gridTemplateColumns = 'repeat(auto-fill, minmax(250px, 1fr))';
        } else if (width < 992) {
            container.style.gridTemplateColumns = 'repeat(auto-fill, minmax(280px, 1fr))';
        } else {
            container.style.gridTemplateColumns = 'repeat(auto-fill, minmax(300px, 1fr))';
        }
    });
}

/**
 * 添加内容块动画效果
 */
function animateContentBlocks() {
    const contentBlocks = document.querySelectorAll('.content-block');
    
    contentBlocks.forEach((block, index) => {
        // 添加初始状态
        block.style.opacity = '0';
        block.style.transform = 'translateY(20px)';
        block.style.transition = `opacity 0.5s ease ${index * 0.1}s, transform 0.5s ease ${index * 0.1}s`;
        
        // 添加到可见区域时显示
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    block.style.opacity = '1';
                    block.style.transform = 'translateY(0)';
                    observer.unobserve(block);
                }
            });
        }, { threshold: 0.1 });
        
        observer.observe(block);
    });
}