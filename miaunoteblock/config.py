"""配置文件默认值、读取与保存。"""

import json
import os

from .constants import Ansi

CONFIG_FILE = "nbs_chain_config.json"
DEFAULT_CONFIG = {
    "direction": "east",
    "merge_groups": [],
    "layout_style": "flat",
    "layout_radius": 5,
    "master_group": None,
    "flat_spacing": 3,
    "nest_layers": 1,
    "layer_gap": 4,
    "num_threads": 4,
    "use_redstone_lamp": False,
    "stereo_layers": [],
    "uniform_repeater_mode": False,
    "group_staircase_modes": {},  # 每组生成模式：{"0": "staircase", "1": "default", ...}
    "lyrics_track": None,        # 歌词轨道（原始 layer ID），None 为禁用
    "lyrics_text": "",           # 歌词文本，空格分隔段落
    "lyrics_color": "white",
    "lyrics_scale": 1.0,
    "lyrics_duration": 20,
    "lyrics_enter": 5,
    "lyrics_exit": 5,
    "lyrics_y_offset": 5,
    "lyrics_side_offset": None
}

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
            return cfg
        except:
            pass
    return dict(DEFAULT_CONFIG)

def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print(Ansi.success("配置已保存"))
    except Exception as e:
        print(Ansi.error(f"保存配置失败: {e}"))


# ── 常量 ─────────────────────────────────────────────────────

