import time
import random
import pyautogui
import customtkinter as ctk
from ui.modules.base_module import BaseModule
from utils.logger import logger
from core.capture import capture_window, match_template
class EventTowerPanel(BaseModule):
    def __init__(self, main_frame, game_window):
        super().__init__(main_frame, game_window)
        self.module_name = "活动爬塔"
        self.folder_name = "event_tower" # 预留给后续特征图的文件夹名
        self.challenged_count = 0
    
    def _create_range_row(self, parent_frame, label_text, var_min_name, var_max_name, default_min, default_max):
        """[新增] 辅助方法：创建一个带双输入框的区间配置行，并自动绑定本地保存"""
        row = ctk.CTkFrame(parent_frame, fg_color="transparent")
        row.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row, text=label_text, font=("微软雅黑", 12), text_color="#6B7280", width=120, anchor="w").pack(side="left")
        
        # 获取并绑定最小值
        val_min = self._get_saved_value(var_min_name, default_min)
        var_min = ctk.StringVar(value=val_min)
        self.config_vars[var_min_name] = var_min
        self._bind_save_event(var_min_name, var_min)
        
        # 获取并绑定最大值
        val_max = self._get_saved_value(var_max_name, default_max)
        var_max = ctk.StringVar(value=val_max)
        self.config_vars[var_max_name] = var_max
        self._bind_save_event(var_max_name, var_max)
        
        # 输入验证
        vcmd = (self.main_frame.root.register(self.main_frame._validate_num), "%P")
        
        # 界面布局 (从右往左 pack: 最大值 -> "~" -> 最小值)
        ctk.CTkEntry(row, textvariable=var_max, width=50, height=30, font=("微软雅黑", 12), border_color="#E5E7EB", fg_color="#F9FAFB", validate="key", validatecommand=vcmd).pack(side="right")
        ctk.CTkLabel(row, text="~", text_color="#6B7280").pack(side="right", padx=5)
        ctk.CTkEntry(row, textvariable=var_min, width=50, height=30, font=("微软雅黑", 12), border_color="#E5E7EB", fg_color="#F9FAFB", validate="key", validatecommand=vcmd).pack(side="right")

    def render_config_ui(self, parent_frame):
        """渲染活动爬塔专属配置界面"""
        # 1. 挑战次数
        self._create_config_row(parent_frame, "挑战次数 (空=无限)", "challenge_count", "")
        
        # 2. 战斗时间区间 (默认 12~15 秒)
        self._create_range_row(parent_frame, "战斗时间 (秒)", "battle_min", "battle_max", "12.0", "15.0")
        
        # 3. 战斗间隔区间 (默认 1.5~3 秒)
        self._create_range_row(parent_frame, "战斗间隔 (秒)", "interval_min", "interval_max", "1.5", "3.0")

    def run(self):
        """活动爬塔核心逻辑循环"""
        # --- 1. 获取基础配置 ---
        count_str = self.config_vars["challenge_count"].get()
        target_count = int(count_str) if count_str else None
        
        logger.log(f"启动【{self.module_name}】 | 目标: {'无限' if not target_count else target_count}次", "info")
        self.challenged_count = 0

        # --- 2. 核心循环 ---
        while self.is_running:
            # 检查次数是否达成
            if target_count is not None and self.challenged_count >= target_count:
                logger.log("已达到设定的挑战次数，任务完成！", "success")
                break

            logger.log(f"--- 开始第 {self.challenged_count + 1} 次爬塔 ---", "info")
            
            # 步骤 A：寻找并点击挑战按钮
            if not self._click_challenge():
                logger.log("未找到挑战按钮，等待 2 秒后重试...", "warn")
                time.sleep(2)
                continue

            self.challenged_count += 1
            
            # 步骤 B：动态计算本次战斗所需的时间并盲等
            try:
                b_min = float(self.config_vars["battle_min"].get())
                b_max = float(self.config_vars["battle_max"].get())
                # 确保 min 和 max 顺序正确，防止报错
                battle_wait = random.uniform(min(b_min, b_max), max(b_min, b_max))
            except:
                battle_wait = 15.0

            # 扣除 BaseModule 中写死的 5 秒默认等待，剩余的用来前置等待
            pre_wait = max(0, battle_wait - 5.0)
            logger.log(f"战斗中... 预计耗时 {battle_wait:.1f} 秒", "debug")
            
            if pre_wait > 0:
                start_t = time.time()
                while time.time() - start_t < pre_wait and self.is_running:
                    time.sleep(0.5)
            
            if not self.is_running: 
                break 
            
            # 步骤 C：执行智能结算检测
            logger.log("准备进入结算检测流程", "debug")
            self.wait_battle_settlement(
                target_checker=self._is_challenge_ready, 
                timeout=45 
            )
            
            # 步骤 D：更新主界面数据
            self.main_frame.update_challenged_times(self.challenged_count)
            self.main_frame.update_kill_count(self.challenged_count, 0)
            
            # 步骤 E：战斗间隔（休息）
            if not self.is_running:
                break
                
            try:
                i_min = float(self.config_vars["interval_min"].get())
                i_max = float(self.config_vars["interval_max"].get())
                interval_wait = random.uniform(min(i_min, i_max), max(i_min, i_max))
            except:
                interval_wait = 2.0
                
            logger.log(f"单次挑战结束，休息 {interval_wait:.1f} 秒...", "debug")
            start_t = time.time()
            while time.time() - start_t < interval_wait and self.is_running:
                time.sleep(0.5)

    def _click_challenge(self):
        """尝试寻找并点击挑战按钮，带有轻量重试机制"""
        retry_count = 0
        while retry_count < 5 and self.is_running:
            result = capture_window(self.game_window.hwnd)
            if result and result[0] is not None:
                screen, current_size = result
                is_match, score, pos = match_template(
                    screen, 
                    self._img("challenge.png"), 
                    current_size, 
                    threshold=0.75
                )
                
                if is_match and pos:
                    logger.log(f"找到挑战按钮 (匹配分: {score:.2f}) -> 执行点击", "debug")
                    self._click_point_randomly(pos,50,30)
                    return True
                    
            retry_count += 1
            time.sleep(1)
            
        return False
    
    def _is_challenge_ready(self):
        """[目标检查器] 判断挑战按钮是否在屏幕上 (说明已经回到了活动主界面)"""
        if not self.is_running:
            return False

        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            return False

        screen, current_size = result
        is_match, _, _ = match_template(
            screen, 
            self._img("challenge.png"), 
            current_size, 
            threshold=0.75
        )
        return is_match