import threading
import time
from utils.logger import logger

class BaseModule:
    def __init__(self, main_frame, game_window):
        self.main_frame = main_frame
        self.game_window = game_window
        self.is_running = False
        self.thread = None
        self.module_name = "未知模块"

    def run(self):
        """
        子类必须实现此方法，包含具体的业务逻辑循环。
        在循环中应时刻检查 self.is_running。
        """
        raise NotImplementedError

    def start(self):
        """启动任务的通用逻辑"""
        if not self.game_window.is_valid():
            logger.log("请先检测并选中游戏窗口", "warn")
            return

        if self.is_running:
            return

        self.is_running = True
        self.main_frame.set_start_stop_state(True)
        self.main_frame.reset_statistics() # 重置统计
        
        logger.log(f"启动功能: {self.module_name}", "info")
        
        # 创建守护线程运行任务
        self.thread = threading.Thread(target=self._wrapper_run, daemon=True)
        self.thread.start()

    def stop(self):
        """停止任务的通用逻辑"""
        if not self.is_running:
            return
            
        self.is_running = False
        logger.log(f"正在停止: {self.module_name}...", "warn")
        # 实际停止逻辑依赖于 run 方法中对 self.is_running 的检查
        self.main_frame.set_start_stop_state(False)

    def _wrapper_run(self):
        """包装运行逻辑，处理异常和结束状态"""
        try:
            self.run()
        except Exception as e:
            logger.log(f"任务运行出错: {e}", "error")
            import traceback
            traceback.print_exc()
        finally:
            self.is_running = False
            # 确保在主线程更新按钮状态
            self.main_frame.root.after(0, lambda: self.main_frame.set_start_stop_state(False))
            logger.log(f"{self.module_name} 已结束", "info")