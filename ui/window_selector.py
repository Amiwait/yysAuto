import customtkinter as ctk
import threading
from core.game_window import GameWindow
from utils.logger import logger

class WindowSelector:
    def __init__(self, main_frame, game_window: GameWindow):
        self.main_frame = main_frame
        self.game_window = game_window
        # 绑定顶部检测按钮的事件
        self.main_frame.bind_window_detect_command(self.start_auto_detection)
        # 初始化状态显示
        self.main_frame.reset_window_info()

    def start_auto_detection(self):
        """启动窗口自动检测（异步执行）"""
        self.main_frame.window_detect_btn.configure(state="disabled", text="检测中...")
        logger.log("开始自动检测游戏窗口...", "info")

        def task():
            success = self.game_window.try_auto_set()
            # 主线程更新UI
            self.main_frame.root.after(0, lambda: self._finish_detection(success))

        threading.Thread(target=task, daemon=True).start()

    def _finish_detection(self, success: bool):
        """检测完成后的UI更新"""
        self.main_frame.window_detect_btn.configure(state="normal", text="自动检测窗口")
        if success:
            # 获取窗口信息并更新UI
            title = self.game_window.title
            size = (self.game_window.width, self.game_window.height)
            pos = (self.game_window.left, self.game_window.top)
            self.main_frame.update_window_info(title, size, pos)
            logger.log(f"找到窗口：{title} | 大小: {size[0]}×{size[1]} | 位置: {pos}", "info")
            self.game_window.activate()
        else:
            self.main_frame.reset_window_info()
            logger.log("未找到匹配窗口", "warn")