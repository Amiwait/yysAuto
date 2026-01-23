import customtkinter as ctk
from utils.logger import logger

# === 🎨 UI 配色方案 (现代清爽风) ===
THEME = {
    "bg_main": "#F3F4F6",        # 整体背景色 (浅灰)
    "bg_card": "#FFFFFF",        # 卡片背景色 (纯白)
    "primary": "#6366F1",        # 主题色 (靛蓝)
    "primary_hover": "#4F46E5",  # 主题色悬停
    "success": "#10B981",        # 成功/开始 (翠绿)
    "success_hover": "#059669",
    "danger": "#EF4444",         # 危险/停止 (赤红)
    "danger_hover": "#DC2626",
    "text_main": "#1F2937",      # 主标题文字
    "text_sub": "#6B7280",       # 副标题/说明文字
    "border": "#E5E7EB"          # 边框颜色
}

class MainFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.root = master
        
        # 应用整体背景色
        self.configure(fg_color=THEME["bg_main"]) 
        
        self._setup_grid()
        self._create_top_bar()
        self._create_left_panel()
        self._create_right_log_panel()

    def _setup_grid(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def _create_top_bar(self):
        """顶部状态栏：白底阴影效果"""
        top_bar = ctk.CTkFrame(self, fg_color=THEME["bg_card"], height=60, corner_radius=0)
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        top_bar.grid_columnconfigure(1, weight=1)

        # 自动检测按钮 (胶囊样式)
        self.window_detect_btn = ctk.CTkButton(
            top_bar,
            text="🔍 自动检测窗口",
            command=None,
            width=140,
            height=36,
            corner_radius=18,  # 圆角胶囊
            fg_color=THEME["primary"],
            hover_color=THEME["primary_hover"],
            font=("微软雅黑", 13, "bold")
        )
        self.window_detect_btn.pack(side="left", padx=20, pady=12)

        # 窗口信息展示
        info_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, padx=20)
        
        # 辅助函数：创建信息标签
        def create_info_item(label_text, default_value):
            container = ctk.CTkFrame(info_frame, fg_color="transparent")
            container.pack(side="left", padx=15)
            ctk.CTkLabel(container, text=label_text, font=("微软雅黑", 12), text_color=THEME["text_sub"]).pack(side="left")
            val_label = ctk.CTkLabel(container, text=default_value, font=("微软雅黑", 12, "bold"), text_color=THEME["text_main"])
            val_label.pack(side="left", padx=(5, 0))
            return val_label

        self.title_label = create_info_item("窗口:", "未检测")
        self.size_label = create_info_item("尺寸:", "-- × --")
        self.pos_label = create_info_item("位置:", "(--, --)")

    def _create_left_panel(self):
        """左侧面板：卡片式布局"""
        # 左侧滚动容器 (防止小屏幕显示不全)
        left_panel = ctk.CTkFrame(self, fg_color="transparent", width=300)
        left_panel.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        
        # === 卡片 1: 功能选择 ===
        func_card = ctk.CTkFrame(left_panel, fg_color=THEME["bg_card"], corner_radius=10, border_width=1, border_color=THEME["border"])
        func_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(func_card, text="功能选择", font=("微软雅黑", 14, "bold"), text_color=THEME["text_main"]).pack(anchor="w", padx=15, pady=(15, 5))
        
        self.funct_var = ctk.StringVar(value="困28")
        self.funct_combobox = ctk.CTkComboBox(
            func_card,
            values=["困28", "自动探索", "自动御魂", "自动结界"],
            variable=self.funct_var,
            width=260,
            height=38,
            font=("微软雅黑", 13),
            state="readonly",
            fg_color="#F9FAFB",
            border_color=THEME["border"],
            button_color=THEME["primary"]
        )
        self.funct_combobox.pack(padx=15, pady=(0, 15), fill="x")

        # === 卡片 2: 参数配置 ===
        config_card = ctk.CTkFrame(left_panel, fg_color=THEME["bg_card"], corner_radius=10, border_width=1, border_color=THEME["border"])
        config_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(config_card, text="运行配置", font=("微软雅黑", 14, "bold"), text_color=THEME["text_main"]).pack(anchor="w", padx=15, pady=(15, 10))

        # 辅助函数：创建配置行
        def create_config_row(parent, label, entry_var, validate_cmd, width=60):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=5)
            ctk.CTkLabel(row, text=label, font=("微软雅黑", 12), text_color=THEME["text_sub"], width=100, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(
                row, textvariable=entry_var, width=width, height=30,
                font=("微软雅黑", 12), border_color=THEME["border"], fg_color="#F9FAFB",
                validate="key", validatecommand=validate_cmd
            )
            entry.pack(side="right")
            return entry

        # 挑战次数
        self.challenge_count_var = ctk.StringVar(value="")
        create_config_row(config_card, "挑战次数 (空=无限)", self.challenge_count_var, (self.root.register(self._validate_num), "%P"))

        # 结算等待
        self.settle_wait_var = ctk.StringVar(value="5")
        create_config_row(config_card, "结算等待 (秒)", self.settle_wait_var, (self.root.register(self._validate_num), "%P"))

        # 小怪等待 (特殊处理范围输入)
        wait_row = ctk.CTkFrame(config_card, fg_color="transparent")
        wait_row.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(wait_row, text="小怪等待 (秒)", font=("微软雅黑", 12), text_color=THEME["text_sub"], width=100, anchor="w").pack(side="left")
        
        self.wait_max_var = ctk.StringVar(value="5.0")
        ctk.CTkEntry(wait_row, textvariable=self.wait_max_var, width=50, height=30, font=("微软雅黑", 12), border_color=THEME["border"], fg_color="#F9FAFB").pack(side="right")
        ctk.CTkLabel(wait_row, text="~", text_color=THEME["text_sub"]).pack(side="right", padx=5)
        self.wait_min_var = ctk.StringVar(value="1.0")
        ctk.CTkEntry(wait_row, textvariable=self.wait_min_var, width=50, height=30, font=("微软雅黑", 12), border_color=THEME["border"], fg_color="#F9FAFB").pack(side="right")

        # 增加底部间距
        ctk.CTkFrame(config_card, height=10, fg_color="transparent").pack()

        # === 卡片 3: 实时统计 ===
        stats_card = ctk.CTkFrame(left_panel, fg_color=THEME["bg_card"], corner_radius=10, border_width=1, border_color=THEME["border"])
        stats_card.pack(fill="x", pady=(0, 15))

        self.challenged_times_var = ctk.StringVar(value="0")
        self.kill_total_var = ctk.StringVar(value="0")

        # 统计数据使用大号字体显示
        stats_grid = ctk.CTkFrame(stats_card, fg_color="transparent")
        stats_grid.pack(fill="x", padx=15, pady=15)
        stats_grid.grid_columnconfigure(0, weight=1)
        stats_grid.grid_columnconfigure(1, weight=1)

        # 左边：已挑战
        ctk.CTkLabel(stats_grid, text="已挑战(次)", font=("微软雅黑", 11), text_color=THEME["text_sub"]).grid(row=0, column=0)
        self.challenged_times_label = ctk.CTkLabel(stats_grid, textvariable=self.challenged_times_var, font=("微软雅黑", 20, "bold"), text_color=THEME["primary"])
        self.challenged_times_label.grid(row=1, column=0)

        # 右边：击杀数
        ctk.CTkLabel(stats_grid, text="总击杀(只)", font=("微软雅黑", 11), text_color=THEME["text_sub"]).grid(row=0, column=1)
        self.kill_total_label = ctk.CTkLabel(stats_grid, textvariable=self.kill_total_var, font=("微软雅黑", 20, "bold"), text_color="#10B981") 
        self.kill_total_label.grid(row=1, column=1)

        # === 底部控制按钮 ===
        # 先定义按钮容器，使用 side=bottom 沉底
        btn_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", pady=(0, 15)) # pady 稍微调整，给上方留空间
        
        self.start_btn = ctk.CTkButton(
            btn_frame, text="▶ 开始任务", command=None, height=45, corner_radius=22,
            fg_color=THEME["success"], hover_color=THEME["success_hover"], font=("微软雅黑", 15, "bold"),
            width=130
        )
        self.start_btn.pack(side="left", padx=(0, 10), expand=True, fill="x")
        
        self.stop_btn = ctk.CTkButton(
            btn_frame, text="⏹ 停止", command=None, height=45, corner_radius=22,
            fg_color=THEME["danger"], hover_color=THEME["danger_hover"], font=("微软雅黑", 15, "bold"),
            width=100, state="disabled"
        )
        self.stop_btn.pack(side="right", expand=True, fill="x")

        # === [新增] 调试模式开关 ===
        # 使用 side=bottom，且在 btn_frame 之后 pack，这会使它位于按钮的"上方"
        debug_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        debug_frame.pack(side="bottom", fill="x", padx=15, pady=(10, 10))

        self.debug_mode_var = ctk.BooleanVar(value=False)
        self.debug_chk = ctk.CTkCheckBox(
            debug_frame, 
            text="开启调试模式 (显示详细日志)", 
            variable=self.debug_mode_var,
            command=self._on_debug_mode_change,
            font=("微软雅黑", 12), 
            text_color=THEME["text_sub"],
            checkbox_width=18, 
            checkbox_height=18
        )
        self.debug_chk.pack(side="left")

    def _create_right_log_panel(self):
        """右侧日志面板：简洁终端风"""
        log_panel = ctk.CTkFrame(self, fg_color="transparent")
        log_panel.grid(row=1, column=1, sticky="nsew", padx=(0, 15), pady=15)
        log_panel.grid_rowconfigure(1, weight=1)
        log_panel.grid_columnconfigure(0, weight=1)

        # 标题栏
        header = ctk.CTkFrame(log_panel, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        ctk.CTkLabel(header, text="运行日志", font=("微软雅黑", 14, "bold"), text_color=THEME["text_main"]).pack(side="left")
        ctk.CTkLabel(header, text="详细记录", font=("微软雅黑", 11), text_color=THEME["text_sub"]).pack(side="right", anchor="s")

        # 文本框 (更细的边框，更柔和的背景)
        self.log_text = ctk.CTkTextbox(
            log_panel,
            wrap="word",
            font=("Consolas", 12),
            fg_color=THEME["bg_card"],
            text_color="#374151",
            border_width=1,
            border_color=THEME["border"],
            corner_radius=10,
            activate_scrollbars=False # 使用外部滚动条
        )
        self.log_text.grid(row=1, column=0, sticky="nsew")

        # 滚动条
        scrollbar = ctk.CTkScrollbar(log_panel, command=self.log_text.yview, fg_color="transparent", button_color=THEME["border"], button_hover_color=THEME["text_sub"])
        scrollbar.grid(row=1, column=1, sticky="ns", padx=(5, 0))
        self.log_text.configure(yscrollcommand=scrollbar.set)

        # 日志颜色配置
        self.log_text.tag_config("info", foreground="#374151")
        self.log_text.tag_config("warn", foreground="#D97706")
        self.log_text.tag_config("error", foreground="#DC2626")
        self.log_text.tag_config("debug", foreground="#6366F1")
        self.log_text.tag_config("success", foreground="#059669")

    # ========== 逻辑功能方法 ==========

    def _on_debug_mode_change(self):
        """[新增] 切换调试模式回调"""
        if self.debug_mode_var.get():
            logger.set_level("debug")
            logger.log("已开启调试模式 (显示详细日志)", "debug")
        else:
            logger.set_level("info")
            logger.log("已关闭调试模式 (仅显示关键信息)", "info")

    def update_window_info(self, title: str, size: tuple, pos: tuple):
        """更新窗口信息显示"""
        self.title_label.configure(text=title)
        self.size_label.configure(text=f"{size[0]} × {size[1]}")
        self.pos_label.configure(text=f"({pos[0]}, {pos[1]})")

    def reset_window_info(self):
        """重置窗口信息"""
        self.title_label.configure(text="未检测")
        self.size_label.configure(text="-- × --")
        self.pos_label.configure(text="(--, --)")

    def update_challenged_times(self, times):
        """更新挑战次数统计"""
        self.challenged_times_var.set(str(times))

    def update_kill_count(self, monster_total, boss_total):
        """更新击杀统计"""
        total = monster_total + boss_total
        self.kill_total_var.set(str(total)) 

    def reset_statistics(self):
        """重置统计数据"""
        self.challenged_times_var.set("0")
        self.kill_total_var.set("0")

    def append_log(self, message: str, level: str = "info"):
        """追加日志"""
        tag = level.lower()
        self.log_text.insert("end", message + "\n", tag)
        self.log_text.see("end")

    def get_selected_function(self):
        """获取当前选择的功能"""
        return self.funct_var.get()

    def get_challenge_count(self):
        """获取设定的挑战次数（None=无限）"""
        try:
            count = self.challenge_count_var.get().strip()
            return int(count) if count else None
        except ValueError:
            return None

    def get_settle_wait_time(self):
        """获取结算等待时长"""
        try:
            wait_time = float(self.settle_wait_var.get().strip())
            return wait_time if wait_time > 0 else 5.0
        except (ValueError, AttributeError):
            return 5.0
            
    def get_monster_wait_range(self):
        """获取小怪击杀等待间隔的[最小值, 最大值]"""
        try:
            min_wait = float(self.wait_min_var.get().strip())
            max_wait = float(self.wait_max_var.get().strip())
            # 确保最小值≤最大值
            if min_wait > max_wait:
                min_wait, max_wait = max_wait, min_wait
            return (min_wait, max_wait)
        except (ValueError, AttributeError):
            return (1.0, 5.0)

    # --- 按钮绑定方法 ---
    def bind_window_detect_command(self, command):
        self.window_detect_btn.configure(command=command)

    def bind_start_command(self, command):
        self.start_btn.configure(command=command)

    def bind_stop_command(self, command):
        self.stop_btn.configure(command=command)

    def set_start_stop_state(self, is_running: bool):
        """设置开始/停止按钮状态"""
        if is_running:
            self.start_btn.configure(state="disabled", fg_color="#9CA3AF") # 变灰
            self.stop_btn.configure(state="normal")
        else:
            self.start_btn.configure(state="normal", fg_color=THEME["success"])
            self.stop_btn.configure(state="disabled")

    # --- 验证方法 ---
    def _validate_float(self, value):
        if value == "": return True
        try:
            float(value)
            return True
        except ValueError:
            return False

    def _validate_num(self, value):
        if value == "" or value.isdigit(): return True
        try:
            float(value)
            return True
        except ValueError:
            return False