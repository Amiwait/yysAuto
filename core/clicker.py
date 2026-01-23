# core/clicker.py
import random
import time
import pyautogui
from core.capture import capture_window, match_template
from utils.logger import logger


def click_ui_element(game_window, template_path, threshold=0.80, click_offset_range=(-15, 15, -15, 15),
                     max_attempts=3, attempt_delay=0.6, description="UI元素"):
    """
    通用点击方法：匹配模板 → 获取区域 → 在区域内随机点击
    :param game_window: GameWindow 对象
    :param template_path: 模板路径
    :param threshold: 匹配阈值
    :param click_offset_range: 随机偏移范围 (min_x, max_x, min_y, max_y)，默认 ±15 像素
    :param max_attempts: 最大尝试次数（防止怪物/元素移动）
    :param attempt_delay: 每次尝试间隔秒
    :param description: 用于日志的元素描述
    :return: bool - 是否成功点击
    """
    logger.log(f"开始尝试点击 {description} (模板: {template_path})", "INFO")

    for attempt in range(max_attempts):
        logger.log(f"第 {attempt+1}/{max_attempts} 次尝试...", "INFO")

        # 激活窗口 + 等待渲染
        game_window.activate()
        time.sleep(0.3)

        # 截图
        result = capture_window(game_window.hwnd)
        if result is None or result[0] is None:
            logger.log("截图失败，无法进行匹配", "ERROR")
            continue

        screen, current_size = result

        # 匹配模板（使用你已有的动态缩放版本）
        is_match, score, center_pos = match_template(screen, template_path, current_size, threshold=threshold)

        if is_match and center_pos:
            center_x, center_y = center_pos

            # 计算随机偏移（在标志/按钮范围内随机点）
            offset_x = random.randint(click_offset_range[0], click_offset_range[1])
            offset_y = random.randint(click_offset_range[2], click_offset_range[3])

            click_x = center_x + offset_x
            click_y = center_y + offset_y

            # 转为屏幕绝对坐标
            window_left, window_top, _, _ = game_window.rect
            abs_x = window_left + click_x
            abs_y = window_top + click_y

            # 随机延迟 + 点击
            time.sleep(random.uniform(0.15, 0.4))
            pyautogui.click(abs_x, abs_y)

            logger.log(f"成功点击 {description}！(绝对坐标: {abs_x}, {abs_y}) | 分数: {score:.3f}", "INFO")
            return True

        logger.log(f"未匹配到 {description} (最高分数: {score:.3f})", "WARN")
        time.sleep(attempt_delay)

    logger.log(f"经过 {max_attempts} 次尝试，仍未找到 {description}", "WARN")
    return False