<div align="center">

<img src="https://raw.githubusercontent.com/your-org/MiauRedstoneMusic/main/assets/miaunoteblock-logo.svg" alt="MiauNoteBlock logo" width="160" />

<h1>MiauNoteBlock</h1>

<p><b>Turn Note Block Studio songs into playable Minecraft redstone music.</b></p>
<p>Interactive Python generator that converts <code>.nbs</code> files into <code>.schem</code> note-block structures for Minecraft Java 1.21.11.</p>

<p>
  <a href="https://webnbs.com"><b>Online NBS &nbsp;›</b></a> &nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="Readme_CN.md"><b>中文文档</b></a> &nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="mpe_docs.md"><b>Lyric Mod Docs</b></a>
</p>

<p>
  <img src="https://img.shields.io/badge/Minecraft%20Java-1.21.11-62B47A?style=for-the-badge&logo=minecraft&logoColor=white" alt="Minecraft Java 1.21.11" />
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.x" />
  <img src="https://img.shields.io/badge/Output-.schem-7B61FF?style=for-the-badge" alt=".schem output" />
  <img src="https://img.shields.io/badge/License-Apache%202.0-D22128?style=for-the-badge&logo=apache&logoColor=white" alt="Apache License 2.0" />
  <img src="https://img.shields.io/badge/Status-Experimental-F2C94C?style=for-the-badge" alt="Experimental status" />
</p>

<p>
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square" alt="PRs welcome" />
  <img src="https://img.shields.io/badge/AI--assisted-~70%25-8A63D2?style=flat-square" alt="AI-assisted" />
</p>

<sub>Repository brand <b>MiauRedstoneMusic</b> &nbsp;·&nbsp; Product name <b>MiauNoteBlock</b></sub>

</div>

---

## Table of Contents

- [Overview](#overview)
- [At a Glance](#at-a-glance)
- [Features](#features)
- [Layouts](#layouts)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Lyric Command Blocks](#lyric-command-blocks)
- [Project Structure](#project-structure)
- [Brand Assets](#brand-assets)
- [Notes and Limitations](#notes-and-limitations)
- [Contributing](#contributing)
- [License](#license)
- [AI-Generated Code Notice](#ai-generated-code-notice)
- [Acknowledgements](#acknowledgements)

---

## Overview

**MiauNoteBlock** is an interactive Python utility in the **MiauRedstoneMusic** repository. It reads `.nbs` music files, converts their note and instrument data into Minecraft redstone note-block chains, and saves the result as a `.schem` structure file for Minecraft Java Edition.

It is built around the Minecraft Java **1.21.11** workflow and can optionally generate a synchronized **lyric command-block track** powered by the MiauParticleEffects Fabric mod.

---

## At a Glance

| | |
| :-- | :-- |
| **Input** | Note Block Studio `.nbs` files |
| **Output** | `.schem` structure (`mcschematic.Version.JE_1_21`) |
| **Interface** | Interactive terminal menu |
| **Target** | Minecraft Java Edition 1.21.11 |
| **Optional** | Particle-based lyrics via MiauParticleEffects |
| **Config** | `nbs_chain_config.json` in the working directory |

---

## Features

| Capability | What it gives you |
| :-- | :-- |
| **NBS conversion** | Reads notes and instruments, then emits a playable redstone chain. |
| **Track grouping** | Merges two or three virtual layers into a single generated group. |
| **Smart grouping** | Automatic grouping by instrument category, or maximum merging. |
| **Instrument handling** | Detects instruments and reorders tracks, with percussion placed later. |
| **Stereo support** | Mono tracks plus selected stereo tracks, duplicated and distributed symmetrically. |
| **Rich layouts** | Flat, circle, square, semicircle, semisquare, nested-circle, and nested-square. |
| **Master group** | Choose a core group for non-flat layouts. |
| **Staircase modes** | Per-group default or descending staircase generation. |
| **Timing engine** | Repeater and support blocks represent timing gaps and signal paths. |
| **Modern instruments** | Maps NBS instruments to note-block under-blocks, including copper and waxed copper stages. |
| **Light mode** | Optional redstone lamps in place of the default white-wool support mode. |
| **Lyric track** | Optional command-block chain that calls `/mpe text` from MiauParticleEffects. |

---

## Layouts

MiauNoteBlock can arrange each group with a different footprint, so the redstone structure matches the shape of your song instead of a single long line.

| Layout | Description |
| :-- | :-- |
| **Flat** | Straight rows, the densest and simplest arrangement. |
| **Circle** | Groups distributed around a ring. |
| **Square** | Groups distributed around a square. |
| **Semicircle** | Half-ring arrangement. |
| **Semisquare** | Half-square arrangement. |
| **Nested circle** | Concentric rings that reuse space efficiently. |
| **Nested square** | Concentric squares for compact builds. |

---

## Requirements

**Core**

- Python 3.x
- [`pynbs`](https://pypi.org/) — NBS parsing
- [`mcschematic`](https://pypi.org/) — structure construction and saving

**In-game**

- Minecraft Java Edition 1.21.11

**Optional lyric display**

- MiauParticleEffects for Minecraft Java 1.21.11 + Fabric
- Fabric Loader 0.16.0 or newer
- The matching Fabric API
- Java 21
- The mod installed on both client and server; a dedicated server needs it to detect note-block events and broadcast them

<sub>No dependency lockfile or packaged installer is currently included. Install dependencies according to your Python environment and package sources.</sub>

---

## Installation

**1 · Clone or download the repository**

```powershell
git clone https://github.com/your-org/MiauRedstoneMusic.git
cd MiauRedstoneMusic
```

**2 · Create and activate a virtual environment (optional)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**3 · Install dependencies**

```powershell
python -m pip install pynbs mcschematic
```

**4 · Prepare an input song**

Keep the `.nbs` file you want to convert accessible on your machine.

<sub>The exact package availability and compatible versions may depend on your environment. This README intentionally does not claim a tested package matrix.</sub>

---

## Usage

**Windows launcher**

```powershell
pm.bat
```

**Direct entry point**

```powershell
python miau_redstone_music.py
```

**Module form**

```powershell
python -m miaunoteblock
```

### Interactive Flow

| Step | Action |
| :--: | :-- |
| 1 | Enter the path to an `.nbs` file (default prompt: `song.nbs`). |
| 2 | Choose whether to vertically compress and reorder tracks by instrument. |
| 3 | Review the detected song metadata and virtual layers. |
| 4 | Configure direction, grouping, layout, stereo tracks, repeater timing, staircase modes, and optional lyrics. |
| 5 | Press Enter from the menu to generate the structure. |
| 6 | Enter the output path, or accept `./redstone_music.schem`. |

The generated file can be loaded with a compatible Minecraft structure workflow, such as a schematic-capable editor or server tool. The generator reports the normalized block bounds and suggests the resulting origin after loading; the exact paste workflow depends on your setup.

---

## Lyric Command Blocks

Generate a synchronous lyric track that renders through particles.

1. Select an original NBS layer as the lyric track.
2. Enter lyric segments separated by spaces, with line breaks separating lines.
3. Configure color, scale, duration, enter time, exit time, vertical offset, and side offset.
4. Generate the `.schem` file.

Each command block calls:

```text
/mpe text "lyric segment" <x> <y> <z> color=white scale=1.0 duration=20 enter=5 exit=5
```

MiauParticleEffects provides the `/mpe text` entry point and renders the text as particle-based display content. See [mpe_docs.md](mpe_docs.md) for the documented mod environment and command options.

---

## Project Structure

| Path | Purpose |
| :-- | :-- |
| `miau_redstone_music.py` | Interactive entry point. |
| `pm.bat` | Windows launcher for the entry point. |
| `miaunoteblock/` | Main package. `app.py` holds the interactive flow and `main()`; `constants.py`, `config.py`, `lyrics.py`, `instruments.py`, `layout.py`, and `generation.py` hold reusable logic. |
| `mpe_docs.md` | MiauParticleEffects command and environment notes. |
| `Readme_CN.md` | Chinese documentation. |

---

## Brand Assets

The logo in the header is a **placeholder** and should be replaced with the final GitHub raw or CDN asset URL before publishing.

**Recommended logo specification**

| Property | Recommendation |
| :-- | :-- |
| **Format** | SVG (preferred) or PNG |
| **Size** | 512 × 512 px |
| **Background** | Transparent |
| **Style** | Simple, recognizable at small sizes, readable on both light and dark GitHub themes |
| **Display width** | 140–180 px in the README header |

A flat, single-object mark with a limited palette works best: it stays legible as a favicon, a social preview, and an in-README badge.

---

## Notes and Limitations

> **Notes**
> - The input file must contain notes; empty NBS files cannot produce a music chain.
> - Lyric rendering requires MiauParticleEffects. Without the mod, the generated lyric commands will not provide their intended display.
> - Minecraft Java, Fabric, Fabric API, Java, and MiauParticleEffects versions should match the target environment, especially for 1.21.11.

> **Limitations**
> - Large songs, dense chords, small particle density, or many simultaneous effects may require substantial Minecraft performance headroom.
> - The tool currently generates `.schem` structures only; it does not export a standalone command text file or another structure format.
> - The tool is interactive and writes configuration beside the current working directory rather than using a documented global configuration path.
> - The repository does not currently provide official release binaries, screenshots, or a verified download URL.

---

## Contributing

Contributions are welcome. Before opening a pull request:

- Explain the user-visible behavior you changed.
- Keep conversion behavior and Minecraft version assumptions explicit.
- Preserve the existing interactive workflow unless the change requires otherwise.
- Include a reproducible example when changing NBS parsing, timing, layout, instrument mapping, or lyric commands.
- Do not include copyrighted music files, secrets, or generated build artifacts in commits.

---

## License

Released under the **Apache License 2.0**. See [LICENSE](LICENSE) for the full text.

You are free to use, modify, and distribute this project in compliance with the license terms.

---

## AI-Generated Code Notice

> Approximately **70%** of the code was generated with AI assistance. Perfect quality cannot be guaranteed, although the AI is impressive. Some code comments may be imperfect, and the codebase may contain unrelated AI-generated notes. When reading or reviewing the code, you may want to use AI assistance as an additional aid.

---

## Acknowledgements

| Project | Role |
| :-- | :-- |
| [`pynbs`](https://pypi.org/) | NBS file parsing |
| [`mcschematic`](https://pypi.org/) | Schematic construction and saving |
| MiauParticleEffects | Optional lyric command-block workflow |

<sub>The links above point to package indexes rather than claiming a specific project page or release artifact.</sub>

<div align="center">
<br />
<sub>Built for the Minecraft Java redstone music community.</sub>
</div>
