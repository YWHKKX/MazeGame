#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一字体管理器模块
"""

import pygame
import emoji
from src.core import emoji_constants
from src.utils.logger import game_logger


class UnifiedFontManager:
    """统一字体管理器 - 整合Emoji和中文字体管理功能"""

    def __init__(self):
        """初始化统一字体管理器"""
        game_logger.info("初始化统一字体管理器...")

        # 字体实例
        self.chinese_font_name = None
        self.emoji_font_name = None
        self.english_font_name = None
        self.emoji_mapper = None
        self._fonts_initialized = False

        game_logger.info("统一字体管理器初始化完成")

    def _ensure_fonts_initialized(self):
        """确保字体已初始化（延迟初始化）"""
        if not self._fonts_initialized:
            try:
                # 检查pygame是否已初始化
                if not pygame.get_init():
                    game_logger.info("pygame未初始化，跳过字体初始化")
                    return
                self._initialize_fonts()
                self._fonts_initialized = True
            except Exception as e:
                game_logger.info(f"字体初始化失败: {e}")
                self._fonts_initialized = True  # 标记为已尝试，避免重复尝试

    def _initialize_fonts(self):
        """初始化所有字体系统"""
        game_logger.info("初始化字体系统...")

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
                    game_logger.info(f"找到中文字体: {font_name}")
                    break
            except Exception as e:
                continue

        if not self.chinese_font_name:
            game_logger.info("未找到理想的中文字体，将使用默认字体")
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
                    game_logger.info(f"找到表情符号字体: {font_name}")
                    break
                else:
                    game_logger.info(f"字体 {font_name} emoji支持不完整")
            except Exception as e:
                game_logger.info(f"字体 {font_name} 加载失败: {e}")
                continue

        # 如果没有找到专门的表情符号字体，尝试使用中文字体
        if not self.emoji_font_name and self.chinese_font_name:
            try:
                test_font = pygame.font.SysFont(self.chinese_font_name, 24)
                test_surface = test_font.render(
                    emoji_constants.CASTLE, True, (255, 255, 255))
                if test_surface.get_width() > 10:
                    self.emoji_font_name = self.chinese_font_name
                    game_logger.info(
                        f"{emoji_constants.CHECK} 使用中文字体支持表情符号: {self.chinese_font_name}")
            except:
                pass

        if not self.emoji_font_name:
            game_logger.info("未找到表情符号字体，将使用文本替代")
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
            game_logger.info(f"⚠️ emoji字体获取失败: {e}")
            # 最后的回退方案
            try:
                return pygame.font.Font(None, size)
            except:
                return pygame.font.SysFont('arial', size)

    def safe_render(self, font, text, color=(255, 255, 255), use_emoji_fallback=False, ui_scale: float = 1.0,
                    antialias: bool = True, background_color=None):
        """
        安全渲染文本 - 正确区分emoji和中文字符，支持抗锯齿和颜色优化

        Args:
            font: 字体对象
            text: 要渲染的文本
            color: 文字颜色 (R, G, B)
            use_emoji_fallback: 是否使用emoji回退
            ui_scale: UI缩放比例
            antialias: 是否启用抗锯齿 (默认True)
            background_color: 背景颜色，None表示透明背景
        """
        self._ensure_fonts_initialized()

        # 检查文本是否包含真正的emoji字符（而不是中文）
        has_emoji = self._contains_emoji(text)
        has_chinese = self._contains_chinese(text)

        # 优先处理纯emoji的情况
        if has_emoji and not has_chinese:
            # 如果只有emoji字符，使用emoji字体渲染
            try:
                emoji_font = self.get_emoji_font(font.get_height())
                surface = emoji_font.render(
                    text, antialias, color, background_color)
                if surface.get_width() > 0 and surface.get_height() > 0:
                    return surface
            except Exception as e:
                game_logger.info(f"⚠️ emoji字体渲染失败: {e}")

        # 处理包含中文的情况
        if has_chinese:
            # 优先使用中文字体
            try:
                chinese_font = self.get_font(font.get_height())
                surface = chinese_font.render(
                    text, antialias, color, background_color)
                if surface.get_width() > 0 and surface.get_height() > 0:
                    return surface
            except Exception as e:
                game_logger.info(f"⚠️ 中文字体渲染失败: {e}")

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
                        # 缩放图片到合适大小，应用UI缩放
                        target_size = int(32 * ui_scale)  # 应用UI缩放
                        if image.get_width() > target_size or image.get_height() > target_size:
                            scale = min(target_size / image.get_width(),
                                        target_size / image.get_height())
                            new_width = int(image.get_width() * scale)
                            new_height = int(image.get_height() * scale)
                            image = pygame.transform.scale(
                                image, (new_width, new_height))
                        return image

        # 回退到原有的文本渲染逻辑
        return self._render_text_fallback(font, text, color, antialias, background_color)

    def _contains_emoji(self, text):
        """检查文本是否包含emoji字符 - 改进的Unicode范围检测"""
        # 完整的Unicode表情符号和符号范围
        emoji_ranges = [
            # 基础表情符号
            (0x1F600, 0x1F64F),  # 表情符号 (Emoticons)
            (0x1F300, 0x1F5FF),  # 杂项符号和象形文字 (Misc Symbols and Pictographs)
            (0x1F680, 0x1F6FF),  # 交通和地图符号 (Transport and Map)
            (0x1F700, 0x1F77F),  # 炼金术符号 (Alchemical Symbols)
            (0x1F780, 0x1F7FF),  # 几何形状扩展 (Geometric Shapes Extended)
            (0x1F800, 0x1F8FF),  # 补充箭头-C (Supplemental Arrows-C)
            (0x1F900, 0x1F9FF),  # 补充符号和象形文字 (Supplemental Symbols and Pictographs)
            (0x1FA00, 0x1FA6F),  # 棋盘符号扩展 (Chess Symbols)
            (0x1FA70, 0x1FAFF),  # 符号和象形文字扩展-A (Symbols and Pictographs Extended-A)

            # 人员相关符号
            (0x1F9D0, 0x1F9FF),  # 人员符号 (Person Symbols)

            # 区域指示符号
            (0x1F1E0, 0x1F1FF),  # 区域指示符号 (Regional Indicator Symbols)

            # 传统符号
            (0x2600, 0x26FF),    # 杂项符号 (Miscellaneous Symbols)
            (0x2700, 0x27BF),    # 装饰符号 (Dingbats)
            (0x27C0, 0x27EF),    # 杂项数学符号-A (Misc Mathematical Symbols-A)
            (0x27F0, 0x27FF),    # 补充箭头-A (Supplemental Arrows-A)

            # 箭头和符号
            (0x2B00, 0x2BFF),    # 杂项符号和箭头 (Misc Symbols and Arrows)
            (0x2E00, 0x2E7F),    # 补充标点符号 (Supplemental Punctuation)

            # 特殊字符
            (0x200D, 0x200D),    # 零宽度连接符 (Zero Width Joiner) - 用于组合表情符号
            (0xFE0F, 0xFE0F),    # 变化选择器-16 (Variation Selector-16) - 用于表情符号变化
            (0xFE0E, 0xFE0E),    # 变化选择器-15 (Variation Selector-15)

            # 其他Unicode符号
            (0x20E0, 0x20FF),    # 组合标记符号 (Combining Diacritical Marks for Symbols)
            (0x2120, 0x212F),    # 字母类符号 (Letterlike Symbols)
            (0x2130, 0x214F),    # 数字形式 (Number Forms)
            (0x2190, 0x21FF),    # 箭头 (Arrows)
            (0x2200, 0x22FF),    # 数学运算符 (Mathematical Operators)
            (0x2300, 0x23FF),    # 杂项技术符号 (Miscellaneous Technical)
            (0x2400, 0x243F),    # 控制图片 (Control Pictures)
            (0x2440, 0x245F),    # 光学字符识别 (Optical Character Recognition)
            (0x2460, 0x24FF),    # 封闭字母数字 (Enclosed Alphanumerics)
            (0x2500, 0x257F),    # 制表符 (Box Drawing)
            (0x2580, 0x259F),    # 方块元素 (Block Elements)
            (0x25A0, 0x25FF),    # 几何形状 (Geometric Shapes)
            (0x2800, 0x28FF),    # 盲文图案 (Braille Patterns)
        ]

        # 检查每个字符
        for char in text:
            char_code = ord(char)
            for start, end in emoji_ranges:
                if start <= char_code <= end:
                    return True

        # 检查组合表情符号（如 🧙‍♂️）
        if '\u200d' in text:  # 零宽度连接符
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

    def render_emoji_text(self, text, font, color=(255, 255, 255), antialias=True, background_color=None):
        """
        渲染包含Emoji的文本 - 正确的emoji短代码转换，支持抗锯齿和背景颜色

        Args:
            text: 要渲染的文本
            font: 字体对象
            color: 文字颜色 (R, G, B)
            antialias: 是否启用抗锯齿 (默认True)
            background_color: 背景颜色，None表示透明背景
        """
        self._ensure_fonts_initialized()

        try:
            # 第一步：将emoji短代码转换为Unicode字符
            unicode_text = self._convert_emoji_shortcodes_to_unicode(text)

            # 第二步：使用emoji字体渲染Unicode字符
            emoji_font = self.get_emoji_font(font.get_height())

            # 尝试使用emoji字体渲染Unicode字符
            surface = emoji_font.render(
                unicode_text, antialias, color, background_color)

            # 检查渲染结果
            if surface.get_width() > 0 and surface.get_height() > 0:
                return surface

            # 如果emoji字体失败，尝试原始字体渲染Unicode字符
            surface = font.render(unicode_text, antialias,
                                  color, background_color)
            if surface.get_width() > 0 and surface.get_height() > 0:
                return surface

            # 最后的回退方案：转换为文本描述
            fallback_text = self._convert_emoji_to_text(unicode_text)
            return font.render(fallback_text, antialias, color, background_color)

        except Exception as e:
            game_logger.info(f"⚠️ 文本渲染失败: {e}")
            # 紧急回退方案
            fallback_text = self._convert_emoji_to_text(text)
            return font.render(fallback_text, antialias, color, background_color)

    def _render_text_fallback(self, font, text, color, antialias=True, background_color=None):
        """
        回退文本渲染方法 - 支持抗锯齿和背景颜色

        Args:
            font: 字体对象
            text: 要渲染的文本
            color: 文字颜色 (R, G, B)
            antialias: 是否启用抗锯齿
            background_color: 背景颜色，None表示透明背景
        """
        try:
            return font.render(text, antialias, color, background_color)
        except:
            # 如果字体渲染失败，使用默认字体
            try:
                default_font = pygame.font.Font(None, 24)
                return default_font.render(text, antialias, color, background_color)
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
                game_logger.info(f"🔄 Emoji转换: '{text}' -> '{converted_text}'")

            return converted_text
        except Exception as e:
            game_logger.info(f"⚠️ Emoji转换失败: {e}")
            return text  # 如果转换失败，返回原文本

    def _convert_emoji_to_text(self, text):
        """将emoji转换为文本描述 - 改进的回退机制"""
        # 扩展的emoji到文本的映射表
        emoji_to_text = {
            # 游戏相关
            '🎮': '[游戏]', '🎯': '[目标]', '⚔️': '[战斗]', '👹': '[怪物]',
            '💰': '[金币]', '⛏️': '[挖掘]', '🏰': '[城堡]', '💖': '[心形]',
            '🔨': '[锤子]', '🛑': '[停止]', '📚': '[书籍]', '🔍': '[搜索]',
            '✅': '[确认]', '⚠️': '[警告]', '❌': '[错误]', '🏗️': '[建造]',
            '📝': '[笔记]', '📤': '[发送]', '🎒': '[背包]', '💀': '[骷髅]',
            '🗡️': '[剑]', '🛡️': '[盾牌]', '💚': '[绿心]', '🔤': '[字母]',
            '📊': '[图表]', '📷': '[相机]', '🚀': '[火箭]', '🧙': '[法师]',
            '🌿': '[植物]', '🗿': '[石头]', '👑': '[王冠]', '🐲': '[龙]',
            '🔥': '[火焰]', '🦅': '[鹰]', '🦎': '[蜥蜴]', '🛠️': '[工具]',

            # 地图和导航相关
            '🗺️': '[地图]', '🧭': '[指南针]', '📍': '[位置]', '🎪': '[马戏团]',
            '🏛️': '[建筑]', '🏟️': '[体育场]', '🏭': '[工厂]', '🏢': '[办公楼]',
            '🏬': '[商场]', '🏪': '[商店]', '🏫': '[学校]', '🏥': '[医院]',
            '🏨': '[酒店]', '🏩': '[爱情酒店]', '🏦': '[银行]', '🏧': '[ATM]',

            # 人员相关（包括组合表情符号）
            '🧙‍♂️': '[男法师]', '🧙‍♀️': '[女法师]', '🧛‍♂️': '[男吸血鬼]', '🧛‍♀️': '[女吸血鬼]',
            '🧚‍♂️': '[男精灵]', '🧚‍♀️': '[女精灵]', '🧜‍♂️': '[男美人鱼]', '🧜‍♀️': '[女美人鱼]',
            '🧝‍♂️': '[男精灵]', '🧝‍♀️': '[女精灵]', '🧞‍♂️': '[男精灵]', '🧞‍♀️': '[女精灵]',
            '🧟‍♂️': '[男僵尸]', '🧟‍♀️': '[女僵尸]', '👨‍💻': '[程序员]', '👩‍💻': '[程序员]',
            '👨‍🎨': '[艺术家]', '👩‍🎨': '[艺术家]', '👨‍🚀': '[宇航员]', '👩‍🚀': '[宇航员]',
            '👨‍⚕️': '[医生]', '👩‍⚕️': '[医生]', '👨‍⚖️': '[法官]', '👩‍⚖️': '[法官]',
            '👨‍✈️': '[飞行员]', '👩‍✈️': '[飞行员]', '👨‍🔬': '[科学家]', '👩‍🔬': '[科学家]',
            '👨‍🔧': '[机械师]', '👩‍🔧': '[机械师]', '👨‍🍳': '[厨师]', '👩‍🍳': '[厨师]',

            # 其他常用表情符号
            '🗂️': '[文件夹]', '🗃️': '[文件盒]', '🗄️': '[文件柜]', '🗑️': '[垃圾桶]',
            '🔒': '[锁定]', '🔓': '[解锁]', '🔏': '[锁定笔]', '🔐': '[锁定钥匙]',
            '🔑': '[钥匙]', '🗝️': '[旧钥匙]', '⚖️': '[天平]', '🔗': '[链接]',
            '⛓️': '[链条]', '🪝': '[钩子]', '🧰': '[工具箱]', '🧲': '[磁铁]',
            '⚗️': '[蒸馏器]', '🧪': '[试管]', '🧫': '[培养皿]', '🧬': '[DNA]',
            '🔬': '[显微镜]', '🔭': '[望远镜]', '📡': '[卫星天线]', '💉': '[注射器]',
            '💊': '[药丸]', '🩹': '[创可贴]', '🩺': '[听诊器]', '🚪': '[门]',
            '🛏️': '[床]', '🛋️': '[沙发]', '🚽': '[马桶]', '🚿': '[淋浴]',
            '🛁': '[浴缸]', '🧴': '[瓶子]', '🧷': '[安全别针]', '🧹': '[扫帚]',
            '🧺': '[篮子]', '🧻': '[纸巾]', '🚰': '[饮水机]', '🪠': '[马桶疏通器]',

            # 动物相关
            '🐶': '[狗]', '🐱': '[猫]', '🐭': '[老鼠]', '🐹': '[仓鼠]',
            '🐰': '[兔子]', '🦊': '[狐狸]', '🐻': '[熊]', '🐼': '[熊猫]',
            '🐨': '[考拉]', '🐯': '[老虎]', '🦁': '[狮子]', '🐮': '[牛]',
            '🐷': '[猪]', '🐸': '[青蛙]', '🐵': '[猴子]', '🙈': '[不看猴子]',
            '🙉': '[不听猴子]', '🙊': '[不说猴子]', '🐒': '[猴子]', '🦍': '[大猩猩]',
            '🦧': '[猩猩]', '🐕': '[狗]', '🦮': '[导盲犬]', '🐕‍🦺': '[服务犬]',
            '🐩': '[贵宾犬]', '🐺': '[狼]', '🦊': '[狐狸]', '🦝': '[浣熊]',
            '🐱': '[猫]', '🐈': '[猫]', '🦁': '[狮子]', '🐯': '[老虎]',
            '🐅': '[老虎]', '🐆': '[豹子]', '🐴': '[马]', '🐎': '[马]',
            '🦄': '[独角兽]', '🦓': '[斑马]', '🦌': '[鹿]', '🐂': '[公牛]',
            '🐃': '[水牛]', '🐄': '[奶牛]', '🐪': '[骆驼]', '🐫': '[双峰骆驼]',
            '🦙': '[羊驼]', '🦒': '[长颈鹿]', '🐘': '[大象]', '🦣': '[猛犸象]',
            '🦏': '[犀牛]', '🦛': '[河马]', '🐭': '[老鼠]', '🐁': '[老鼠]',
            '🐀': '[老鼠]', '🐹': '[仓鼠]', '🐰': '[兔子]', '🐇': '[兔子]',
            '🐿️': '[松鼠]', '🦫': '[海狸]', '🦔': '[刺猬]', '🦇': '[蝙蝠]',
            '🐻': '[熊]', '🐻‍❄️': '[北极熊]', '🐨': '[考拉]', '🐼': '[熊猫]',
            '🦥': '[树懒]', '🦦': '[水獭]', '🦨': '[臭鼬]', '🦘': '[袋鼠]',
            '🦡': '[獾]', '🐾': '[爪印]', '🦃': '[火鸡]', '🐔': '[鸡]',
            '🐓': '[公鸡]', '🐣': '[小鸡]', '🐤': '[小鸡]', '🐥': '[小鸡]',
            '🐦': '[鸟]', '🐧': '[企鹅]', '🕊️': '[鸽子]', '🦅': '[鹰]',
            '🦆': '[鸭子]', '🦢': '[天鹅]', '🦉': '[猫头鹰]', '🦩': '[火烈鸟]',
            '🦚': '[孔雀]', '🦜': '[鹦鹉]', '🐸': '[青蛙]', '🐊': '[鳄鱼]',
            '🐢': '[乌龟]', '🦎': '[蜥蜴]', '🐍': '[蛇]', '🐲': '[龙]',
            '🐉': '[龙]', '🦕': '[蜥脚类恐龙]', '🦖': '[霸王龙]', '🐳': '[鲸鱼]',
            '🐋': '[鲸鱼]', '🐬': '[海豚]', '🦭': '[海豹]', '🐟': '[鱼]',
            '🐠': '[热带鱼]', '🐡': '[河豚]', '🦈': '[鲨鱼]', '🐙': '[章鱼]',
            '🐚': '[贝壳]', '🐌': '[蜗牛]', '🦋': '[蝴蝶]', '🐛': '[虫子]',
            '🐜': '[蚂蚁]', '🐝': '[蜜蜂]', '🐞': '[瓢虫]', '🦗': '[蟋蟀]',
            '🕷️': '[蜘蛛]', '🕸️': '[蜘蛛网]', '🦂': '[蝎子]', '🦟': '[蚊子]',
            '🦠': '[细菌]',

            # 食物相关
            '🍎': '[苹果]', '🍊': '[橙子]', '🍋': '[柠檬]', '🍌': '[香蕉]',
            '🍉': '[西瓜]', '🍇': '[葡萄]', '🍓': '[草莓]', '🫐': '[蓝莓]',
            '🍈': '[甜瓜]', '🍒': '[樱桃]', '🍑': '[桃子]', '🥭': '[芒果]',
            '🍍': '[菠萝]', '🥥': '[椰子]', '🥝': '[猕猴桃]', '🍅': '[番茄]',
            '🍆': '[茄子]', '🥑': '[牛油果]', '🥦': '[西兰花]', '🥬': '[绿叶蔬菜]',
            '🥒': '[黄瓜]', '🌶️': '[辣椒]', '🫑': '[甜椒]', '🌽': '[玉米]',
            '🥕': '[胡萝卜]', '🫒': '[橄榄]', '🧄': '[大蒜]', '🧅': '[洋葱]',
            '🥔': '[土豆]', '🍠': '[红薯]', '🥐': '[羊角面包]', '🥖': '[法棍]',
            '🍞': '[面包]', '🥨': '[椒盐卷饼]', '🥯': '[百吉饼]', '🧀': '[奶酪]',
            '🥚': '[鸡蛋]', '🍳': '[煎蛋]', '🧈': '[黄油]', '🥞': '[煎饼]',
            '🧇': '[华夫饼]', '🥓': '[培根]', '🥩': '[肉]', '🍗': '[鸡肉]',
            '🍖': '[骨头肉]', '🦴': '[骨头]', '🌭': '[热狗]', '🍔': '[汉堡]',
            '🍟': '[薯条]', '🍕': '[披萨]', '🌮': '[玉米饼]', '🌯': '[卷饼]',
            '🫔': '[玉米粉蒸肉]', '🥙': '[填馅面包]', '🧆': '[法拉费]', '🥚': '[鸡蛋]',
            '🍳': '[煎蛋]', '🥘': '[平底锅食物]', '🍲': '[火锅]', '🫕': '[火锅]',
            '🥣': '[碗]', '🥗': '[沙拉]', '🍿': '[爆米花]', '🧈': '[黄油]',
            '🧂': '[盐]', '🥫': '[罐头]', '🍱': '[便当]', '🍘': '[米饼]',
            '🍙': '[饭团]', '🍚': '[米饭]', '🍛': '[咖喱饭]', '🍜': '[拉面]',
            '🍝': '[意大利面]', '🍠': '[红薯]', '🍢': '[关东煮]', '🍣': '[寿司]',
            '🍤': '[炸虾]', '🍥': '[鱼糕]', '🥮': '[月饼]', '🍡': '[团子]',
            '🥟': '[饺子]', '🥠': '[幸运饼干]', '🥡': '[外卖盒]', '🦀': '[螃蟹]',
            '🦞': '[龙虾]', '🦐': '[虾]', '🦑': '[鱿鱼]', '🦪': '[牡蛎]',
            '🍦': '[冰淇淋]', '🍧': '[刨冰]', '🍨': '[冰淇淋]', '🍩': '[甜甜圈]',
            '🍪': '[饼干]', '🎂': '[蛋糕]', '🍰': '[蛋糕]', '🧁': '[纸杯蛋糕]',
            '🥧': '[派]', '🍫': '[巧克力]', '🍬': '[糖果]', '🍭': '[棒棒糖]',
            '🍮': '[布丁]', '🍯': '[蜂蜜]', '🍼': '[奶瓶]', '🥛': '[牛奶]',
            '☕': '[咖啡]', '🫖': '[茶壶]', '🍵': '[茶]', '🍶': '[清酒]',
            '🍾': '[香槟]', '🍷': '[酒]', '🍸': '[鸡尾酒]', '🍹': '[热带鸡尾酒]',
            '🍺': '[啤酒]', '🍻': '[啤酒杯]', '🥂': '[香槟杯]', '🥃': '[威士忌]',
            '🥤': '[饮料]', '🧋': '[奶茶]', '🧃': '[果汁盒]', '🧉': '[马黛茶]',
            '🧊': '[冰块]'
        }

        # 替换emoji为文本
        result = text
        for emoji_char, text_desc in emoji_to_text.items():
            result = result.replace(emoji_char, text_desc)

        return result

    def safe_log_with_emoji(self, text, fallback_prefix="", force_fallback=False):
        """
        安全的打印方法，自动处理表情符号兼容性

        Args:
            text: 要打印的文本
            fallback_prefix: 回退文本的前缀
            force_fallback: 是否强制使用回退模式
        """
        import sys

        # 如果强制使用回退模式，直接转换
        if force_fallback:
            safe_text = self._convert_emoji_to_text(text)
            game_logger.info(f"{fallback_prefix}{safe_text}")
            return True

        # 检查是否包含表情符号
        has_emoji = self._contains_emoji(text)

        if not has_emoji:
            # 没有表情符号，直接打印
            game_logger.info(text)
            return True

        # 尝试直接打印表情符号
        try:
            # 设置控制台编码
            if sys.platform == "win32":
                import os
                # 临时设置UTF-8编码
                old_cp = os.popen('chcp').read().strip()
                os.system('chcp 65001 > nul 2>&1')

            game_logger.info(text)

            # 恢复原始编码
            if sys.platform == "win32":
                os.system(f'chcp {old_cp.split()[-1]} > nul 2>&1')

            return True

        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            # 编码错误，使用文本替代
            safe_text = self._convert_emoji_to_text(text)
            game_logger.info(f"{fallback_prefix}{safe_text}")
            return False
        except Exception as e:
            # 其他错误，也使用文本替代
            game_logger.info(f"⚠️ 打印错误: {e}")
            safe_text = self._convert_emoji_to_text(text)
            game_logger.info(f"{fallback_prefix}{safe_text}")
            return False

    def get_emoji_fallback_text(self, text):
        """
        获取表情符号的文本替代版本

        Args:
            text: 原始文本

        Returns:
            str: 文本替代版本
        """
        return self._convert_emoji_to_text(text)

    def is_emoji_supported(self, text):
        """
        检查表情符号是否被支持

        Args:
            text: 要检查的文本

        Returns:
            bool: 是否支持
        """
        if not self._contains_emoji(text):
            return True

        # 尝试渲染测试
        try:
            test_font = self.get_emoji_font(24)
            test_surface = test_font.render(text, True, (255, 255, 255))

            # 检查渲染结果
            if test_surface.get_width() > 5 and test_surface.get_height() > 5:
                # 检查是否有实际内容（不是空白）
                try:
                    import pygame
                    pixels = pygame.surfarray.array3d(test_surface)
                    return pixels.sum() > 0
                except:
                    return test_surface.get_width() > 10
            return False
        except:
            return False

    @staticmethod
    def safe_render_static(font, text, color, antialias=True, background_color=None):
        """
        静态方法：安全渲染文本，优先使用图片，支持抗锯齿和背景颜色

        Args:
            font: 字体对象
            text: 要渲染的文本
            color: 文字颜色 (R, G, B)
            antialias: 是否启用抗锯齿 (默认True)
            background_color: 背景颜色，None表示透明背景
        """
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
        return UnifiedFontManager._render_text_fallback_static(font, text, color, antialias, background_color)

    @staticmethod
    def _render_text_fallback_static(font, text, color, antialias=True, background_color=None):
        """
        静态回退文本渲染方法 - 支持抗锯齿和背景颜色

        Args:
            font: 字体对象
            text: 要渲染的文本
            color: 文字颜色 (R, G, B)
            antialias: 是否启用抗锯齿 (默认True)
            background_color: 背景颜色，None表示透明背景
        """
        try:
            return font.render(text, antialias, color, background_color)
        except:
            # 如果字体渲染失败，使用默认字体
            try:
                default_font = pygame.font.Font(None, 24)
                return default_font.render(text, antialias, color, background_color)
            except:
                # 最后的回退方案 - 创建透明表面
                surface = pygame.Surface((100, 24), pygame.SRCALPHA)
                return surface

    def render_text_antialiased(self, font, text, color=(255, 255, 255), background_color=None):
        """
        便捷方法：渲染抗锯齿文本

        Args:
            font: 字体对象
            text: 要渲染的文本
            color: 文字颜色 (R, G, B)
            background_color: 背景颜色，None表示透明背景
        """
        return self.safe_render(font, text, color, antialias=True, background_color=background_color)

    def render_text_solid(self, font, text, color=(255, 255, 255), background_color=(0, 0, 0)):
        """
        便捷方法：渲染实心背景文本

        Args:
            font: 字体对象
            text: 要渲染的文本
            color: 文字颜色 (R, G, B)
            background_color: 背景颜色
        """
        return self.safe_render(font, text, color, antialias=True, background_color=background_color)

    def render_text_transparent(self, font, text, color=(255, 255, 255)):
        """
        便捷方法：渲染透明背景文本（推荐用于游戏UI）

        Args:
            font: 字体对象
            text: 要渲染的文本
            color: 文字颜色 (R, G, B)
        """
        return self.safe_render(font, text, color, antialias=True, background_color=None)

    def render_text_performance(self, font, text, color=(255, 255, 255)):
        """
        便捷方法：渲染文本（性能优先，禁用抗锯齿）

        Args:
            font: 字体对象
            text: 要渲染的文本
            color: 文字颜色 (R, G, B)
        """
        return self.safe_render(font, text, color, antialias=False, background_color=None)

    def get_bold_font(self, size=10):
        """
        获取加粗字体 - 专门用于金币显示等需要突出显示的文字

        Args:
            size: 字体大小

        Returns:
            pygame.font.Font: 加粗字体对象
        """
        self._ensure_fonts_initialized()

        # 尝试使用系统加粗字体
        bold_fonts = [
            'Arial Bold',
            'Arial',
            'Microsoft YaHei Bold',
            'Microsoft YaHei',
            'SimHei',
            'Tahoma',
            'sans-serif'
        ]

        for font_name in bold_fonts:
            try:
                font = pygame.font.SysFont(font_name, size, bold=True)
                # 测试字体是否正常工作
                test_surface = font.render("测试", True, (255, 255, 255))
                if test_surface.get_width() > 5:
                    return font
            except:
                continue

        # 最后回退到默认字体
        try:
            return pygame.font.Font(None, size)
        except:
            return pygame.font.SysFont('arial', size)

    def render_gold_text(self, text, color=(255, 255, 0), size=16):
        """
        专门用于金币数显示的渲染方法 - 加粗、抗锯齿、透明背景

        Args:
            text: 要渲染的文本
            color: 文字颜色 (R, G, B)
            size: 字体大小

        Returns:
            pygame.Surface: 渲染后的文本表面
        """
        bold_font = self.get_bold_font(size)
        return self.render_text_transparent(bold_font, text, color)
