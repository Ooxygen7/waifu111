/**
 * 管理员对话记录页面交互功能
 */

// 初始化对话管理功能
function initConversationManagement() {
  const deleteButtons = document.querySelectorAll('[data-action="delete"]');
  const deleteModal = document.getElementById('deleteModal');
  const confirmDeleteBtn = document.getElementById('confirmDelete');
  let currentConvId = null;
  
  // 点击删除按钮
  deleteButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();
      currentConvId = this.dataset.id;
      
      // 显示模态框
      if (deleteModal) {
        deleteModal.classList.add('show');
        document.body.classList.add('modal-open');
      }
    });
  });
  
  // 关闭模态框
  if (deleteModal) {
    const closeButtons = deleteModal.querySelectorAll('[data-dismiss="modal"]');
    closeButtons.forEach(button => {
      button.addEventListener('click', function() {
        deleteModal.classList.remove('show');
        document.body.classList.remove('modal-open');
      });
    });
    
    // 点击模态框背景关闭
    const modalBackdrop = deleteModal.querySelector('.modal-backdrop');
    if (modalBackdrop) {
      modalBackdrop.addEventListener('click', function() {
        deleteModal.classList.remove('show');
        document.body.classList.remove('modal-open');
      });
    }
    
    // 确认删除
    if (confirmDeleteBtn) {
      confirmDeleteBtn.addEventListener('click', function() {
        if (currentConvId) {
          // 发送删除请求
          fetch(`/api/conversations/${currentConvId}`, {
            method: 'DELETE',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': getCsrfToken()
            }
          })
          .then(response => {
            if (response.ok) {
              // 删除成功，移除对应的卡片
              const card = document.querySelector(`.conversation-card[data-id="${currentConvId}"]`);
              if (card) {
                card.style.opacity = '0';
                setTimeout(() => {
                  card.style.height = '0';
                  card.style.margin = '0';
                  card.style.padding = '0';
                  card.style.overflow = 'hidden';
                  
                  setTimeout(() => {
                    card.remove();
                    
                    // 如果没有对话了，刷新页面
                    const remainingCards = document.querySelectorAll('.conversation-card');
                    if (remainingCards.length === 0) {
                      window.location.reload();
                    } else {
                      // 更新统计数据
                      updateStats();
                    }
                  }, 300);
                }, 300);
              }
              
              // 关闭模态框
              deleteModal.classList.remove('show');
              document.body.classList.remove('modal-open');
              
              // 显示成功消息
              showNotification('删除成功', 'success');
            } else {
              throw new Error('删除失败');
            }
          })
          .catch(error => {
            console.error('Error:', error);
            showNotification('删除失败: ' + error.message, 'error');
          });
        }
      });
    }
  }
}

// 更新统计数据
function updateStats() {
  const conversationCards = document.querySelectorAll('.conversation-card');
  const countElement = document.querySelector('.stat-value.primary');
  const turnsElement = document.querySelector('.stat-value.success');
  const characterElement = document.querySelector('.stat-value.info');
  
  if (countElement) {
    countElement.textContent = conversationCards.length;
  }
  
  if (turnsElement) {
    let totalTurns = 0;
    conversationCards.forEach(card => {
      const turnsBadge = card.querySelector('.turns-badge');
      if (turnsBadge) {
        const turnsText = turnsBadge.textContent.trim();
        const turnsMatch = turnsText.match(/(\d+)/);
        if (turnsMatch) {
          totalTurns += parseInt(turnsMatch[1], 10);
        }
      }
    });
    turnsElement.textContent = totalTurns;
  }
  
  if (characterElement) {
    let characterCount = 0;
    conversationCards.forEach(card => {
      if (card.querySelector('.character-badge')) {
        characterCount++;
      }
    });
    characterElement.textContent = characterCount;
  }
  
  // 更新对话计数徽章
  const countBadge = document.querySelector('.conversation-count-badge');
  if (countBadge) {
    countBadge.textContent = `${conversationCards.length} 个对话`;
  }
}

// 获取CSRF令牌
function getCsrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
}

// 显示通知
function showNotification(message, type = 'info') {
  // 检查是否已存在通知容器
  let container = document.querySelector('.notification-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'notification-container';
    document.body.appendChild(container);
  }
  
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  
  // 添加图标
  const icon = document.createElement('span');
  icon.className = 'notification-icon';
  switch (type) {
    case 'success':
      icon.textContent = '✓';
      break;
    case 'error':
      icon.textContent = '✗';
      break;
    case 'warning':
      icon.textContent = '⚠';
      break;
    default:
      icon.textContent = 'ℹ';
  }
  notification.appendChild(icon);
  
  // 添加消息文本
  const messageEl = document.createElement('span');
  messageEl.className = 'notification-message';
  messageEl.textContent = message;
  notification.appendChild(messageEl);
  
  // 添加关闭按钮
  const closeBtn = document.createElement('button');
  closeBtn.className = 'notification-close';
  closeBtn.textContent = '×';
  closeBtn.addEventListener('click', () => {
    notification.classList.remove('show');
    setTimeout(() => {
      notification.remove();
    }, 300);
  });
  notification.appendChild(closeBtn);
  
  container.appendChild(notification);
  
  // 显示通知
  setTimeout(() => {
    notification.classList.add('show');
  }, 10);
  
  // 自动关闭
  setTimeout(() => {
    if (notification.parentNode) {
      notification.classList.remove('show');
      setTimeout(() => {
        if (notification.parentNode) {
          notification.remove();
        }
      }, 300);
    }
  }, 5000);
}

// 初始化批量操作功能
function initBatchOperations() {
  const selectAllCheckbox = document.getElementById('selectAll');
  const batchActionButtons = document.querySelectorAll('.batch-action');
  const itemCheckboxes = document.querySelectorAll('.item-checkbox');
  
  if (selectAllCheckbox) {
    // 全选/取消全选
    selectAllCheckbox.addEventListener('change', function() {
      const isChecked = this.checked;
      itemCheckboxes.forEach(checkbox => {
        checkbox.checked = isChecked;
        
        // 更新卡片选中状态
        const card = checkbox.closest('.conversation-card');
        if (card) {
          if (isChecked) {
            card.classList.add('selected');
          } else {
            card.classList.remove('selected');
          }
        }
      });
      
      // 更新批量操作按钮状态
      updateBatchActionButtons();
    });
  }
  
  // 单个选择框变化时更新全选框状态
  itemCheckboxes.forEach(checkbox => {
    checkbox.addEventListener('change', function() {
      // 更新卡片选中状态
      const card = this.closest('.conversation-card');
      if (card) {
        if (this.checked) {
          card.classList.add('selected');
        } else {
          card.classList.remove('selected');
        }
      }
      
      updateSelectAllCheckbox();
      updateBatchActionButtons();
    });
    
    // 点击卡片也可以选中/取消选中
    const card = checkbox.closest('.conversation-card');
    if (card) {
      // 排除点击操作按钮和链接的情况
      card.addEventListener('click', function(e) {
        if (e.target.closest('.conversation-action-btn') || e.target.closest('a') || e.target.closest('button') || e.target.closest('input[type="checkbox"]')) {
          return;
        }
        
        checkbox.checked = !checkbox.checked;
        
        // 更新卡片选中状态
        if (checkbox.checked) {
          card.classList.add('selected');
        } else {
          card.classList.remove('selected');
        }
        
        updateSelectAllCheckbox();
        updateBatchActionButtons();
      });
    }
  });
  
  // 更新全选框状态
  function updateSelectAllCheckbox() {
    if (selectAllCheckbox) {
      const totalCheckboxes = itemCheckboxes.length;
      const checkedCheckboxes = Array.from(itemCheckboxes).filter(cb => cb.checked).length;
      
      selectAllCheckbox.checked = totalCheckboxes > 0 && checkedCheckboxes === totalCheckboxes;
      selectAllCheckbox.indeterminate = checkedCheckboxes > 0 && checkedCheckboxes < totalCheckboxes;
    }
  }
  
  // 更新批量操作按钮状态
  function updateBatchActionButtons() {
    const hasChecked = Array.from(itemCheckboxes).some(cb => cb.checked);
    const checkedCount = Array.from(itemCheckboxes).filter(cb => cb.checked).length;
    
    batchActionButtons.forEach(button => {
      button.disabled = !hasChecked;
      if (hasChecked) {
        button.classList.remove('disabled');
        // 更新按钮文本显示选中数量
        if (button.dataset.action === 'delete') {
          const originalText = button.getAttribute('data-original-text') || button.innerHTML;
          if (!button.getAttribute('data-original-text')) {
            button.setAttribute('data-original-text', originalText);
          }
          button.innerHTML = `<i class="fas fa-trash-alt"></i> 删除选中的 ${checkedCount} 项`;
        }
      } else {
        button.classList.add('disabled');
        // 恢复原始按钮文本
        const originalText = button.getAttribute('data-original-text');
        if (originalText) {
          button.innerHTML = originalText;
        }
      }
    });
    
    // 更新选中计数
    const selectionCounter = document.querySelector('.selection-counter');
    if (selectionCounter) {
      if (checkedCount > 0) {
        selectionCounter.textContent = `已选择 ${checkedCount} 项`;
        selectionCounter.style.display = 'block';
      } else {
        selectionCounter.style.display = 'none';
      }
    }
  }
  
  // 初始化批量操作按钮
  batchActionButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();
      
      if (this.disabled || this.classList.contains('disabled')) {
        return;
      }
      
      const action = this.dataset.action;
      const checkedIds = Array.from(itemCheckboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value);
      
      if (checkedIds.length === 0) return;
      
      switch (action) {
        case 'delete':
          // 使用模态框确认而不是浏览器默认确认框
          const deleteModal = document.getElementById('batchDeleteModal') || document.getElementById('deleteModal');
          if (deleteModal) {
            // 更新模态框内容
            const countElement = deleteModal.querySelector('.batch-count');
            if (countElement) {
              countElement.textContent = checkedIds.length;
            }
            
            // 显示模态框
            deleteModal.classList.add('show');
            document.body.classList.add('modal-open');
            
            // 设置确认按钮点击事件
            const confirmBtn = deleteModal.querySelector('#confirmBatchDelete') || deleteModal.querySelector('#confirmDelete');
            if (confirmBtn) {
              // 移除旧的事件监听器
              const newConfirmBtn = confirmBtn.cloneNode(true);
              confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
              
              // 添加新的事件监听器
              newConfirmBtn.addEventListener('click', function() {
                batchDelete(checkedIds);
                deleteModal.classList.remove('show');
                document.body.classList.remove('modal-open');
              });
            }
          } else {
            // 如果没有模态框，使用默认确认框
            if (confirm(`确定要删除选中的 ${checkedIds.length} 个对话吗？此操作不可撤销。`)) {
              batchDelete(checkedIds);
            }
          }
          break;
        // 可以添加其他批量操作
      }
    });
  });
  
  // 批量删除
  function batchDelete(ids) {
    // 显示加载状态
    const deleteButton = document.querySelector('.batch-action[data-action="delete"]');
    if (deleteButton) {
      const originalText = deleteButton.innerHTML;
      deleteButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 删除中...';
      deleteButton.disabled = true;
    }
    
    fetch('/api/conversations/batch-delete', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify({ ids })
    })
    .then(response => {
      if (response.ok) {
        return response.json();
      } else {
        throw new Error('批量删除失败');
      }
    })
    .then(data => {
      // 删除成功，移除对应的卡片
      ids.forEach(id => {
        const card = document.querySelector(`.conversation-card[data-id="${id}"]`);
        if (card) {
          card.style.opacity = '0';
          setTimeout(() => {
            card.style.height = '0';
            card.style.margin = '0';
            card.style.padding = '0';
            card.style.overflow = 'hidden';
            
            setTimeout(() => {
              card.remove();
            }, 300);
          }, 300);
        }
      });
      
      // 如果没有对话了，刷新页面
      setTimeout(() => {
        const remainingCards = document.querySelectorAll('.conversation-card');
        if (remainingCards.length === 0) {
          window.location.reload();
        } else {
          // 更新统计数据
          updateStats();
          
          // 重置全选框
          const selectAllCheckbox = document.getElementById('selectAll');
          if (selectAllCheckbox) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
          }
          
          // 更新批量操作按钮状态
          updateBatchActionButtons();
        }
      }, 600);
      
      // 显示成功消息
      showNotification(`成功删除 ${ids.length} 个对话`, 'success');
      
      // 恢复删除按钮状态
      if (deleteButton) {
        const originalText = deleteButton.getAttribute('data-original-text');
        if (originalText) {
          deleteButton.innerHTML = originalText;
        } else {
          deleteButton.innerHTML = '<i class="fas fa-trash-alt"></i> 批量删除';
        }
        deleteButton.disabled = false;
      }
    })
    .catch(error => {
      console.error('Error:', error);
      showNotification('批量删除失败: ' + error.message, 'error');
      
      // 恢复删除按钮状态
      if (deleteButton) {
        const originalText = deleteButton.getAttribute('data-original-text');
        if (originalText) {
          deleteButton.innerHTML = originalText;
        } else {
          deleteButton.innerHTML = '<i class="fas fa-trash-alt"></i> 批量删除';
        }
        deleteButton.disabled = false;
      }
    });
  }
}

// 页面加载完成后初始化所有功能
document.addEventListener('DOMContentLoaded', () => {
  initConversationManagement();
  initBatchOperations();
});