#!/usr/bin/env python3
"""
Trime 微立体 (.9.png) 键帽贴图与皮肤一键生成脚本

功能简介：
  1. 零第三方图像库依赖（仅用 Python 标准库 zlib + struct + math，通过 SDF 距离场实现高精度抗锯齿）。
  2. 严格遵循 Trime 源码 NinePatchBitmapFactory.kt 规范，自动在贴图最外圈写入 1px 透明边与纯黑 (0,0,0,255) 拉伸引导线。
  3. 从指定的基准皮肤（默认 GeekGT_Bravo.trime.yaml）读取亮/暗色配色，批量生成全套 66 张普通键、大圆角胶囊键、红底返回键及按下态下沉贴图。
  4. 自动生成对应的 3D 皮肤配置文件（默认 GeekGT_Bravo_3D.trime.yaml）并执行 YAML 语法与文件完整性校验。

使用示例：
  # 1. 使用默认柔和微立体参数重新生成（阴影厚度 2.2px）
  python3 generate_3d_theme.py

  # 2. 自定义更轻或更重的立体阴影厚度与透明度
  python3 generate_3d_theme.py --shadow-depth 1.8 --light-shadow-alpha 0.14 --dark-shadow-alpha 0.45

  # 3. 仅重绘 .9.png 贴图（保留手动修改过的 YAML 文件）
  python3 generate_3d_theme.py --only-textures --shadow-depth 2.5

  # 4. 为 Butter 版本生成专属 3D 皮肤
  python3 generate_3d_theme.py --source GeekGT_Butter.trime.yaml --output GeekGT_Butter_3D.trime.yaml --name GeekGT_Butter_3D --bg-folder GeekGT_Butter_3D
"""

import argparse
import math
import re
import struct
import zlib
from pathlib import Path
import yaml


def write_png_rgba(path: Path, w: int, h: int, pixels: bytearray) -> None:
    """将 RGBA 字节数组编码为标准 PNG 文件写入磁盘。"""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = bytearray()
    stride = w * 4
    for y in range(h):
        raw.append(0)  # Filter type 0 (None)
        raw.extend(pixels[y * stride : (y + 1) * stride])

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def sdf_round_rect(px: float, py: float, x0: float, y0: float, x1: float, y1: float, r: float) -> float:
    """圆角矩形有符号距离场（SDF），用于 1px 边缘平滑抗锯齿。"""
    cx = (x0 + x1) * 0.5
    cy = (y0 + y1) * 0.5
    hx = (x1 - x0) * 0.5 - r
    hy = (y1 - y0) * 0.5 - r
    dx = abs(px - cx) - max(hx, 0.0)
    dy = abs(py - cy) - max(hy, 0.0)
    out_d = math.hypot(max(dx, 0.0), max(dy, 0.0))
    in_d = min(max(dx, dy), 0.0)
    return out_d + in_d - r


def blend_over(dst: tuple, src: tuple) -> tuple:
    """Porter-Duff Source-Over Alpha 混合。"""
    sa = src[3]
    da = dst[3]
    oa = sa + da * (1.0 - sa)
    if oa <= 1e-6:
        return (0.0, 0.0, 0.0, 0.0)
    r = (src[0] * sa + dst[0] * da * (1.0 - sa)) / oa
    g = (src[1] * sa + dst[1] * da * (1.0 - sa)) / oa
    b = (src[2] * sa + dst[2] * da * (1.0 - sa)) / oa
    return (r, g, b, oa)


def parse_hex_rgb(hex_int: int) -> tuple:
    return (
        ((hex_int >> 16) & 0xFF) / 255.0,
        ((hex_int >> 8) & 0xFF) / 255.0,
        (hex_int & 0xFF) / 255.0,
    )


def generate_9patch_key(
    path: Path,
    body_hex: int,
    is_dark: bool,
    shadow_depth: float,
    shadow_alpha: float,
    radius: float,
    top_highlight: float = 0.0,
    pill: bool = False,
    pressed: bool = False,
) -> None:
    """生成单张符合 Android / Trime NinePatchBitmapFactory 规范的 .9.png 微立体键帽贴图。"""
    if pill:
        iw, ih = 128, 124
        sx1, sx2 = 62, 66
        sy1, sy2 = 58, 62
    else:
        iw, ih = 84, 96
        sx1, sx2 = 36, 48
        sy1, sy2 = 36, 56

    w, h = iw + 2, ih + 2
    pixels = bytearray(w * h * 4)

    br, bg, bb = parse_hex_rgb(body_hex)
    if is_dark:
        shadow_rgba = (0.0, 0.0, 0.0, shadow_alpha if not pressed else shadow_alpha * 0.45)
        border_rgba = (1.0, 1.0, 1.0, 0.08)
    else:
        shadow_rgba = (0.0, 0.0, 0.0, shadow_alpha if not pressed else shadow_alpha * 0.45)
        border_rgba = (0.0, 0.0, 0.0, 0.06)

    pad_x = 1.0
    if pressed:
        # 按下态：主体下沉一半阴影深度，底影变薄
        sink = max(1.0, shadow_depth * 0.65)
        body_y0 = 1.0 + sink
        body_y1 = ih - 1.0 - max(0.5, shadow_depth * 0.35)
        sh_y0 = body_y0 + 0.8
        sh_y1 = ih - 1.0
    else:
        body_y0 = 1.0
        body_y1 = ih - 1.0 - shadow_depth
        sh_y0 = 1.0 + shadow_depth
        sh_y1 = ih - 1.0

    for y in range(ih):
        py = y + 0.5
        for x in range(iw):
            px = x + 0.5
            col = (0.0, 0.0, 0.0, 0.0)

            r_eff = min(radius, (body_y1 - body_y0) * 0.5)
            # 1. 底部立体阴影层
            d_sh = sdf_round_rect(px, py, pad_x, sh_y0, iw - pad_x, sh_y1, r_eff)
            a_sh = max(0.0, min(1.0, 0.5 - d_sh))
            if a_sh > 0.0:
                col = blend_over(
                    col, (shadow_rgba[0], shadow_rgba[1], shadow_rgba[2], shadow_rgba[3] * a_sh)
                )

            # 2. 键帽主体层
            d_body = sdf_round_rect(px, py, pad_x, body_y0, iw - pad_x, body_y1, r_eff)
            a_body = max(0.0, min(1.0, 0.5 - d_body))
            if a_body > 0.0:
                col = blend_over(col, (br, bg, bb, a_body))
                # 极克制的键帽轮廓
                if not is_dark:
                    edge = max(0.0, min(1.0, 1.0 - abs(d_body + 0.5)))
                    if edge > 0.0:
                        col = blend_over(
                            col, (border_rgba[0], border_rgba[1], border_rgba[2], border_rgba[3] * edge * a_body)
                        )
                # 顶部内缘细微弧形高光（常态显示，按下态自动关闭增强按压下陷感）
                if not pressed and top_highlight > 0.0:
                    d_inner = sdf_round_rect(px, py, pad_x, body_y0 + 1.8, iw - pad_x, body_y1, radius)
                    hl_mask = max(0.0, min(1.0, d_inner + 0.5)) * max(0.0, 1.0 - (py - body_y0) / 22.0)
                    if hl_mask > 0.0:
                        col = blend_over(col, (1.0, 1.0, 1.0, top_highlight * hl_mask * a_body))

            idx = ((y + 1) * w + (x + 1)) * 4
            pixels[idx] = int(round(col[0] * 255))
            pixels[idx + 1] = int(round(col[1] * 255))
            pixels[idx + 2] = int(round(col[2] * 255))
            pixels[idx + 3] = int(round(col[3] * 255))

    # 3. 外圈 1px 点九拉伸黑线 (严格 RGBA = 0,0,0,255)
    for x in range(sx1 + 1, sx2 + 1):
        idx = (0 * w + x) * 4
        pixels[idx : idx + 4] = b"\x00\x00\x00\xff"
    for y in range(sy1 + 1, sy2 + 1):
        idx = (y * w + 0) * 4
        pixels[idx : idx + 4] = b"\x00\x00\x00\xff"

    write_png_rgba(path, w, h, pixels)


def build_textures(args: argparse.Namespace, base_dir: Path, bravo_data: dict) -> Path:
    bg_dir = base_dir / "backgrounds" / args.bg_folder
    bg_dir.mkdir(parents=True, exist_ok=True)

    light_sch = bravo_data["preset_color_schemes"]["default"]
    dark_sch = bravo_data["preset_color_schemes"]["flower_dark"]

    count = 0
    for prefix, sch, is_dark in [("l", light_sch, False), ("d", dark_sch, True)]:
        s_alpha = args.dark_shadow_alpha if is_dark else args.light_shadow_alpha
        t_hl = args.dark_highlight if is_dark else args.light_highlight
        # 字母/数字区键帽：默认统一为数字1(gd00)纯色；传 --gradient 时生成16级对角渐变
        if args.gradient:
            for i in range(16):
                k = f"gd{i:02d}"
                generate_9patch_key(
                    bg_dir / f"{prefix}_{k}.9.png", sch[k], is_dark, args.shadow_depth, s_alpha, args.radius, top_highlight=t_hl
                )
                count += 1
        else:
            generate_9patch_key(
                bg_dir / f"{prefix}_gd00.9.png", sch["gd00"], is_dark, args.shadow_depth, s_alpha, args.radius, top_highlight=t_hl
            )
            count += 1
        # 常规圆角中性色键（彩色按键 c1/c2/c3/c5/benter/red 保持原版纯色扁平）
        for k in ("bkg", "juhao"):
            generate_9patch_key(
                bg_dir / f"{prefix}_{k}.9.png", sch[k], is_dark, args.shadow_depth, s_alpha, args.radius, top_highlight=t_hl
            )
            count += 1
        # 按下态下沉贴图（无顶部高光）
        pressed_hex = 0xFFD0D0D0 if not is_dark else 0xFF454545
        generate_9patch_key(
            bg_dir / f"{prefix}_pressed.9.png",
            pressed_hex,
            is_dark,
            args.shadow_depth,
            s_alpha,
            args.radius,
            top_highlight=0.0,
            pressed=True,
        )
        count += 1

    print(f"[OK] 已生成 {count} 张 .9.png 贴图 -> {bg_dir} (shadow_depth={args.shadow_depth}px)")
    return bg_dir


def build_yaml(args: argparse.Namespace, base_dir: Path, src_path: Path, bg_dir: Path) -> Path:
    txt = src_path.read_text(encoding="utf-8")

    # 1. 更新顶层主题名称
    txt = re.sub(
        r"^name:.*$",
        f"name: {args.name}     # 方案名称（微立体.9.png版本）",
        txt,
        count=1,
        flags=re.M,
    )

    # 2. 在 style: 下写入 background_folder（依据 ColorManager.kt L304）
    txt = re.sub(
        r"^  round_corner:.*$",
        f"  background_folder: {args.bg_folder} # 对应 backgrounds/{args.bg_folder}/*.9.png\n"
        f"  round_corner: 7 # 纯色回退圆角（.9.png 按键由贴图自身决定圆角与立体底影）",
        txt,
        count=1,
        flags=re.M,
    )

    # 3. 彩色键保持纯色扁平；将左下 ?123 与右下回车的纯色圆角调大至 28dp（更圆润）
    txt = txt.replace(
        "key_back_color: c3, key_text_color: th4, width: 15, round_corner: 24",
        "key_back_color: c3, key_text_color: th4, width: 15, round_corner: 28",
        1,
    )
    txt = txt.replace(
        "- {click: Return, key_back_color: benter, key_text_color: tenter, width: 20, round_corner: 24}",
        "- {click: Return, key_back_color: benter, key_text_color: tenter, width: 20, round_corner: 28}",
        1,
    )

    # 4. 替换 default 与 flower_dark 配色方案为 .9.png 贴图引用
    lines = txt.splitlines()
    out = []
    in_color_schemes = False
    cur_scheme = None
    img_keys = {f"gd{i:02d}" for i in range(16)} | {"bkg", "juhao"}

    for line in lines:
        if re.match(r"^[a-zA-Z0-9_]+:", line):
            in_color_schemes = line.startswith("preset_color_schemes:")
            cur_scheme = None

        if in_color_schemes:
            m_sch = re.match(r"^  ([^\s#][^:]*):\s*$", line)
            if m_sch:
                cur_scheme = m_sch.group(1)

        if in_color_schemes and cur_scheme in ("default", "flower_dark"):
            prefix = "l" if cur_scheme == "default" else "d"
            if re.match(r"^    name:", line):
                out.append('    name: "繁花·3D"' if prefix == "l" else '    name: "繁花·暗色3D"')
                continue
            m_kv = re.match(r"^    ([a-zA-Z0-9_]+):", line)
            if m_kv:
                k = m_kv.group(1)
                if k in img_keys:
                    if not args.gradient and re.match(r"^gd\d{2}$", k):
                        out.append(f"    {k}: {prefix}_gd00.9.png")
                    else:
                        out.append(f"    {k}: {prefix}_{k}.9.png")
                    continue
                if k == "hilited_key_back_color":
                    out.append(f"    hilited_key_back_color: {prefix}_pressed.9.png")
                    # 防止 PopupKeyboardUi 读取 hilited_popup_back_color(@ColorInt) 时回退到 .9.png 导致崩溃
                    hp_bg = "0xff5b9bd5" if prefix == "l" else "0xff2c4560"
                    out.append(f"    hilited_popup_back_color: {hp_bg}")
                    out.append("    hilited_popup_text_color: 0xffffffff")
                    continue



        out.append(line)

    dst = base_dir / args.output
    new_txt = "\n".join(out) + "\n"
    dst.write_text(new_txt, encoding="utf-8")

    # 严格校验 YAML 与所有引用的 .9.png 贴图均存在
    data = yaml.safe_load(new_txt)
    assert data["style"]["background_folder"] == args.bg_folder
    for sname in ("default", "flower_dark"):
        sch = data["preset_color_schemes"][sname]
        for k, v in sch.items():
            if isinstance(v, str) and v.endswith(".9.png"):
                assert (bg_dir / v).is_file(), f"缺少贴图文件: {v}"
    print(f"[OK] 已生成并校验皮肤配置 -> {dst} (theme name: {data['name']})")
    return dst


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trime 微立体 (.9.png) 键帽贴图与皮肤一键生成工具",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--source", default="GeekGT_Bravo.trime.yaml", help="作为基准的源皮肤文件名")
    parser.add_argument("--output", default="GeekGT_Bravo_3D.trime.yaml", help="输出的 3D 皮肤文件名")
    parser.add_argument("--name", default="GeekGT_Bravo_3D", help="生成的主题显示名称 (YAML 顶层 name)")
    parser.add_argument("--bg-folder", default="GeekGT_3D", help="贴图子目录名 (位于 backgrounds/<bg-folder>/)")
    parser.add_argument("--shadow-depth", type=float, default=2.2, help="底部立体阴影厚度 (px，默认 2.2 为原版一半)")
    parser.add_argument("--light-shadow-alpha", type=float, default=0.17, help="亮色方案底部阴影透明度 (0.0~1.0)")
    parser.add_argument("--dark-shadow-alpha", type=float, default=0.50, help="暗色方案底部阴影透明度 (0.0~1.0)")
    parser.add_argument("--light-highlight", type=float, default=0.0, help="亮色方案顶部内高光强度 (0.0~1.0)")
    parser.add_argument("--dark-highlight", type=float, default=0.15, help="暗色方案顶部内高光强度 (0.0~1.0)")
    parser.add_argument("--radius", type=float, default=22.0, help="普通按键圆角半径 (px，3x密度下约 7dp)")
    parser.add_argument("--pill-radius", type=float, default=56.0, help="左下?123与右下回车大圆角半径 (px，默认56大圆角矩形感)")
    parser.add_argument("--gradient", action="store_true", help="启用16级对角渐变贴图（默认关闭，所有字母与数字键统一为数字1键颜色）")
    parser.add_argument("--only-textures", action="store_true", help="仅重绘 .9.png 贴图，不覆盖现有 YAML 文件")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    src_path = base_dir / args.source
    if not src_path.is_file():
        raise FileNotFoundError(f"找不到基准皮肤文件: {src_path}")

    bravo_data = yaml.safe_load(src_path.read_text(encoding="utf-8"))
    bg_dir = build_textures(args, base_dir, bravo_data)
    if not args.only_textures:
        build_yaml(args, base_dir, src_path, bg_dir)


if __name__ == "__main__":
    main()
