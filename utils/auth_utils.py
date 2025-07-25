"""
统一认证和权限管理工具模块

该模块提供统一的认证和基于角色的访问控制(RBAC)功能，
支持会话管理、权限验证和安全性优化。
"""

import os
import json
import hashlib
import secrets
import time
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional, Any, Tuple
from flask import session, request, redirect, url_for, flash, current_app

from utils.config_utils import get_config

logger = logging.getLogger(__name__)

# 权限级别定义
class Permission:
    """权限级别常量"""
    ADMIN = 'admin'
    VIEWER = 'viewer'
    
    # 权限层级（数字越大权限越高）
    LEVELS = {
        VIEWER: 1,
        ADMIN: 2
    }
    
    @classmethod
    def has_permission(cls, user_permission: str, required_permission: str) -> bool:
        """检查用户是否具有所需权限"""
        user_level = cls.LEVELS.get(user_permission, 0)
        required_level = cls.LEVELS.get(required_permission, 0)
        return user_level >= required_level

class AuthConfig:
    """认证配置管理"""
    
    @staticmethod
    def get_passwords() -> Dict[str, str]:
        """获取认证密码配置"""
        return {
            'admin': get_config('auth.WEB_PW') or get_config('WEB_PW', '123456'),
            'viewer': get_config('auth.VIEWER_PW') or get_config('VIEWER_PW', 'viewer123')
        }
    
    @staticmethod
    def get_admin_ids() -> List[int]:
        """获取管理员ID列表"""
        admin_ids = get_config('auth.ADMIN') or get_config('ADMIN', [])
        return admin_ids if isinstance(admin_ids, list) else []
    
    @staticmethod
    def get_session_timeout() -> int:
        """获取会话超时时间（秒）"""
        return get_config('session.timeout', 3600)  # 默认1小时
    
    @staticmethod
    def get_max_login_attempts() -> int:
        """获取最大登录尝试次数"""
        return get_config('security.max_login_attempts', 5)
    
    @staticmethod
    def get_lockout_duration() -> int:
        """获取账户锁定时间（秒）"""
        return get_config('security.lockout_duration', 300)  # 默认5分钟

class SessionManager:
    """会话管理器"""
    
    @staticmethod
    def create_session(user_permission: str, user_data: Optional[Dict] = None) -> str:
        """创建用户会话"""
        session_id = secrets.token_urlsafe(32)
        current_time = time.time()
        
        session['logged_in'] = True
        session['user_permission'] = user_permission
        session['session_id'] = session_id
        session['login_time'] = current_time
        session['last_activity'] = current_time
        
        if user_data:
            session['user_data'] = user_data
        
        logger.info(f"用户会话创建成功: permission={user_permission}, session_id={session_id}")
        return session_id
    
    @staticmethod
    def validate_session() -> bool:
        """验证会话有效性"""
        if 'logged_in' not in session:
            return False
        
        current_time = time.time()
        last_activity = session.get('last_activity', 0)
        timeout = AuthConfig.get_session_timeout()
        
        # 检查会话是否超时
        if current_time - last_activity > timeout:
            SessionManager.destroy_session()
            logger.info("会话超时，已清除")
            return False
        
        # 更新最后活动时间
        session['last_activity'] = current_time
        return True
    
    @staticmethod
    def destroy_session():
        """销毁用户会话"""
        session_id = session.get('session_id', 'unknown')
        session.clear()
        logger.info(f"用户会话已销毁: session_id={session_id}")
    
    @staticmethod
    def get_user_permission() -> Optional[str]:
        """获取当前用户权限"""
        if SessionManager.validate_session():
            return session.get('user_permission')
        return None
    
    @staticmethod
    def get_session_info() -> Dict[str, Any]:
        """获取会话信息"""
        if not SessionManager.validate_session():
            return {}
        
        return {
            'user_permission': session.get('user_permission'),
            'session_id': session.get('session_id'),
            'login_time': session.get('login_time'),
            'last_activity': session.get('last_activity'),
            'user_data': session.get('user_data', {})
        }

class SecurityManager:
    """安全管理器"""
    
    # 登录尝试记录（实际应用中应使用Redis或数据库）
    _login_attempts: Dict[str, Dict] = {}
    
    @classmethod
    def record_login_attempt(cls, ip_address: str, success: bool):
        """记录登录尝试"""
        current_time = time.time()
        
        if ip_address not in cls._login_attempts:
            cls._login_attempts[ip_address] = {
                'attempts': 0,
                'last_attempt': current_time,
                'locked_until': 0
            }
        
        attempt_data = cls._login_attempts[ip_address]
        
        if success:
            # 登录成功，清除尝试记录
            attempt_data['attempts'] = 0
            attempt_data['locked_until'] = 0
        else:
            # 登录失败，增加尝试次数
            attempt_data['attempts'] += 1
            attempt_data['last_attempt'] = current_time
            
            # 检查是否需要锁定
            max_attempts = AuthConfig.get_max_login_attempts()
            if attempt_data['attempts'] >= max_attempts:
                lockout_duration = AuthConfig.get_lockout_duration()
                attempt_data['locked_until'] = current_time + lockout_duration
                logger.warning(f"IP {ip_address} 因多次登录失败被锁定")
    
    @classmethod
    def is_ip_locked(cls, ip_address: str) -> bool:
        """检查IP是否被锁定"""
        if ip_address not in cls._login_attempts:
            return False
        
        attempt_data = cls._login_attempts[ip_address]
        current_time = time.time()
        
        return current_time < attempt_data.get('locked_until', 0)
    
    @classmethod
    def get_remaining_lockout_time(cls, ip_address: str) -> int:
        """获取剩余锁定时间（秒）"""
        if ip_address not in cls._login_attempts:
            return 0
        
        attempt_data = cls._login_attempts[ip_address]
        current_time = time.time()
        locked_until = attempt_data.get('locked_until', 0)
        
        if current_time < locked_until:
            return int(locked_until - current_time)
        return 0
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """密码哈希（用于未来的密码存储）"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 迭代次数
        )
        
        return password_hash.hex(), salt
    
    @staticmethod
    def verify_password(password: str, password_hash: str, salt: str) -> bool:
        """验证密码"""
        computed_hash, _ = SecurityManager.hash_password(password, salt)
        return secrets.compare_digest(computed_hash, password_hash)

class AuthManager:
    """认证管理器"""
    
    @staticmethod
    def authenticate(password: str, ip_address: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        用户认证
        
        Args:
            password: 用户输入的密码
            ip_address: 用户IP地址
            
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (是否成功, 权限级别, 错误信息)
        """
        # 检查IP是否被锁定
        if SecurityManager.is_ip_locked(ip_address):
            remaining_time = SecurityManager.get_remaining_lockout_time(ip_address)
            error_msg = f"登录失败次数过多，请在 {remaining_time} 秒后重试"
            return False, None, error_msg
        
        # 获取配置的密码
        passwords = AuthConfig.get_passwords()
        
        # 验证密码并确定权限级别
        user_permission = None
        if password == passwords['admin']:
            user_permission = Permission.ADMIN
        elif password == passwords['viewer']:
            user_permission = Permission.VIEWER
        
        success = user_permission is not None
        
        # 记录登录尝试
        SecurityManager.record_login_attempt(ip_address, success)
        
        if success:
            logger.info(f"用户认证成功: permission={user_permission}, ip={ip_address}")
            return True, user_permission, None
        else:
            logger.warning(f"用户认证失败: ip={ip_address}")
            return False, None, "密码错误"
    
    @staticmethod
    def login(password: str, ip_address: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        用户登录
        
        Args:
            password: 用户输入的密码
            ip_address: 用户IP地址
            
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (是否成功, 权限级别, 错误信息)
        """
        success, user_permission, error_msg = AuthManager.authenticate(password, ip_address)
        
        if success:
            # 创建会话
            SessionManager.create_session(user_permission)
            return True, user_permission, None
        
        return False, None, error_msg
    
    @staticmethod
    def logout():
        """用户登出"""
        SessionManager.destroy_session()
    
    @staticmethod
    def get_current_user() -> Dict[str, Any]:
        """获取当前用户信息"""
        session_info = SessionManager.get_session_info()
        if not session_info:
            return {}
        
        return {
            'permission': session_info.get('user_permission'),
            'is_admin': session_info.get('user_permission') == Permission.ADMIN,
            'is_viewer': session_info.get('user_permission') == Permission.VIEWER,
            'login_time': session_info.get('login_time'),
            'session_id': session_info.get('session_id')
        }

def permission_required(required_permission: str):
    """
    权限验证装饰器
    
    Args:
        required_permission: 所需权限级别 ('admin' 或 'viewer')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 验证会话
            if not SessionManager.validate_session():
                flash('请先登录', 'warning')
                return redirect(url_for('login', next=request.url))
            
            user_permission = SessionManager.get_user_permission()
            
            # 检查权限
            if not Permission.has_permission(user_permission, required_permission):
                flash('您没有权限访问此页面', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def admin_required(f):
    """管理员权限装饰器"""
    return permission_required(Permission.ADMIN)(f)

def viewer_required(f):
    """浏览者权限装饰器"""
    return permission_required(Permission.VIEWER)(f)

def get_client_ip() -> str:
    """获取客户端IP地址"""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    elif request.environ.get('HTTP_X_REAL_IP'):
        return request.environ['HTTP_X_REAL_IP']
    else:
        return request.environ.get('REMOTE_ADDR', '127.0.0.1')