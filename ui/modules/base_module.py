import os
import time
import random
import json
import pyautogui
from abc import ABC, abstractmethod
import threading
import customtkinter as ctk
from typing import Dict, Optional, Any,Callable
from utils.logger import logger
from core.capture import capture_window, match_template
from utils.logger import logger

class BaseModule(ABC):
    """
    抽象策略基类 (Abstract Strategy)
    定义所有自动化模块必须实现的接口规范。
    """
    def __init__(self, main_frame: Any, game_window: Any):
        # 使用 Any 类型注解避免循环导入，实际应为 MainFrame 和 GameWindow 类型
        self.main_frame = main_frame
        self.game_window = game_window
        self.is_running: bool = False
        self.thread: Optional[threading.Thread] = None
        self.module_name: str = "未知模块"
        self.config_vars: Dict[str, ctk.StringVar] = {}
        self.folder_name = ""

    @abstractmethod
    def run(self) -> None:
        """
        [必须实现] 核心业务逻辑循环。
        """
        pass

    @abstractmethod
    def render_config_ui(self, parent_frame: ctk.CTkFrame) -> None:
        """
        [必须实现] 渲染该模块特有的配置界面。
        """
        pass

    def start(self) -> None:
        """模板方法：统一处理启动流程"""
        if not self.game_window.is_valid():
            logger.log("请先检测并选中游戏窗口", "warn")
            return

        if self.is_running:
            return

        self.is_running = True
        # 调用 MainFrame 的公共方法更新 UI 状态
        self.main_frame.set_start_stop_state(True)
        self.main_frame.reset_statistics()
        
        logger.log(f"启动功能: {self.module_name}", "info")
        
        self.thread = threading.Thread(target=self._wrapper_run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """模板方法：统一处理停止流程"""
        if not self.is_running:
            return
            
        self.is_running = False
        logger.log(f"正在停止: {self.module_name}...", "warn")
        # UI 状态的恢复由 _wrapper_run 的 finally 块保证，这里不做冗余操作

    def _wrapper_run(self) -> None:
        """异常捕获与状态清理的包装器"""
        try:
            self.run()
        except Exception as e:
            logger.log(f"任务运行出错: {e}", "error")
            import traceback
            traceback.print_exc()
        finally:
            self.is_running = False
            # 线程安全地更新 UI
            self.main_frame.root.after(0, lambda: self.main_frame.set_start_stop_state(False))
            logger.log(f"{self.module_name} 已结束", "info")

    def _get_saved_value(self, var_name: str, default_value: Any) -> str:
        """从本地配置读取保存的值"""
        config_file = "user_config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    # 按照模块名隔离配置，例如: {"活动爬塔": {"battle_wait": "10"}}
                    return str(cfg.get(self.module_name, {}).get(var_name, default_value))
            except:
                pass
        return str(default_value)

    def _bind_save_event(self, var_name: str, ctk_var: ctk.StringVar):
        """绑定变量改变事件，每次输入变化时自动保存到本地"""
        config_file = "user_config.json"
        def on_change(*args):
            val = ctk_var.get()
            cfg = {}
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        cfg = json.load(f)
                except:
                    pass
            
            if self.module_name not in cfg:
                cfg[self.module_name] = {}
                
            cfg[self.module_name][var_name] = val
            
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=4)
            except:
                pass

        # 监听变量写入事件
        ctk_var.trace_add("write", on_change)

    def _create_config_row(self, parent: ctk.CTkFrame, label: str, var_name: str, 
                           default_value: str, width: int = 60) -> ctk.StringVar:
        """辅助方法：快速创建配置行"""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row, text=label, font=("微软雅黑", 12), 
                     text_color="#6B7280", width=120, anchor="w").pack(side="left")
        # 【修改点 1】不再直接使用 default_value，而是尝试从本地读取
        actual_val = self._get_saved_value(var_name, default_value)
        var = ctk.StringVar(value=actual_val)
        self.config_vars[var_name] = var
        
        # 【修改点 2】给这个变量绑定保存事件，只要你在界面上改了数字，瞬间就会存入 JSON
        self._bind_save_event(var_name, var)

        var = ctk.StringVar(value=str(default_value))
        self.config_vars[var_name] = var
        
        # 假设 MainFrame 有 _validate_num 方法
        vcmd = (self.main_frame.root.register(self.main_frame._validate_num), "%P")
        
        ctk.CTkEntry(
            row, textvariable=var, width=width, height=30,
            font=("微软雅黑", 12), border_color="#E5E7EB", fg_color="#F9FAFB",
            validate="key", validatecommand=vcmd
        ).pack(side="right")
        return var
    
    def _img(self, filename):
        """获取当前模块专属图片路径"""
        # 例如: assets/templates/kun28/monster.png
        if self.folder_name:
            return os.path.join("assets", "templates", self.folder_name, filename)
        return os.path.join("assets", "templates", filename)

    def _common_img(self, filename):
        """获取通用图片路径"""
        # 例如: assets/templates/common/settlement.png
        return os.path.join("assets", "templates", "common", filename)
    
    def is_in_exploration(self, screen=None, current_size=None) -> bool:
        """
        [通用检测] 判断当前是否处于探索地图界面 (底部有灯笼/卷轴图标)
        :param screen: 可选，如果外部已经截图了，传进来避免重复截图
        :param current_size: 可选，配合 screen 使用
        :return: bool
        """
        # 1. 资源准备
        # 因为我们把图片移到了 common，所以用 _common_img
        template_path = self._common_img("explore_icon.png") 
        
        # 2. 如果外部没传截图，自己截
        if screen is None or current_size is None:
            # 必须检查窗口是否有效
            if not self.game_window.is_valid():
                return False
            result = capture_window(self.game_window.hwnd)
            if result is None or result[0] is None:
                return False
            screen, current_size = result

        # 3. 执行匹配
        # 探索界面的特征通常很明显，阈值可以设得适中 (0.7 - 0.75)
        is_match, score, _ = match_template(
            screen, 
            template_path, 
            current_size, 
            threshold=0.70
        )
        
        # 调试日志 (可选，不需要太频繁)
        # logger.log(f"探索界面检测: {score:.2f}", "debug")
        
        return is_match
    
    def wait_battle_settlement(self, target_checker: Optional[Callable[[], bool]] = None, timeout: int = 60):
        """
        通用战斗结算等待循环。
        会一直等待直到超时，或者 target_checker 返回 True。
        期间如果检测到结算界面（common/settlement.png 或 common/settlement_panel.png），会点击右下角跳过。
        
        :param target_checker: 一个无参函数，返回 True 表示已离开结算流程（如检测到了“关卡入口”或“组队房间”）
        :param timeout: 超时时间（秒），防止卡死
        """
        if not self.is_running:
            return

        # 1. 获取等待时间配置 (尝试从 config_vars 读取，如果没有则默认 5s)
        wait_s = 5.0
        if "settle_wait" in self.config_vars:
            try:
                wait_s = float(self.config_vars["settle_wait"].get())
            except:
                pass
        
        logger.log(f"等待战斗结算动画 ({wait_s}s)...", "debug")
        time.sleep(wait_s)
        
        logger.log("开始监测结算状态...", "debug")
        start_time = time.time()
        
        while self.is_running:
            # 超时检查
            if time.time() - start_time > timeout:
                logger.log(f"❌ 结算流程超时 ({timeout}s)，停止等待", "warn")
                break

            # 随机间隔 (模拟真人反应)
            time.sleep(random.uniform(0.3, 0.8))

            # 1. 检查是否达到目标状态 (例如：已回到关卡/房间)
            if target_checker:
                if target_checker():
                    logger.log("✅ 检测到目标状态，结算流程结束", "debug")
                    break
            
            # 2. 截图
            result = capture_window(self.game_window.hwnd)
            if result is None or result[0] is None:
                continue
            screen, current_size = result
            
            # 3. 检测是否在结算界面 (Scene1: 达摩/赢/金币, Scene2: 详细数据面板)
            # 请确保 assets/templates/common/ 下有这两张图
            is_scene2, score2, _ = match_template(
                screen, self._common_img("settlement_panel.png"), current_size, threshold=0.75
            )
            is_scene1, score1, _ = match_template(
                screen, self._common_img("settlement.png"), current_size, threshold=0.75
            )
            
            # 4. 如果在结算界面，点击右下角区域跳过
            if is_scene2 or is_scene1:
                debug_msg = f"检测到结算: 面板({score2:.2f})" if is_scene2 else f"检测到结算: 标志({score1:.2f})"
                logger.log(f"{debug_msg} -> 点击跳过", "debug")
                
                # 计算右下角点击区域 (基于当前窗口大小动态计算)
                # 假设标准参考系是 968x584
                scale = min(current_size[0] / 968.0, current_size[1] / 584.0)
                
                # 定义右下角 400x200 (缩放后) 的区域
                area_w = int(400 * scale)
                area_h = int(200 * scale)
                area_right = current_size[0] - 10
                area_bottom = current_size[1] - 10
                area_left = max(0, area_right - area_w)
                area_top = max(0, area_bottom - area_h)
                
                self._click_random_area(area_left, area_right, area_top, area_bottom)
            else:
                # 既不是目标状态，也不是结算界面，可能是黑屏转场中
                pass

    def _click_random_area(self, x_min, x_max, y_min, y_max):
        """[通用] 在指定矩形区域内随机点击"""
        if not self.is_running: return
        
        rand_x = random.randint(int(x_min), int(x_max))
        rand_y = random.randint(int(y_min), int(y_max))
        
        window_left, window_top, _, _ = self.game_window.rect
        abs_x = window_left + rand_x
        abs_y = window_top + rand_y
        
        # 平滑移动鼠标
        pyautogui.moveTo(abs_x, abs_y, duration=random.uniform(0.1, 0.3))
        pyautogui.click()
    
    def _click_point_randomly(self, pos,skew_x,skew_y):
        """在目标点附近做随机范围小偏移并点击 (防检测)"""
        x, y = pos
        offset_x = random.randint(-skew_x, skew_x)
        offset_y = random.randint(-skew_y, skew_y)
        
        abs_x = self.game_window.rect[0] + x + offset_x
        abs_y = self.game_window.rect[1] + y + offset_y
        
        pyautogui.moveTo(abs_x, abs_y, duration=random.uniform(0.15, 0.35))
        pyautogui.click()