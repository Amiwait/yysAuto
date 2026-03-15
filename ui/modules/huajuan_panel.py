import customtkinter as ctk
from ui.modules.base_module import BaseModule
from utils.logger import logger


class ShuaHuajuanPanel(BaseModule):
    def __init__(self, main_frame, game_window):
        super().__init__(main_frame, game_window)
        self.module_name = "刷绘卷"
        self.folder_name = "shua_huajuan"

        # 统计变量
        self.monster_count = 0
        self.realm_raid_count = 0

    def render_config_ui(self, parent_frame):
        """渲染刷绘卷的专属配置"""

        # 1. 持续时间
        self._create_config_row(parent_frame, "持续时间 (分钟)", "duration_min", "60")

        # 2. 困28 配置块
        self._create_section(parent_frame, "困28", [
            ("战斗时间 (秒)", "kun28_battle_time", "30"),
            ("战斗间隔 (秒)", "kun28_battle_interval", "3"),
        ])

        # 3. 结界突破 配置块
        self._create_section(parent_frame, "结界突破", [
            ("战斗时间 (秒)", "realm_battle_time", "15"),
            ("战斗间隔 (秒)", "realm_battle_interval", "3"),
        ])

        # 4. 数据统计卡片（两列样式）
        stats_card = ctk.CTkFrame(
            parent_frame,
            fg_color="#F3F4F6",
            corner_radius=8
        )
        stats_card.pack(fill="x", pady=(12, 0))

        stats_grid = ctk.CTkFrame(stats_card, fg_color="transparent")
        stats_grid.pack(fill="x", padx=15, pady=12)
        stats_grid.grid_columnconfigure(0, weight=1)
        stats_grid.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(stats_grid, text="怪物", font=("微软雅黑", 11), text_color="#6B7280").grid(row=0, column=0)
        self.monster_count_var = ctk.StringVar(value="0")
        ctk.CTkLabel(
            stats_grid, textvariable=self.monster_count_var,
            font=("微软雅黑", 20, "bold"), text_color="#6366F1"
        ).grid(row=1, column=0)

        ctk.CTkLabel(stats_grid, text="结界", font=("微软雅黑", 11), text_color="#6B7280").grid(row=0, column=1)
        self.realm_raid_count_var = ctk.StringVar(value="0")
        ctk.CTkLabel(
            stats_grid, textvariable=self.realm_raid_count_var,
            font=("微软雅黑", 20, "bold"), text_color="#10B981"
        ).grid(row=1, column=1)

    def _create_section(self, parent, title, fields):
        """创建带边框的配置分组"""
        # 外层容器加边框
        section = ctk.CTkFrame(
            parent,
            fg_color="#F9FAFB",
            border_width=1,
            border_color="#E5E7EB",
            corner_radius=8
        )
        section.pack(fill="x", pady=(8, 0))

        # 标题
        ctk.CTkLabel(
            section, text=title,
            font=("微软雅黑", 12, "bold"), text_color="#374151"
        ).pack(anchor="w", padx=10, pady=(6, 2))

        # 内部配置行
        inner = ctk.CTkFrame(section, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=(0, 8))

        for label, var_name, default in fields:
            self._create_config_row(inner, label, var_name, default)

    def run(self):
        """核心业务逻辑（待实现）"""
        logger.log("刷绘卷功能尚未实现", "warn")

    def update_stats(self, monster_count: int, realm_raid_count: int):
        """更新统计数据（供后续逻辑调用）"""
        self.monster_count = monster_count
        self.realm_raid_count = realm_raid_count
        self.monster_count_var.set(str(monster_count))
        self.realm_raid_count_var.set(str(realm_raid_count))
