import cv2
import numpy as np
from PIL import ImageGrab
import win32gui
import win32con
from utils.logger import logger
import time
from functools import partial

# 标准分辨率（建议根据你最常用的游戏窗口设置）
STANDARD_WIDTH = 968
STANDARD_HEIGHT = 548

# 强制全屏幕捕获模式（视情况保留或注释）
ImageGrab.grab = partial(ImageGrab.grab, all_screens=True)


def capture_window(hwnd):
    """截取指定窗口的屏幕图像"""
    if not hwnd or not win32gui.IsWindow(hwnd):
        logger.log("无效的游戏窗口句柄", "ERROR")
        return None, (0, 0)

    rect = win32gui.GetWindowRect(hwnd)
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top

    # 简单尺寸合理性检查
    if width <= 100 or height <= 100 or left < -10000:
        logger.log("窗口矩形尺寸异常，无法截图", "ERROR")
        return None, (width, height)

    try:
        img = ImageGrab.grab(bbox=rect)
        if img is None:
            logger.log("屏幕捕获失败（ImageGrab 返回 None）", "ERROR")
            return None, (width, height)

        img_np = np.array(img)
        img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

        # 可选：仅在调试时开启，生产环境建议注释
        cv2.imwrite("debug_last_screenshot.png", img_cv)

        return img_cv, (width, height)

    except Exception as e:
        logger.log(f"截图失败: {str(e)}", "ERROR")
        return None, (width, height)


import cv2
import numpy as np # 必须导入 numpy
from utils.logger import logger
from core.game_window import STANDARD_WIDTH, STANDARD_HEIGHT

def match_template(screen_img, template_path, current_size, threshold=0.80):
    """(保持原有的单目标匹配函数不变)"""
    try:
        # [调试] 提取文件名
        template_name = template_path.replace("\\", "/").split("/")[-1]
        logger.log(f"开始匹配", "debug")
        
        template_base = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template_base is None:
            logger.log(f"无法加载模板图像: {template_path}", "ERROR")
            return False, 0.0, None

        gray_screen = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)

        scale_w = current_size[0] / STANDARD_WIDTH
        scale_h = current_size[1] / STANDARD_HEIGHT
        scale = min(scale_w, scale_h)

        new_w = int(template_base.shape[1] * scale)
        new_h = int(template_base.shape[0] * scale)
        
        if new_w < 4 or new_h < 4:
            return False, 0.0, None

        template_resized = cv2.resize(template_base, (new_w, new_h))

        res = cv2.matchTemplate(gray_screen, template_resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val > 0.5:
            # 仅在调试模式输出，避免刷屏
            pass 

        if max_val >= threshold:
            center_x = max_loc[0] + new_w // 2
            center_y = max_loc[1] + new_h // 2
            return True, max_val, (center_x, center_y)
        else:
            logger.log(f"匹配分数{max_val}", "debug")

        return False, max_val, None

    except Exception as e:
        logger.log(f"模板匹配异常: {str(e)}", "ERROR")
        return False, 0.0, None

def match_all_template(screen_img, template_path, current_size, threshold=0.80):
    """
    [新增] 多目标匹配，返回所有匹配目标的中心点坐标列表
    """
    try:
        template_base = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template_base is None:
            return []

        gray_screen = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)

        # 计算缩放
        scale = min(current_size[0] / STANDARD_WIDTH, current_size[1] / STANDARD_HEIGHT)
        new_w = int(template_base.shape[1] * scale)
        new_h = int(template_base.shape[0] * scale)

        if new_w < 4 or new_h < 4:
            return []

        template_resized = cv2.resize(template_base, (new_w, new_h))

        # 匹配
        res = cv2.matchTemplate(gray_screen, template_resized, cv2.TM_CCOEFF_NORMED)
        
        # 获取所有大于阈值的点
        loc = np.where(res >= threshold)
        
        points = []
        # zip(*loc[::-1]) 将 (row, col) 转换为 (x, y)
        for pt in zip(*loc[::-1]):
            center_x = pt[0] + new_w // 2
            center_y = pt[1] + new_h // 2
            
            # [非极大值抑制] 简单去重：如果新点距离已有点太近，则忽略
            # 距离阈值设为模板宽度的 1/2
            is_duplicate = False
            for exist_pt in points:
                dist = ((center_x - exist_pt[0])**2 + (center_y - exist_pt[1])**2)**0.5
                if dist < new_w / 2:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                points.append((center_x, center_y))
                
        return points

    except Exception as e:
        logger.log(f"多目标匹配异常: {str(e)}", "ERROR")
        return []