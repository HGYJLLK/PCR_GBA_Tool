"""
交互式角色头像提取工具

流程:
  1. 标定阶段：依次框选 3 个头像（R1C1、R1C2、R2C1），系统推算完整网格
  2. 调整阶段：绿框已就位，按 ↑↓ 上下微调直到完全对齐，Enter 确认
  3. 命名阶段：逐个显示头像，终端输入角色名保存

调整阶段键位:
  ↑ / ↓       上下移动 1px
  w / s       上下移动 5px
  c           重新标定
  Enter       确认
  q / ESC     退出

用法:
  python dev_tools/extract_avatars.py --input logs/ui/screenshot_xxx.png
  python dev_tools/extract_avatars.py --input logs/ui/screenshot_xxx.png --cols 8 --rows 2
"""

import os
import sys
import argparse

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "."))

WIN_NAME   = "PCR Avatar Extractor"
KEY_UP     = 2490368
KEY_DOWN   = 2621440
KEY_ENTER  = 13
KEY_ESC    = 27

DEFAULT_COLS = 8
DEFAULT_ROWS = 2
OUTPUT_DIR   = "./assets/character"


def make_square(r: tuple) -> tuple:
    """将矩形自动修正为正方形（取宽高均值为边长，保持中心不变）"""
    x1, y1, x2, y2 = r
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    side = round(((x2 - x1) + (y2 - y1)) / 2)
    h = side // 2
    return (round(cx) - h, round(cy) - h, round(cx) - h + side, round(cy) - h + side)


# ===========================================================================
# 鼠标框选
# ===========================================================================

class RoiSelector:
    def __init__(self):
        self.p0 = self.p1 = None
        self.drawing = self.done = False

    def callback(self, evt, x, y, flags, param):
        if evt == cv2.EVENT_LBUTTONDOWN:
            self.p0 = self.p1 = (x, y)
            self.drawing, self.done = True, False
        elif evt == cv2.EVENT_MOUSEMOVE and self.drawing:
            self.p1 = (x, y)
        elif evt == cv2.EVENT_LBUTTONUP:
            self.p1, self.drawing, self.done = (x, y), False, True

    def current_rect(self):
        """拖动中的矩形（实时预览用）"""
        if not self.p0 or not self.p1:
            return None
        return (min(self.p0[0], self.p1[0]), min(self.p0[1], self.p1[1]),
                max(self.p0[0], self.p1[0]), max(self.p0[1], self.p1[1]))

    def confirmed_rect(self):
        """松开鼠标后的最终矩形，宽高需 > 5"""
        r = self.current_rect()
        if r and r[2]-r[0] > 5 and r[3]-r[1] > 5:
            return r
        return None


# ===========================================================================
# 绘制工具
# ===========================================================================

# 3 个标定格子的颜色
CAL_COLORS = [(0, 200, 255), (50, 255, 50), (255, 150, 0)]


def status_strip(vis: np.ndarray, left: str, right: str = "") -> np.ndarray:
    """在图像下方追加一条 24px 状态条（不覆盖图像内容）"""
    bar = np.zeros((24, vis.shape[1], 3), dtype=np.uint8)
    cv2.putText(bar, left,  (6, 17), cv2.FONT_HERSHEY_SIMPLEX,
                0.46, (100, 220, 255), 1, cv2.LINE_AA)
    if right:
        tw = cv2.getTextSize(right, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)[0][0]
        cv2.putText(bar, right, (vis.shape[1]-tw-6, 17),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (150, 150, 150), 1, cv2.LINE_AA)
    return np.vstack([vis, bar])


def draw_cal_rects(vis: np.ndarray, rects: list) -> np.ndarray:
    """绘制已完成的标定框（带标签）"""
    labels = ["R1C1", "R1C2", "R2C1"]
    for i, r in enumerate(rects):
        c = CAL_COLORS[i]
        cv2.rectangle(vis, (r[0], r[1]), (r[2], r[3]), c, 2)
        cv2.putText(vis, labels[i], (r[0]+2, r[1]+14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, c, 1, cv2.LINE_AA)
    return vis


def draw_grid(vis: np.ndarray, col_xs: list, av_w: int, av_h: int,
              grid_y: int, cell_h: int, rows: int, highlight: int = -1) -> np.ndarray:
    """绘制所有绿色头像框"""
    cols = len(col_xs)
    for row in range(rows):
        for ci, cx in enumerate(col_xs):
            idx = row * cols + ci
            x1, y1 = cx, grid_y + row * cell_h
            x2, y2 = x1 + av_w, y1 + av_h
            color = (0, 0, 220) if idx == highlight else (0, 220, 50)
            thick = 3          if idx == highlight else 2
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, thick)
            cv2.putText(vis, str(idx+1), (x1+3, y1+14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                        (80, 80, 255) if idx == highlight else (0, 255, 180),
                        1, cv2.LINE_AA)
    return vis


# ===========================================================================
# 阶段一：标定（框选 3 个格子）
# ===========================================================================

def select_one_roi(image: np.ndarray, instruction: str,
                   done_rects: list) -> tuple:
    """
    让用户框选一个矩形，松手后自动修正为正方形并预览。
    用户按 Enter 接受修正后的正方形，或重新拖拽。
    Returns (x1,y1,x2,y2) 正方形 或 None（退出）。
    """
    sel = RoiSelector()
    cv2.namedWindow(WIN_NAME, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(WIN_NAME, sel.callback)

    while True:
        vis = image.copy()
        if done_rects:
            vis = draw_cal_rects(vis, done_rects)

        cr = sel.current_rect()
        if cr:
            if sel.done:
                # 松手后：显示修正后的正方形（青色）
                sq = make_square(cr)
                cv2.rectangle(vis, (sq[0], sq[1]), (sq[2], sq[3]), (255, 220, 0), 2)
                # 同时淡显原始选框（灰色虚线效果用细线代替）
                cv2.rectangle(vis, (cr[0], cr[1]), (cr[2], cr[3]), (120, 120, 120), 1)
                side = sq[2] - sq[0]
                cv2.putText(vis, f"{side}x{side}", (sq[0]+2, sq[1]-4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 220, 0), 1, cv2.LINE_AA)
                vis = status_strip(vis, instruction,
                                   "Enter=接受正方形  重新拖拽=重选  q=退出")
            else:
                # 拖动中：显示原始框（橙色）+ 实时尺寸
                cv2.rectangle(vis, (cr[0], cr[1]), (cr[2], cr[3]), (0, 165, 255), 2)
                w, h = cr[2]-cr[0], cr[3]-cr[1]
                cv2.putText(vis, f"{w}x{h}", (cr[0]+2, cr[1]-4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 165, 255), 1, cv2.LINE_AA)
                vis = status_strip(vis, instruction, "拖拽中...  q=退出")
        else:
            vis = status_strip(vis, instruction, "拖拽框选头像区域  q=退出")

        cv2.imshow(WIN_NAME, vis)

        key = cv2.waitKey(20)
        if key in (ord('q'), KEY_ESC):
            return None
        if key == KEY_ENTER and sel.done:
            r = sel.confirmed_rect()
            if r:
                return make_square(r)
            print("  框选区域太小，请重试")


def phase_calibrate(image: np.ndarray, cols: int):
    """
    用户依次框选 3 个头像（已自动修正为正方形），推算网格参数：
      步骤1：第1行 第1列       → 确定锚点 X/Y
      步骤2：第1行 最后一列    → 跨整行计算精确列间距（消除累积偏移）
      步骤3：第2行 第1列       → 计算行间距

    Returns (col_xs, cell_h, av_side, initial_y) 或 None（退出）。
    """
    steps = [
        f"标定 1/3：框选 第1行 第1列 的头像",
        f"标定 2/3：框选 第1行 第{cols}列（最后一列）的头像  ← 跨行测量，精度高",
        f"标定 3/3：框选 第2行 第1列 的头像",
    ]
    labels = ["R1C1", f"R1C{cols}", "R2C1"]
    rects  = []

    for i, step in enumerate(steps):
        r = select_one_roi(image, step, rects)
        if r is None:
            return None
        rects.append(r)
        side = r[2] - r[0]
        print(f"  {labels[i]}: {r}  (边长={side}px)")

    r00, r0N, r01 = rects   # r0N = 第1行最后一列

    # ---------- 推算 ----------
    # cell_w：总跨度 ÷ (cols-1)，误差被 (cols-1) 均摊
    total_col_span = r0N[0] - r00[0]
    cell_w = total_col_span / (cols - 1)

    # cell_h：第1列两行上边缘之差
    cell_h = round(r01[1] - r00[1])

    # 头像边长：3 个正方形的均值
    av_side = round(sum(r[2]-r[0] for r in rects) / 3)

    # col 0 锚点 X：R1C1 和 R2C1 左边缘均值
    anchor_x = round((r00[0] + r01[0]) / 2)

    # col_xs：等间距，浮点计算后取整（避免整数截断造成的小误差）
    col_xs = [round(anchor_x + c * cell_w) for c in range(cols)]

    # 初始 Y：R1C1 和 R1C_LAST 上边缘均值
    initial_y = round((r00[1] + r0N[1]) / 2)

    print(f"\n  cell_w={cell_w:.2f}  cell_h={cell_h}  av_side={av_side}")
    print(f"  anchor_x={anchor_x}  initial_y={initial_y}")
    print(f"  col_xs={col_xs}")

    return col_xs, cell_h, av_side, av_side, initial_y


# ===========================================================================
# 阶段二：垂直微调
# ===========================================================================

def phase_adjust_y(image: np.ndarray, col_xs: list, av_w: int, av_h: int,
                   cell_h: int, rows: int, initial_y: int):
    """
    显示绿框，用户按 ↑↓ 上下移动直到对齐，Enter 确认。
    Returns (final_y, action)  action: 'confirm' | 'recalibrate' | 'quit'
    """
    grid_y = initial_y
    cv2.namedWindow(WIN_NAME, cv2.WINDOW_AUTOSIZE)

    while True:
        vis = draw_grid(image.copy(), col_xs, av_w, av_h, grid_y, cell_h, rows)
        vis = status_strip(
            vis,
            f"Y={grid_y}  ↑↓=±1px  w/s=±5px",
            "Enter=确认  c=重新标定  q=退出"
        )
        cv2.imshow(WIN_NAME, vis)
        key = cv2.waitKey(0)

        if key in (ord('q'), KEY_ESC):
            return grid_y, 'quit'
        if key == KEY_ENTER:
            return grid_y, 'confirm'
        if key == ord('c'):
            return grid_y, 'recalibrate'

        if   key == KEY_UP:     grid_y -= 1
        elif key == KEY_DOWN:   grid_y += 1
        elif key == ord('w'):   grid_y -= 5
        elif key == ord('s'):   grid_y += 5


# ===========================================================================
# 阶段三：命名保存
# ===========================================================================

def phase_name_and_save(image: np.ndarray, col_xs: list, av_w: int, av_h: int,
                         grid_y: int, cell_h: int, rows: int, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    img_h, img_w = image.shape[:2]
    cols  = len(col_xs)
    total = cols * rows
    saved = {}

    print(f"\n共 {total} 个格子，开始逐个命名")
    print("  输入名称 → TEMPLATE_<名称>.png  |  Enter=跳过  |  q=结束\n")

    cv2.namedWindow(WIN_NAME, cv2.WINDOW_AUTOSIZE)

    for row in range(rows):
        for ci, cx in enumerate(col_xs):
            idx = row * cols + ci
            x1 = max(0, cx)
            y1 = max(0, grid_y + row * cell_h)
            x2 = min(img_w, cx + av_w)
            y2 = min(img_h, y1 + av_h)
            if x2 <= x1 or y2 <= y1:
                print(f"  [{idx+1}] 超出图像边界，跳过")
                continue

            avatar = image[y1:y2, x1:x2].copy()

            # 显示：当前格高亮红框 + 右上角放大预览
            vis = draw_grid(image.copy(), col_xs, av_w, av_h, grid_y, cell_h, rows, highlight=idx)
            av3 = cv2.resize(avatar, (avatar.shape[1]*3, avatar.shape[0]*3),
                             interpolation=cv2.INTER_LINEAR)
            ah, aw_ = av3.shape[:2]
            px, py = img_w - aw_ - 6, 6
            if px >= 0 and py + ah <= vis.shape[0]:
                vis[py:py+ah, px:px+aw_] = av3
                cv2.rectangle(vis, (px, py), (px+aw_, py+ah), (0, 0, 220), 2)
            vis = status_strip(vis, f"[{idx+1}/{total}] 在终端输入角色名",
                               "Enter=跳过  q=结束")
            cv2.imshow(WIN_NAME, vis)
            cv2.waitKey(1)

            # 终端命名
            while True:
                name = input(f"  [{idx+1:2d}/{total}] 角色名（Enter=跳过，q=结束）: ").strip()

                if name.lower() == 'q':
                    cv2.destroyAllWindows()
                    _summary(saved, output_dir)
                    return

                if name == '':
                    print("    跳过")
                    break

                if any(c in name for c in r'\/:*?"<>|'):
                    print("    名称含非法字符，请重新输入")
                    continue

                out_name = f"TEMPLATE_{name.upper()}.png"
                out_path = os.path.join(output_dir, out_name)
                if os.path.exists(out_path):
                    if input(f"    {out_name} 已存在，覆盖？(y/N): ").strip().lower() != 'y':
                        continue

                cv2.imencode(".png", avatar)[1].tofile(out_path)
                saved[idx] = name.upper()
                print(f"    已保存 → {out_path}")
                break

    cv2.destroyAllWindows()
    _summary(saved, output_dir)


def _summary(saved: dict, output_dir: str):
    print(f"\n完成！共保存 {len(saved)} 个头像到 {output_dir}/")
    for idx, name in sorted(saved.items()):
        print(f"  #{idx+1:2d}: TEMPLATE_{name}.png")


# ===========================================================================
# 主流程
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(description="交互式角色头像提取")
    parser.add_argument("--input",  "-i", required=True, help="输入截图路径（1280×720）")
    parser.add_argument("--output", "-o", default=OUTPUT_DIR,
                        help=f"输出目录（默认: {OUTPUT_DIR}）")
    parser.add_argument("--cols", type=int, default=DEFAULT_COLS,
                        help=f"列数（默认: {DEFAULT_COLS}）")
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS,
                        help=f"行数（默认: {DEFAULT_ROWS}）")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"错误：找不到文件 {args.input}")
        sys.exit(1)

    image = cv2.imdecode(np.fromfile(args.input, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        print(f"无法读取图片: {args.input}")
        sys.exit(1)

    while True:
        # ---- 标定 ----
        cal = phase_calibrate(image, args.cols)
        if cal is None:
            print("已退出。")
            cv2.destroyAllWindows()
            return
        col_xs, cell_h, av_w, av_h, initial_y = cal

        # ---- 垂直微调 ----
        while True:
            final_y, action = phase_adjust_y(
                image, col_xs, av_w, av_h, cell_h, args.rows, initial_y)

            if action == 'quit':
                print("已退出。")
                cv2.destroyAllWindows()
                return

            if action == 'recalibrate':
                break   # 跳出内层，重新标定

            # confirm
            cv2.destroyAllWindows()
            phase_name_and_save(
                image, col_xs, av_w, av_h, final_y, cell_h, args.rows, args.output)
            return

        # recalibrate → 继续外层循环


if __name__ == "__main__":
    main()
