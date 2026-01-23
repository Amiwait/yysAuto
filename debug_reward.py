import cv2
import numpy as np
import os
import time

# 导入你的核心模块
# 确保此脚本在 yysAuto 文件夹同级，或者在 yysAuto 内部但能正确导入

from core.game_window import GameWindow
from core.capture import capture_window

# === 配置区域 (必须与 kun28_panel.py 中的一致) ===
STANDARD_WIDTH = 968
STANDARD_HEIGHT = 584 # 注意：之前代码里有时是 548 有时是 584，请确认你的 capture.py 里是多少，这里暂按 584
COLLECT_DETECT_STD_X = 100
COLLECT_DETECT_STD_Y = 80
COLLECT_DETECT_STD_W = 500
COLLECT_DETECT_STD_H = 340
TEMPLATE_PATH = "assets/templates/collect_reward_marker.png"

def debug_collect_reward():
    print("=== 开始采集奖励调试分析 ===")
    
    # 1. 连接游戏窗口
    gw = GameWindow()
    print("正在查找游戏窗口...")
    if not gw.try_auto_set():
        print("❌ 未找到游戏窗口，请确保游戏已打开且标题包含 'MuMu' 或你设置的关键字")
        return

    print(f"✅ 找到窗口: {gw.title} ({gw.width}x{gw.height})")
    gw.activate()
    time.sleep(0.5)

    # 2. 截图
    img_res = capture_window(gw.hwnd)
    if img_res is None or img_res[0] is None:
        print("❌ 截图失败")
        return
    
    screen, current_size = img_res
    screen_debug = screen.copy() # 用于画图
    current_w, current_h = current_size

    # 3. 加载模板
    if not os.path.exists(TEMPLATE_PATH):
        print(f"❌ 模板文件不存在: {TEMPLATE_PATH}")
        return
    
    template = cv2.imread(TEMPLATE_PATH, cv2.IMREAD_GRAYSCALE)
    if template is None:
        print("❌ 模板加载失败")
        return
    h_temp, w_temp = template.shape[:2]

    # === 分析 1: 现在的逻辑 (区域检测) ===
    print("\n--- 分析 1: 当前逻辑 (固定区域检测) ---")
    
    # 计算缩放和区域
    scale_x = current_w / STANDARD_WIDTH
    scale_y = current_h / STANDARD_HEIGHT
    
    detect_x = int(COLLECT_DETECT_STD_X * scale_x)
    detect_y = int(COLLECT_DETECT_STD_Y * scale_y)
    detect_w = int(COLLECT_DETECT_STD_W * scale_x)
    detect_h = int(COLLECT_DETECT_STD_H * scale_y)

    print(f"标准分辨率: {STANDARD_WIDTH}x{STANDARD_HEIGHT}")
    print(f"当前分辨率: {current_w}x{current_h} (缩放 x:{scale_x:.2f}, y:{scale_y:.2f})")
    print(f"检测区域: x={detect_x}, y={detect_y}, w={detect_w}, h={detect_h}")

    # 在图上画出检测区域 (蓝色框)
    cv2.rectangle(screen_debug, (detect_x, detect_y), (detect_x + detect_w, detect_y + detect_h), (255, 0, 0), 2)
    cv2.putText(screen_debug, "Detect Area", (detect_x, detect_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    # 裁剪并匹配
    try:
        screen_cropped = screen[detect_y:detect_y+detect_h, detect_x:detect_x+detect_w]
        gray_cropped = cv2.cvtColor(screen_cropped, cv2.COLOR_BGR2GRAY)
        
        # 缩放模板以适应当前分辨率 (这步是关键，capture.py 里有这个逻辑吗？)
        # 注意：你的 match_template 里有缩放逻辑，这里我们手动模拟一下最简单的匹配
        # 为了严谨，我们直接调用 opencv 原生匹配，不依赖 match_template 封装，以便看原始分数
        
        # 既然是缩放后的画面，模板也应该缩放
        # 使用 min(scale_x, scale_y) 作为缩放因子 (参考你的 match_template)
        final_scale = min(scale_x, scale_y)
        new_w_temp = int(w_temp * final_scale)
        new_h_temp = int(h_temp * final_scale)
        template_resized = cv2.resize(template, (new_w_temp, new_h_temp))
        
        res = cv2.matchTemplate(gray_cropped, template_resized, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        print(f"区域内最高匹配度: {max_val:.4f}")
        
        if max_val >= 0.8:
            print("✅ 区域检测成功！")
            # 画出匹配结果 (绿色实心点)
            top_left = (detect_x + max_loc[0], detect_y + max_loc[1])
            bottom_right = (top_left[0] + new_w_temp, top_left[1] + new_h_temp)
            cv2.rectangle(screen_debug, top_left, bottom_right, (0, 255, 0), 2)
            cv2.putText(screen_debug, f"Match: {max_val:.2f}", (top_left[0], top_left[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        else:
            print("❌ 区域检测失败 (分数过低)")

    except Exception as e:
        print(f"❌ 区域检测出错: {e}")

    # === 分析 2: 全屏搜索 (看看是不是在区域外) ===
    print("\n--- 分析 2: 全屏搜索 (排查区域问题) ---")
    gray_full = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
    
    # 同样缩放模板
    final_scale = min(scale_x, scale_y)
    new_w_temp = int(w_temp * final_scale)
    new_h_temp = int(h_temp * final_scale)
    template_resized = cv2.resize(template, (new_w_temp, new_h_temp))

    res_full = cv2.matchTemplate(gray_full, template_resized, cv2.TM_CCOEFF_NORMED)
    min_val_f, max_val_f, min_loc_f, max_loc_f = cv2.minMaxLoc(res_full)

    print(f"全屏最高匹配度: {max_val_f:.4f}")
    print(f"全屏最佳位置: {max_loc_f}")

    # 画出全屏最佳位置 (黄色虚线框)
    top_left_f = max_loc_f
    bottom_right_f = (top_left_f[0] + new_w_temp, top_left_f[1] + new_h_temp)
    cv2.rectangle(screen_debug, top_left_f, bottom_right_f, (0, 255, 255), 2)
    cv2.putText(screen_debug, f"Global: {max_val_f:.2f}", (top_left_f[0], bottom_right_f[1] + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    # === 结论 ===
    print("\n=== 诊断结果 ===")
    if max_val_f > max_val + 0.1: # 如果全屏比区域内高很多
        print("👉 问题原因：检测区域设置错误！图标在蓝色框外面（看生成的图片黄色框位置）。")
    elif max_val_f < 0.8:
        print("👉 问题原因：匹配度过低。可能是图标变了，或者模板截取不清晰。尝试降低阈值或重新截图。")
    elif max_val >= 0.8:
        print("👉 奇怪：测试显示应该能匹配到。可能是代码逻辑中的其他条件（如 is_running 标志）阻止了点击。")

    # 保存结果图
    output_path = "debug_analysis_result.png"
    cv2.imwrite(output_path, screen_debug)
    print(f"\n已保存分析图片至: {output_path}")
    print("请打开图片查看：蓝色框是设定的区域，黄色框是实际找到的最佳位置。")

if __name__ == "__main__":
    debug_collect_reward()