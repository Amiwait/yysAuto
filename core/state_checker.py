# core/state_checker.py  （新建这个文件）
import time
from core.capture import capture_window, match_template
from utils.logger import logger


def check_ui_state(game_window, template_path, threshold=0.80, description="未知界面", max_retries=1, retry_delay=1.0):
    """
    统一检查当前游戏界面是否匹配指定模板
    :param game_window: GameWindow 对象
    :param template_path: 模板图片路径
    :param threshold: 匹配阈值
    :param description: 用于日志的界面描述（例如"关卡入口"）
    :param max_retries: 失败时重试次数（默认1次不重试）
    :param retry_delay: 重试间隔秒数
    :return: (bool: 是否匹配, float: 最高匹配分数, tuple: 匹配位置 或 None)
    """
    for attempt in range(max_retries + 1):
        if attempt > 0:
            logger.log(f"第 {attempt} 次重试检查 {description}...", "INFO")
            time.sleep(retry_delay)

        # 激活窗口
        game_window.activate()
        time.sleep(0.5)  # 等待渲染

        result = capture_window(game_window.hwnd)
        if result is None or result[0] is None:
            logger.log(f"截图失败，无法检查 {description}", "ERROR")
            continue

        screen, current_size = result

        is_match = match_template(screen, template_path, current_size, threshold=threshold)

        if is_match:
            # match_template 已打印分数和位置，这里可以再取一次或扩展返回
            logger.log(f"✅ 当前处于 {description}", "INFO")
            return True, 0.0, None  # 后续可扩展返回实际分数和位置

        logger.log(f"未匹配到 {description} (尝试 {attempt+1}/{max_retries+1})", "WARN")

    logger.log(f"经过 {max_retries+1} 次尝试，仍不在 {description}", "WARN")
    return False, 0.0, None