import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import mido
import pyperclip
import os
from threading import Thread


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


class MidiToBeepGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MIDI to Beep Converter")
        self.root.geometry("550x500")
        self.root.minsize(500, 450)
        
        # Variables
        self.file_path = tk.StringVar()
        self.speed = tk.DoubleVar(value=1.0)
        self.channel = tk.IntVar(value=0)
        self.merge_channels = tk.BooleanVar(value=False)
        self.reverse_priority = tk.BooleanVar(value=False)
        self.old_logic = tk.BooleanVar(value=False)
        self.export_type = tk.StringVar(value="single_line")
        self.copy_to_clipboard = tk.BooleanVar(value=True)
        self.save_to_file = tk.BooleanVar(value=False)
        
        self.setup_ui()
    
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # File selection
        ttk.Label(main_frame, text="MIDI File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_path, width=40)
        self.file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(file_frame, text="Browse", command=self.browse_file).grid(row=0, column=1, padx=(5, 0))
        
        # Speed setting
        ttk.Label(main_frame, text="Speed:").grid(row=1, column=0, sticky=tk.W, pady=5)
        speed_frame = ttk.Frame(main_frame)
        speed_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Scale(speed_frame, from_=0.1, to=3.0, variable=self.speed, orient=tk.HORIZONTAL, length=200).grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.speed_label = ttk.Label(speed_frame, text="1.0x")
        self.speed_label.grid(row=0, column=1, padx=(10, 0))
        
        # Update speed label when scale changes
        self.speed.trace_add('write', self.update_speed_label)
        
        # Channel settings
        ttk.Label(main_frame, text="Channel:").grid(row=2, column=0, sticky=tk.W, pady=5)
        channel_frame = ttk.Frame(main_frame)
        channel_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        
        self.channel_spinbox = ttk.Spinbox(channel_frame, from_=0, to=15, textvariable=self.channel, width=5)
        self.channel_spinbox.grid(row=0, column=0, sticky=tk.W)
        
        # Options
        ttk.Label(main_frame, text="Options:").grid(row=3, column=0, sticky=tk.W, pady=5)
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Checkbutton(options_frame, text="Merge all channels", variable=self.merge_channels, command=self.toggle_channel_state).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(options_frame, text="Reverse channel priority", variable=self.reverse_priority).grid(row=0, column=1, sticky=tk.W)
        ttk.Checkbutton(options_frame, text="Use old conversion logic", variable=self.old_logic).grid(row=1, column=0, sticky=tk.W)
        
        # Export type
        ttk.Label(main_frame, text="Export Type:").grid(row=4, column=0, sticky=tk.W, pady=5)
        export_frame = ttk.Frame(main_frame)
        export_frame.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5)
        
        export_options = [
            ("Single line", "single_line", 0, 0),
            ("Multi-line (Linux \\)", "multi_line_linux", 0, 1),
            ("Multi-line (Windows ^)", "multi_line_windows", 1, 1),
            ("Arduino Sequential", "arduino_sequential", 0, 2),
            ("Arduino Arrays", "arduino_arrays", 1, 2)
        ]
        
        for text, value, row, col in export_options:
            ttk.Radiobutton(export_frame, text=text, variable=self.export_type, value=value).grid(row=row, column=col, sticky=tk.W, padx=(0, 15), pady=2)

        
        # Output options
        ttk.Label(main_frame, text="Output:").grid(row=5, column=0, sticky=tk.W, pady=5)
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Checkbutton(output_frame, text="Copy to clipboard", variable=self.copy_to_clipboard).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(output_frame, text="Save to file", variable=self.save_to_file).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        # Convert buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=20)
        
        self.convert_button = ttk.Button(button_frame, text="Convert", command=self.convert_file)
        self.convert_button.grid(row=0, column=0, padx=(0, 10))
        
        self.export_file_button = ttk.Button(button_frame, text="Convert & Export to File", command=self.convert_and_export)
        self.export_file_button.grid(row=0, column=1)
        
        # Status/Output area
        ttk.Label(main_frame, text="Output Preview:").grid(row=7, column=0, sticky=tk.W, pady=(10, 5))
        
        # Text area with scrollbar
        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.output_text = tk.Text(text_frame, height=12, wrap=tk.WORD, font=("Courier", 9))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=scrollbar.set)
        
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(8, weight=1)
        file_frame.columnconfigure(0, weight=1)
        speed_frame.columnconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Initial state
        self.toggle_channel_state()
    
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select MIDI File",
            filetypes=[("MIDI files", "*.mid *.midi"), ("All files", "*.*")]
        )
        if filename:
            self.file_path.set(filename)
    
    def get_save_filename(self):
        export_type = self.export_type.get()
        
        # Suggest appropriate file extensions based on export type
        if export_type in ["arduino_sequential", "arduino_arrays"]:
            filetypes = [("Arduino files", "*.ino"), ("C++ files", "*.cpp"), ("Text files", "*.txt"), ("All files", "*.*")]
            default_ext = ".ino"
        elif export_type == "multi_line_windows":
            filetypes = [("Batch files", "*.bat *.cmd"), ("Text files", "*.txt"), ("All files", "*.*")]
            default_ext = ".bat"
        elif export_type == "multi_line_linux":
            filetypes = [("Shell scripts", "*.sh"), ("Text files", "*.txt"), ("All files", "*.*")]
            default_ext = ".sh"
        else:
            filetypes = [("Text files", "*.txt"), ("Shell scripts", "*.sh"), ("All files", "*.*")]
            default_ext = ".txt"
        
        # Generate suggested filename based on input MIDI file
        if self.file_path.get():
            base_name = os.path.splitext(os.path.basename(self.file_path.get()))[0]
            suggested_name = f"{base_name}_beep{default_ext}"
        else:
            suggested_name = f"melody{default_ext}"
        
        filename = filedialog.asksaveasfilename(
            title="Save Output File",
            filetypes=filetypes,
            defaultextension=default_ext,
            initialfile=suggested_name
        )
        return filename
    
    def update_speed_label(self, *args):
        self.speed_label.config(text=f"{self.speed.get():.1f}x")
    
    def toggle_channel_state(self):
        if self.merge_channels.get():
            self.channel_spinbox.config(state='disabled')
        else:
            self.channel_spinbox.config(state='readonly')
    
    def format_output(self, notes, speed):
        export_type = self.export_type.get()
        
        if export_type == "single_line":
            return self.format_single_line(notes, speed)
        elif export_type == "multi_line_linux":
            return self.format_multi_line(notes, speed, "\\")
        elif export_type == "multi_line_windows":
            return self.format_multi_line(notes, speed, "^")
        elif export_type == "arduino_sequential":
            return self.format_arduino_sequential(notes, speed)
        elif export_type == "arduino_arrays":
            return self.format_arduino_arrays(notes, speed)
        
    def format_single_line(self, notes, speed):
        final = "beep "
        for n, f, d in notes:
            if d == 0:
                continue
            if f == 1:
                final += f"-D {d * speed} "
            else:
                final += f"-n -f {f} -l {d * speed} "
        return final.strip()
    
    def format_multi_line(self, notes, speed, continuation_char):
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
    
    def format_arduino_sequential(self, notes, speed):
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
    
    def format_arduino_arrays(self, notes, speed):
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
    
    def convert_file(self):
        if not self.validate_inputs():
            return
        
        # Disable buttons during conversion
        self.convert_button.config(text="Converting...", state='disabled')
        self.export_file_button.config(text="Converting...", state='disabled')
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, "Processing MIDI file...\n")
        self.root.update()
        
        # Run conversion in a separate thread to prevent GUI freezing
        Thread(target=self.do_conversion, daemon=True).start()
    
    def convert_and_export(self):
        if not self.validate_inputs():
            return
        
        # Get save filename first
        save_path = self.get_save_filename()
        if not save_path:
            return  # User cancelled
        
        # Disable buttons during conversion
        self.convert_button.config(text="Converting...", state='disabled')
        self.export_file_button.config(text="Converting...", state='disabled')
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, "Processing MIDI file...\n")
        self.root.update()
        
        # Run conversion in a separate thread to prevent GUI freezing
        Thread(target=self.do_conversion, args=(save_path,), daemon=True).start()
    
    def validate_inputs(self):
        if not self.file_path.get():
            messagebox.showerror("Error", "Please select a MIDI file first.")
            return False
        
        if not os.path.isfile(self.file_path.get()):
            messagebox.showerror("Error", f"File '{self.file_path.get()}' not found.")
            return False
        
        return True
    
    def do_conversion(self, save_path=None):
        try:
            # Get parameters
            target_channel = None if self.merge_channels.get() else self.channel.get()
            merge = 1 if self.merge_channels.get() else 0
            reverse = 1 if self.reverse_priority.get() else 0
            old = 1 if self.old_logic.get() else 0
            
            # Extract notes
            extract_fn = extract_monophonic_notes_old if old else extract_monophonic_notes
            notes = extract_fn(
                self.file_path.get(),
                target_channel,
                merge,
                reverse
            )
            
            # Build output based on export type
            speed = 1000 * self.speed.get()
            final = self.format_output(notes, speed)
            
            # Handle outputs
            clipboard_success = False
            file_success = False
            
            # Copy to clipboard if requested
            if self.copy_to_clipboard.get() and not save_path:
                try:
                    pyperclip.copy(final)
                    clipboard_success = True
                except Exception as e:
                    pass  # Handle in completion message
            
            # Save to file if requested or if save_path is provided
            if self.save_to_file.get() or save_path:
                try:
                    file_path = save_path or self.get_save_filename()
                    if file_path:
                        with open(file_path, 'w') as f:
                            f.write(final)
                        file_success = True
                        save_path = file_path
                except Exception as e:
                    save_path = None  # Indicate failure
            
            # Update GUI on main thread
            self.root.after(0, self.conversion_complete, final, len(notes), clipboard_success, file_success, save_path)
            
        except Exception as e:
            self.root.after(0, self.conversion_error, str(e))
    
    def conversion_complete(self, command, note_count, clipboard_success, file_success, save_path):
        self.convert_button.config(text="Convert", state='normal')
        self.export_file_button.config(text="Convert & Export to File", state='normal')
        
        # Show preview (truncated if too long)
        preview = command
        if len(preview) > 2000:
            preview = preview[:2000] + "\n... (truncated)"
        
        export_type_names = {
            "single_line": "Single Line",
            "multi_line_linux": "Multi-line (Linux)",
            "multi_line_windows": "Multi-line (Windows)",
            "arduino_sequential": "Arduino Sequential",
            "arduino_arrays": "Arduino Arrays"
        }
        
        export_name = export_type_names.get(self.export_type.get(), "Unknown")
        
        # Build status message
        status_lines = [
            f"✓ Conversion complete!",
            f"✓ {note_count} notes processed",
            f"✓ Export type: {export_name}"
        ]
        
        if self.copy_to_clipboard.get() and clipboard_success:
            status_lines.append("✓ Copied to clipboard")
        elif self.copy_to_clipboard.get():
            status_lines.append("⚠ Clipboard copy failed")
        
        if save_path:
            status_lines.append(f"✓ Saved to: {save_path}")
        elif self.save_to_file.get():
            status_lines.append("⚠ File save failed or cancelled")
        
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, "\n".join(status_lines) + "\n\n")
        self.output_text.insert(tk.END, f"Output preview:\n{'-'*50}\n{preview}")
        
        # Show success message
        message_parts = [f"Conversion complete!\n{note_count} notes processed."]
        if clipboard_success:
            message_parts.append("Output copied to clipboard.")
        if save_path:
            message_parts.append(f"Output saved to file:\n{save_path}")
        
        messagebox.showinfo("Success", "\n".join(message_parts))
    
    def conversion_error(self, error_msg):
        self.convert_button.config(text="Convert", state='normal')
        self.export_file_button.config(text="Convert & Export to File", state='normal')
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, f"❌ Error: {error_msg}")
        messagebox.showerror("Conversion Error", f"An error occurred:\n{error_msg}")


if __name__ == "__main__":
    root = tk.Tk()
    app = MidiToBeepGUI(root)
    root.mainloop()
