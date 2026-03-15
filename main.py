import customtkinter as ctk
import pyautogui
from core.game_window import GameWindow
from ui.main_frame import MainFrame
from utils.logger import logger

def main():
    # 1. 关闭 PyAutoGUI 的故障安全保护 (防止鼠标移到角落报错)
    pyautogui.FAILSAFE = False 
    
    # 2. 设置界面主题
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    
    # 3. 创建主窗口
    root = ctk.CTk()
    root.title("阴阳师自动化辅助")
    root.geometry("1100x750")
    
    # === [关键修改] 先初始化 GameWindow ===
    game_window = GameWindow()
    
    # === [关键修改] 将 game_window 传给 MainFrame ===
    main_frame = MainFrame(root, game_window)
    main_frame.pack(fill="both", expand=True)

    # 4. 绑定日志输出
    # 让 logger 把消息转发给 main_frame.append_log
    logger.add_listener(main_frame.append_log)
    
    # 5. 绑定自动检测按钮事件
    def on_detect_click():
        logger.log("开始检测游戏窗口...", "info")
        if game_window.try_auto_set():
            game_window.activate()
            main_frame.update_window_info(
                game_window.title, 
                (game_window.width, game_window.height), 
                (game_window.left, game_window.top)
            )
            logger.log(f"成功绑定: {game_window.title}", "success")
        else:
            main_frame.reset_window_info()
            logger.log("未找到游戏窗口 (请打开MuMu模拟器)", "error")
            
    main_frame.bind_window_detect_command(on_detect_click)

    # 6. 启动主循环
    logger.log("程序就绪", "info")
    root.mainloop()

if __name__ == "__main__":
    main()