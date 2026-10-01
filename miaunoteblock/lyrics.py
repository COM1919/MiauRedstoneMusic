"""歌词解析、段落映射与歌词命令方块轨道生成。"""

import json
from typing import List, Tuple

from .constants import DIR_OFFSET, OPPOSITE_FACING, SIDE_AXIS
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

def map_lyrics_to_notes(segments: List[str], lyrics_notes: List) -> List[Tuple[int, str, int]]:
    """
    将歌词段落映射到音符序列
    返回: [(tick, 显示文字, 持续音符数), ...]
    - segments: 歌词段落列表
    - lyrics_notes: 歌词轨道的音符列表（已排序）
    每个段落对应连续的一组音符，段落首音符显示整段文字
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
        result.append((tick, seg, len(segment_notes)))
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
    uniform_repeater_mode: bool = False
) -> List[str]:
    dx, _, dz = DIR_OFFSET[direction]
    facing = OPPOSITE_FACING[direction]
    side_axis = SIDE_AXIS[direction]
    base_x, base_y, base_z = base
    current_y = base_y - 3
    base_block = "minecraft:redstone_lamp" if use_lamp else "minecraft:white_wool"
    sorted_notes = sorted(lyrics_notes, key=lambda note: note.tick)
    mapping = {tick: text for tick, text, _ in lyrics_mapping}
    if not sorted_notes:
        return []

    commands = []

    def add_support(x: int, z: int):
        commands.append(f"setblock {x} {current_y - 1} {z} {base_block}")

    def command_block(x: int, z: int, text: str):
        display_x = x + int(config.get("lyrics_side_offset") or 0) if side_axis == "x" else x
        display_z = z + int(config.get("lyrics_side_offset") or 0) if side_axis == "z" else z
        display_y = base_y + int(config.get("lyrics_y_offset", 5))
        options = [
            f"color={config.get('lyrics_color', 'white')}",
            f"scale={max(0.05, min(64.0, float(config.get('lyrics_scale', 1.0))))}",
            f"duration={max(0, int(config.get('lyrics_duration', 20)))}",
            f"enter={max(0, int(config.get('lyrics_enter', 5)))}",
            f"exit={max(0, int(config.get('lyrics_exit', 5)))}"
        ]
        command = f"/mpe text {json.dumps(text, ensure_ascii=False)} {display_x} {display_y} {display_z} {' '.join(options)}"
        nbt = json.dumps(command, ensure_ascii=False)
        commands.append(f"setblock {x} {current_y} {z} minecraft:command_block[facing={facing}]{{Command:{nbt}}}")

    valid_ticks = sorted({note.tick for note in sorted_notes if 0 <= note.tick <= max_tick})
    if max_tick not in valid_ticks:
        valid_ticks.append(max_tick)
    valid_ticks.sort()
    if not valid_ticks:
        return []

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
            relay_x, relay_z = current_x + dx, current_z + dz
            support_x, support_z = relay_x + dx, relay_z + dz
            add_support(relay_x, relay_z)
            add_support(support_x, support_z)
            commands.append(f"setblock {support_x} {current_y} {support_z} minecraft:repeater[facing={facing},delay={delay}]")
            current_x, current_z = support_x, support_z

        event_x, event_z = current_x + dx, current_z + dz
        add_support(event_x, event_z)
        text = mapping.get(tick)
        if text is None:
            commands.append(f"setblock {event_x} {current_y} {event_z} {base_block}")
        else:
            command_block(event_x, event_z, text)
        current_x, current_z = event_x, event_z
        previous_tick = tick

    return commands

# ── 歌词设置 UI ──────────────────────────────────────────────

