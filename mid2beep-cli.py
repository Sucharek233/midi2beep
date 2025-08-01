import mido
import pyperclip
import sys
import argparse
import os


def note_to_freq(note: int) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


def extract_monophonic_notes(midi_path: str, target_channel: int = 0, merge: int = 0, reverse: int = 0):
    mid = mido.MidiFile(midi_path)
    ticks_per_beat = mid.ticks_per_beat
    default_tempo = 500_000  # µs per beat = 120 BPM

    # Merge all events from all tracks into one timeline
    events = []
    for track in mid.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            events.append((abs_tick, msg))

    # Sort by absolute time first, then by channel priority
    if reverse:
        # Higher channels get priority (processed last, so they override)
        events.sort(key=lambda x: (x[0], getattr(x[1], 'channel', -1)))
    else:
        # Lower channels get priority (processed last, so they override)
        events.sort(key=lambda x: (x[0], -getattr(x[1], 'channel', 999)))

    current_tick = 0
    current_time = 0.0
    current_tempo = default_tempo

    timeline = []
    last_event_time = 0.0

    active_note = None
    active_note_start_time = 0.0

    for abs_tick, msg in events:
        delta_ticks = abs_tick - current_tick
        delta_time = mido.tick2second(delta_ticks, ticks_per_beat, current_tempo)
        current_time += delta_time
        current_tick = abs_tick

        # Skip if channel doesn't match (if filtering)
        if not merge:
            if hasattr(msg, "channel") and target_channel is not None:
                if msg.channel != target_channel:
                    continue

        if msg.type == "set_tempo":
            current_tempo = msg.tempo

        elif msg.type == "note_on" and msg.velocity > 0:
            # New note starts

            # First, stop the currently active note if one is playing
            if active_note is not None:
                duration = current_time - active_note_start_time
                if active_note_start_time > last_event_time:
                    delay = active_note_start_time - last_event_time
                    timeline.append((0, 1, round(delay, 6)))
                timeline.append((active_note, round(note_to_freq(active_note), 2), round(duration, 6)))
                last_event_time = current_time

            # Start the new note
            active_note = msg.note
            active_note_start_time = current_time

        elif msg.type in ("note_off", "note_on") and (msg.type == "note_off" or msg.velocity == 0):
            # Stop the note only if it is currently active
            if active_note == msg.note:
                duration = current_time - active_note_start_time
                if active_note_start_time > last_event_time:
                    delay = active_note_start_time - last_event_time
                    timeline.append((0, 1, round(delay, 6)))
                timeline.append((active_note, round(note_to_freq(active_note), 2), round(duration, 6)))
                last_event_time = current_time
                active_note = None

    # If any note was left hanging, close it at end of track
    if active_note is not None:
        duration = current_time - active_note_start_time
        if active_note_start_time > last_event_time:
            delay = active_note_start_time - last_event_time
            timeline.append((0, 1, round(delay, 6)))
        timeline.append((active_note, round(note_to_freq(active_note), 2), round(duration, 6)))

    return timeline

def extract_monophonic_notes_old(midi_path: str, target_channel: int = 0, merge: int = 0, reverse: int = 0):
    mid = mido.MidiFile(midi_path)
    ticks_per_beat = mid.ticks_per_beat
    default_tempo = 500_000  # µs per beat = 120 BPM

    # Merge all events from all tracks into one timeline
    events = []
    for track in mid.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            events.append((abs_tick, msg))

    # Sort all by absolute time (tick)
    if reverse:
        events.reverse()
    events.sort(key=lambda x: x[0])

    current_tick = 0
    current_time = 0.0
    current_tempo = default_tempo

    timeline = []
    last_event_time = 0.0

    active_note = None
    active_note_start_time = 0.0

    for abs_tick, msg in events:
        delta_ticks = abs_tick - current_tick
        delta_time = mido.tick2second(delta_ticks, ticks_per_beat, current_tempo)
        current_time += delta_time
        current_tick = abs_tick

        # Skip if channel doesn't match (if filtering)
        if not merge:
            if hasattr(msg, "channel") and target_channel is not None:
                if msg.channel != target_channel:
                    continue

        if msg.type == "set_tempo":
            current_tempo = msg.tempo

        elif msg.type == "note_on" and msg.velocity > 0:
            # New note starts

            # First, stop the currently active note if one is playing
            if active_note is not None:
                duration = current_time - active_note_start_time
                if active_note_start_time > last_event_time:
                    delay = active_note_start_time - last_event_time
                    timeline.append((0, 1, round(delay, 6)))
                timeline.append((active_note, round(note_to_freq(active_note), 2), round(duration, 6)))
                last_event_time = current_time

            # Start the new note
            active_note = msg.note
            active_note_start_time = current_time

        elif msg.type in ("note_off", "note_on") and (msg.type == "note_off" or msg.velocity == 0):
            # Stop the note only if it is currently active
            if active_note == msg.note:
                duration = current_time - active_note_start_time
                if active_note_start_time > last_event_time:
                    delay = active_note_start_time - last_event_time
                    timeline.append((0, 1, round(delay, 6)))
                timeline.append((active_note, round(note_to_freq(active_note), 2), round(duration, 6)))
                last_event_time = current_time
                active_note = None

    # If any note was left hanging, close it at end of track
    if active_note is not None:
        duration = current_time - active_note_start_time
        if active_note_start_time > last_event_time:
            delay = active_note_start_time - last_event_time
            timeline.append((0, 1, round(delay, 6)))
        timeline.append((active_note, round(note_to_freq(active_note), 2), round(duration, 6)))

    return timeline


def format_single_line(notes, speed):
    final = "beep "
    for n, f, d in notes:
        if d == 0:
            continue
        if f == 1:
            final += f"-D {d * speed} "
        else:
            final += f"-n -f {f} -l {d * speed} "
    return final.strip()


def format_multi_line(notes, speed, continuation_char):
    lines = ["beep \\"] if continuation_char == "\\" else ["beep ^"]
    
    for n, f, d in notes:
        if d == 0:
            continue
        if f == 1:
            lines.append(f"  -D {d * speed} {continuation_char}")
        else:
            lines.append(f"  -n -f {f} -l {d * speed} {continuation_char}")
    
    # Remove continuation character from last line
    if lines:
        lines[-1] = lines[-1].rstrip(f" {continuation_char}")
    
    return "\n".join(lines)


def format_arduino_sequential(notes, speed):
    code = []
    code.append("// Generated Arduino beep code")
    code.append("// Connect buzzer to pin 8 (or change BUZZER_PIN)")
    code.append("")
    code.append("#define BUZZER_PIN 8")
    code.append("")
    code.append("void setup() {")
    code.append("  pinMode(BUZZER_PIN, OUTPUT);")
    code.append("}")
    code.append("")
    code.append("void loop() {")
    code.append("  playMelody();")
    code.append("  delay(2000); // Wait 2 seconds before repeating")
    code.append("}")
    code.append("")
    code.append("void playMelody() {")
    
    for n, f, d in notes:
        if d == 0:
            continue
        duration_ms = int(d * speed)
        if f == 1:
            code.append(f"  delay({duration_ms});")
        else:
            freq = int(f)
            code.append(f"  tone(BUZZER_PIN, {freq}, {duration_ms});")
            code.append(f"  delay({duration_ms});")
            code.append(f"  noTone(BUZZER_PIN);")
    
    code.append("}")
    
    return "\n".join(code)


def format_arduino_arrays(notes, speed):
    frequencies = []
    durations = []
    
    for n, f, d in notes:
        if d == 0:
            continue
        duration_ms = int(d * speed)
        if f == 1:
            frequencies.append(0)  # 0 for rest
        else:
            frequencies.append(int(f))
        durations.append(duration_ms)
    
    code = []
    code.append("// Generated Arduino beep code with arrays")
    code.append("// Connect buzzer to pin 8 (or change BUZZER_PIN)")
    code.append("")
    code.append("#define BUZZER_PIN 8")
    code.append("")
    
    # Format frequencies array
    code.append("int frequencies[] = {")
    for i in range(0, len(frequencies), 10):  # 10 per line
        line = "  " + ", ".join(map(str, frequencies[i:i+10]))
        if i + 10 < len(frequencies):
            line += ","
        code.append(line)
    code.append("};")
    code.append("")
    
    # Format durations array
    code.append("int durations[] = {")
    for i in range(0, len(durations), 10):  # 10 per line
        line = "  " + ", ".join(map(str, durations[i:i+10]))
        if i + 10 < len(durations):
            line += ","
        code.append(line)
    code.append("};")
    code.append("")
    
    code.append(f"int noteCount = {len(frequencies)};")
    code.append("")
    code.append("void setup() {")
    code.append("  pinMode(BUZZER_PIN, OUTPUT);")
    code.append("}")
    code.append("")
    code.append("void loop() {")
    code.append("  playMelody();")
    code.append("  delay(2000); // Wait 2 seconds before repeating")
    code.append("}")
    code.append("")
    code.append("void playMelody() {")
    code.append("  for (int i = 0; i < noteCount; i++) {")
    code.append("    if (frequencies[i] == 0) {")
    code.append("      delay(durations[i]);")
    code.append("    } else {")
    code.append("      tone(BUZZER_PIN, frequencies[i], durations[i]);")
    code.append("      delay(durations[i]);")
    code.append("      noTone(BUZZER_PIN);")
    code.append("    }")
    code.append("  }")
    code.append("}")
    
    return "\n".join(code)


def format_output(notes, speed, export_type):
    if export_type == "single":
        return format_single_line(notes, speed)
    elif export_type == "linux":
        return format_multi_line(notes, speed, "\\")
    elif export_type == "windows":
        return format_multi_line(notes, speed, "^")
    elif export_type == "arduino":
        return format_arduino_sequential(notes, speed)
    elif export_type == "arduino-arrays":
        return format_arduino_arrays(notes, speed)
    else:
        return format_single_line(notes, speed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a MIDI file into various beep formats.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Export Types:
  single         Single line beep command (default)
  linux          Multi-line with Linux continuation (\\)
  windows        Multi-line with Windows continuation (^)
  arduino        Arduino sequential code
  arduino-arrays Arduino code using arrays

Examples:
  python midi2beep.py -file song.mid
  python midi2beep.py -file song.mid -oldlogic
  python midi2beep.py -file song.mid -speed 1.5 -merge -reverse
  python midi2beep.py -file song.mid -export arduino -output song.ino
  python midi2beep.py -file song.mid -export linux -channel 2 -nocopy
        """
    )

    parser.add_argument("-file", required=True, help="Path to the input MIDI file")
    parser.add_argument("-output", help="Output file (if not specified, copies to clipboard)")
    parser.add_argument("-speed", type=float, default=1.0, help="Speed multiplier (default: 1.0)")
    parser.add_argument("-channel", type=int, default=0, help="Target MIDI channel (default: 0)")
    parser.add_argument("-merge", action="store_true", help="Merge all channels")
    parser.add_argument("-reverse", action="store_true", help="Reverse channel priority (use with -merge)")
    parser.add_argument("-export", choices=["single", "linux", "windows", "arduino", "arduino-arrays"], 
                       default="single", help="Export format (default: single)")
    parser.add_argument("-nocopy", action="store_true", help="Don't copy to clipboard")
    parser.add_argument("-noprint", action="store_true", help="Don't print to stdout")
    parser.add_argument("-oldlogic", action="store_true", help="Use old conversion logic")
    parser.add_argument("-quiet", action="store_true", help="Suppress status messages")

    args = parser.parse_args()
    
    # Validate file
    if not os.path.isfile(args.file):
        print(f"Error: File '{args.file}' not found or not readable.")
        sys.exit(1)
    
    try:
        # Process MIDI
        if not args.quiet:
            print(f"Processing MIDI file: {args.file}")
        
        target_channel = None if args.merge else args.channel
        merge = 1 if args.merge else 0
        reverse = 1 if args.reverse else 0
        
        extract_fn = extract_monophonic_notes_old if args.oldlogic else extract_monophonic_notes
        notes = extract_fn(args.file, target_channel, merge, reverse)
        
        if not args.quiet:
            print(f"Extracted {len(notes)} notes/events")
        
        # Format output
        speed = 1000 * args.speed
        final = format_output(notes, speed, args.export)
        
        # Output handling
        if args.output:
            # Write to file
            with open(args.output, 'w') as f:
                f.write(final)
            if not args.quiet:
                print(f"Output written to: {args.output}")
        else:
            if not args.noprint:
                # Print to stdout
                print(final)
        
        # Clipboard handling
        if not args.nocopy and not args.output:
            try:
                pyperclip.copy(final)
                if not args.quiet:
                    print("\n✓ Output copied to clipboard")
            except Exception as e:
                if not args.quiet:
                    print(f"\n⚠ Warning: Could not copy to clipboard: {e}")
        
        if not args.quiet and args.export in ["arduino", "arduino-arrays"]:
            print("\n✓ Arduino code generated successfully!")
            print("  Remember to connect your buzzer to pin 8 or modify the code")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
