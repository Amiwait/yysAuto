import time
import random
import cv2
from core.game_window import GameWindow
from ui.modules.kun28_panel import Kun28Panel
from utils.logger import logger
from core.capture import capture_window, match_template

# === 1. 定义一个用于诊断的子类 ===
class DebugKun28Panel(Kun28Panel):
    """
    这是一个专门用于测试的'诊断版'面板。
    它覆盖了原有的 _is_interference_scene 方法，
    强制把匹配的分数打印出来，帮你通过数字看清为什么检测失败。
    """
    def _is_interference_scene(self):
        """覆盖原方法，添加详细调试信息"""
        if not self.is_running:
            return True
            
        result = capture_window(self.game_window.hwnd)
        if result is None or result[0] is None:
            print("❌ [诊断] 截图失败 (None)")
            return True # 这里的逻辑保留原样
            
        screen, current_size = result
        
        # 1. 诊断对话框
        dialog_tmpl = "assets/templates/girl_mask_dialog.png"
        is_dialog, score_d, _ = match_template(screen, dialog_tmpl, current_size, threshold=0.78)
        
        # 2. 诊断探索界面 (重点关注这个！)
        explo_tmpl = "assets/templates/exploration_map_bottom_icons.png"
        is_explo, score_e, _ = match_template(screen, explo_tmpl, current_size, threshold=0.5)
        
        # 打印诊断日志
        print(f"   🔍 [场景检测] 探索界面匹配分: {score_e:.4f} (阈值0.5) | 对话框: {score_d:.4f}")
        
        if is_dialog or is_explo:
            return True
            
        return False

# === 2. 模拟主界面配置 ===
class MockMainFrame:
    def __init__(self): self.root = None
    def get_threshold(self): return 0.8
    def get_delay_multiplier(self): return 1.0
    def is_reward_enabled(self): return True
    def get_settle_wait_time(self): return 5.0
    def get_monster_wait_range(self): return (1.0, 3.0)
    # 空实现
    def update_kill_count(self, a, b): pass
    def update_challenged_times(self, t): pass
    def reset_statistics(self): pass
    def set_start_stop_state(self, state): pass
    def get_selected_function(self): return "困28"
    def get_challenge_count(self): return None

# === 3. 测试主流程 ===
def run_test():
    print("=== 开始采集逻辑深度诊断 ===")
    
    # 初始化日志
    logger.set_level("debug")

    # 初始化窗口
    gw = GameWindow()
    if not gw.try_auto_set():
        print("❌ 未找到游戏窗口！请打开模拟器并保持前台。")
        return
    
    print(f"✅ 绑定窗口: {gw.title} ({gw.width}x{gw.height})")
    gw.activate()

    # 初始化模拟环境
    mock_frame = MockMainFrame()
    
    # 【关键】使用 DebugKun28Panel 而不是普通的 Kun28Panel
    # 这样我们就能看到 _is_interference_scene 里的秘密了
    panel = DebugKun28Panel(mock_frame, gw)
    
    # 手动设置状态
    panel.is_running = True
    panel.global_threshold = 0.8 

    print("\n⚠️  测试准备就绪！")
    print("👉 请手动将游戏停在【采集奖励结算界面】(有小纸人/红达摩)。")
    print("👉 脚本将执行 _collect_all_rewards 方法。")
    print("👉 请重点观察日志中 '🔍 [场景检测]' 后面的分数！")
    print("   如果分数低于 0.5，说明这就是它认为'没跳转'的原因。")
    print("3秒后开始...")
    time.sleep(3)

    try:
        panel._collect_all_rewards()
        print("\n✅ 测试流程结束")
        
    except KeyboardInterrupt:
        print("\n⏹ 用户强制停止")
    except Exception as e:
        print(f"\n❌ 发生异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()