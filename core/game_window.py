import win32gui
import win32con
import win32api
import time
from utils.logger import logger

# === [关键修复 1] 定义标准分辨率常量 ===
# 这是制作模板图片时的基准分辨率，用于计算缩放比例
# 如果缺少这两个变量，capture.py 就会报错 ImportError
STANDARD_WIDTH = 968 
STANDARD_HEIGHT = 584

class GameWindow:
    def __init__(self):
        self.hwnd = None  # 窗口句柄
        self.title = ""   # 窗口标题
        self.rect = (0, 0, 0, 0)  # 窗口矩形 (left, top, right, bottom)

    @property
    def width(self):
        """计算窗口宽度（right - left）"""
        return self.rect[2] - self.rect[0] if self.rect else 0

    @property
    def height(self):
        """计算窗口高度（bottom - top）"""
        return self.rect[3] - self.rect[1] if self.rect else 0

    @property
    def left(self):
        """窗口左坐标"""
        return self.rect[0] if self.rect else 0

    @property
    def top(self):
        """窗口上坐标"""
        return self.rect[1] if self.rect else 0

    def try_auto_set(self):
        """自动检测并设置阴阳师窗口（核心逻辑）"""
        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                # 匹配阴阳师窗口标题（根据你的模拟器调整关键词）
                if "MuMu安卓设备" in title:
                    extra["hwnd"] = hwnd
                    extra["title"] = title
                    extra["rect"] = win32gui.GetWindowRect(hwnd)
                    return False  # 找到后停止遍历
            return True

        result = {"hwnd": None, "title": "", "rect": (0,0,0,0)}
        win32gui.EnumWindows(callback, result)

        if result["hwnd"]:
            self.hwnd = result["hwnd"]
            self.title = result["title"]
            self.rect = result["rect"]
            return True
        return False

    def is_valid(self):
        """判断窗口是否有效"""
        return self.hwnd is not None and win32gui.IsWindow(self.hwnd)

    def activate(self):
        """
        激活游戏窗口（将窗口置顶）
        [关键修复 2] 增加对 -32000 坐标（最小化）的强制还原处理
        """
        if self.hwnd:
            try:
                # 1. 检查是否最小化 (坐标 -32000)
                # 某些情况下 IsIconic 判断不准，直接看坐标最稳
                current_rect = win32gui.GetWindowRect(self.hwnd)
                if current_rect[0] == -32000 or current_rect[1] == -32000:
                    logger.log("检测到窗口最小化，正在还原...", "warn")
                    win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
                    time.sleep(0.5) # 给一点动画时间
                
                # 2. 常规恢复 (IsIconic)
                if win32gui.IsIconic(self.hwnd):
                    win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
                
                # 3. 尝试置顶
                win32gui.SetForegroundWindow(self.hwnd)
                
                # 4. [关键] 重新更新窗口坐标
                # 还原窗口后，坐标变了，必须刷新 self.rect，否则后续截图和点击都会错位
                self.rect = win32gui.GetWindowRect(self.hwnd)
                
            except Exception as e:
                # 备选方案：通过发送 Alt 键来获取输入流权限
                try:
                    import win32com.client
                    shell = win32com.client.Dispatch("WScript.Shell")
                    shell.SendKeys('%') # 发送 Alt 键
                    win32gui.SetForegroundWindow(self.hwnd)
                    # 激活后也要刷新坐标
                    self.rect = win32gui.GetWindowRect(self.hwnd)
                except:
                    print(f"警告: 无法将窗口置顶 (可能被系统拦截): {e}")