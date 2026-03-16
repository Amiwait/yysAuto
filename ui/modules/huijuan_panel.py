import customtkinter as ctk
import time
import random
import pyautogui
from core.capture import capture_window, match_template, match_all_template
from utils.logger import logger
from ui.modules.base_module import BaseModule

# 复用 kun28 布局常量
STANDARD_WIDTH  = 968
STANDARD_HEIGHT = 584
KUN28_LEFT_REL        = 785 / STANDARD_WIDTH
KUN28_TOP_REL         = 403 / STANDARD_HEIGHT
KUN28_WIDTH_REL       = 160 / STANDARD_WIDTH
KUN28_HEIGHT_REL      =  80 / STANDARD_HEIGHT
EXPLORATION_LEFT_REL  = 663 / STANDARD_WIDTH
EXPLORATION_TOP_REL   = 421 / STANDARD_HEIGHT
EXPLORATION_WIDTH_REL =  98 / STANDARD_WIDTH
EXPLORATION_HEIGHT_REL =  46 / STANDARD_HEIGHT
MONSTER_PER_LEVEL     = 7
COLLECT_DETECT_STD_X  = 275
COLLECT_DETECT_STD_Y  = 210
COLLECT_DETECT_STD_W  = 430
COLLECT_DETECT_STD_H  = 280


class ShuaHuajuanPanel(BaseModule):
    def __init__(self, main_frame, game_window):
        super().__init__(main_frame, game_window)
        self.module_name = "刷绘卷"
        self.folder_name = "shua_huajuan"
        self.monster_count = 0
        self.realm_raid_count = 0

    # ── 模板路径辅助 ──────────────────────────────────────────────────────────

    def _k28_img(self, filename: str) -> str:
        return f"assets/templates/kun28/{filename}"

    def _rr_img(self, filename: str) -> str:
        return f"assets/templates/realm_raid/{filename}"

    # ── UI ───────────────────────────────────────────────────────────────────

    def render_config_ui(self, parent_frame):
        self._create_config_row(parent_frame, "持续时间 (分钟)", "duration_min", "60")

        self._create_section(parent_frame, "困28", [
            ("战斗时间 (秒)", "kun28_battle_time", "30"),
            ("战斗间隔 (秒)", "kun28_battle_interval", "3"),
        ])

        self._create_section(parent_frame, "结界突破", [
            ("战斗时间 (秒)", "realm_battle_time", "15"),
            ("战斗间隔 (秒)", "realm_battle_interval", "3"),
        ])

        # 数据统计卡片
        stats_card = ctk.CTkFrame(parent_frame, fg_color="#F3F4F6", corner_radius=8)
        stats_card.pack(fill="x", pady=(12, 0))

        stats_grid = ctk.CTkFrame(stats_card, fg_color="transparent")
        stats_grid.pack(fill="x", padx=15, pady=12)
        stats_grid.grid_columnconfigure(0, weight=1)
        stats_grid.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(stats_grid, text="怪物", font=("微软雅黑", 11),
                     text_color="#6B7280").grid(row=0, column=0)
        self.monster_count_var = ctk.StringVar(value="0")
        ctk.CTkLabel(stats_grid, textvariable=self.monster_count_var,
                     font=("微软雅黑", 20, "bold"), text_color="#6366F1").grid(row=1, column=0)

        ctk.CTkLabel(stats_grid, text="结界", font=("微软雅黑", 11),
                     text_color="#6B7280").grid(row=0, column=1)
        self.realm_raid_count_var = ctk.StringVar(value="0")
        ctk.CTkLabel(stats_grid, textvariable=self.realm_raid_count_var,
                     font=("微软雅黑", 20, "bold"), text_color="#10B981").grid(row=1, column=1)

    def _create_section(self, parent, title, fields):
        section = ctk.CTkFrame(parent, fg_color="#F9FAFB",
                               border_width=1, border_color="#E5E7EB", corner_radius=8)
        section.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(section, text=title,
                     font=("微软雅黑", 12, "bold"), text_color="#374151").pack(
            anchor="w", padx=10, pady=(6, 2))
        inner = ctk.CTkFrame(section, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=(0, 8))
        for label, var_name, default in fields:
            self._create_config_row(inner, label, var_name, default)

    # ── 主循环 ────────────────────────────────────────────────────────────────

    def run(self):
        try:
            duration_min = float(self.config_vars["duration_min"].get())
        except Exception:
            duration_min = 60.0

        end_time = time.time() + duration_min * 60
        self.monster_count = 0
        self.realm_raid_count = 0
        self.monster_count_var.set("0")
        self.realm_raid_count_var.set("0")
        logger.log(f"刷绘卷开始，计划运行 {duration_min:.0f} 分钟", "info")

        while self.is_running and time.time() < end_time:
            remaining = (end_time - time.time()) / 60
            logger.log(f"--- 困28轮次开始，剩余 {remaining:.1f} 分钟 ---", "info")

            # 1. 进入困28关卡
            if not self._k28_enter_level():
                if self.is_running:
                    time.sleep(1.5)
                continue

            # 2. 关卡内战斗
            monsters_killed, success = self._k28_fight_in_level()
            if success:
                self.monster_count += monsters_killed
                self.monster_count_var.set(str(self.monster_count))
                logger.log(
                    f"困28完成，本轮击杀 {monsters_killed} 只，累计 {self.monster_count}", "success"
                )

                # 3. 检查结界突破券（预留，暂不实现）
                ticket_result = self._check_realm_ticket()
                logger.log(f"结界突破券: {ticket_result}", "debug")

                # 4. 判断是否进行结界突破
                if self._should_do_realm_raid(ticket_result):
                    logger.log("满足结界突破条件，开始结界突破...", "info")
                    if self._rr_do_single_raid():
                        self.realm_raid_count += 1
                        self.realm_raid_count_var.set(str(self.realm_raid_count))
                        time.sleep(self._cfg_f("realm_battle_interval", 3.0))

            # 5. 困28轮次间隔
            if self.is_running:
                time.sleep(self._cfg_f("kun28_battle_interval", 3.0))

        logger.log(
            f"刷绘卷结束 | 怪物: {self.monster_count} | 结界突破: {self.realm_raid_count}",
            "success",
        )

    # ── 结界突破条件判断（预留）────────────────────────────────────────────────

    def _check_realm_ticket(self):
        """检查结界突破券数量（暂不实现，返回 None）。
        TODO: 实现 OCR 读取后补充此处逻辑。"""
        return None

    def _should_do_realm_raid(self, ticket_result) -> bool:  # noqa: ARG002
        """判断是否应当进行结界突破（暂时始终返回 False）。
        TODO: 根据 ticket_result 判断条件后启用。"""
        return False

    # ══════════════════════════════════════════════════════════════════════════
    # 困28 核心逻辑（基于 kun28_panel.py，模板路径改为 _k28_img）
    # ══════════════════════════════════════════════════════════════════════════

    def _k28_enter_level(self) -> bool:
        """进入困28关卡入口"""
        if not self.is_running:
            return False
        logger.log("尝试进入困28关卡...", "debug")
        self.game_window.activate()
        time.sleep(0.8)

        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            logger.log("截图失败", "error")
            return False
        screen, current_size = result
        cw, ch = current_size

        # 情况 A：停在"少女与面具"对话框
        is_dialog, val, _ = match_template(
            screen, self._k28_img("dialog.png"), current_size, threshold=0.78
        )
        logger.log(f"少女对话框匹配: {val:.2f}", "debug")
        if is_dialog:
            self._k28_click_exploration_btn(cw, ch)
            time.sleep(random.uniform(2.0, 3.5))
            return self._k28_check_level_entry(cw, ch)

        # 情况 B：停在探索地图
        if self.is_in_exploration():
            self._k28_click_kun28_btn(cw, ch)
            time.sleep(random.uniform(2.0, 4.0))
            result2 = capture_window(self.game_window.hwnd)
            if result2 and result2[0] is not None:
                scr2, _ = result2
                is_dialog2, _, _ = match_template(
                    scr2, self._k28_img("dialog.png"), current_size, threshold=0.78
                )
                if is_dialog2:
                    self._k28_click_exploration_btn(cw, ch)
                    time.sleep(random.uniform(2.0, 3.5))
                    return self._k28_check_level_entry(cw, ch)
        return False

    def _k28_fight_in_level(self):
        """关卡内战斗：7 小怪 + 1 BOSS + 采集 + 宝箱。
        返回 (monsters_killed: int, success: bool)"""
        if not self.is_running or not self._k28_check_if_in_level():
            return 0, False

        monster_killed = 0
        while monster_killed < MONSTER_PER_LEVEL and self.is_running:
            logger.log(f"击杀第 {monster_killed + 1}/{MONSTER_PER_LEVEL} 只小怪", "info")
            if self._k28_click_monster("normal"):
                self._k28_wait_settlement()
                monster_killed += 1
                if monster_killed < MONSTER_PER_LEVEL:
                    time.sleep(random.uniform(1.0, 5.0))
            else:
                detect = self._k28_detect_monster_or_boss()
                if detect and detect[0] == "boss":
                    logger.log(f"已击杀 {monster_killed} 只，发现 BOSS，提前进入 BOSS 战", "info")
                    break
                else:
                    logger.log("无法继续击杀小怪，本关放弃", "warn")
                    return monster_killed, False

        if not self.is_running:
            return monster_killed, False

        time.sleep(random.uniform(2.5, 8.0))
        logger.log("开始挑战 BOSS", "info")
        if self._k28_click_monster("boss") and self.is_running:
            self._k28_wait_settlement()
            monster_killed += 1
            logger.log("BOSS 击杀完成", "info")
            time.sleep(random.uniform(5, 10))
            self._k28_collect_all_rewards()
            time.sleep(random.uniform(5, 10))
            self._k28_detect_and_collect_map_treasure()
            return monster_killed, True
        else:
            logger.log("BOSS 击杀失败", "warn")
            return monster_killed, False

    def _k28_wait_settlement(self):
        """等待困28战斗结算，读取 kun28_battle_time 配置"""
        if not self.is_running:
            return
        wait_s = self._cfg_f("kun28_battle_time", 30.0)
        logger.log(f"等待战斗结算 ({wait_s}s)...", "debug")
        time.sleep(wait_s)

        start = time.time()
        rect = self.game_window.rect
        cw = rect[2] - rect[0]
        ch = rect[3] - rect[1]

        while self.is_running:
            if time.time() - start > 60:
                logger.log("结算流程超时 (60s)，强制退出", "warn")
                break
            time.sleep(random.uniform(0.3, 1.0))

            if self._k28_check_level_entry(cw, ch):
                logger.log("已返回关卡界面，结算完成", "debug")
                break

            result = capture_window(self.game_window.hwnd)
            if result is None or result[0] is None:
                continue
            screen, current_size = result

            is_s2, _, _ = match_template(
                screen, self._common_img("settlement_panel.png"), current_size, threshold=0.75
            )
            is_s1, _, _ = match_template(
                screen, self._common_img("settlement.png"), current_size, threshold=0.75
            )
            if is_s2 or is_s1:
                scale = min(current_size[0] / STANDARD_WIDTH, current_size[1] / STANDARD_HEIGHT)
                ar = current_size[0] - 10
                ab = current_size[1] - 10
                al = ar - int(400 * scale)
                at = ab - int(200 * scale)
                self._click_random_area(al, ar, at, ab)

    # ── 困28 辅助方法 ─────────────────────────────────────────────────────────

    def _k28_detect_monster_or_boss(self):
        if not self.is_running:
            return None
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            return None
        screen, current_size = result

        found_m, score_m, pos_m = match_template(
            screen, self._k28_img("monster.png"), current_size, threshold=0.8
        )
        if found_m and pos_m:
            logger.log(f"检测到小怪 (分: {score_m:.2f})", "debug")
            return ("normal", pos_m, score_m)

        found_b, score_b, pos_b = match_template(
            screen, self._k28_img("boss.png"), current_size, threshold=0.65
        )
        if found_b and pos_b:
            logger.log(f"检测到 BOSS (分: {score_b:.2f})", "debug")
            return ("boss", pos_b, score_b)
        return None

    def _k28_click_monster(self, monster_type="normal") -> bool:
        if not self.is_running:
            return False
        max_retries = 10 if monster_type == "normal" else 20
        for _ in range(max_retries):
            if not self.is_running:
                return False
            detect = self._k28_detect_monster_or_boss()
            if detect is not None:
                dtype, pos, score = detect
                if dtype == monster_type:
                    cx, cy = pos
                    abs_x = self.game_window.rect[0] + cx + random.randint(-20, 20)
                    abs_y = self.game_window.rect[1] + cy + random.randint(-15, 15)
                    time.sleep(random.uniform(0.1, 0.25))
                    pyautogui.click(abs_x, abs_y)
                    return True
                if monster_type == "normal" and dtype == "boss":
                    logger.log("找小怪时发现 BOSS，停止", "info")
                    return False
            # 没找到目标：小怪则向左拖动，BOSS 则等待
            if monster_type == "normal":
                self._k28_drag_page_left()
            else:
                time.sleep(0.5)
        logger.log(f"未找到目标: {monster_type}", "warn")
        return False

    def _k28_drag_page_left(self):
        if not self.is_running:
            return
        wr = self.game_window.rect
        ww = wr[2] - wr[0]
        wh = wr[3] - wr[1]
        cx = wr[0] + ww / 2
        cy = wr[1] + wh / 2
        sx = int(random.uniform(cx - ww * 0.2, cx + ww * 0.2))
        sy = int(random.uniform(cy - wh * 0.2, cy + wh * 0.2))
        dist = ww * random.uniform(0.2, 0.4)
        ex = int(sx - dist)
        ey = int(sy + random.randint(-int(wh * 0.05), int(wh * 0.05)))
        pyautogui.moveTo(sx, sy, duration=random.uniform(0.1, 0.2))
        time.sleep(random.uniform(0.05, 0.1))
        pyautogui.mouseDown()
        time.sleep(random.uniform(0.05, 0.15))
        pyautogui.moveTo(ex, ey, duration=random.uniform(0.25, 0.5), tween=pyautogui.easeOutQuad)
        time.sleep(random.uniform(0.05, 0.15))
        pyautogui.mouseUp()
        time.sleep(0.8)

    def _k28_check_if_in_level(self) -> bool:
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            return False
        screen, sz = result
        in_level, _, _ = match_template(screen, self._k28_img("entry.png"), sz, threshold=0.80)
        return in_level

    def _k28_check_level_entry(self, current_width, current_height) -> bool:
        if not self.is_running:
            return False
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            return False
        screen, sz = result
        in_level, _, _ = match_template(screen, self._k28_img("entry.png"), sz, threshold=0.80)
        return in_level

    def _k28_click_kun28_btn(self, cw, ch):
        if not self.is_running:
            return
        bl = int(KUN28_LEFT_REL * cw)
        bt = int(KUN28_TOP_REL * ch)
        bw = int(KUN28_WIDTH_REL * cw)
        bh = int(KUN28_HEIGHT_REL * ch)
        wl, wt, _, _ = self.game_window.rect
        rx = random.randint(wl + bl + 10, wl + bl + bw - 10)
        ry = random.randint(wt + bt + 5, wt + bt + bh - 5)
        time.sleep(random.uniform(0.3, 0.8))
        pyautogui.click(rx, ry)

    def _k28_click_exploration_btn(self, cw, ch):
        if not self.is_running:
            return
        bl = int(EXPLORATION_LEFT_REL * cw)
        bt = int(EXPLORATION_TOP_REL * ch)
        bw = int(EXPLORATION_WIDTH_REL * cw)
        bh = int(EXPLORATION_HEIGHT_REL * ch)
        wl, wt, _, _ = self.game_window.rect
        rx = random.randint(wl + bl + 5, wl + bl + bw - 5)
        ry = random.randint(wt + bt + 5, wt + bt + bh - 5)
        time.sleep(random.uniform(0.4, 1.0))
        pyautogui.click(rx, ry)

    def _k28_is_interference(self) -> bool:
        """是否处于干扰场景（少女与面具对话框 / 探索地图）"""
        if not self.is_running:
            return True
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            return True
        screen, sz = result
        is_dialog, _, _ = match_template(screen, self._k28_img("dialog.png"), sz, threshold=0.78)
        if is_dialog:
            return True
        is_explore, _, _ = match_template(
            screen, self._k28_img("explore_icon.png"), sz, threshold=0.65
        )
        return is_explore

    def _k28_detect_collect_reward(self):
        if not self.is_running:
            return None
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            return None
        screen, (ww, wh) = result
        sx, sy = ww / STANDARD_WIDTH, wh / STANDARD_HEIGHT
        dx = max(0, int(COLLECT_DETECT_STD_X * sx))
        dy = max(0, int(COLLECT_DETECT_STD_Y * sy))
        dw = min(int(COLLECT_DETECT_STD_W * sx), ww - dx)
        dh = min(int(COLLECT_DETECT_STD_H * sy), wh - dy)
        crop = screen[dy:dy + dh, dx:dx + dw]
        if crop.size == 0:
            return None
        found, _, pos = match_template(
            crop, self._k28_img("reward.png"), (ww, wh), threshold=0.8
        )
        if found and pos:
            return (pos[0] + dx, pos[1] + dy)
        return None

    def _k28_click_collect_reward(self, pos):
        if not self.is_running:
            return
        cx, cy = pos
        abs_x = self.game_window.rect[0] + cx + random.randint(-15, 15)
        abs_y = self.game_window.rect[1] + cy + random.randint(-15, 15)
        time.sleep(random.uniform(0.1, 0.25))
        pyautogui.click(abs_x, abs_y)

    def _k28_count_rewards(self) -> int:
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            return 0
        screen, sz = result
        pts = match_all_template(screen, self._k28_img("reward.png"), sz, threshold=0.8)
        return len(pts)

    def _k28_collect_all_rewards(self):
        if not self.is_running or self._k28_is_interference():
            return
        logger.log("开始采集奖励...", "info")
        initial_count = self._k28_count_rewards()
        if initial_count > 0:
            logger.log(f"发现 {initial_count} 个奖励", "info")

        collected = 0
        no_reward_streak = 0
        while self.is_running:
            pos = self._k28_detect_collect_reward()
            if pos:
                no_reward_streak = 0
                collected += 1
                self._k28_click_collect_reward(pos)
                if collected < initial_count:
                    # 非最后一个：快速确认
                    time.sleep(0.6)
                    self._click_safe_bottom_area()
                    time.sleep(random.uniform(0.8, 1.2))
                else:
                    # 可能是最后一个：等待自动跳转
                    time.sleep(random.uniform(3, 5))
                    if self._k28_is_interference():
                        logger.log("采集后已自动跳转", "debug")
                        break
                    self._click_safe_bottom_area()
                    time.sleep(1.0)
            else:
                no_reward_streak += 1
                if no_reward_streak >= 3:
                    break
                time.sleep(0.5)

        if collected > 0:
            logger.log(f"采集完成，共 {collected} 个", "info")
        else:
            logger.log("无采集奖励", "info")

    def _k28_detect_and_collect_map_treasure(self):
        if not self.is_running:
            return
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            return
        screen, sz = result
        found, _, pos = match_template(
            screen, self._k28_img("treasure.png"), sz, threshold=0.75
        )
        if found and pos:
            logger.log("发现地图宝箱，准备领取", "info")
            self._click_pos(pos)
            time.sleep(random.uniform(1.5, 2.5))
            self._click_safe_bottom_area()
            time.sleep(random.uniform(1.5, 2.0))

    # ══════════════════════════════════════════════════════════════════════════
    # 结界突破核心逻辑
    # ══════════════════════════════════════════════════════════════════════════

    def _rr_do_single_raid(self) -> bool:
        """执行一次完整结界突破流程，返回是否成功"""
        wait_time = self._cfg_f("realm_battle_time", 15.0)

        target_pos = self._rr_find_target()
        if target_pos is None:
            logger.log("未发现结界突破目标", "warn")
            return False

        logger.log("发现结界目标，准备进攻...", "info")
        self._click_pos(target_pos)
        time.sleep(random.uniform(0.8, 1.2))

        if not self._rr_click_attack_button():
            logger.log("未找到进攻按钮", "warn")
            self._click_safe_bottom_area()
            return False

        logger.log(f"结界突破战斗开始，等待 {wait_time}s...", "info")
        time.sleep(wait_time)
        self._rr_handle_settlement()
        logger.log("结界突破完成", "success")
        return True

    def _rr_find_target(self):
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            return None
        screen, sz = result
        found, _, pos = match_template(screen, self._rr_img("target.png"), sz, threshold=0.8)
        return pos if found else None

    def _rr_click_attack_button(self) -> bool:
        time.sleep(0.5)
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            return False
        screen, sz = result
        found, _, pos = match_template(screen, self._rr_img("attack.png"), sz, threshold=0.8)
        if found and pos:
            self._click_pos(pos)
            return True
        return False

    def _rr_handle_settlement(self):
        for _ in range(random.randint(3, 5)):
            if not self.is_running:
                break
            self._click_safe_bottom_area()
            time.sleep(random.uniform(0.8, 1.2))

    # ══════════════════════════════════════════════════════════════════════════
    # 通用辅助方法
    # ══════════════════════════════════════════════════════════════════════════

    def _click_safe_bottom_area(self):
        """在底部 36% 安全区域内随机点击（跳过结算 / 关闭弹窗）"""
        if not self.is_running:
            return
        wr = self.game_window.rect
        wx, wy = wr[0], wr[1]
        ww = wr[2] - wr[0]
        wh = wr[3] - wr[1]
        y_top = int(wh * 0.64) + 10
        y_bot = wh - 10
        cx = random.randint(wx + 10, wx + ww - 10)
        cy = random.randint(wy + y_top, wy + y_bot)
        time.sleep(random.uniform(0.1, 0.3))
        pyautogui.moveTo(cx, cy, duration=random.uniform(0.15, 0.4), tween=pyautogui.easeOutQuad)
        time.sleep(random.uniform(0.05, 0.15))
        pyautogui.click()

    def _click_pos(self, pos, skew: int = 10):
        """在目标坐标附近随机偏移后点击"""
        x, y = pos
        abs_x = self.game_window.rect[0] + x + random.randint(-skew, skew)
        abs_y = self.game_window.rect[1] + y + random.randint(-skew, skew)
        pyautogui.moveTo(abs_x, abs_y, duration=random.uniform(0.15, 0.35))
        pyautogui.click()

    def _cfg_f(self, key: str, default: float) -> float:
        """安全读取 float 类型的配置变量"""
        try:
            return float(self.config_vars[key].get())
        except Exception:
            return default

    def update_stats(self, monster_count: int, realm_raid_count: int):
        """外部更新统计数据的入口"""
        self.monster_count = monster_count
        self.realm_raid_count = realm_raid_count
        self.monster_count_var.set(str(monster_count))
        self.realm_raid_count_var.set(str(realm_raid_count))
