/**
 * Chart Configuration
 * 图表配置
 */

// 全局Chart.js配置
const initChartConfig = () => {
  // 确保Chart对象存在
  if (typeof Chart === 'undefined') {
    console.error('Chart.js 未加载');
    return;
  }

  // 设置全局默认值
  Chart.defaults.responsive = true;
  Chart.defaults.maintainAspectRatio = false;
  Chart.defaults.font.family = getComputedStyle(document.documentElement).getPropertyValue('--font-family-base').trim();
  
  // 获取当前主题
  const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
  
  // 设置全局颜色
  const textColor = isDarkMode ? 'rgba(255, 255, 255, 0.7)' : 'rgba(0, 0, 0, 0.7)';
  const gridColor = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
  
  // 设置全局字体颜色
  Chart.defaults.color = textColor;
  
  // 设置全局网格线颜色
  Chart.defaults.scale.grid.color = gridColor;
  Chart.defaults.scale.grid.borderColor = gridColor;
  
  // 设置全局刻度线颜色
  Chart.defaults.scale.ticks.color = textColor;
  
  // 设置全局图例样式
  Chart.defaults.plugins.legend.labels.color = textColor;
  
  // 设置全局提示框样式
  Chart.defaults.plugins.tooltip.backgroundColor = isDarkMode ? 'rgba(31, 31, 31, 0.9)' : 'rgba(0, 0, 0, 0.75)';
  Chart.defaults.plugins.tooltip.titleColor = isDarkMode ? '#ffffff' : '#ffffff';
  Chart.defaults.plugins.tooltip.bodyColor = isDarkMode ? 'rgba(255, 255, 255, 0.7)' : '#ffffff';
  Chart.defaults.plugins.tooltip.borderColor = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.cornerRadius = 4;
  Chart.defaults.plugins.tooltip.titleMarginBottom = 8;
  Chart.defaults.plugins.tooltip.bodySpacing = 4;
  Chart.defaults.plugins.tooltip.displayColors = true;
  Chart.defaults.plugins.tooltip.boxPadding = 3;
  Chart.defaults.plugins.tooltip.usePointStyle = true;
  Chart.defaults.plugins.tooltip.callbacks = {
    ...Chart.defaults.plugins.tooltip.callbacks,
    labelPointStyle: function(context) {
      return {
        pointStyle: 'circle',
        rotation: 0
      };
    }
  };
  
  // 添加自定义类名到提示框
  Chart.defaults.plugins.tooltip.callbacks.beforeLabel = function(context) {
    const tooltipEl = document.querySelector('.chart-js-tooltip');
    if (tooltipEl) {
      tooltipEl.classList.add('chart-js-tooltip');
      const tooltipHeader = tooltipEl.querySelector('.tooltip-header');
      if (tooltipHeader) {
        tooltipHeader.classList.add('chart-js-tooltip-header');
      }
    }
    return context.dataset.label + ': ' + context.formattedValue;
  };
};

// 创建图表配置
const createChartConfig = (type, labels, datasets, options = {}) => {
  // 获取当前主题
  const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
  
  // 基础配置
  const baseConfig = {
    type: type,
    data: {
      labels: labels,
      datasets: datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          mode: 'index',
          intersect: false
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: {
            color: isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'
          }
        },
        x: {
          grid: {
            color: isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'
          }
        }
      },
      ...options
    }
  };
  
  return baseConfig;
};

// 更新图表主题
const updateChartsTheme = () => {
  // 获取当前主题
  const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
  
  // 文本和网格颜色
  const textColor = isDarkMode ? 'rgba(255, 255, 255, 0.7)' : 'rgba(0, 0, 0, 0.7)';
  const gridColor = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
  
  // 更新全局配置
  Chart.defaults.color = textColor;
  Chart.defaults.scale.grid.color = gridColor;
  Chart.defaults.scale.grid.borderColor = gridColor;
  Chart.defaults.scale.ticks.color = textColor;
  Chart.defaults.plugins.legend.labels.color = textColor;
  Chart.defaults.plugins.tooltip.backgroundColor = isDarkMode ? 'rgba(31, 31, 31, 0.9)' : 'rgba(0, 0, 0, 0.75)';
  
  // 获取所有图表实例并更新
  Object.values(Chart.instances).forEach(chart => {
    // 更新网格线颜色
    if (chart.config.options.scales && chart.config.options.scales.y) {
      chart.config.options.scales.y.grid.color = gridColor;
      chart.config.options.scales.y.ticks.color = textColor;
    }
    
    if (chart.config.options.scales && chart.config.options.scales.x) {
      chart.config.options.scales.x.grid.color = gridColor;
      chart.config.options.scales.x.ticks.color = textColor;
    }
    
    // 更新图例颜色
    if (chart.config.options.plugins && chart.config.options.plugins.legend) {
      chart.config.options.plugins.legend.labels.color = textColor;
    }
    
    // 更新提示框颜色
    if (chart.config.options.plugins && chart.config.options.plugins.tooltip) {
      chart.config.options.plugins.tooltip.backgroundColor = isDarkMode ? 'rgba(31, 31, 31, 0.9)' : 'rgba(0, 0, 0, 0.75)';
    }
    
    // 重新渲染图表
    chart.update();
  });
};

// 监听主题变化
const setupThemeChangeListener = () => {
  // 创建一个MutationObserver来监听data-theme属性的变化
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
        updateChartsTheme();
      }
    });
  });
  
  // 开始观察document.documentElement的data-theme属性
  observer.observe(document.documentElement, { attributes: true });
  
  // 监听主题切换按钮点击
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      // 主题切换后会触发MutationObserver
      setTimeout(updateChartsTheme, 50); // 添加小延迟确保DOM已更新
    });
  }
};

// 创建响应式图表
const createResponsiveChart = (chartId, type, labels, datasets, options = {}) => {
  const chartElement = document.getElementById(chartId);
  if (!chartElement) {
    console.error(`未找到ID为${chartId}的元素`);
    return null;
  }
  
  // 创建图表配置
  const config = createChartConfig(type, labels, datasets, options);
  
  // 创建图表实例
  const chart = new Chart(chartElement.getContext('2d'), config);
  
  return chart;
};

// 初始化所有图表
const initAllCharts = () => {
  // 初始化全局配置
  initChartConfig();
  
  // 设置主题变化监听器
  setupThemeChangeListener();
  
  // 初始化用户增长趋势图
  if (document.getElementById('userGrowthChart')) {
    const userLabels = Array.from(document.querySelectorAll('[data-user-growth-label]')).map(el => el.dataset.userGrowthLabel);
    const userData = Array.from(document.querySelectorAll('[data-user-growth-value]')).map(el => parseInt(el.dataset.userGrowthValue));
    
    if (userLabels.length > 0 && userData.length > 0) {
      createResponsiveChart('userGrowthChart', 'line', userLabels, [{
        label: '新增用户',
        data: userData,
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.1)',
        tension: 0.4,
        fill: true
      }]);
    }
  }
  
  // 初始化对话活跃度趋势图
  if (document.getElementById('dialogTrendChart')) {
    const dialogLabels = Array.from(document.querySelectorAll('[data-dialog-trend-label]')).map(el => el.dataset.dialogTrendLabel);
    const dialogData = Array.from(document.querySelectorAll('[data-dialog-trend-value]')).map(el => parseInt(el.dataset.dialogTrendValue));
    
    if (dialogLabels.length > 0 && dialogData.length > 0) {
      createResponsiveChart('dialogTrendChart', 'line', dialogLabels, [{
        label: '对话数量',
        data: dialogData,
        borderColor: 'rgb(40, 167, 69)',
        backgroundColor: 'rgba(40, 167, 69, 0.1)',
        tension: 0.4,
        fill: true
      }]);
    }
  }
  
  // 初始化Token消耗趋势图
  if (document.getElementById('tokenTrendChart')) {
    const tokenLabels = Array.from(document.querySelectorAll('[data-token-trend-label]')).map(el => el.dataset.tokenTrendLabel);
    const tokenData = Array.from(document.querySelectorAll('[data-token-trend-value]')).map(el => parseInt(el.dataset.tokenTrendValue));
    
    if (tokenLabels.length > 0 && tokenData.length > 0) {
      createResponsiveChart('tokenTrendChart', 'line', tokenLabels, [{
        label: 'Token消耗',
        data: tokenData,
        borderColor: 'rgb(255, 193, 7)',
        backgroundColor: 'rgba(255, 193, 7, 0.1)',
        tension: 0.4,
        fill: true
      }], {
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: function(value) {
                if (value >= 1000000) {
                  return (value / 1000000).toFixed(1) + 'M';
                } else if (value >= 1000) {
                  return (value / 1000).toFixed(1) + 'K';
                }
                return value;
              }
            }
          }
        }
      });
    }
  }
  
  // 初始化群聊活跃趋势图
  if (document.getElementById('groupTrendChart')) {
    const groupLabels = Array.from(document.querySelectorAll('[data-group-trend-label]')).map(el => el.dataset.groupTrendLabel);
    const groupData = Array.from(document.querySelectorAll('[data-group-trend-value]')).map(el => parseInt(el.dataset.groupTrendValue));
    
    if (groupLabels.length > 0 && groupData.length > 0) {
      createResponsiveChart('groupTrendChart', 'line', groupLabels, [{
        label: '群聊消息',
        data: groupData,
        borderColor: 'rgb(23, 162, 184)',
        backgroundColor: 'rgba(23, 162, 184, 0.1)',
        tension: 0.4,
        fill: true
      }]);
    }
  }
};

// 当DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', initAllCharts);

// 导出函数供其他模块使用
window.chartUtils = {
  createResponsiveChart,
  updateChartsTheme,
  createChartConfig
};