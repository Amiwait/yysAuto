import customtkinter as ctk
import time
import random
import pyautogui
import cv2             # 新增
import numpy as np
from ui.modules.base_module import BaseModule
from utils.logger import logger
from core.capture import capture_window, match_template

# 模板路径常量
TEMPLATE_CHALLENGE_ACTIVE = "assets/templates/soul_challenge_active.png" # 亮色挑战按钮
TEMPLATE_CHALLENGE_GRAY = "assets/templates/soul_challenge_gray.png"     # 灰色挑战按钮
TEMPLATE_IN_BATTLE = "assets/templates/battle_monster_marker.png"        # 战斗中标志 (借用小怪标记，或者你可以截一个魂王特有的)
# 注意：你需要确保 assets 目录下有这几张图

class SoulKingPanel(BaseModule):
    def __init__(self, main_frame, game_window):
        super().__init__(main_frame, game_window)
        self.module_name = "魂王"
        self.folder_name = "soul_king"
        self.challenged_count = 0
        self.driver_row = None 

    def render_config_ui(self, parent_frame):
        """渲染魂王配置界面"""
        # 1. 挑战次数
        self._create_config_row(parent_frame, "挑战次数 (空=无限)", "challenge_count", "")
        
        # 2. 战斗等待
        self._create_config_row(parent_frame, "战斗等待 (秒)", "battle_wait", "35")

        # 3. 组队设置
        row_team = ctk.CTkFrame(parent_frame, fg_color="transparent")
        row_team.pack(fill="x", pady=5)
        
        if "is_team" not in self.config_vars:
            self.config_vars["is_team"] = ctk.BooleanVar(value=False)
        
        chk_team = ctk.CTkCheckBox(
            row_team, 
            text="开启组队模式", 
            variable=self.config_vars["is_team"],
            font=("微软雅黑", 12), text_color="#6B7280",
            checkbox_width=20, checkbox_height=20,
            command=self._update_driver_option_visibility
        )
        chk_team.pack(side="left")

        # 4. 队长选项
        self.driver_row = ctk.CTkFrame(parent_frame, fg_color="transparent")
        if "is_driver" not in self.config_vars:
            self.config_vars["is_driver"] = ctk.BooleanVar(value=True) 
        
        chk_driver = ctk.CTkCheckBox(
            self.driver_row, 
            text="我是队长 (司机)", 
            variable=self.config_vars["is_driver"],
            font=("微软雅黑", 12), text_color="#6B7280",
            checkbox_width=20, checkbox_height=20
        )
        chk_driver.pack(side="left", padx=(25, 0))

        self._update_driver_option_visibility()

    def _update_driver_option_visibility(self):
        if self.config_vars["is_team"].get():
            self.driver_row.pack(fill="x", pady=5)
        else:
            self.driver_row.pack_forget()

    def run(self):
        # 获取配置
        count_str = self.config_vars["challenge_count"].get()
        target_count = int(count_str) if count_str else None
        
        try:
            battle_wait = float(self.config_vars["battle_wait"].get())
        except:
            battle_wait = 35.0

        is_team = self.config_vars["is_team"].get()
        is_driver = self.config_vars["is_driver"].get()

        mode_desc = "单人模式"
        if is_team:
            mode_desc = "组队-队长" if is_driver else "组队-队员"

        logger.log(f"启动魂王 [{mode_desc}] | 目标: {'无限' if not target_count else target_count}次", "info")

        while self.is_running:
            if target_count is not None and self.challenged_count >= target_count:
                logger.log("任务完成", "success")
                break

            self.challenged_count += 1
            logger.log(f"--- 第 {self.challenged_count} 次挑战 ---", "info")
            
            # === 阶段 1: 准备/开始战斗 ===
            if not is_team:
                # 单人模式：直接找挑战按钮点
                if not self._wait_for_teammate_start(is_solo=True):
                    break
            else:
                # 组队模式
                if is_driver:
                    # 队长：检测按钮颜色，亮了才点
                    if not self._wait_for_teammate_start(is_solo=False):
                        break
                else:
                    # 队员：啥也不干，干等进入战斗
                    logger.log("等待队长开车...", "info")
                    if not self._wait_battle_start():
                        break

            # === 阶段 2: 战斗中 ===
            logger.log(f"战斗开始，等待 {battle_wait} 秒...", "info")
            
            # 分段等待，支持随时停止
            start_t = time.time()
            while time.time() - start_t < battle_wait and self.is_running:
                time.sleep(1)
            
            if not self.is_running: break
            
            # === 阶段 3: 结算 ===
            # 这里简单处理，实际上魂王可能需要点好几次（开箱子、队友协战奖励等）
            logger.log("战斗结束，处理结算...", "debug")
            self._handle_settlement()
            
            # 更新统计
            self.main_frame.update_challenged_times(self.challenged_count)
            self.main_frame.update_kill_count(self.challenged_count * 20, 0) # 假设一把20体力用于演示
            
            time.sleep(1.5) # 轮次间隔

    def _wait_for_teammate_start(self, is_solo=False):
        """
        [核心逻辑] 等待并点击开始
        is_solo=True: 不管颜色直接点
        is_solo=False: 对比灰/亮按钮，亮了才点
        """
        logger.log("检测挑战状态...", "debug")
        
        while self.is_running:
            result = capture_window(self.game_window.hwnd)
            if result is None or result[0] is None:
                continue
            screen, current_size = result

            # 1. 匹配亮色
            is_active, score_active, pos_active = match_template(
                screen, self._img("active.png"), current_size, threshold=0.9
            )

            # 2. 匹配灰色
            is_gray, score_gray, _ = match_template(
                screen, self._img("gray.png"), current_size, threshold=0.9
            )

            # 单人模式：只要能匹配到（不管是亮是灰，其实单人应该只有亮），就点
            if is_solo:
                if is_active or score_active > 0.8:
                    self._click_button(pos_active if pos_active else (0,0)) # 这里简化了，实际需保证 pos 存在
                    return True
            
            # === 组队队长模式：核心判断 ===
            else:
                # 策略：谁的分数高，当前就是什么状态
                # 只有当 亮色分 > 灰色分 且 亮色分足够高时，才点击
                if score_active > score_gray and score_active > 0.85:
                    logger.log(f"队友已就位 (Active:{score_active:.2f} > Gray:{score_gray:.2f}) -> 开车！", "success")
                    self._click_button(pos_active)
                    
                    # 点击后，稍微等一下，确认是否真的进入了战斗（防止点击无效）
                    time.sleep(2)
                    # 这里可以加个判断：如果还在这个界面，说明没点到或者卡了，循环会继续，下一次自然会重试
                    return True
                
                elif score_gray > 0.8:
                    logger.log(f"等待队友中... (Gray:{score_gray:.2f})", "debug")
                    time.sleep(1.0)
                else:
                    # 既不是亮也不是灰（可能已经进战斗了，或者在其他界面）
                    # 尝试检测是否已经在战斗中
                    if self._check_in_battle():
                        return True
                    
                    logger.log("未检测到挑战按钮，寻找中...", "debug")
                    time.sleep(1.0)
            
            time.sleep(0.5)
        return False

    def _wait_battle_start(self):
        """队员逻辑：等待直到进入战斗画面"""
        wait_start = time.time()
        while self.is_running:
            if self._check_in_battle():
                logger.log("检测到战斗开始！", "success")
                return True
            
            if time.time() - wait_start > 60: # 超时保护
                logger.log("等待开局超时 (60s)", "warn")
                return False
            
            time.sleep(1)
        return False

    def _check_in_battle(self):
        """简单的战斗场景检测"""
        # 这里你可以换成检测左上角的"回合数"或者右下角的"自动/手动"图标
        # 暂时用 TEMPLATE_IN_BATTLE 占位
        # 实际魂王建议检测: assets/templates/soul_battle_mark.png (你需要自己截图)
        return False # 占位，需实现

    def _handle_settlement(self):
        """魂王结算：通常需要点多次屏幕直到回到房间"""
        # 简单狂点右下角策略
        for _ in range(3):
            if not self.is_running: break
            self.main_frame.current_module._click_safe_bottom_area() # 借用 Kun28 的方法或自己写
            time.sleep(1.5)

    def _click_button(self, pos):
        """点击指定坐标"""
        if not pos: return
        x, y = pos
        # 随机偏移
        rx, ry = x + random.randint(-15, 15), y + random.randint(-5, 5)
        
        win_left, win_top, _, _ = self.game_window.rect
        pyautogui.click(win_left + rx, win_top + ry)

    def _is_region_colorful(self, screen_img, center_pos, size=20, threshold=40):
        """
        [核心判断] 检查指定坐标周围区域的颜色饱和度
        :param screen_img: 原始彩色截图 (BGR)
        :param center_pos: 中心坐标 (x, y)
        :param size: 取样大小 (正方形边长)
        :param threshold: 饱和度阈值 (大于此值认为是有颜色的/亮起的)
        :return: True(亮色/有颜色), False(灰色)
        """
        try:
            cx, cy = int(center_pos[0]), int(center_pos[1])
            
            # 1. 裁剪中心一小块区域 (防止越界)
            h, w = screen_img.shape[:2]
            x1 = max(0, cx - size // 2)
            y1 = max(0, cy - size // 2)
            x2 = min(w, cx + size // 2)
            y2 = min(h, cy + size // 2)
            
            roi = screen_img[y1:y2, x1:x2]
            if roi.size == 0: return False

            # 2. BGR 转 HSV
            hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            
            # 3. 获取饱和度 (S通道) 的平均值
            # HSV中: H=色相, S=饱和度, V=亮度
            saturation = hsv_roi[:, :, 1] # 获取 S 通道
            mean_sat = np.mean(saturation)
            
            # [调试日志] 可以在调试模式下打印看看具体数值
            # logger.log(f"颜色检测: 饱和度={mean_sat:.1f} (阈值{threshold})", "debug")
            
            return mean_sat > threshold

        except Exception as e:
            logger.log(f"颜色识别异常: {e}", "error")
            return False