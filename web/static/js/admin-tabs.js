/**
 * 管理员标签页脚本
 * Admin Tabs Script
 */

document.addEventListener('DOMContentLoaded', function() {
  // 获取所有标签页组
  const tabGroups = document.querySelectorAll('.admin-tabs');
  
  tabGroups.forEach(tabGroup => {
    const tabs = tabGroup.querySelectorAll('.admin-tabs-link');
    
    tabs.forEach(tab => {
      tab.addEventListener('click', function(event) {
        event.preventDefault();
        
        // 获取目标面板ID
        const targetId = this.getAttribute('data-target');
        if (!targetId) return;
        
        const targetPane = document.getElementById(targetId);
        if (!targetPane) return;
        
        // 获取所有相关的标签和面板
        const siblingTabs = tabGroup.querySelectorAll('.admin-tabs-link');
        const siblingPanes = document.querySelectorAll('.admin-tabs-pane');
        
        // 移除所有活动状态
        siblingTabs.forEach(tab => tab.classList.remove('active'));
        siblingPanes.forEach(pane => pane.classList.remove('active'));
        
        // 设置当前标签和面板为活动状态
        this.classList.add('active');
        targetPane.classList.add('active');
        
        // 触发自定义事件，通知其他组件标签已切换
        const tabChangeEvent = new CustomEvent('tabChange', {
          detail: {
            tabId: this.id,
            targetId: targetId
          }
        });
        document.dispatchEvent(tabChangeEvent);
      });
    });
  });
});