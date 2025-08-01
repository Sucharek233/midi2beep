# midi2beep

Convert MIDI files to a monophonic sequence of `beep` commands (Linux-style syntax) or Arduino code.\
This is a simple app, don't expect miracles :)

~~This project was mostly vibecoded~~ Nah it was almost completely vibecoded, but uhhh it works so ye :)\
Man, chatgpt can generate very nice readme files, I'm impressed xdd

---

## Installation

### For GUI:
```bash
pip install mido tk pyperclip
````
### For CLI:
```bash
pip install mido pyperclip argparse
````
### For Minimal:
```bash
pip install mido
````

### Python libraries used:

* `mido`: for parsing MIDI files
* `tk` (tkinter), `threading`: for the GUI and its functionality
* `pyperclip`: for copying the output to clipboard
* `argparse`, `sys`, `os`: for argument parsing and file validation

---

## GUI Usage
![gui](https://github.com/Sucharek233/midi2beep/blob/master/img/gui.png)

### 1. Select a MIDI File
* Click **Browse** to choose a `.mid` file from your computer.

### 2. Set Playback Speed
* Adjust the **Speed** slider to change playback/conversion speed (0.1× to 3.0×). Warning! This slider is reversed! (2x is **2x slower**)

### 3. Choose a Channel
* Use the **Channel** spinbox to target a specific MIDI channel (0–15).
* Or enable **Merge all channels** to include all channels in conversion. This is probably the **most important** feature of this app.

### 4. Configure Options
* **Merge all channels** – combine all tracks.
* **Reverse channel priority** – prioritizes later channels.
* **Use old conversion logic** – uses conversion logic from v1.

### 5. Export Type
* `Single line` – one-line output
* `Multi-line` – split by OS (Linux `\`, Windows `^`)
* `Arduino Sequential` – step-by-step playback
* `Arduino Arrays` – array-based output that looks nicer :) (**takes up more flash memory!**)

### 6. Output
* **Copy to clipboard** – places result in your clipboard.
* **Save to file** – saves output to a file.

---

## CLI Usage

### Basic Usage

```bash
python midi2beep.py -file <path_to_midi>
```

### Flags

| Argument    | Description                                                                                |
| ----------- | -------------------------------------------------------------------------------------------|
| `-file`     | **(Required)** Path to the input `.mid` file                                               |
| `-output`   | Output file path (if omitted, result is copied to clipboard)                               |
| `-speed`    | Playback speed multiplier (default: `1.0`) Warning! This is reversed! (2 is **2x slower**) |
| `-channel`  | MIDI channel to convert (`0 - 15`, default: `0`)                                           |
| `-merge`    | Merge all channels into a single output                                                    |
| `-reverse`  | Reverse channel priority (useful with `-merge`)                                            |
| `-export`   | Export format (see below; default: `single`)                                               |
| `-nocopy`   | Do **not** copy output to clipboard                                                        |
| `-noprint`  | Do **not** print output to stdout                                                          |
| `-oldlogic` | Uses conversion logic from v1.                                                             |
| `-quiet`    | Suppress all status messages                                                               |

### Export Formats

| Value            | Description                                   |
| ---------------- | --------------------------------------------- |
| `single`         | Single-line beep command *(default)*          |
| `linux`          | Multi-line with Linux line continuation (`\`) |
| `windows`        | Multi-line with Windows continuation (`^`)    |
| `arduino`        | Arduino `tone()` commands                     |
| `arduino-arrays` | Arduino array-based format                    |

### Examples

```bash
# Basic conversion (default format: single line)
python midi2beep.py -file song.mid

# Use legacy conversion logic
python midi2beep.py -file song.mid -oldlogic

# Increase speed and merge all channels, reversing priority
python midi2beep.py -file song.mid -speed 1.5 -merge -reverse

# Export as Arduino code
python midi2beep.py -file song.mid -export arduino -output song.ino

# Export as Linux multi-line script without copying to clipboard
python midi2beep.py -file song.mid -export linux -channel 2 -nocopy
```
## How to play the output on a Computer

### Linux (PC speaker)
1. Install the `beep` utility.
2. Setup proper permissions on `/dev/input/by-path/platform-pcspkr-event-spkr` (or just `chmod 777` it lmao, bad advice but works)
3. Paste the generated beep sequence into the terminal.

### Windows
1. Use [my fork](https://github.com/Sucharek233/beep-on-windows/releases) ([Download the zip directly](https://github.com/Sucharek233/beep-on-windows/releases/download/1.0/beep.zip)) of [pc-beeper](https://github.com/cocafe/pc-beeper) adapted for Linux-compatible syntax.
2. Extract the zip file.
3. Open a command prompt as Administrator and navigate to the extracted folder.
4. Paste the output from this tool.

---

## Common Issues with Playback on a Computer

### Getting no sound?

* Your system likely doesn't have a physical PC speaker.
* Most laptops use emulated beepers or none at all — and these may not produce any sound.
* This tool **requires** access to an actual or emulated PC speaker.

---

## How does it work?

* Parses the MIDI file using `mido`, collecting all events from all tracks.
* Merges and sorts events by absolute time (converted from ticks to seconds).
* Filters channels:
  * If `-channel` is set: processes only that channel.
  * If `-merge` is set: uses all channels, in priority order (optionally reversed).
* Plays only **one note at a time** (monophonic mode):
  * When a new note starts, the previous one is immediately cut off.
  * This compresses the melody line into a single stream but may lose overlapping harmonies.

* Adds delay for silent gaps between notes.
* Copies the result to your clipboard, ready to paste into a terminal for playback.