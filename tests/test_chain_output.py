"""MiauRedstoneMusic 输出数据自检脚本。

不依赖 pytest，直接 `python tests/test_chain_output.py` 运行。

覆盖内容：
1. 歌词命令方块链的结构与红石计时（四个方向、跟随/固定模式、均匀/合并中继器）。
2. 命令方块链的纵向位置：默认应位于「整个结构最低方块」下方，且与音乐链不重叠。
3. 启动点（红石块）与起手中继器的相对位置。
4. /mpe text 显示坐标是结构上方的绝对锚点，与命令方块链高度无关。
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from miaunoteblock.constants import DIR_OFFSET, SIDE_AXIS
from miaunoteblock.layout import compute_offsets
from miaunoteblock.generation import (
    build_all_commands_virtual,
    find_structure_bottom,
    split_to_repeaters,
)
from miaunoteblock.lyrics import build_lyrics_commands, build_lyrics_track


# ── 测试用对象 ────────────────────────────────────────────────

class FakeNote:
    def __init__(self, tick, layer=0, key=45, instrument=0):
        self.tick = tick
        self.layer = layer
        self.key = key
        self.instrument = instrument

    @property
    def pitch(self):
        return self.key


def make_layers():
    """两个音乐组 + 一个歌词轨道（歌词轨道并入组 0）。"""
    layer0 = [FakeNote(t, layer=0) for t in (0, 5, 10, 20, 30)]
    layer1 = [FakeNote(t, layer=1, key=50) for t in (0, 3, 30)]
    layer2 = [FakeNote(t, layer=2, key=60) for t in (0, 5, 10, 20, 30)]  # 歌词轨道
    virtual_layers = [
        {"vid": 0, "original_id": 0, "side": None, "notes": layer0, "inst": 0, "cat": "钢琴"},
        {"vid": 1, "original_id": 1, "side": None, "notes": layer1, "inst": 0, "cat": "钢琴"},
        {"vid": 2, "original_id": 2, "side": None, "notes": layer2, "inst": 0, "cat": "钢琴"},
    ]
    layer_to_group = {0: 0, 1: 1, 2: 0}
    return virtual_layers, layer_to_group


def base_config():
    return {
        "layout_style": "flat",
        "flat_spacing": 3,
        "master_group": None,
        "lyrics_color": "white",
        "lyrics_scale": 1.0,
        "lyrics_duration": 20,
        "lyrics_enter": 5,
        "lyrics_exit": 5,
        "lyrics_y_offset": 5,
        "lyrics_side_offset": 0,
        "lyrics_follow": True,
        "lyrics_chain_y_offset": 1,
    }


# ── 解析与模拟工具 ────────────────────────────────────────────

SETBLOCK_RE = re.compile(r"^setblock\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(.+)$")
DELAY_RE = re.compile(r"delay=(\d+)")
CMD_RE = re.compile(r"\{Command:(.*)\}$")
MPE_RE = re.compile(r'/mpe text "((?:[^"\\]|\\.)*)"\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(.*)$')


def parse_setblocks(cmds):
    """{ (x,y,z): block } —— 只解析 setblock，后写覆盖先写。"""
    blocks = {}
    for cmd in cmds:
        m = SETBLOCK_RE.match(cmd.strip())
        if m:
            key = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            blocks[key] = m.group(4)
    return blocks


def axis_key(direction):
    return "x" if direction in ("east", "west") else "z"


def axis_coord(coord, key):
    return coord[0] if key == "x" else coord[2]


def simulate_layer(blocks, layer_y, key, step):
    """沿链轴模拟红石传播，返回 (各位置受电时间, 错误信息)。

    模型：起手中继器由红石块输入供电（t=0），中继器每经过一个 +delay，
    普通方块（命令方块/羊毛）记录当前时间并即时把强充能传给下一个中继器。
    相邻方块在链轴上必须相差 1 格，否则视为断链。
    """
    items = [c for c in blocks.items() if c[0][1] == layer_y]
    items.sort(key=lambda it: axis_coord(it[0], key), reverse=(step < 0))
    power = 0
    times = {}
    prev = None
    for coord, block in items:
        c = axis_coord(coord, key)
        if prev is not None and abs(c - prev) != 1:
            return None, f"断链：链轴坐标 {prev} -> {c}（间隔 {abs(c - prev)}）"
        if "repeater" in block:
            m = DELAY_RE.search(block)
            power += int(m.group(1)) if m else 1
        else:
            times[c] = power
        prev = c
    return times, None


def expected_event_offsets(valid_ticks, uniform):
    """按实际布局推算每个事件格相对 base 的链轴偏移（格）。"""
    offsets = []
    cursor = 0
    prev = None
    for tick in valid_ticks:
        if prev is not None:
            blank = max(0, tick - prev - 1)
            delays = [1] * blank if uniform else split_to_repeaters(blank)
            cursor += 2 + 2 * len(delays)
        offsets.append((tick, cursor))
        prev = tick
    return offsets


def extract_mpe(block):
    """从命令方块 block 串中提取 /mpe 命令并解析出 (text, x, y, z, options)。"""
    m = CMD_RE.search(block)
    if not m:
        return None
    cmd = json.loads(m.group(1))
    mm = MPE_RE.match(cmd)
    if not mm:
        return None
    text = json.loads('"' + mm.group(1) + '"')
    return text, int(mm.group(2)), int(mm.group(3)), int(mm.group(4)), mm.group(5)


# ── 断言容器 ──────────────────────────────────────────────────

class Checks:
    def __init__(self):
        self.passed = 0
        self.failed = []

    def ok(self, cond, msg):
        if cond:
            self.passed += 1
        else:
            self.failed.append(msg)

    def report(self, name):
        status = "OK" if not self.failed else "FAIL"
        print(f"  [{name}] {status}  通过断言 {self.passed} 条")
        for f in self.failed:
            print(f"      ✗ {f}")
        return not self.failed


# ── 测试 1：歌词链计时（四方向）───────────────────────────────

def test_lyrics_timing_all_directions():
    print("测试 1：歌词链结构与计时（四个方向，跟随模式）")
    virtual_layers, layer_to_group = make_layers()
    lyrics_notes = sorted(
        [n for vl in virtual_layers for n in vl["notes"] if n.layer == 2],
        key=lambda n: n.tick,
    )
    mapping = [(t, f"L{t}", 0) for t in (0, 5, 10, 20, 30)]
    max_tick, origin = 30, 0
    valid_ticks = sorted({n.tick for n in lyrics_notes} | {origin, max_tick})

    all_ok = True
    for direction in ("east", "west", "south", "north"):
        chk = Checks()
        dx, _, dz = DIR_OFFSET[direction]
        key = axis_key(direction)
        step = dx if key == "x" else dz
        side_axis = SIDE_AXIS[direction]
        base = (100, 64, 200)
        chain_y = 40  # 人为放在结构下方
        config = base_config()
        anchor_side = base[2] + 0 if side_axis == "z" else base[0] + 0
        anchor_y = base[1] + 5

        cmds = build_lyrics_commands(
            lyrics_notes, mapping, base, direction, max_tick, config,
            anchor_side=anchor_side, anchor_chain=None, anchor_y=anchor_y,
            origin_tick=origin, fixed_tick=None, chain_y=chain_y,
        )
        blocks = parse_setblocks(cmds)

        # 1a. 链层所有方块都在 chain_y
        chain_blocks = {c: b for c, b in blocks.items() if c[1] == chain_y}
        chk.ok(len(chain_blocks) > 0, "链层没有方块")
        chk.ok(all(c[1] == chain_y for c in chain_blocks), "存在非 chain_y 的链层方块")

        # 1b. 无断链
        times, err = simulate_layer(blocks, chain_y, key, step)
        chk.ok(err is None, err or "")

        # 1c. 事件格偏移正确
        offsets = expected_event_offsets(valid_ticks, uniform=False)
        base_axis = axis_coord(base, key)
        for tick, off in offsets:
            coord = base_axis + off * step
            chk.ok(coord in times, f"tick {tick} 事件格缺失 (coord={coord})")

        # 1d. 受电时间 = 1 + (tick - origin)
        if times is not None:
            for tick, off in offsets:
                coord = base_axis + off * step
                want = 1 + (tick - origin)
                chk.ok(times.get(coord) == want,
                       f"tick {tick} 受电时间 {times.get(coord)} != {want}")

        # 1e. mpe 显示坐标 = 绝对锚点（与 chain_y 无关）
        mpe_blocks = [b for c, b in blocks.items() if "command_block" in b]
        chk.ok(len(mpe_blocks) == len(mapping), f"命令方块数 {len(mpe_blocks)} != {len(mapping)}")
        for b in mpe_blocks:
            parsed = extract_mpe(b)
            chk.ok(parsed is not None, "无法解析 /mpe 命令")
            if parsed:
                _, mx, my, mz, _ = parsed
                chk.ok(my == anchor_y, f"显示 y {my} != 锚点 {anchor_y}")
                if side_axis == "z":
                    chk.ok(mz == anchor_side, f"显示 z {mz} != 锚点 {anchor_side}")
                else:
                    chk.ok(mx == anchor_side, f"显示 x {mx} != 锚点 {anchor_side}")

        all_ok &= chk.report(direction)
    return all_ok


# ── 测试 2：固定位置模式 ──────────────────────────────────────

def test_fixed_position():
    print("测试 2：固定位置模式（文字不跟随）")
    chk = Checks()
    virtual_layers, _ = make_layers()
    lyrics_notes = sorted(
        [n for vl in virtual_layers for n in vl["notes"] if n.layer == 2],
        key=lambda n: n.tick,
    )
    mapping = [(t, f"L{t}", 0) for t in (0, 5, 10, 20, 30)]
    direction, key = "east", "x"
    base = (100, 64, 200)
    chain_y = 40
    config = base_config()
    origin, max_tick = 0, 30
    fixed_tick = 15  # 期望落在 tick 10 与 20 之间，取更近者

    cmds = build_lyrics_commands(
        lyrics_notes, mapping, base, direction, max_tick, config,
        anchor_side=base[2], anchor_chain=None, anchor_y=base[1] + 5,
        origin_tick=origin, fixed_tick=fixed_tick, chain_y=chain_y,
    )
    blocks = parse_setblocks(cmds)
    mpe = [extract_mpe(b) for c, b in blocks.items() if "command_block" in b]
    mpe = [p for p in mpe if p]
    chk.ok(len(mpe) == len(mapping), f"命令方块数 {len(mpe)} != {len(mapping)}")
    chain_coords = {p[1] for p in mpe}  # east 方向链轴为 x
    chk.ok(len(chain_coords) == 1, f"固定模式下链轴坐标不唯一: {sorted(chain_coords)}")

    # 校验固定坐标确实是离 fixed_tick 最近的事件格
    valid_ticks = sorted({n.tick for n in lyrics_notes} | {origin, max_tick})
    offsets = expected_event_offsets(valid_ticks, uniform=False)
    best_tick, best_off = min(offsets, key=lambda it: abs(it[0] - fixed_tick))
    want_x = base[0] + best_off
    chk.ok(chain_coords == {want_x},
           f"固定坐标 {sorted(chain_coords)} != 期望 {want_x} (tick {best_tick})")
    return chk.report("fixed")


# ── 测试 3：命令方块链相对结构底部 ────────────────────────────

def test_chain_below_structure():
    print("测试 3：命令方块链位于整个结构底部下方（相对位置）")
    chk = Checks()
    virtual_layers, layer_to_group = make_layers()
    config = base_config()
    config["lyrics_track"] = 2
    config["lyrics_import"] = {str(t): {"text": f"L{t}", "duration": 0}
                               for t in (0, 5, 10, 20, 30)}
    start = (0, 64, 0)
    max_tick = 30
    direction = "east"

    groups = sorted(set(layer_to_group.values()))
    offsets = compute_offsets(groups, config, len(groups))
    group_offset_dict = {gid: offsets[i] for i, gid in enumerate(groups)}

    music_cmds, activation_positions = build_all_commands_virtual(
        virtual_layers, layer_to_group, [group_offset_dict[g] for g in groups],
        start, direction, max_tick, use_lamp=False, uniform_repeater_mode=False,
        group_staircase_modes={},
    )
    struct_bottom = find_structure_bottom(music_cmds)

    lyr_cmds, lyr_activation, chain_y = build_lyrics_track(
        [n for vl in virtual_layers for n in vl["notes"]],
        virtual_layers, layer_to_group, group_offset_dict,
        start, direction, max_tick, config,
        use_lamp=False, uniform_repeater_mode=False, struct_bottom_y=struct_bottom,
    )

    chk.ok(lyr_cmds, "歌词链未生成")
    chk.ok(lyr_activation is not None, "歌词链启动点缺失")
    chk.ok(chain_y == struct_bottom - config["lyrics_chain_y_offset"],
           f"chain_y {chain_y} != struct_bottom {struct_bottom} - offset")

    blocks = parse_setblocks(lyr_cmds)
    chk.ok(all(c[1] <= struct_bottom - 1 for c in blocks),
           "歌词链存在高于结构底部的方块")

    # 与音乐链不重叠（同一坐标不会被两条链写两次）
    music_blocks = parse_setblocks(music_cmds)
    overlap = set(blocks) & set(music_blocks)
    chk.ok(not overlap, f"歌词链与音乐链坐标重叠: {sorted(overlap)[:5]}")

    # 启动点 y == chain_y 且正好在起手中继器后方 1 格（与音乐链一致：input = relay - step）
    ax, ay, az = lyr_activation
    chk.ok(ay == chain_y, f"启动点 y {ay} != chain_y {chain_y}")
    dx, _, dz = DIR_OFFSET[direction]
    start_relay = (ax + dx, chain_y, az + dz)
    chk.ok("repeater" in blocks.get(start_relay, ""),
           f"启动点后方 1 格不是起手中继器: {blocks.get(start_relay)}")
    # 启动点在起手中继器之前，不应落在任何方块上
    chk.ok("repeater" not in blocks.get((ax, chain_y, az), ""), "启动点被占用")

    # 启动点与音乐组启动点总数一致（每组一个 + 歌词一个）
    all_activations = list(activation_positions.values())
    all_activations.append(lyr_activation)
    chk.ok(len(all_activations) == len(groups) + 1,
           f"启动点数量 {len(all_activations)} != 组数+1 {len(groups) + 1}")
    chk.ok(len(set(all_activations)) == len(all_activations), "启动点存在重复")

    # 计时与音乐链一致：歌词链事件受电时间 == 1 + (tick - origin)
    times, err = simulate_layer(blocks, chain_y, "x", dx)
    chk.ok(err is None, err or "")
    if times is not None:
        for tick in (0, 5, 10, 20, 30):
            off = dict(expected_event_offsets(sorted({0, 5, 10, 20, 30}), False))[tick]
            chk.ok(times.get(start[0] + off) == 1 + tick,
                   f"tick {tick} 受电时间错误")
    return chk.report("relative")


# ── 测试 4：圆形排版 —— 链仍在最底部，文字在主轨道上方 ────────

def test_circle_layout():
    print("测试 4：圆形排版下的相对位置")
    chk = Checks()
    virtual_layers, layer_to_group = make_layers()
    config = base_config()
    config.update({"layout_style": "circle", "layout_radius": 6,
                   "lyrics_track": 2, "lyrics_follow": False})
    config["lyrics_import"] = {str(t): {"text": f"L{t}", "duration": 0}
                               for t in (0, 5, 10, 20, 30)}
    start = (0, 64, 0)
    max_tick = 30
    groups = sorted(set(layer_to_group.values()))
    offsets = compute_offsets(groups, config, len(groups))
    group_offset_dict = {gid: offsets[i] for i, gid in enumerate(groups)}

    music_cmds, _ = build_all_commands_virtual(
        virtual_layers, layer_to_group, [group_offset_dict[g] for g in groups],
        start, "east", max_tick, False, False, {},
    )
    struct_bottom = find_structure_bottom(music_cmds)

    lyr_cmds, _, chain_y = build_lyrics_track(
        [n for vl in virtual_layers for n in vl["notes"]],
        virtual_layers, layer_to_group, group_offset_dict,
        start, "east", max_tick, config, struct_bottom_y=struct_bottom,
    )
    chk.ok(lyr_cmds, "歌词链未生成")
    chk.ok(chain_y < struct_bottom, "歌词链没有位于结构下方")

    blocks = parse_setblocks(lyr_cmds)
    mpe = [extract_mpe(b) for b in blocks.values() if "command_block" in b]
    mpe = [p for p in mpe if p]
    chk.ok(mpe, "没有命令方块")
    # 圆形排版：主轨道偏移 (0,0) 或 master；文字 y 应为 start_y + offset + lyrics_y_offset
    ys = {p[2] for p in mpe}
    chk.ok(all(y >= start[1] for y in ys), f"文字 y 低于结构起始: {sorted(ys)}")
    chk.ok(len(ys) == 1, f"固定模式文字高度应唯一: {sorted(ys)}")
    # 固定模式链轴坐标应唯一
    xs = {p[1] for p in mpe}
    chk.ok(len(xs) == 1, f"固定模式链轴坐标应唯一: {sorted(xs)}")
    return chk.report("circle")


def main():
    results = [
        test_lyrics_timing_all_directions(),
        test_fixed_position(),
        test_chain_below_structure(),
        test_circle_layout(),
    ]
    print()
    if all(results):
        print("全部通过")
        return 0
    print("存在失败项")
    return 1


if __name__ == "__main__":
    sys.exit(main())
