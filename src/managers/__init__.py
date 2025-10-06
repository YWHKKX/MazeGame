"""游戏管理器模块"""

from .resource_manager import ResourceManager, get_resource_manager, reset_resource_manager, ResourceInfo

__all__ = [
    'ResourceManager',
    'get_resource_manager',
    'reset_resource_manager',
    'ResourceInfo'
]
