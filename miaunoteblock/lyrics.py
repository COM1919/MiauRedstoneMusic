"""歌词解析、段落映射与歌词命令方块轨道生成。"""

import json
from typing import List, Tuple

from .config import save_config
from .constants import Ansi, DIR_OFFSET, OPPOSITE_FACING, SIDE_AXIS
from .generation import split_to_repeaters

def parse_lyrics(lyrics_text: str) -> List[str]:
    """解析歌词文本，按空格和换行分段，返回段落列表"""
    segments = []
    for line in lyrics_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = line.split(' ')
        segments.extend([p for p in parts if p])
    return segments

def load_lyrics_json(path: str) -> List[Tuple[int, str, int]]:
    """读取编辑器导出的歌词 JSON。

    文件结构：
        {
          "type": "noteblock-web-lyrics",
          "formatVersion": 1,
          "tempo": 13,
          "lyrics": {"234": {"text": "...", "duration": 14}, ...}
        }

    lyrics 的键为 tick，仅记录有歌词的 tick，其余 tick 不出现。
    返回 [(tick, 文字, 显示时长), ...]，按 tick 升序；时长为 0 表示使用全局设置。
    """
    with open(path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON 格式错误: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("根节点必须是 JSON 对象")
    lyrics = data.get("lyrics")
    if not isinstance(lyrics, dict):
        raise ValueError("缺少 lyrics 字段，或它不是 JSON 对象")
    entries: List[Tuple[int, str, int]] = []
    for key, value in lyrics.items():
        try:
            tick = int(key)
        except (TypeError, ValueError):
            continue
        if isinstance(value, dict):
            text = value.get("text", "")
            try:
                duration = int(value.get("duration") or 0)
            except (TypeError, ValueError):
                duration = 0
        elif isinstance(value, str):
            text, duration = value, 0
        else:
            continue
        text = (text or "").strip()
        if not text:
            continue
        entries.append((tick, text, max(0, duration)))
    entries.sort(key=lambda item: item[0])
    return entries

def map_lyrics_to_notes(segments: List[str], lyrics_notes: List) -> List[Tuple[int, str, int]]:
    """
    将歌词段落映射到音符序列
    返回: [(tick, 显示文字, 显示时长), ...]
    - segments: 歌词段落列表
    - lyrics_notes: 歌词轨道的音符列表（已排序）
    每个段落对应连续的一组音符，段落首音符显示整段文字；时长为 0 表示使用全局设置
    """
    result = []
    note_idx = 0
    for seg in segments:
        seg_len = len(seg)
        if seg_len == 0:
            continue
        # 该段落对应的音符范围
        end_idx = min(note_idx + seg_len, len(lyrics_notes))
        segment_notes = lyrics_notes[note_idx:end_idx]
        if not segment_notes:
            break
        tick = segment_notes[0].tick
        result.append((tick, seg, 0))
        note_idx = end_idx
    return result

def build_lyrics_commands(
    lyrics_notes: List,
    lyrics_mapping: List[Tuple[int, str, int]],
    base: Tuple[int, int, int],
    direction: str,
    max_tick: int,
    config: dict,
    use_lamp: bool = False,
    uniform_repeater_mode: bool = False,
    anchor_side: int = None,
    anchor_chain: int = None,
    anchor_y: int = None,
    origin_tick: int = None,
    fixed_tick: int = None
) -> List[str]:
    """生成歌词命令方块链。

    lyrics_mapping 为 [(tick, 显示文字, 显示时长), ...]，时长为 0 时使用全局设置。
    anchor_side / anchor_chain / anchor_y 用于把文字固定到主轨道上方：
    - anchor_side：文字在侧向轴（垂直于链条）上的坐标，None 表示跟随命令方块
    - anchor_chain：文字在链条轴上的坐标，None 表示跟随命令方块向前移动
    - anchor_y：文字高度，None 表示以歌词轨道为基准加上 lyrics_y_offset
    origin_tick：主链条的时间原点（全局第一个 tick），None 表示以歌词自身的第一个 tick 为原点。
    会在该 tick 处补一个空白事件格，使歌词链与音乐链的计时原点一致
    fixed_tick：文字不跟随时，取最接近该 tick 的事件格的链轴坐标作为固定位置
    """
    dx, _, dz = DIR_OFFSET[direction]
    facing = OPPOSITE_FACING[direction]
    side_axis = SIDE_AXIS[direction]
    base_x, base_y, base_z = base
    current_y = base_y - 3
    base_block = "minecraft:redstone_lamp" if use_lamp else "minecraft:white_wool"
    sorted_notes = sorted(lyrics_notes, key=lambda note: note.tick)
    mapping = {tick: (text, duration) for tick, text, duration in lyrics_mapping}
    if not sorted_notes:
        return []

    commands = []
    side_offset = int(config.get("lyrics_side_offset") or 0)
    global_duration = max(0, int(config.get("lyrics_duration", 20)))

    def add_support(x: int, z: int):
        commands.append(f"setblock {x} {current_y - 1} {z} {base_block}")

    def command_block(x: int, z: int, text: str, duration: int):
        if side_axis == "z":
            chain_coord = anchor_chain if anchor_chain is not None else x
            side_coord = (anchor_side if anchor_side is not None else z) + side_offset
            display_x, display_z = chain_coord, side_coord
        else:
            chain_coord = anchor_chain if anchor_chain is not None else z
            side_coord = (anchor_side if anchor_side is not None else x) + side_offset
            display_x, display_z = side_coord, chain_coord
        display_y = anchor_y if anchor_y is not None else base_y + int(config.get("lyrics_y_offset", 5))
        text_duration = duration if duration and duration > 0 else global_duration
        options = [
            f"color={config.get('lyrics_color', 'white')}",
            f"scale={max(0.05, min(64.0, float(config.get('lyrics_scale', 1.0))))}",
            f"duration={text_duration}",
            f"enter={max(0, int(config.get('lyrics_enter', 5)))}",
            f"exit={max(0, int(config.get('lyrics_exit', 5)))}"
        ]
        command = f"/mpe text {json.dumps(text, ensure_ascii=False)} {display_x} {display_y} {display_z} {' '.join(options)}"
        nbt = json.dumps(command, ensure_ascii=False)
        commands.append(f"setblock {x} {current_y} {z} minecraft:command_block[facing={facing}]{{Command:{nbt}}}")

    valid_ticks = sorted(
        {note.tick for note in sorted_notes if 0 <= note.tick <= max_tick}
        | {tick for tick in mapping if 0 <= tick <= max_tick}
    )
    if origin_tick is not None and 0 <= origin_tick <= max_tick:
        # 主链条的时间原点：并入有效 tick，使歌词链与音乐链的计时起点一致
        valid_ticks = sorted(set(valid_ticks) | {origin_tick})
        early_ticks = [tick for tick in valid_ticks if tick < origin_tick]
        if early_ticks:
            print(Ansi.error(f"警告：{len(early_ticks)} 个事件早于音乐起点 tick {origin_tick}，已跳过"))
            valid_ticks = [tick for tick in valid_ticks if tick >= origin_tick]
    if max_tick not in valid_ticks:
        valid_ticks.append(max_tick)
    valid_ticks.sort()
    if not valid_ticks:
        return []

    # 固定文字位置：预先按实际链条布局求出最接近 fixed_tick 的事件格坐标
    # （每个空白 tick 的中继器最多覆盖 4 tick、占 2 格，不能按 tick 数直接换算）
    if fixed_tick is not None and anchor_chain is None:
        cursor = 0
        best_offset = 0
        best_dist = None
        prev = None
        for tick in valid_ticks:
            if prev is not None:
                blank_ticks = max(0, tick - prev - 1)
                delays = [1] * blank_ticks if uniform_repeater_mode else split_to_repeaters(blank_ticks)
                cursor += 2 + 2 * len(delays)   # 事件格后的中继器 + 空白中继器对 + 下一个事件格
            dist = abs(tick - fixed_tick)
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_offset = cursor
            prev = tick
        if side_axis == "z":
            anchor_chain = base_x + best_offset * dx
        else:
            anchor_chain = base_z + best_offset * dz

    # 与音乐链完全一致的链条结构：
    #   事件格自身占 1 红石 tick（其后紧跟一个 delay=1 中继器），
    #   空白 tick 用 [连接羊毛 + 中继器] 填充（每个中继器最多覆盖 4 tick）
    start_x = base_x - dx
    start_z = base_z - dz
    commands.append(f"setblock {start_x} {current_y} {start_z} minecraft:repeater[facing={facing},delay=1]")
    add_support(start_x, start_z)
    previous_tick = None
    current_x, current_z = start_x, start_z

    for tick in valid_ticks:
        blank_ticks = 0 if previous_tick is None else max(0, tick - previous_tick - 1)
        extra_delays = [1] * blank_ticks if uniform_repeater_mode else split_to_repeaters(blank_ticks)
        for delay in extra_delays:
            connector_x, connector_z = current_x + dx, current_z + dz
            repeater_x, repeater_z = connector_x + dx, connector_z + dz
            add_support(connector_x, connector_z)
            add_support(repeater_x, repeater_z)
            # 链层连接方块：与音乐链一致，中继器之间靠羊毛传导
            commands.append(f"setblock {connector_x} {current_y} {connector_z} minecraft:white_wool")
            commands.append(f"setblock {repeater_x} {current_y} {repeater_z} minecraft:repeater[facing={facing},delay={delay}]")
            current_x, current_z = repeater_x, repeater_z

        event_x, event_z = current_x + dx, current_z + dz
        add_support(event_x, event_z)
        entry = mapping.get(tick)
        if entry is None:
            commands.append(f"setblock {event_x} {current_y} {event_z} {base_block}")
        else:
            command_block(event_x, event_z, entry[0], entry[1])
        current_x, current_z = event_x, event_z

        # 事件格占用 1 红石 tick：与音乐链一致，紧邻其后放一个 delay=1 中继器
        relay_x, relay_z = current_x + dx, current_z + dz
        add_support(relay_x, relay_z)
        commands.append(f"setblock {relay_x} {current_y} {relay_z} minecraft:repeater[facing={facing},delay=1]")
        current_x, current_z = relay_x, relay_z
        previous_tick = tick

    return commands

# ── 歌词设置 UI ──────────────────────────────────────────────

def import_lyrics_json(config: dict):
    """从编辑器导出的 JSON 文件导入歌词"""
    print(Ansi.title("\n=== 导入歌词 JSON ==="))
    print(Ansi.info("支持编辑器导出的歌词文件（type: noteblock-web-lyrics）。"))
    print(Ansi.dim("文件中每个 tick 记录一次歌词，未记录的 tick 表示该处没有歌词。"))
    current = config.get("lyrics_import") or {}
    if current:
        print(Ansi.info(f"当前已导入 {len(current)} 条歌词"))

    raw = input(Ansi.prompt("请输入 JSON 文件路径 (直接回车=取消): ")).strip().strip('"').strip("'")
    if not raw:
        print(Ansi.info("已取消导入"))
        return
    try:
        entries = load_lyrics_json(raw)
    except FileNotFoundError:
        print(Ansi.error("文件不存在"))
        return
    except ValueError as exc:
        print(Ansi.error(f"解析失败: {exc}"))
        return
    except OSError as exc:
        print(Ansi.error(f"读取失败: {exc}"))
        return
    if not entries:
        print(Ansi.error("文件中没有有效歌词"))
        return

    config["lyrics_import"] = {
        str(tick): {"text": text, "duration": duration} for tick, text, duration in entries
    }
    print(Ansi.success(f"已导入 {len(entries)} 条歌词（生成时优先于手动输入的歌词）"))
    for tick, text, duration in entries[:5]:
        print(Ansi.dim(f"  tick {tick}: {text} (duration={duration})"))
    if len(entries) > 5:
        print(Ansi.dim(f"  …… 其余 {len(entries) - 5} 条"))
    save_config(config)

def edit_lyrics_settings(config: dict):
    """交互式修改歌词显示参数"""
    print(Ansi.title("\n=== 歌词显示参数 ==="))
    print(Ansi.info("直接回车保留当前值。"))

    follow = config.get("lyrics_follow", True)
    print(Ansi.dim(f"当前文字位置: {'随音乐沿结构上方前进' if follow else '固定在结构纵向中心'}"))
    follow_in = input(Ansi.prompt("文字是否跟随向前移动 (y/n，回车=不修改): ")).strip().lower()
    if follow_in in ("y", "yes"):
        config["lyrics_follow"] = True
    elif follow_in in ("n", "no"):
        config["lyrics_follow"] = False

    color = input(Ansi.prompt(f"颜色 ({config.get('lyrics_color', 'white')}): ")).strip()
    if color:
        config["lyrics_color"] = color

    scale = input(Ansi.prompt(f"字形高度 scale ({config.get('lyrics_scale', 1.0)}): ")).strip()
    if scale:
        try:
            config["lyrics_scale"] = max(0.05, min(64.0, float(scale)))
        except ValueError:
            print(Ansi.error("scale 必须是数字，未修改"))

    duration = input(Ansi.prompt(f"默认显示时长 duration ({config.get('lyrics_duration', 20)}): ")).strip()
    if duration:
        try:
            config["lyrics_duration"] = max(0, int(duration))
        except ValueError:
            print(Ansi.error("duration 必须是整数，未修改"))

    enter = input(Ansi.prompt(f"入场时长 enter ({config.get('lyrics_enter', 5)}): ")).strip()
    if enter:
        try:
            config["lyrics_enter"] = max(0, int(enter))
        except ValueError:
            print(Ansi.error("enter 必须是整数，未修改"))

    exit_in = input(Ansi.prompt(f"出场时长 exit ({config.get('lyrics_exit', 5)}): ")).strip()
    if exit_in:
        try:
            config["lyrics_exit"] = max(0, int(exit_in))
        except ValueError:
            print(Ansi.error("exit 必须是整数，未修改"))

    height = input(Ansi.prompt(f"文字相对主轨道的高度 ({config.get('lyrics_y_offset', 5)}): ")).strip()
    if height:
        try:
            config["lyrics_y_offset"] = int(height)
        except ValueError:
            print(Ansi.error("高度必须是整数，未修改"))

    side = config.get("lyrics_side_offset")
    side_in = input(Ansi.prompt(f"额外的侧向偏移 ({'未设置' if side is None else side}): ")).strip()
    if side_in:
        try:
            config["lyrics_side_offset"] = int(side_in)
        except ValueError:
            print(Ansi.error("侧向偏移必须是整数，未修改"))

    save_config(config)

