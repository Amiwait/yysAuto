import threading
import datetime

class Logger:
    # 定义日志等级权重
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    SUCCESS = 50

    # 字符串到权重的映射
    LEVEL_MAP = {
        "debug": DEBUG,
        "info": INFO,
        "warn": WARN,
        "error": ERROR,
        "success": SUCCESS
    }

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Logger, cls).__new__(cls)
                cls._instance.listeners = []
                # 默认只显示 INFO 及以上 (过滤掉 DEBUG)
                cls._instance.current_level = cls.INFO 
        return cls._instance

    def set_level(self, level_str):
        """
        设置日志打印级别
        :param level_str: 'debug', 'info', 'warn', 'error'
        """
        level_weight = self.LEVEL_MAP.get(level_str.lower(), self.INFO)
        self.current_level = level_weight

    def add_listener(self, callback):
        self.listeners.append(callback)

    def log(self, message, level="info"):
        """
        记录日志
        :param message: 日志内容
        :param level: 日志等级 ('debug', 'info', 'warn', 'error', 'success')
        """
        # 1. 检查等级是否足够
        msg_weight = self.LEVEL_MAP.get(level.lower(), self.INFO)
        if msg_weight < self.current_level:
            return  # 等级不够，直接忽略

        # 2. 格式化日志
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        level_cn_map = {
            "debug": "调试",
            "info": "信息",
            "warn": "警告",
            "error": "错误",
            "success": "成功"
        }
        level_tag = level_cn_map.get(level.lower(), "信息")
        
        formatted_message = f"[{level_tag}] {message}"
        full_log = f"{timestamp} {formatted_message}"

        # 3. 打印到控制台 (可选，方便开发看)
        print(full_log)

        # 4. 通知 UI 更新
        for listener in self.listeners:
            # 这里的 level 传原始英文，用于 UI 颜色判断
            listener(full_log, level)

logger = Logger()