#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一字体管理器模块
"""

import pygame
import emoji
from src.core import emoji_constants


class UnifiedFontManager:
    """统一字体管理器 - 整合Emoji和中文字体管理功能"""

    def __init__(self):
        """初始化统一字体管理器"""
        print("🔧 初始化统一字体管理器...")

        # 字体实例
        self.chinese_font_name = None
        self.emoji_font_name = None
        self.english_font_name = None
        self.emoji_mapper = None
        self._fonts_initialized = False

        print("✅ 统一字体管理器初始化完成")

    def _ensure_fonts_initialized(self):
        """确保字体已初始化（延迟初始化）"""
        if not self._fonts_initialized:
            try:
                # 检查pygame是否已初始化
                if not pygame.get_init():
                    print("⚠️ pygame未初始化，跳过字体初始化")
                    return
                self._initialize_fonts()
                self._fonts_initialized = True
            except Exception as e:
                print(f"⚠️ 字体初始化失败: {e}")
                self._fonts_initialized = True  # 标记为已尝试，避免重复尝试

    def _initialize_fonts(self):
        """初始化所有字体系统"""
        print("🔤 初始化字体系统...")

        # 中文字体优先级列表
        chinese_fonts = [
            'Microsoft YaHei',      # Windows 微软雅黑
            'SimHei',              # Windows 黑体
            'SimSun',              # Windows 宋体
            'Microsoft JhengHei',  # Windows 微软正黑体
            'PingFang SC',         # macOS 苹方
            'Hiragino Sans GB',    # macOS 冬青黑体
            'STHeiti',             # macOS 华文黑体
            'WenQuanYi Micro Hei',  # Linux 文泉驿微米黑
            'Noto Sans CJK SC',    # Linux Google Noto
            'DejaVu Sans',         # 通用备选字体
            'Arial Unicode MS',    # Unicode支持字体
            'Tahoma'               # 最后备选
        ]

        # 表情符号字体优先级列表 - 基于测试结果的改进字体选择
        emoji_fonts = [
            'Segoe UI Emoji',      # Windows 表情符号字体 (100%支持率)
            'Segoe UI Symbol',     # Windows 符号字体 (100%支持率)
            'Microsoft YaHei UI',  # Windows 微软雅黑UI (100%支持率)
            'Microsoft YaHei',     # Windows 微软雅黑 (100%支持率)
            'SimHei',             # Windows 黑体 (100%支持率)
            'SimSun',             # Windows 宋体 (100%支持率)
            'Microsoft JhengHei',  # Windows 微软正黑体 (100%支持率)
            'Arial Unicode MS',    # 通用Unicode字体 (100%支持率)
            'Tahoma',             # Windows 字体 (100%支持率)
            'Arial',              # 通用字体 (100%支持率)
            'Calibri',            # Windows 字体 (100%支持率)
            'Segoe UI',           # Windows 字体 (100%支持率)
            'Noto Color Emoji',    # Linux Google字体
            'Apple Color Emoji',   # macOS 表情符号字体
            'DejaVu Sans',         # 通用字体
            'sans-serif'           # 系统默认 (100%支持率)
        ]

        # 尝试找到可用的中文字体
        for font_name in chinese_fonts:
            try:
                test_font = pygame.font.SysFont(font_name, 24)
                # 测试渲染中文和表情符号
                test_texts = ["测试中文", emoji_constants.GAME,
                              emoji_constants.MONEY, emoji_constants.COMBAT]
                font_works = True

                for test_text in test_texts:
                    try:
                        test_surface = test_font.render(
                            test_text, True, (255, 255, 255))
                        if test_surface.get_width() < 5:  # 如果渲染出来宽度太小，可能不支持
                            font_works = False
                            break
                    except Exception as e:
                        font_works = False
                        break

                if font_works:
                    self.chinese_font_name = font_name
                    print(f"{emoji_constants.CHECK} 找到中文字体: {font_name}")
                    break
            except Exception as e:
                continue

        if not self.chinese_font_name:
            print("⚠️ 未找到理想的中文字体，将使用默认字体")
            self.chinese_font_name = None

        # 尝试找到可用的表情符号字体 - 基于测试结果的改进方法
        for font_name in emoji_fonts:
            try:
                test_font = pygame.font.SysFont(font_name, 24)
                # 测试多个emoji字符
                test_chars = [emoji_constants.CASTLE, emoji_constants.MONSTER,
                              emoji_constants.MONEY, emoji_constants.GAME]
                font_works = True

                for char in test_chars:
                    try:
                        test_surface = test_font.render(
                            char, True, (255, 255, 255))
                        # 检查渲染结果是否有效
                        if test_surface.get_width() < 5 or test_surface.get_height() < 5:
                            font_works = False
                            break

                        # 额外检查：确保不是空白渲染
                        # 通过检查像素来判断是否有实际内容
                        try:
                            pixels = pygame.surfarray.array3d(test_surface)
                            if pixels.sum() == 0:  # 完全是黑色（空白）
                                font_works = False
                                break
                        except:
                            # 如果无法检查像素，至少检查尺寸
                            if test_surface.get_width() < 10:
                                font_works = False
                                break
                    except:
                        font_works = False
                        break

                if font_works:
                    self.emoji_font_name = font_name
                    print(f"✅ 找到表情符号字体: {font_name}")
                    break
                else:
                    print(f"⚠️ 字体 {font_name} emoji支持不完整")
            except Exception as e:
                print(f"❌ 字体 {font_name} 加载失败: {e}")
                continue

        # 如果没有找到专门的表情符号字体，尝试使用中文字体
        if not self.emoji_font_name and self.chinese_font_name:
            try:
                test_font = pygame.font.SysFont(self.chinese_font_name, 24)
                test_surface = test_font.render(
                    emoji_constants.CASTLE, True, (255, 255, 255))
                if test_surface.get_width() > 10:
                    self.emoji_font_name = self.chinese_font_name
                    print(
                        f"{emoji_constants.CHECK} 使用中文字体支持表情符号: {self.chinese_font_name}")
            except:
                pass

        if not self.emoji_font_name:
            print("⚠️ 未找到表情符号字体，将使用文本替代")
            self.emoji_font_name = 'default'

    def get_font(self, size=24):
        """获取中文字体 - 增强版"""
        self._ensure_fonts_initialized()

        # 尝试多个字体选项
        font_candidates = []

        if self.chinese_font_name:
            font_candidates.append(self.chinese_font_name)

        # 添加更多备选字体
        font_candidates.extend([
            'Microsoft YaHei',
            'SimHei',
            'SimSun',
            'Arial Unicode MS',
            'Tahoma',
            'Arial'
        ])

        for font_name in font_candidates:
            try:
                font = pygame.font.SysFont(font_name, size)
                # 测试字体是否正常工作
                test_surface = font.render("测试", True, (255, 255, 255))
                if test_surface.get_width() > 10:
                    return font
            except:
                continue

        # 最后回退到默认字体
        try:
            return pygame.font.Font(None, size)
        except:
            return pygame.font.SysFont('arial', size)

    def get_emoji_font(self, size=24):
        """获取Emoji字体 - 改进的编码处理"""
        self._ensure_fonts_initialized()

        try:
            if self.emoji_font_name and self.emoji_font_name != 'default':
                # 使用SysFont而不是Font，更好的编码支持
                return pygame.font.SysFont(self.emoji_font_name, size)
            else:
                # 使用系统默认字体，通常对Unicode支持更好
                # 根据测试结果，sans-serif在Windows上支持emoji
                return pygame.font.SysFont('sans-serif', size)
        except Exception as e:
            print(f"⚠️ emoji字体获取失败: {e}")
            # 最后的回退方案
            try:
                return pygame.font.Font(None, size)
            except:
                return pygame.font.SysFont('arial', size)

    def safe_render(self, font, text, color=(255, 255, 255), use_emoji_fallback=False):
        """安全渲染文本 - 正确区分emoji和中文字符"""
        self._ensure_fonts_initialized()

        # 检查文本是否包含真正的emoji字符（而不是中文）
        has_emoji = self._contains_emoji(text)
        has_chinese = self._contains_chinese(text)

        # 优先处理纯emoji的情况
        if has_emoji and not has_chinese:
            # 如果只有emoji字符，使用emoji字体渲染
            try:
                emoji_font = self.get_emoji_font(font.get_height())
                surface = emoji_font.render(text, True, color)
                if surface.get_width() > 0 and surface.get_height() > 0:
                    return surface
            except Exception as e:
                print(f"⚠️ emoji字体渲染失败: {e}")

        # 处理包含中文的情况
        if has_chinese:
            # 优先使用中文字体
            try:
                chinese_font = self.get_font(font.get_height())
                surface = chinese_font.render(text, True, color)
                if surface.get_width() > 0 and surface.get_height() > 0:
                    return surface
            except Exception as e:
                print(f"⚠️ 中文字体渲染失败: {e}")

        # 如果表情符号映射器可用，尝试使用图片
        if self.emoji_mapper and has_emoji:
            # 检查是否包含表情符号
            emojis_in_text = []
            for char in text:
                if char in self.emoji_mapper.EMOJI_MAPPING:
                    emojis_in_text.append(char)

            if emojis_in_text:
                # 如果文本只包含一个表情符号，直接返回图片
                if len(emojis_in_text) == 1 and len(text.strip()) == 1:
                    emoji = emojis_in_text[0]
                    image = self.emoji_mapper.get_image(emoji)
                    if image:
                        # 缩放图片到合适大小
                        target_size = 32  # 默认大小
                        if image.get_width() > target_size or image.get_height() > target_size:
                            scale = min(target_size / image.get_width(),
                                        target_size / image.get_height())
                            new_width = int(image.get_width() * scale)
                            new_height = int(image.get_height() * scale)
                            image = pygame.transform.scale(
                                image, (new_width, new_height))
                        return image

        # 回退到原有的文本渲染逻辑
        return self._render_text_fallback(font, text, color)

    def _contains_emoji(self, text):
        """检查文本是否包含emoji字符"""
        emoji_ranges = [
            (0x1F600, 0x1F64F),  # 表情符号
            (0x1F300, 0x1F5FF),  # 杂项符号和象形文字
            (0x1F680, 0x1F6FF),  # 交通和地图符号
            (0x1F1E0, 0x1F1FF),  # 区域指示符号
            (0x2600, 0x26FF),    # 杂项符号
            (0x2700, 0x27BF),    # 装饰符号
            (0x1F900, 0x1F9FF),  # 补充符号和象形文字
        ]

        for char in text:
            char_code = ord(char)
            for start, end in emoji_ranges:
                if start <= char_code <= end:
                    return True
        return False

    def _contains_chinese(self, text):
        """检查文本是否包含中文字符"""
        for char in text:
            char_code = ord(char)
            # 中文Unicode范围
            if (0x4E00 <= char_code <= 0x9FFF or  # CJK统一汉字
                0x3400 <= char_code <= 0x4DBF or  # CJK扩展A
                    0x20000 <= char_code <= 0x2A6DF):  # CJK扩展B
                return True
        return False

    def render_emoji_text(self, text, font, color=(255, 255, 255)):
        """渲染包含Emoji的文本 - 正确的emoji短代码转换"""
        self._ensure_fonts_initialized()

        try:
            # 第一步：将emoji短代码转换为Unicode字符
            unicode_text = self._convert_emoji_shortcodes_to_unicode(text)

            # 第二步：使用emoji字体渲染Unicode字符
            emoji_font = self.get_emoji_font(font.get_height())

            # 尝试使用emoji字体渲染Unicode字符
            surface = emoji_font.render(unicode_text, True, color)

            # 检查渲染结果
            if surface.get_width() > 0 and surface.get_height() > 0:
                return surface

            # 如果emoji字体失败，尝试原始字体渲染Unicode字符
            surface = font.render(unicode_text, True, color)
            if surface.get_width() > 0 and surface.get_height() > 0:
                return surface

            # 最后的回退方案：转换为文本描述
            fallback_text = self._convert_emoji_to_text(unicode_text)
            return font.render(fallback_text, True, color)

        except Exception as e:
            print(f"⚠️ 文本渲染失败: {e}")
            # 紧急回退方案
            fallback_text = self._convert_emoji_to_text(text)
            return font.render(fallback_text, True, color)

    def _render_text_fallback(self, font, text, color):
        """回退文本渲染方法"""
        try:
            return font.render(text, True, color)
        except:
            # 如果字体渲染失败，使用默认字体
            try:
                default_font = pygame.font.Font(None, 24)
                return default_font.render(text, True, color)
            except:
                # 最后的回退方案 - 创建透明表面而不是黑色表面
                surface = pygame.Surface((100, 24), pygame.SRCALPHA)
                return surface

    def _convert_emoji_shortcodes_to_unicode(self, text):
        """将emoji短代码转换为Unicode字符"""
        try:
            # 使用emoji库将短代码转换为Unicode字符
            # 注意：新版本的emoji库不再支持use_aliases参数
            converted_text = emoji.emojize(text)

            # 调试输出
            if text != converted_text:
                print(f"🔄 Emoji转换: '{text}' -> '{converted_text}'")

            return converted_text
        except Exception as e:
            print(f"⚠️ Emoji转换失败: {e}")
            return text  # 如果转换失败，返回原文本

    def _convert_emoji_to_text(self, text):
        """将emoji转换为文本描述 - 改进的回退机制"""
        # emoji到文本的映射表
        emoji_to_text = {
            '🎮': '[游戏]',
            '🎯': '[目标]',
            '⚔️': '[战斗]',
            '👹': '[怪物]',
            '💰': '[金币]',
            '⛏️': '[挖掘]',
            '🏰': '[城堡]',
            '💖': '[心形]',
            '🔨': '[锤子]',
            '🛑': '[停止]',
            '📚': '[书籍]',
            '🔍': '[搜索]',
            '✅': '[确认]',
            '⚠️': '[警告]',
            '❌': '[错误]',
            '🏗️': '[建造]',
            '📝': '[笔记]',
            '📤': '[发送]',
            '🎒': '[背包]',
            '💀': '[骷髅]',
            '🗡️': '[剑]',
            '🛡️': '[盾牌]',
            '💚': '[绿心]',
            '🔤': '[字母]',
            '📊': '[图表]',
            '📷': '[相机]',
            '🚀': '[火箭]',
            '🧙': '[法师]',
            '🌿': '[植物]',
            '🗿': '[石头]',
            '👑': '[王冠]',
            '🐲': '[龙]',
            '🔥': '[火焰]',
            '🦅': '[鹰]',
            '🦎': '[蜥蜴]',
            '🛠️': '[工具]'
        }

        # 替换emoji为文本
        result = text
        for emoji_char, text_desc in emoji_to_text.items():
            result = result.replace(emoji_char, text_desc)

        return result

    @staticmethod
    def safe_render_static(font, text, color):
        """静态方法：安全渲染文本，优先使用图片"""
        # 尝试使用全局表情符号映射器
        try:
            from img.emoji_mapping import EmojiImageMapper
            try:
                mapper = EmojiImageMapper()
                if any(ord(char) > 127 for char in text):
                    # 检查是否包含表情符号
                    emojis_in_text = []
                    for char in text:
                        if ord(char) > 127 and char in mapper.EMOJI_MAPPING:
                            emojis_in_text.append(char)

                    if emojis_in_text:
                        # 如果文本只包含一个表情符号，直接返回图片
                        if len(emojis_in_text) == 1 and len(text.strip()) == 1:
                            emoji = emojis_in_text[0]
                            image = mapper.get_image(emoji)
                            if image:
                                # 缩放图片到合适大小
                                target_size = 32
                                if image.get_width() > target_size or image.get_height() > target_size:
                                    scale = min(
                                        target_size / image.get_width(), target_size / image.get_height())
                                    new_width = int(image.get_width() * scale)
                                    new_height = int(
                                        image.get_height() * scale)
                                    image = pygame.transform.scale(
                                        image, (new_width, new_height))
                                return image
            except Exception as e:
                pass  # 回退到文本渲染
        except ImportError:
            pass  # 图片映射器不可用，回退到文本渲染

        # 回退到原有的文本渲染逻辑
        return UnifiedFontManager._render_text_fallback_static(font, text, color)

    @staticmethod
    def _render_text_fallback_static(font, text, color):
        """静态回退文本渲染方法"""
        try:
            return font.render(text, True, color)
        except:
            # 如果字体渲染失败，使用默认字体
            try:
                default_font = pygame.font.Font(None, 24)
                return default_font.render(text, True, color)
            except:
                # 最后的回退方案
                return pygame.Surface((100, 24))
