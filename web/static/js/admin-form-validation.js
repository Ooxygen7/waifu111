/**
 * 管理员表单验证脚本
 * Admin Form Validation Script
 */

document.addEventListener('DOMContentLoaded', function() {
  // 获取所有需要验证的表单
  const forms = document.querySelectorAll('.admin-form[data-validate="true"]');
  
  forms.forEach(form => {
    // 阻止默认提交行为，进行验证
    form.addEventListener('submit', function(event) {
      if (!validateForm(form)) {
        event.preventDefault();
        event.stopPropagation();
      }
    });
    
    // 实时验证
    if (form.getAttribute('data-validate-live') === 'true') {
      const inputs = form.querySelectorAll('input, select, textarea');
      
      inputs.forEach(input => {
        input.addEventListener('blur', function() {
          validateInput(input);
        });
        
        input.addEventListener('input', function() {
          if (input.classList.contains('is-invalid')) {
            validateInput(input);
          }
        });
      });
    }
  });
  
  /**
   * 验证整个表单
   * @param {HTMLFormElement} form - 表单元素
   * @returns {boolean} - 验证是否通过
   */
  function validateForm(form) {
    let isValid = true;
    const inputs = form.querySelectorAll('input, select, textarea');
    
    inputs.forEach(input => {
      if (!validateInput(input)) {
        isValid = false;
      }
    });
    
    if (!isValid) {
      // 滚动到第一个错误输入
      const firstInvalid = form.querySelector('.is-invalid');
      if (firstInvalid) {
        firstInvalid.focus();
        firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
    
    return isValid;
  }
  
  /**
   * 验证单个输入
   * @param {HTMLElement} input - 输入元素
   * @returns {boolean} - 验证是否通过
   */
  function validateInput(input) {
    // 如果输入被禁用或不需要验证，则跳过
    if (input.disabled || input.type === 'hidden' || input.type === 'button' || 
        input.type === 'submit' || input.type === 'reset' || input.type === 'file') {
      return true;
    }
    
    let isValid = true;
    const value = input.value.trim();
    
    // 检查必填项
    if (input.hasAttribute('required') && value === '') {
      setInvalid(input, '此字段是必填项');
      isValid = false;
    }
    
    // 检查最小长度
    else if (input.hasAttribute('minlength') && value.length < parseInt(input.getAttribute('minlength'))) {
      const minLength = input.getAttribute('minlength');
      setInvalid(input, `请至少输入 ${minLength} 个字符`);
      isValid = false;
    }
    
    // 检查最大长度
    else if (input.hasAttribute('maxlength') && value.length > parseInt(input.getAttribute('maxlength'))) {
      const maxLength = input.getAttribute('maxlength');
      setInvalid(input, `请不要超过 ${maxLength} 个字符`);
      isValid = false;
    }
    
    // 检查模式匹配
    else if (input.hasAttribute('pattern') && value !== '') {
      const pattern = new RegExp(input.getAttribute('pattern'));
      if (!pattern.test(value)) {
        setInvalid(input, input.getAttribute('data-pattern-message') || '请输入有效的格式');
        isValid = false;
      }
    }
    
    // 检查类型验证
    else if (value !== '') {
      switch (input.type) {
        case 'email':
          const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
          if (!emailPattern.test(value)) {
            setInvalid(input, '请输入有效的电子邮件地址');
            isValid = false;
          }
          break;
          
        case 'url':
          const urlPattern = /^(https?:\/\/)?([\da-z.-]+)\.([a-z.]{2,6})([/\w.-]*)*\/?$/;
          if (!urlPattern.test(value)) {
            setInvalid(input, '请输入有效的URL');
            isValid = false;
          }
          break;
          
        case 'number':
          if (isNaN(value)) {
            setInvalid(input, '请输入有效的数字');
            isValid = false;
          } else {
            // 检查最小值
            if (input.hasAttribute('min') && parseFloat(value) < parseFloat(input.getAttribute('min'))) {
              setInvalid(input, `请输入不小于 ${input.getAttribute('min')} 的值`);
              isValid = false;
            }
            // 检查最大值
            else if (input.hasAttribute('max') && parseFloat(value) > parseFloat(input.getAttribute('max'))) {
              setInvalid(input, `请输入不大于 ${input.getAttribute('max')} 的值`);
              isValid = false;
            }
          }
          break;
          
        case 'date':
          if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
            setInvalid(input, '请输入有效的日期格式 (YYYY-MM-DD)');
            isValid = false;
          }
          break;
      }
    }
    
    // 如果验证通过，设置为有效状态
    if (isValid) {
      setValid(input);
    }
    
    return isValid;
  }
  
  /**
   * 设置输入为无效状态
   * @param {HTMLElement} input - 输入元素
   * @param {string} message - 错误消息
   */
  function setInvalid(input, message) {
    input.classList.remove('is-valid');
    input.classList.add('is-invalid');
    
    // 查找或创建错误消息元素
    let feedback = input.nextElementSibling;
    if (!feedback || !feedback.classList.contains('invalid-feedback')) {
      feedback = document.createElement('div');
      feedback.className = 'invalid-feedback';
      input.parentNode.insertBefore(feedback, input.nextSibling);
    }
    
    feedback.textContent = message;
  }
  
  /**
   * 设置输入为有效状态
   * @param {HTMLElement} input - 输入元素
   */
  function setValid(input) {
    input.classList.remove('is-invalid');
    input.classList.add('is-valid');
    
    // 移除错误消息
    const feedback = input.nextElementSibling;
    if (feedback && feedback.classList.contains('invalid-feedback')) {
      feedback.textContent = '';
    }
  }
  
  // 导出验证函数，以便其他脚本使用
  window.adminFormValidation = {
    validateForm,
    validateInput
  };
});