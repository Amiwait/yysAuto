import customtkinter as ctk
from ui.main_frame import MainFrame
from ui.window_selector import WindowSelector
from ui.modules.kun28_panel import Kun28Panel
from core.game_window import GameWindow
from utils.logger import logger

# 修改 yysAuto/main.py
import customtkinter as ctk
from ui.main_frame import MainFrame
from ui.window_selector import WindowSelector
from ui.modules.kun28_panel import Kun28Panel
from core.game_window import GameWindow
from utils.logger import logger

class ModuleManager:
    def __init__(self, main_frame, game_window):
        self.main_frame = main_frame
        self.modules = {
            "困28": Kun28Panel(main_frame, game_window),
            # 未来这里可以加: "自动御魂": SoulPanel(main_frame, game_window)
        }
        self.current_module = None
        
        # 绑定 UI 事件
        self.main_frame.bind_start_command(self.on_start)
        self.main_frame.bind_stop_command(self.on_stop)

    def on_start(self):
        selected_name = self.main_frame.get_selected_function()
        module = self.modules.get(selected_name)
        
        if module:
            self.current_module = module
            self.current_module.start()
        else:
            logger.log(f"功能 [{selected_name}] 尚未实现", "warn")

    def on_stop(self):
        if self.current_module:
            self.current_module.stop()

def main():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("阴阳师辅助工具 v0.2")
    root.geometry("1100x650")

    game_window = GameWindow()
    main_frame = MainFrame(root)
    main_frame.pack(fill="both", expand=True)

    # 初始化功能模块
    WindowSelector(main_frame, game_window)
    ModuleManager(main_frame, game_window) # 使用管理器替代直接注册
    #logger.set_level('debug')

    logger.add_listener(main_frame.append_log)
    
    logger.log("程序就绪", "info")
    root.mainloop()

if __name__ == "__main__":
    main()