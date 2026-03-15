# 文件路径: yysAuto/ui/modules/realm_raid_panel.py

import customtkinter as ctk
import time
import random
import pyautogui
from ui.modules.base_module import BaseModule
from utils.logger import logger
import pytesseract
import sys
import os
import cv2
import re
from core.capture import capture_window, match_template

# === 🌟 关键：你需要截图并保存以下模板到 assets/templates/ ===
# 1. 结界突破界面的进攻标志（通常是那个红色的达摩或者是勋章标志）
TEMPLATE_RAID_TARGET = "assets/templates/raid_target_icon.png"
# 2. 点击目标后，底部弹出的“进攻”按钮
TEMPLATE_ATTACK_BUTTON = "assets/templates/raid_attack_button.png"
# 3. (可选) 失败标志，用于判断是否打不过
TEMPLATE_FAILED = "assets/templates/battle_failed.png"

# 定义一个获取资源绝对路径的函数
def get_resource_path(relative_path):
    """获取资源的绝对路径，兼容开发环境和 PyInstaller 打包环境"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的 exe，资源在 sys._MEIPASS 临时目录下
        base_path = sys._MEIPASS
    else:
        # 如果是开发环境，资源在当前文件路径的相对位置
        # 假设当前文件在 ui/modules/ 下，我们需要回退到项目根目录
        # 注意：这里根据你 bin 文件夹实际放置的位置调整
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    return os.path.join(base_path, relative_path)

# === 设置 Tesseract 路径 ===
# 指向我们复制进来的 bin 目录
tess_executable = get_resource_path(os.path.join("bin", "Tesseract-OCR", "tesseract.exe"))
pytesseract.pytesseract.tesseract_cmd = tess_executable

# === (关键) 还需要设置 TESSDATA_PREFIX 环境变量 ===
# 否则 Tesseract 可能会找不到语言包报错
tess_data_dir = get_resource_path(os.path.join("bin", "Tesseract-OCR", "tessdata"))
os.environ["TESSDATA_PREFIX"] = tess_data_dir

class RealmRaidPanel(BaseModule):
    def __init__(self, main_frame, game_window):
        super().__init__(main_frame, game_window)
        self.module_name = "结界突破"
        self.folder_name = "realm_raid"
        self.total_battles = 0

    def render_config_ui(self, parent_frame):
        """渲染结界突破的专属配置"""
        # 1. 战斗等待时间设置
        self._create_config_row(parent_frame, "战斗等待 (秒)", "battle_wait", "15")
        
        # 2. 失败重试（可选配置，这里演示如何加第二个）
        # self._create_config_row(parent_frame, "失败重试 (次)", "retry_count", "0")

    def run(self):
        # 获取配置参数
        try:
            wait_time = float(self.config_vars["battle_wait"].get())
        except:
            wait_time = 15.0
            
        logger.log(f"启动结界突破 | 战斗等待: {wait_time}s", "info")
        
        while self.is_running:
            # === 1. 寻找进攻目标 ===
            target_pos = self._find_target()
            
            if target_pos:
                logger.log("发现目标，准备进攻...", "info")
                # 点击目标
                self._click_point(target_pos)
                time.sleep(random.uniform(0.8, 1.2))
                
                # === 2. 点击确认进攻按钮 ===
                if self._click_attack_button():
                    # === 3. 进入战斗等待 ===
                    logger.log(f"战斗开始，等待 {wait_time} 秒...", "info")
                    time.sleep(wait_time)
                    
                    # === 4. 结算流程 (简单狂点) ===
                    logger.log("战斗结束，处理结算...", "debug")
                    self._handle_settlement()
                    
                    # === 5. 更新统计 ===
                    self.total_battles += 1
                    self.main_frame.update_challenged_times(self.total_battles)
                    
                    # 稍微休息一下，防止被检测
                    time.sleep(random.uniform(1.5, 3.0))
                else:
                    logger.log("未找到进攻按钮，可能点歪了或已被攻破", "warn")
                    # 点击空白处取消选中，避免卡死
                    self.main_frame.current_module._click_safe_bottom_area()
                    time.sleep(1.0)
            else:
                logger.log("当前屏幕未发现可攻击目标 (请手动刷新或拖动)", "warn")
                time.sleep(3.0) # 没找到就歇一会

    def _find_target(self):
        """在屏幕上寻找结界图标"""
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None: return None
        screen, current_size = result
        
        # 匹配目标图标
        is_match, score, pos = match_template(
            screen, self._img("target.png"), current_size, threshold=0.8
        )
        if is_match:
            return pos
        return None

    def _click_attack_button(self):
        """点击确认进攻按钮"""
        # 给一点时间让按钮弹出来
        time.sleep(0.5) 
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None: return False
        screen, current_size = result
        
        is_match, score, pos = match_template(
            screen, self._img("attack.png"), current_size, threshold=0.8
        )
        if is_match and pos:
            self._click_point(pos)
            return True
        return False
    
    def check_ticket_count(self):
        """
        检查结界突破券数量
        :return: (int: 当前数量, int: 上限) 或 None
        """
        if not self.is_running: return None

        # 1. 获取当前截图
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None: return None
        screen, current_size = result
        width, height = current_size

        # 2. 判断当前场景
        # 逻辑 A: 是否在探索界面
        if self._is_in_exploration(screen, current_size):
            logger.log("当前处于探索界面，检查门票...", "debug")
            
            # === 坐标计算 (基于 968x584 标准分辨率) ===
            # 标准参数
            STD_W, STD_H = 968, 584
            REF_X, REF_Y = 490, 48
            REF_W, REF_H = 140, 40
            
            # 计算缩放比例 (以宽、高缩放比中较小的一个为准，保证区域不越界)
            scale = min(width / STD_W, height / STD_H)
            
            # 计算实际裁剪区域
            crop_x = int(REF_X * scale)
            crop_y = int(REF_Y * scale)
            crop_w = int(REF_W * scale)
            crop_h = int(REF_H * scale)
            
            # 边界安全检查
            if crop_x + crop_w > width: crop_w = width - crop_x
            if crop_y + crop_h > height: crop_h = height - crop_y
            
            # 3. 图像预处理 (OCR 识别的关键)
            # 裁剪
            roi = screen[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]
            
            # 转灰度
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            
            # 二值化 (黑白分明)：通常文字是白色的，背景较杂，使用阈值处理
            # 180 是经验值，将大于 180 的像素变为 255 (白)，其余变 0 (黑)
            _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
            
            # [调试] 如果识别不准，可以把这个保存下来看看清楚不清楚
            # cv2.imwrite("debug_ticket_ocr.png", binary)

            try:
                # 4. 执行 OCR
                # config说明: --psm 7 表示把图像视为单行文本
                text = pytesseract.image_to_string(binary, config='--psm 7 outputbase digits')
                
                # 5. 文本解析 (格式: 18/30)
                # 使用正则提取数字，兼容识别出的空格或误读
                # 寻找模式: 数字 + 斜杠 + 数字
                match = re.search(r'(\d+)\s*/\s*(\d+)', text)
                
                if match:
                    current = int(match.group(1))
                    max_num = int(match.group(2))
                    logger.log(f"OCR识别结果: {current}/{max_num}", "info")
                    return current, max_num
                else:
                    logger.log(f"OCR无法解析数字: '{text.strip()}'", "warn")
                    return None
                    
            except Exception as e:
                logger.log(f"OCR识别出错: {e}", "error")
                return None
                
        # 逻辑 B: 结界突破界面 (你可以在这里补充第二个逻辑)
        # elif self._is_in_raid_scene(...):
        #     ...
            
        return None

    def _handle_settlement(self):
        """简单的结算点击逻辑"""
        # 点击 3-4 次右下角安全区域
        for _ in range(random.randint(3, 5)):
            if not self.is_running: break
            self.main_frame.current_module._click_safe_bottom_area()
            time.sleep(random.uniform(0.8, 1.2))

    def _click_point(self, pos):
        """辅助点击"""
        x, y = pos
        abs_x = self.game_window.rect[0] + x + random.randint(-10, 10)
        abs_y = self.game_window.rect[1] + y + random.randint(-10, 10)
        pyautogui.click(abs_x, abs_y)