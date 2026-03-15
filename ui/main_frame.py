import customtkinter as ctk
from typing import Dict, Optional, Tuple, Any
from utils.logger import logger

# === 导入架构核心 ===
from ui.modules.base_module import BaseModule
from ui.module_factory import ModuleFactory  # 请确保你已经创建了 ui/module_factory.py
from ui.modules.event_tower_panel import EventTowerPanel

# === 🎨 UI 配色方案 ===
THEME = {
    "bg_main": "#F3F4F6",
    "bg_card": "#FFFFFF",
    "primary": "#6366F1",
    "primary_hover": "#4F46E5",
    "success": "#10B981",
    "success_hover": "#059669",
    "danger": "#EF4444",
    "danger_hover": "#DC2626",
    "text_main": "#1F2937",
    "text_sub": "#6B7280",
    "border": "#E5E7EB"
}

class MainFrame(ctk.CTkFrame):
    def __init__(self, master: Any, game_window: Any, **kwargs):
        super().__init__(master, **kwargs)
        self.root = master
        self.game_window = game_window  # 保存窗口对象

        # === 核心修改：模块实例缓存 ===
        # 格式: { "功能名": BaseModule实例 }
        self.modules: Dict[str, BaseModule] = {}
        self.current_module: Optional[BaseModule] = None

        self.configure(fg_color=THEME["bg_main"])
        self._setup_grid()
        self._create_top_bar()
        self._create_left_panel()
        self._create_right_log_panel()

        # 初始化：自动选择工厂里的第一个功能
        available_modules = ModuleFactory.get_available_modules()
        if available_modules:
            self.funct_combobox.set(available_modules[0])
            self._on_function_change(available_modules[0])

    def _setup_grid(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def _create_top_bar(self):
        """顶部状态栏"""
        top_bar = ctk.CTkFrame(self, fg_color=THEME["bg_card"], height=60, corner_radius=0)
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        top_bar.grid_columnconfigure(1, weight=1)

        self.window_detect_btn = ctk.CTkButton(
            top_bar, text="🔍 自动检测窗口", command=None, width=140, height=36,
            corner_radius=18, fg_color=THEME["primary"], hover_color=THEME["primary_hover"], font=("微软雅黑", 13, "bold")
        )
        self.window_detect_btn.pack(side="left", padx=20, pady=12)

        info_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, padx=20)

        def create_info_item(label_text, default_value):
            container = ctk.CTkFrame(info_frame, fg_color="transparent")
            container.pack(side="left", padx=15)
            ctk.CTkLabel(container, text=label_text, font=("微软雅黑", 12), text_color=THEME["text_sub"]).pack(side="left")
            val_label = ctk.CTkLabel(container, text=default_value, font=("微软雅黑", 12, "bold"),
                                     text_color=THEME["text_main"])
            val_label.pack(side="left", padx=(5, 0))
            return val_label

        self.title_label = create_info_item("窗口:", "未检测")
        self.size_label = create_info_item("尺寸:", "-- × --")
        self.pos_label = create_info_item("位置:", "(--, --)")

    def _create_left_panel(self):
        """左侧面板 — grid 布局确保按钮始终可见，配置区自适应滚动"""
        left_panel = ctk.CTkFrame(self, fg_color="transparent", width=300)
        left_panel.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)

        # grid 行分配：0=功能选择(固定) 1=配置区(伸缩) 2=调试(固定) 3=按钮(固定)
        left_panel.grid_rowconfigure(0, weight=0)
        left_panel.grid_rowconfigure(1, weight=1)
        left_panel.grid_rowconfigure(2, weight=0)
        left_panel.grid_rowconfigure(3, weight=0)
        left_panel.grid_columnconfigure(0, weight=1)

        # === 1. 功能选择 ===
        func_card = ctk.CTkFrame(left_panel, fg_color=THEME["bg_card"], corner_radius=10,
                                 border_width=1, border_color=THEME["border"])
        func_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(func_card, text="功能选择", font=("微软雅黑", 14, "bold"),
                     text_color=THEME["text_main"]).pack(anchor="w", padx=15, pady=(15, 5))

        available_modules = ModuleFactory.get_available_modules()
        self.funct_var = ctk.StringVar(value="")
        self.funct_combobox = ctk.CTkComboBox(
            func_card,
            values=available_modules,
            command=self._on_function_change,
            width=260, height=38, font=("微软雅黑", 13), state="readonly",
            fg_color="#F9FAFB", border_color=THEME["border"], button_color=THEME["primary"]
        )
        self.funct_combobox.pack(padx=15, pady=(0, 15), fill="x")

        # === 2. 可滚动配置区（填满剩余高度）===
        # scrollbar_fg_color 与背景同色：内容不超出时滚动条轨道不显眼
        self.config_card = ctk.CTkScrollableFrame(
            left_panel,
            fg_color=THEME["bg_card"],
            corner_radius=10,
            border_width=1,
            border_color=THEME["border"],
            scrollbar_fg_color=THEME["bg_card"],
            scrollbar_button_color="#E5E7EB",
            scrollbar_button_hover_color="#D1D5DB",
        )
        self.config_card.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        ctk.CTkLabel(self.config_card, text="运行配置", font=("微软雅黑", 14, "bold"),
                     text_color=THEME["text_main"]).pack(anchor="w", padx=15, pady=(15, 5))

        self.config_container = ctk.CTkFrame(self.config_card, fg_color="transparent")
        self.config_container.pack(fill="x", padx=15, pady=(0, 10))

        # === 3. 调试开关（固定底部）===
        debug_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        debug_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 4))
        self.debug_mode_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            debug_frame, text="调试模式", variable=self.debug_mode_var, command=self._on_debug_change,
            font=("微软雅黑", 12), text_color=THEME["text_sub"], checkbox_width=18, checkbox_height=18
        ).pack(side="left")

        # === 4. 开始/停止按钮（始终可见）===
        btn_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        btn_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.start_btn = ctk.CTkButton(
            btn_frame, text="▶ 开始任务", command=self._on_start_click,
            height=45, corner_radius=22, fg_color=THEME["success"], hover_color=THEME["success_hover"],
            font=("微软雅黑", 15, "bold"), width=130
        )
        self.start_btn.pack(side="left", padx=(0, 10), expand=True, fill="x")
        self.stop_btn = ctk.CTkButton(
            btn_frame, text="⏹ 停止", command=self._on_stop_click,
            height=45, corner_radius=22, fg_color=THEME["danger"], hover_color=THEME["danger_hover"],
            font=("微软雅黑", 15, "bold"), width=100, state="disabled"
        )
        self.stop_btn.pack(side="right", expand=True, fill="x")

        # 统计变量（供各模块调用）
        self.challenged_times_var = ctk.StringVar(value="0")
        self.kill_total_var = ctk.StringVar(value="0")

    def _create_right_log_panel(self):
        log_panel = ctk.CTkFrame(self, fg_color="transparent")
        log_panel.grid(row=1, column=1, sticky="nsew", padx=(0, 15), pady=15)
        log_panel.grid_rowconfigure(1, weight=1)
        log_panel.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(log_panel, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        ctk.CTkLabel(header, text="运行日志", font=("微软雅黑", 14, "bold"), text_color=THEME["text_main"]).pack(side="left")

        self.log_text = ctk.CTkTextbox(log_panel, wrap="word", font=("Consolas", 12), fg_color=THEME["bg_card"],
                                       text_color="#374151", corner_radius=10)
        self.log_text.grid(row=1, column=0, sticky="nsew")
        self.log_text.tag_config("info", foreground="#374151")
        self.log_text.tag_config("warn", foreground="#D97706")
        self.log_text.tag_config("error", foreground="#DC2626")
        self.log_text.tag_config("debug", foreground="#6366F1")
        self.log_text.tag_config("success", foreground="#059669")

    # === 核心逻辑交互 ===

    def _on_function_change(self, choice: str):
        """
        核心修改：当功能切换时，通过工厂获取模块并渲染配置
        """
        if not choice:
            return

        # 1. 懒加载: 如果模块实例还没创建，就问工厂要一个
        if choice not in self.modules:
            try:
                # 调用工厂创建实例
                new_module = ModuleFactory.create_module(choice, self, self.game_window)
                self.modules[choice] = new_module
            except Exception as e:
                logger.log(f"加载模块 '{choice}' 失败: {e}", "error")
                return

        # 2. 切换当前上下文
        self.current_module = self.modules[choice]

        # 3. 刷新配置区 UI
        # 先清空旧的控件
        for widget in self.config_container.winfo_children():
            widget.destroy()

        # 让当前模块画出它自己的配置界面
        if self.current_module:
            self.current_module.render_config_ui(self.config_container)

    def _on_start_click(self):
        if self.current_module:
            self.current_module.start()

    def _on_stop_click(self):
        if self.current_module:
            self.current_module.stop()

    def _on_debug_change(self):
        level = "debug" if self.debug_mode_var.get() else "info"
        logger.set_level(level)

    # --- 开放给外部调用的公共接口 ---

    def update_window_info(self, title: str, size: Tuple[int, int], pos: Tuple[int, int]):
        """更新顶部的窗口信息"""
        self.title_label.configure(text=title)
        self.size_label.configure(text=f"{size[0]} × {size[1]}")
        self.pos_label.configure(text=f"({pos[0]}, {pos[1]})")

    def update_challenged_times(self, times: int):
        """更新已挑战次数"""
        self.challenged_times_var.set(str(times))

    def update_kill_count(self, a: int, b: int):
        """更新杀怪/掉落统计"""
        self.kill_total_var.set(str(a + b))

    def reset_statistics(self):
        """重置所有统计数据"""
        self.challenged_times_var.set("0")
        self.kill_total_var.set("0")

    def set_start_stop_state(self, is_running: bool):
        """切换 开始/停止 按钮状态"""
        if is_running:
            self.start_btn.configure(state="disabled", fg_color="#9CA3AF")
            self.stop_btn.configure(state="normal")
            self.funct_combobox.configure(state="disabled")
        else:
            self.start_btn.configure(state="normal", fg_color=THEME["success"])
            self.stop_btn.configure(state="disabled")
            self.funct_combobox.configure(state="readonly")

    def append_log(self, message: str, level: str = "info"):
        """向日志框追加文本"""
        self.log_text.insert("end", message + "\n", level.lower())
        self.log_text.see("end")

    def bind_window_detect_command(self, cmd):
        """绑定顶部检测按钮的点击事件 (由 main.py 调用)"""
        self.window_detect_btn.configure(command=cmd)

    def _validate_num(self, value):
        """输入框数字验证器"""
        if value == "" or value.isdigit():
            return True
        try:
            float(value)
            return True
        except:
            return False