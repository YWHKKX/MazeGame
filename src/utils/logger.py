#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理器
提供统一的日志输出接口，支持不同日志级别和时间戳
"""

import time
import sys
import inspect
import os
import locale
from enum import Enum
from typing import Optional, Any
from datetime import datetime

# 设置Python编码为UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 尝试设置控制台编码为UTF-8（Windows）
try:
    if sys.platform.startswith('win'):
        # 设置Windows控制台代码页为UTF-8
        os.system('chcp 65001 >nul 2>&1')
        # 设置locale为UTF-8
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except (locale.Error, OSError):
    # 如果设置失败，继续使用默认编码
    pass


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Logger:
    """日志管理器"""

    def __init__(self, name: str = "MazeMaster", level: LogLevel = LogLevel.INFO):
        self.name = name
        self.level = level
        self.enabled = True

        # 颜色代码（ANSI）
        self.colors = {
            LogLevel.DEBUG: '\033[36m',    # 青色
            LogLevel.INFO: '\033[32m',     # 绿色
            LogLevel.WARNING: '\033[33m',  # 黄色
            LogLevel.ERROR: '\033[31m',    # 红色
        }
        self.reset_color = '\033[0m'

    def _should_log(self, level: LogLevel) -> bool:
        """检查是否应该输出该级别的日志"""
        if not self.enabled:
            return False

        level_priority = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3
        }

        return level_priority[level] >= level_priority[self.level]

    def _format_message(self, level: LogLevel, message: str) -> str:
        """格式化日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # 精确到毫秒
        color = self.colors.get(level, '')
        reset = self.reset_color

        # 在DEBUG模式下添加函数名
        if level == LogLevel.DEBUG:
            # 获取调用栈，跳过当前方法(_format_message)和_log方法
            frame = inspect.currentframe()
            try:
                # 向上查找调用栈，找到实际的调用函数
                # 跳过 _format_message -> _log -> debug/info/warning/error
                caller_frame = frame.f_back.f_back.f_back
                if caller_frame:
                    function_name = caller_frame.f_code.co_name
                    class_name = ""
                    # 尝试获取类名
                    if 'self' in caller_frame.f_locals:
                        class_name = caller_frame.f_locals['self'].__class__.__name__ + "."
                    return f"{color}[{timestamp}] [{level.value}] [{self.name}] [{class_name}{function_name}] {message}{reset}"
            finally:
                del frame

        return f"{color}[{timestamp}] [{level.value}] [{self.name}] {message}{reset}"

    def _make_emoji_safe(self, message: str) -> str:
        """将emoji字符转换为安全的文本替代"""
        # 常见的emoji替换映射
        emoji_replacements = {
            '🎨': '[美术]', '🗺️': '[地图]', '⛏️': '[挖掘]', '🏗️': '[建造]',
            '⚔️': '[战斗]', '💀': '[死亡]', '🔥': '[火焰]', '💥': '[爆炸]',
            '🛡️': '[盾牌]', '🎯': '[目标]', '🎆': '[烟花]', '💰': '[金币]',
            '🏰': '[城堡]', '💖': '[心形]', '🔨': '[锤子]', '🛑': '[停止]',
            '📚': '[书籍]', '🔍': '[搜索]', '✅': '[确认]', '⚠️': '[警告]',
            '❌': '[错误]', '📝': '[笔记]', '📤': '[发送]', '🎒': '[背包]',
            '🗡️': '[剑]', '💚': '[绿心]', '🔤': '[字母]', '📊': '[图表]',
            '📷': '[相机]', '🚀': '[火箭]', '🧙': '[法师]', '🌿': '[植物]',
            '🗿': '[石头]', '👑': '[王冠]', '🐲': '[龙]', '🦅': '[鹰]',
            '🦎': '[蜥蜴]', '🛠️': '[工具]', '🧙‍♂️': '[男法师]', '⏸️': '[暂停]',
            '▶️': '[播放]', '🔓': '[解锁]', '🔧': '[工具]', '🎮': '[游戏]',
            '📐': '[尺寸]', '🔍': '[放大]', '👹': '[怪物]', '💖': '[心形]',
            '📝': '[笔记]', '📤': '[发送]', '🎒': '[背包]', '🔤': '[字母]',
            '📊': '[图表]', '📷': '[相机]', '🚀': '[火箭]', '🧙': '[法师]',
            '🌿': '[植物]', '🗿': '[石头]', '👑': '[王冠]', '🐲': '[龙]',
            '🦅': '[鹰]', '🦎': '[蜥蜴]', '🛠️': '[工具]', '🧙‍♂️': '[男法师]'
        }

        # 替换emoji字符
        safe_message = message
        for emoji, replacement in emoji_replacements.items():
            safe_message = safe_message.replace(emoji, replacement)

        return safe_message

    def _convert_to_ascii_safe(self, message: str) -> str:
        """将消息转换为ASCII安全版本"""
        try:
            # 尝试编码为ASCII
            return message.encode('ascii', 'replace').decode('ascii')
        except (UnicodeEncodeError, UnicodeDecodeError):
            # 如果失败，返回简化版本
            return message.encode('utf-8', 'replace').decode('utf-8', 'replace')

    def _log(self, level: LogLevel, message: str, *args, **kwargs):
        """内部日志输出方法"""
        if not self._should_log(level):
            return

        if args:
            message = message.format(*args)
        if kwargs:
            message = message.format(**kwargs)

        # 处理emoji兼容性
        safe_message = self._make_emoji_safe(message)
        formatted_message = self._format_message(level, safe_message)

        try:
            print(formatted_message, file=sys.stdout if level !=
                  LogLevel.ERROR else sys.stderr)
            sys.stdout.flush()
        except UnicodeEncodeError:
            # 如果仍然出现编码错误，使用ASCII安全版本
            ascii_message = self._convert_to_ascii_safe(message)
            safe_formatted_message = self._format_message(level, ascii_message)
            print(safe_formatted_message, file=sys.stdout if level !=
                  LogLevel.ERROR else sys.stderr)
            sys.stdout.flush()

    def debug(self, message: str, *args, **kwargs):
        """调试日志"""
        self._log(LogLevel.DEBUG, message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        """信息日志"""
        self._log(LogLevel.INFO, message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """警告日志"""
        self._log(LogLevel.WARNING, message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """错误日志"""
        self._log(LogLevel.ERROR, message, *args, **kwargs)

    def set_level(self, level: LogLevel):
        """设置日志级别"""
        self.level = level

    def enable(self):
        """启用日志"""
        self.enabled = True

    def disable(self):
        """禁用日志"""
        self.enabled = False


# 全局日志管理器实例
_global_logger: Optional[Logger] = None


def get_logger(name: str = "MazeMaster") -> Logger:
    """获取日志管理器实例"""
    global _global_logger
    if _global_logger is None:
        _global_logger = Logger(name)
    return _global_logger


def set_global_log_level(level: LogLevel):
    """设置全局日志级别"""
    logger = get_logger()
    logger.set_level(level)


def enable_logging():
    """启用全局日志"""
    logger = get_logger()
    logger.enable()


def disable_logging():
    """禁用全局日志"""
    logger = get_logger()
    logger.disable()


# 便捷函数
def debug(message: str, *args, **kwargs):
    """全局调试日志"""
    get_logger().debug(message, *args, **kwargs)


def info(message: str, *args, **kwargs):
    """全局信息日志"""
    get_logger().info(message, *args, **kwargs)


def warning(message: str, *args, **kwargs):
    """全局警告日志"""
    get_logger().warning(message, *args, **kwargs)


def error(message: str, *args, **kwargs):
    """全局错误日志"""
    get_logger().error(message, *args, **kwargs)


# 全局日志实例，供整个游戏使用
game_logger = get_logger("MazeMaster")
