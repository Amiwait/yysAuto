import customtkinter as ctk
import threading
import time
import random
import pyautogui
from core.capture import capture_window, match_template,match_all_template
from utils.logger import logger
from ui.modules.base_module import BaseModule

# 常量定义
STANDARD_WIDTH = 968
STANDARD_HEIGHT = 584
KUN28_LEFT_REL = 785 / STANDARD_WIDTH
KUN28_TOP_REL = 403 / STANDARD_HEIGHT
KUN28_WIDTH_REL = 160 / STANDARD_WIDTH
KUN28_HEIGHT_REL = 80 / STANDARD_HEIGHT
EXPLORATION_LEFT_REL = 663 / STANDARD_WIDTH
EXPLORATION_TOP_REL = 421 / STANDARD_HEIGHT
EXPLORATION_WIDTH_REL = 98 / STANDARD_WIDTH
EXPLORATION_HEIGHT_REL = 46 / STANDARD_HEIGHT
SETTLEMENT_AREA_RIGHT_OFFSET_REL = 400 / STANDARD_WIDTH
SETTLEMENT_AREA_BOTTOM_OFFSET_REL = 200 / STANDARD_HEIGHT
SETTLEMENT_AREA_WIDTH_REL = 400 / STANDARD_WIDTH
SETTLEMENT_AREA_HEIGHT_REL = 200 / STANDARD_HEIGHT

# 核心常量（重点修改：采集奖励检测区域）
MONSTER_PER_LEVEL = 7
BOSS_MARKER_TEMPLATE = "assets/templates/battle_boss_marker.png"
LEVEL_ENTRY_TEMPLATE = "assets/templates/kun28_level_entry_bottom_bar.png"
COLLECT_REWARD_TEMPLATE = "assets/templates/collect_reward_marker.png"
DRAG_AREA_WIDTH = 400
DRAG_AREA_HEIGHT = 200
DRAG_DISTANCE_RATIO = 0.3
MAX_DRAG_TIMES = 10
COLLECT_CLAIM_AREA_WIDTH = 400
COLLECT_CLAIM_AREA_HEIGHT = 220
# 采集奖励检测区域（标准缩放968×584下：500×340像素，可自定义区域左上角坐标）
COLLECT_DETECT_STD_X = 275    # 标准区域左上角X（可根据实际界面调整）
COLLECT_DETECT_STD_Y = 210     # 标准区域左上角Y（可根据实际界面调整）
COLLECT_DETECT_STD_W = 430    # 标准区域宽度（固定500px）
COLLECT_DETECT_STD_H = 280    # 标准区域高度（固定340px）

class Kun28Panel(BaseModule):  # 继承 BaseModule
    def __init__(self, main_frame, game_window):
        super().__init__(main_frame, game_window)
        self.module_name = "困28"
        self.folder_name = "kun28"
        
        # 统计变量
        self.challenged_levels = 0
        self.total_killed_monsters = 0
        self.total_killed_boss = 0
        self.total_collected_rewards = 0
    
    def render_config_ui(self, parent_frame):
        """[实现] 渲染困28的专属配置"""
        # 1. 挑战次数
        self._create_config_row(parent_frame, "挑战次数 (空=无限)", "challenge_count", "")
        
        # 2. 结算等待
        self._create_config_row(parent_frame, "结算等待 (秒)", "settle_wait", "5")
        
        # 3. 小怪等待 (特殊双输入框，手动创建)
        row = ctk.CTkFrame(parent_frame, fg_color="transparent")
        row.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row, text="小怪等待 (秒)", font=("微软雅黑", 12), text_color="#6B7280", width=120, anchor="w").pack(side="left")
        
        self.config_vars["wait_max"] = ctk.StringVar(value="5.0")
        self.config_vars["wait_min"] = ctk.StringVar(value="1.0")
        
        ctk.CTkEntry(row, textvariable=self.config_vars["wait_max"], width=50, height=30, font=("微软雅黑", 12), fg_color="#F9FAFB").pack(side="right")
        ctk.CTkLabel(row, text="~", text_color="#6B7280").pack(side="right", padx=5)
        ctk.CTkEntry(row, textvariable=self.config_vars["wait_min"], width=50, height=30, font=("微软雅黑", 12), fg_color="#F9FAFB").pack(side="right")

    def _random_wait_after_monster_kill(self):
        """小怪击杀后随机等待"""
        try:
            min_w = float(self.config_vars["wait_min"].get())
            max_w = float(self.config_vars["wait_max"].get())
            wait_time = round(random.uniform(min_w, max_w), 1)
            time.sleep(wait_time)
        except:
            time.sleep(1.0)

    def _is_interference_scene(self):
        """判断是否处于干扰场景（少女与面具对话框/探索页面）"""
        if not self.is_running:
            return True
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            return True
        screen, current_size = result
        
        # 检测是否在少女与面具对话框
        dialog_template = "assets/templates/girl_mask_dialog.png"
        is_dialog, _, _ = match_template(
            screen, self._img("dialog.png"), current_size, threshold=0.78
        )
        if is_dialog:
            return True
        
        # 检测是否在探索页面
        exploration_template = "assets/templates/exploration_map_bottom_icons.png"
        logger.log(f"检测是否在探索界面", "debug")
        is_exploration, _, _ = match_template(
            screen, self._img("explore_icon.png"), current_size, threshold=0.65
        )
        if is_exploration:
            return True
        
        return False

    def _detect_collect_reward(self):
        """检测是否有采集奖励（场景过滤+固定尺寸区域检测）"""
        if not self.is_running:
            return None
        
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            return None
        
        screen, current_size = result
        window_width, window_height = current_size # 获取当前完整窗口尺寸
        
        # 计算缩放比例
        scale_x = window_width / STANDARD_WIDTH
        scale_y = window_height / STANDARD_HEIGHT
        
        # 转换检测区域坐标
        detect_x = int(COLLECT_DETECT_STD_X * scale_x)
        detect_y = int(COLLECT_DETECT_STD_Y * scale_y)
        detect_w = int(COLLECT_DETECT_STD_W * scale_x)
        detect_h = int(COLLECT_DETECT_STD_H * scale_y)
        
        # 边界校验
        detect_x = max(0, detect_x)
        detect_y = max(0, detect_y)
        detect_w = min(detect_w, window_width - detect_x)
        detect_h = min(detect_h, window_height - detect_y)
        
        # 裁剪区域
        screen_cropped = screen[detect_y:detect_y+detect_h, detect_x:detect_x+detect_w]
        if screen_cropped.size == 0:
            return None
        
        # === 【修复点】 ===
        # 传入 (window_width, window_height) 而不是 (detect_w, detect_h)
        # 这样 match_template 内部计算缩放比例时，才会得到正确的 1.0 (或实际缩放比)，而不是 0.44
        is_found, score, reward_pos = match_template(
            screen_cropped, 
            self._img("reward.png"),  # <--- 使用新路径
            (window_width, window_height),
            threshold=0.8
        )
        
        # 还原坐标
        if is_found and reward_pos:
            # reward_pos 是相对于裁剪图的坐标，加上偏移量变为绝对坐标
            reward_pos = (reward_pos[0] + detect_x, reward_pos[1] + detect_y)
            logger.log(f"检测到采集奖励（匹配分：{score:.2f}）", "debug")
            return reward_pos
            
        return None

    def _click_collect_reward(self, reward_pos):
        """点击采集奖励"""
        if not self.is_running:
            return False
        center_x, center_y = reward_pos
        offset_x = random.randint(-15, 15)
        offset_y = random.randint(-15, 15)
        click_x = center_x + offset_x
        click_y = center_y + offset_y
        window_left, window_top, _, _ = self.game_window.rect
        abs_x = window_left + click_x
        abs_y = window_top + click_y
        time.sleep(random.uniform(0.1, 0.25))
        pyautogui.click(abs_x, abs_y)
        logger.log("点击采集奖励", "info")
        return True

    def _get_safe_bottom_area(self):
        """[辅助方法] 计算底部 36% 的安全点击区域 (带 10px 内缩)"""
        rect = self.game_window.rect
        window_x, window_y = rect[0], rect[1]
        window_w = rect[2] - rect[0]
        window_h = rect[3] - rect[1]

        # 1. 计算底部 36% 区域的原始边界
        # 顶部边界：高度的 (1 - 0.36) = 64% 处
        area_top_raw = int(window_h * 0.64)
        area_bottom_raw = window_h
        area_left_raw = 0
        area_right_raw = window_w

        # 2. 应用 10px 安全内缩 (防止点到边缘)
        safe_x_min = area_left_raw + 10
        safe_x_max = area_right_raw - 10
        safe_y_min = area_top_raw + 10
        safe_y_max = area_bottom_raw - 10

        # 转换为屏幕绝对坐标范围
        abs_x_min = window_x + safe_x_min
        abs_x_max = window_x + safe_x_max
        abs_y_min = window_y + safe_y_min
        abs_y_max = window_y + safe_y_max

        return (abs_x_min, abs_x_max, abs_y_min, abs_y_max)

    
    def _click_safe_bottom_area(self, action_name="点击下方区域"):
        """
        [通用方法] 在底部 36% 安全区域内随机点击
        适用于：领取奖励、关闭弹窗、点击任意位置继续等
        """
        if not self.is_running:
            return False

        # 获取计算好的安全区域
        x_min, x_max, y_min, y_max = self._get_safe_bottom_area()

        # 生成随机坐标
        click_x = random.randint(x_min, x_max)
        click_y = random.randint(y_min, y_max)

        # 随机等待：移动前
        time.sleep(random.uniform(0.1, 0.3))

        # 带缓动的随机轨迹移动
        duration = random.uniform(0.15, 0.4) # 综合了之前的两个速度范围
        pyautogui.moveTo(click_x, click_y, duration=duration, tween=pyautogui.easeOutQuad)
        
        # 随机等待：移动后，点击前（模拟手指悬停）
        time.sleep(random.uniform(0.05, 0.15))
        
        pyautogui.click()
        
        logger.log(f"{action_name} (坐标: {click_x}, {click_y})", "debug")
        return True

    def _count_rewards(self):
        """[新增] 统计屏幕上当前有多少个奖励"""
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            return 0
        screen, current_size = result
        
        # 使用多目标匹配
        # 注意：这里使用之前的 COLLECT_REWARD_TEMPLATE 常量
        points = match_all_template(
            screen, 
            self._img("reward.png"),  # <--- 使用新路径
            current_size, 
            threshold=0.8
        )
        return len(points)
    
    def _collect_all_rewards(self):
        """
        [极速版] 循环采集所有奖励
        逻辑：先统计总数，对于前 N-1 个奖励直接盲点确认，最后一个才判断跳转。
        """
        if not self.is_running:
            return
        
        # 先检查是否退出到了探索界面
        if self._is_interference_scene():
            return 
        
        logger.log("开始检测采集奖励...", "info")
        
        # 1. 先看一眼总共有几个 (这就是你想要的功能)
        initial_count = self._count_rewards()
        if initial_count > 0:
            logger.log(f"视觉识别: 发现 {initial_count} 个待领取奖励", "info")
        
        collected_count = 0
        no_reward_streak = 0
        
        while self.is_running:
            # 重新检测单个位置进行点击 (因为点击过程中位置可能微调，或者为了获取最新截图)
            reward_pos = self._detect_collect_reward()
            
            if reward_pos:
                no_reward_streak = 0
                collected_count += 1
                self.total_collected_rewards += 1
                
                # 点击箱子
                self._click_collect_reward(reward_pos)
                
                # === [智能判定逻辑] ===
                # 如果当前采集的数量 < 最初识别的总数，说明这绝对不是最后一个
                # 我们可以大胆地直接点击确认，不需要浪费时间去判断界面跳转
                
                if collected_count < initial_count:
                    # [极速模式] 中间奖励
                    # 稍微等待弹窗动画 (0.5s) -> 直接点击确认 -> 稍微等待下一个箱子刷新
                    logger.log(f"领取第 {collected_count}/{initial_count} 个奖励 (极速模式)", "info")
                    time.sleep(0.6) 
                    self._click_safe_bottom_area() # 盲点确认
                    time.sleep(random.uniform(0.8, 1.2)) # 等下一个箱子冒出来
                    
                else:
                    # [安全模式] 可能是最后一个 (或者最初识别漏了，导致计数不对，保险起见走安全逻辑)
                    logger.log(f"领取第 {collected_count} 个奖励 (判定为最后一个)", "debug")
                    
                    # 等待自动跳转
                    time.sleep(random.uniform(3, 5))
                    if self._is_interference_scene():
                        logger.log("检测到自动跳转，采集结束", "debug")
                        break
                    else:
                        # 哎呀，原来不是最后一个（可能识别漏了），那就手动领掉
                        logger.log("未自动跳转，执行手动确认", "debug")
                        self._click_safe_bottom_area()
                        time.sleep(1.0)

            else:
                # 没找到箱子
                no_reward_streak += 1
                if no_reward_streak >= 3:
                    break
                time.sleep(0.5)
                
        if collected_count > 0:
            logger.log(f"采集完成，实领 {collected_count} 个 (初识 {initial_count} 个)", "info")
        else:
            logger.log("无采集奖励", "info")

            
    # ========== 其余方法保持不变 ==========
    def _fight_in_level(self):
        """关卡内战斗逻辑：7小怪 + 1BOSS + 采集奖励"""
        if not self.is_running:
            return False
        
        if not self._check_if_in_level():
            return False
        
        monster_killed = 0
        while monster_killed < MONSTER_PER_LEVEL and self.is_running:
            logger.log(f"开始击杀第 {monster_killed + 1}/{MONSTER_PER_LEVEL} 个小怪", "info")
            
            if self._click_monster(monster_type="normal"):
                self._wait_battle_and_settlement()
                monster_killed += 1
                self.total_killed_monsters += 1
                self.main_frame.update_kill_count(self.total_killed_monsters, self.total_killed_boss)
                logger.log(f"小怪击杀完成 {monster_killed}/{MONSTER_PER_LEVEL}", "info")
                
                if monster_killed < MONSTER_PER_LEVEL:
                    self._random_wait_after_monster_kill()
            else:
                detect_result = self._detect_monster_or_boss()
                if detect_result and detect_result[0] == "boss":
                    logger.log(f"已击杀 {monster_killed} 个小怪，检测到BOSS → 进入BOSS战", "info")
                    break
                else:
                    logger.log("无法继续击杀小怪，本关放弃", "warn")
                    return False
        
        if not self.is_running:
            return False
        
        time.sleep(random.uniform(2.5, 8.0))
        
        logger.log("开始挑战 BOSS", "info")
        if self._click_monster(monster_type="boss") and self.is_running:
            self._wait_battle_and_settlement()
            self.total_killed_boss += 1
            self.main_frame.update_kill_count(self.total_killed_monsters, self.total_killed_boss)
            logger.log("BOSS 击杀完成", "info")
            
            # BOSS击杀后添加采集奖励逻辑
            time.sleep(random.uniform(5, 10))
            self._collect_all_rewards()
            # 退出关卡后等待加载探索界面，领取宝箱
            time.sleep(random.uniform(5,10))
            self._detect_and_collect_map_treasure()

            
            return True
        else:
            logger.log("BOSS 击杀失败", "warn")
            return False

    def _drag_page_left(self):
        """向左拖动屏幕（模拟手指滑动，反检测优化版）"""
        if not self.is_running:
            return False
        
        # 获取窗口尺寸信息
        window_rect = self.game_window.rect
        window_width = window_rect[2] - window_rect[0]
        window_height = window_rect[3] - window_rect[1]
        
        # 计算缩放比例
        scale_x = window_width / STANDARD_WIDTH
        scale_y = window_height / STANDARD_HEIGHT
        
        # 确定拖动起始区域的中心点
        drag_area_center_x = window_rect[0] + window_width / 2
        drag_area_center_y = window_rect[1] + window_height / 2
        
        # 定义拖动起始点的随机范围
        click_x_min = drag_area_center_x - (DRAG_AREA_WIDTH * scale_x) / 2
        click_x_max = drag_area_center_x + (DRAG_AREA_WIDTH * scale_x) / 2
        click_y_min = drag_area_center_y - (DRAG_AREA_HEIGHT * scale_y) / 2
        click_y_max = drag_area_center_y + (DRAG_AREA_HEIGHT * scale_y) / 2
        
        # 随机生成起始点 (X1, Y1)
        start_x = random.randint(int(click_x_min), int(click_x_max))
        start_y = random.randint(int(click_y_min), int(click_y_max))
        
        # --- 反检测核心修改开始 ---
        
        # 1. 随机水平距离：窗口宽度的 20% ~ 40%
        random_distance_ratio = random.uniform(0.2, 0.4)
        drag_distance_x = window_width * random_distance_ratio
        
        # 2. 随机垂直偏移：窗口高度的 -5% ~ +5% (模拟手滑抖动)
        max_vertical_offset = int(window_height * 0.05)
        vertical_offset = random.randint(-max_vertical_offset, max_vertical_offset)
        
        # 计算终点 (X2, Y2)
        # 向左拖动，所以 X 减去距离；Y 加上随机偏移
        end_x = int(start_x - drag_distance_x)
        end_y = int(start_y + vertical_offset)
        
        # 3. 随机滑动持续时间：0.25秒 ~ 0.5秒
        duration = random.uniform(0.25, 0.5)
        
        # 执行操作
        # 先移动到起点（带一点随机延迟）
        pyautogui.moveTo(start_x, start_y, duration=random.uniform(0.1, 0.2))
        time.sleep(random.uniform(0.05, 0.1))
        
        pyautogui.mouseDown()
        # 这一小段 sleep 模拟手指按下去的短暂停顿
        time.sleep(random.uniform(0.05, 0.15))
        
        # 移动到终点
        # tween=pyautogui.easeOutQuad 让移动轨迹呈现"快启动、慢结束"的惯性效果
        pyautogui.moveTo(end_x, end_y, duration=duration, tween=pyautogui.easeOutQuad)
        
        # 模拟松开前的微小停顿
        time.sleep(random.uniform(0.05, 0.15))
        pyautogui.mouseUp()
        
        # --- 反检测核心修改结束 ---
        
        logger.log(f"执行防检测拖动 | 距离: {int(drag_distance_x)}px | 垂直偏移: {vertical_offset}px", "debug")
        time.sleep(0.8)
        return True


    def _detect_monster_or_boss(self):
        """
        识别屏幕上的怪物或BOSS
        【修改版】优先检测小怪，没有小怪再检测BOSS
        """
        if not self.is_running:
            return None
        
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            return None
        screen, current_size = result
        
        # 读取配置的阈值 (如果没有配置则默认为 0.8)
        threshold = getattr(self, 'global_threshold', 0.8)
        
        # === 1. [修改] 优先检测小怪 ===
        monster_template = "assets/templates/battle_monster_marker.png"
        is_monster, score_m, monster_pos = match_template(
            screen, self._img("monster.png"), current_size, threshold=threshold
        )
        if is_monster and monster_pos:
            logger.log(f"[调试] 视觉识别: 发现小怪 (分数:{score_m:.2f})", "debug")
            return ("normal", monster_pos, score_m)

        # === 2. [修改] 其次检测 BOSS ===
        # 只有当屏幕上找不到任何小怪时，才会去检测 BOSS
        is_boss, score_b, boss_pos = match_template(
            screen, self._img("boss.png"), current_size, threshold=threshold - 0.15
        )
        
        if is_boss and boss_pos:
            logger.log(f"[调试] 视觉识别: 发现BOSS (分数:{score_b:.2f})", "debug")
            return ("boss", boss_pos, score_b)
            
        return None

    def _click_monster(self, monster_type="normal"):
        """
        查找并点击怪物/BOSS (带重试机制)
        """
        if not self.is_running:
            return False
        
        # 设置最大重试次数
        # 小怪: 10次 (配合拖动)
        # BOSS: 20次 (约10秒，等待BOSS动画和特效)
        max_retries = MAX_DRAG_TIMES if monster_type == "normal" else 20
        current_retry = 0
        
        while current_retry < max_retries and self.is_running:
            # 1. 执行检测
            detect_result = self._detect_monster_or_boss()
            
            if detect_result is not None:
                detect_type, center_pos, score = detect_result
                
                # [情况 A] 目标匹配 -> 点击
                if monster_type == detect_type:
                    logger.log(f"锁定目标 {detect_type} (分数:{score:.2f})", "debug")
                    
                    center_x, center_y = center_pos
                    offset_x = random.randint(-20, 20)
                    offset_y = random.randint(-15, 15)
                    click_x = center_x + offset_x
                    click_y = center_y + offset_y
                    
                    window_left, window_top, _, _ = self.game_window.rect
                    abs_x = window_left + click_x
                    abs_y = window_top + click_y
                    
                    time.sleep(random.uniform(0.1, 0.25))
                    pyautogui.click(abs_x, abs_y)
                    return True
                
                # [情况 B] 找小怪时看到了 BOSS -> 停止找小怪，准备进BOSS战
                if monster_type == "normal" and detect_type == "boss":
                    logger.log("发现 BOSS，停止寻找小怪", "info")
                    return False

                # [情况 C] 找BOSS时看到了小怪 -> 
                # 由于修改了 _detect_monster_or_boss 优先找 BOSS，
                # 如果代码进到这里，说明屏幕上只有小怪，真的没看见 BOSS。
                # 这可能是 BOSS 还没刷出来（动画延迟），所以我们需要【继续重试】
                if monster_type == "boss" and detect_type == "normal":
                    logger.log(f"目标是BOSS但只看到小怪 (分数:{score:.2f})，等待BOSS出现...", "debug")
            
            # 2. 未找到目标或类型不匹配 -> 执行重试策略
            if monster_type == "normal":
                # 小怪模式：尝试向左拖动寻找
                self._drag_page_left()
                current_retry += 1
            else:
                # BOSS 模式：原地等待 (BOSS不会跑，只需要等它现身)
                time.sleep(0.5)
                current_retry += 1
                if current_retry % 5 == 0:
                    logger.log(f"等待 BOSS 出现... ({current_retry}/{max_retries})", "debug")
                
        logger.log(f"未找到目标: {monster_type}", "warn")
        return False


    def _check_if_in_level(self):
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            return False
        screen, current_size = result
        is_in_level, _, _ = match_template(
            screen, self._img("entry.png"), current_size, threshold=0.80
        )
        return is_in_level

    def start_task(self):
        if not self.game_window.is_valid():
            logger.log("请先检测并选中游戏窗口", "warn")
            return
            
        selected_funct = self.main_frame.get_selected_function()
        if selected_funct != "困28":
            logger.log(f"暂不支持「{selected_funct}」功能", "warn")
            return
        self.is_running = True
        self.challenged_levels = 0
        self.total_killed_monsters = 0
        self.total_killed_boss = 0
        self.total_collected_rewards = 0
        self.main_frame.reset_statistics()
        self.main_frame.set_start_stop_state(True)
        
        self.target_challenge_count = self.main_frame.get_challenge_count()
        if self.target_challenge_count is None:
            logger.log("开始执行困28（无限挑战）", "info")
        else:
            logger.log(f"开始执行困28（目标 {self.target_challenge_count} 次）", "info")
        self.thread = threading.Thread(target=self._run_kun28, daemon=True)
        self.thread.start()

    def stop_task(self):
        self.is_running = False
        self.main_frame.set_start_stop_state(False)
        logger.log(f"已停止 | 挑战 {self.challenged_levels} 次 | "
                  f"小怪 {self.total_killed_monsters} | BOSS {self.total_killed_boss} | 采集奖励 {self.total_collected_rewards}", "info")

    def run(self):
        # 获取配置参数
        count_str = self.config_vars["challenge_count"].get()
        target_count = int(count_str) if count_str else None
        if target_count is None:
            logger.log("模式: 无限挑战", "info")
        else:
            logger.log(f"模式: 目标 {target_count} 次", "info")

        while self.is_running:
            if target_count is not None and self.challenged_levels >= target_count:
                logger.log("已达到设定挑战次数", "success")
                break 

            logger.log(f"--- 开始第 {self.challenged_levels + 1} 次探索 ---", "info")
            
            # 进入关卡逻辑
            if not self._enter_level():
                if self.is_running:
                    time.sleep(1.5)
                continue

            # 关卡内战斗逻辑
            if self._fight_in_level() and self.is_running:
                self.challenged_levels += 1
                self.main_frame.update_challenged_times(self.challenged_levels)
                self.main_frame.update_kill_count(self.total_killed_monsters, self.total_killed_boss)
                logger.log(f"第 {self.challenged_levels} 关 完成", "success")
                time.sleep(2)

        # 循环结束后的总结在 BaseModule._wrapper_run 会自动处理
        logger.log(f"统计: {self.challenged_levels}关 | 小怪{self.total_killed_monsters} | BOSS{self.total_killed_boss}", "info")
        
    def _enter_level(self):
        if not self.is_running:
            return False
        
        # [调试路标 1] 确认方法已进入
        logger.log("[调试] 正在尝试进入关卡...", "debug")
        
        self.game_window.activate()
        time.sleep(0.8)
        
        # 截图
        result = capture_window(self.game_window.hwnd)
        
        # [调试路标 2] 检查截图结果
        if result is None or result[0] is None:
            logger.log("[调试] ❌ 截图失败！(result为None)，可能窗口最小化或句柄失效", "error")
            return False
        
        logger.log("[调试] ✅ 截图成功，准备匹配...", "debug")
        
        screen, current_size = result
        current_width, current_height = current_size
        

        is_in_dialog, val, _ = match_template(screen, self._img("dialog.png"), current_size, threshold=0.78)
        logger.log(f"“少女与面具”对话框,匹配分数:{val}", "debug")
        if is_in_dialog:
            self._click_exploration_button(current_width, current_height)
            time.sleep(random.uniform(2.0, 3.5))
            return self._check_level_entry(current_width, current_height)
            
        is_in_exploration = self.is_in_exploration()
        
        if is_in_exploration:
            self._click_kun28_button(current_width, current_height)
            time.sleep(random.uniform(2.0, 4.0))
            result_new = capture_window(self.game_window.hwnd)
            if result_new and result_new[0] is not None:
                screen_new, _ = result_new
                is_now_in_dialog, _, _ = match_template(screen_new,self._img("dialog.png") , current_size, threshold=0.78)
                if is_now_in_dialog:
                    self._click_exploration_button(current_width, current_height)
                    time.sleep(random.uniform(2.0, 3.5))
                    return self._check_level_entry(current_width, current_height)
        return False

    def _wait_battle_and_settlement(self):
        """
        [最终优化版] 战斗结算循环
        逻辑：
        1. 循环检测是否已退回到关卡界面 (_check_level_entry)。
        2. 如果没退回，则检测是否在结算界面 (Scene1/Scene2)。
        3. 如果在结算界面，执行随机点击以跳过动画/继续。
        4. 包含随机间隔 (0.3~1.0s) 以防检测。
        """
        if not self.is_running:
            return
        try:
            wait_s = float(self.config_vars["settle_wait"].get())
        except:
            wait_s = 5.0
        # 预设等待 (等待战斗结束黑屏转场)
        logger.log(f"等待战斗结算动画 ({wait_s}s)...", "debug")
        time.sleep(wait_s)
        
        logger.log("开始监测结算状态 (目标: 返回关卡界面)...", "debug")
        start_time = time.time()
        # 设置一个超长超时防止卡死 (比如掉线了)
        max_duration = 60 

        # 结算界面模板
        scene1_template = "assets/templates/settlement_icon.png"         # 阶段1: 达摩/赢/金币
        scene2_template = "assets/templates/settlement_scene2_panel.png" # 阶段2: 详细面板

        while self.is_running:
            # 0. 防卡死超时检查
            if time.time() - start_time > max_duration:
                logger.log("❌ 结算流程超时 (60s)，强制退出监测", "warn")
                break

            # 1. [核心逻辑] 随机等待 0.3-1.0s (用户指定)
            sleep_time = random.uniform(0.3, 1.0)
            time.sleep(sleep_time)

            # 2. [核心逻辑] 优先检测：是否已经退回到了关卡界面？
            # 注意：这里需要获取当前的宽高传给 _check_level_entry，但该方法内部会重新截图
            # 为了效率，我们先获取一次窗口大小 (不截图)，传参仅仅是为了满足方法签名
            rect = self.game_window.rect
            curr_w = rect[2] - rect[0]
            curr_h = rect[3] - rect[1]

            if self._check_level_entry(curr_w, curr_h):
                logger.log("✅ 检测到关卡入口，战斗结算流程结束", "debug")
                break
            
            # 3. 如果没回关卡，截图判断是否卡在结算界面
            # (因为 _check_level_entry 内部截图是局部的或未返回图像，这里我们需要重新截取用于匹配结算)
            result = capture_window(self.game_window.hwnd)
            if result is None or result[0] is None:
                continue
            screen, current_size = result
            
            # 4. 检测结算界面 (同时检测 Scene2 和 Scene1，确保覆盖所有结算阶段)
            # 用户逻辑：匹配 scene2_template 证明还在结算
            is_scene2, score2, _ = match_template(
                screen, self._common_img("settlement_panel.png"), current_size, threshold=0.75
            )
            is_scene1, score1, _ = match_template(
                screen, self._common_img("settlement.png"), current_size, threshold=0.75
            )
            
            if is_scene2 or is_scene1:
                debug_info = f"Scene2({score2:.2f})" if is_scene2 else f"Scene1({score1:.2f})"
                logger.log(f"仍在结算界面 [{debug_info}] -> 执行随机点击", "debug")
                
                # 5. [核心逻辑] 按照结算1界面的点击逻辑 (右下角随机点击)
                scale = min(current_size[0] / STANDARD_WIDTH, current_size[1] / STANDARD_HEIGHT)
                area_right = current_size[0] - 10
                area_bottom = current_size[1] - 10
                area_left = area_right - int(400 * scale)
                area_top = area_bottom - int(200 * scale)
                
                self._click_random_area(area_left, area_right, area_top, area_bottom)
            else:
                # 既不是关卡，也不是结算，可能是黑屏转场中
                pass
    def _click_random_area(self, x_min, x_max, y_min, y_max):
        """[辅助] 在指定区域内随机点击"""
        rand_x = random.randint(int(x_min), int(x_max))
        rand_y = random.randint(int(y_min), int(y_max))
        
        window_left, window_top, _, _ = self.game_window.rect
        abs_x = window_left + rand_x
        abs_y = window_top + rand_y
        
        # 稍微带点随机滑动的点击，更像真人
        pyautogui.moveTo(abs_x, abs_y, duration=random.uniform(0.1, 0.3))
        pyautogui.click()


    def _click_kun28_button(self, current_width, current_height):
        if not self.is_running:
            return
        button_left = int(KUN28_LEFT_REL * current_width)
        button_top = int(KUN28_TOP_REL * current_height)
        button_width = int(KUN28_WIDTH_REL * current_width)
        button_height = int(KUN28_HEIGHT_REL * current_height)
        window_left, window_top, _, _ = self.game_window.rect
        abs_left = window_left + button_left
        abs_top = window_top + button_top
        rand_x = random.randint(abs_left + 10, abs_left + button_width - 10)
        rand_y = random.randint(abs_top + 5, abs_top + button_height - 5)
        time.sleep(random.uniform(0.3, 0.8))
        pyautogui.click(rand_x, rand_y)

    def _click_exploration_button(self, current_width, current_height):
        if not self.is_running:
            return
        button_left = int(EXPLORATION_LEFT_REL * current_width)
        button_top = int(EXPLORATION_TOP_REL * current_height)
        button_width = int(EXPLORATION_WIDTH_REL * current_width)
        button_height = int(EXPLORATION_HEIGHT_REL * current_height)
        window_left, window_top, _, _ = self.game_window.rect
        abs_left = window_left + button_left
        abs_top = window_top + button_top
        rand_x = random.randint(abs_left + 5, abs_left + button_width - 5)
        rand_y = random.randint(abs_top + 5, abs_top + button_height - 5)
        time.sleep(random.uniform(0.4, 1.0))
        logger.log(f"点击探索按钮", "debug")
        pyautogui.click(rand_x, rand_y)

    def _check_level_entry(self, current_width, current_height):
        if not self.is_running:
            return False
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            return False
        screen, current_size = result
        is_in_level, _, _ = match_template(screen, self._img("entry.png"), current_size, threshold=0.80)
        return is_in_level
    
    TREASURE_TEMPLATE = "assets/templates/exploration_treasure.png"

    def _detect_and_collect_map_treasure(self):
        """
        [新增] 检测并领取探索地图上的宝箱
        逻辑：检测宝箱图标 -> 点击 -> 等待弹窗 -> 在下方40%区域点击确认
        """
        if not self.is_running:
            return False

        # 1. 截图
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            return False
        screen, current_size = result

        # 2. 匹配宝箱 (阈值设为 0.75，防止地图背景干扰)
        # 注意：你需要把上传的宝箱图片保存为 assets/templates/exploration_treasure.png
        is_match, score, pos = match_template(
            screen, 
            self._img("treasure.png"), 
            current_size, 
            threshold=0.75
        )

        if is_match and pos:
            logger.log(f"发现地图宝箱，准备领取 (匹配分: {score:.2f})", "info")
            
            # 3. 点击宝箱
            self._click_point_randomly(pos)
            
            # 等待领取弹窗弹出 (预留1.5~2.5秒动画时间)
            time.sleep(random.uniform(1.5, 2.5))

            # 4. 点击领取 (窗口下方 40% 区域)
            self._click_safe_bottom_area()
            
            # 等待领取动画结束
            time.sleep(random.uniform(1.5, 2.0))
            return True
            
        return False


    def _click_point_randomly(self, pos):
        """辅助方法：在指定点附近随机点击 (如果你代码里没有类似通用的，可以用这个)"""
        x, y = pos
        # 随机偏移 ±10 像素
        offset_x = random.randint(-10, 10)
        offset_y = random.randint(-10, 10)
        
        abs_x = self.game_window.rect[0] + x + offset_x
        abs_y = self.game_window.rect[1] + y + offset_y
        
        pyautogui.moveTo(abs_x, abs_y, duration=random.uniform(0.2, 0.4))
        pyautogui.click()