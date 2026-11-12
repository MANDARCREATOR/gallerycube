"""
Video Player Viewport & Control Bar for Gallery Cube.
Smooth video playback, interactive timeline scrubber, speed control, loop,
and 1-click snapshot frame extraction to the photo editor.
"""
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional, Callable
from PIL import Image, ImageTk
import customtkinter as ctk

from core.video_engine import VideoEngine


class VideoPlayerView(ctk.CTkFrame):
    def __init__(self, master, on_edit_frame: Optional[Callable[[Image.Image, str], None]] = None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_edit_frame = on_edit_frame

        self.engine = VideoEngine()
        self.is_playing = False
        self.loop = True
        self.speed_factor = 1.0
        self.is_scrubbing = False

        self.current_tk_img: Optional[ImageTk.PhotoImage] = None
        self._timer_id = None

        self._build_ui()

    def _build_ui(self):
        # 1. Video Canvas
        self.canvas = tk.Canvas(
            self,
            bg="#050811",
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<Button-1>", lambda e: self.toggle_play_pause())

        # 2. Control Bar at Bottom
        self.ctrl_bar = ctk.CTkFrame(self, height=54, fg_color="#0f172a", corner_radius=0)
        self.ctrl_bar.pack(fill="x", side="bottom")

        # Top line of control bar: Seek Scrubber
        scrub_frame = ctk.CTkFrame(self.ctrl_bar, fg_color="transparent")
        scrub_frame.pack(fill="x", padx=12, pady=(6, 2))

        self.time_lbl_curr = ctk.CTkLabel(
            scrub_frame,
            text="00:00",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#e2e8f0"
        )
        self.time_lbl_curr.pack(side="left", padx=(0, 8))

        self.scrub_slider = ctk.CTkSlider(
            scrub_frame,
            from_=0.0,
            to=1.0,
            number_of_steps=1000,
            command=self._on_scrub,
            button_color="#4f46e5",
            progress_color="#6366f1",
            height=14
        )
        self.scrub_slider.set(0.0)
        self.scrub_slider.pack(side="left", fill="x", expand=True)
        self.scrub_slider.bind("<ButtonPress-1>", lambda e: setattr(self, "is_scrubbing", True))
        self.scrub_slider.bind("<ButtonRelease-1>", self._on_scrub_release)

        self.time_lbl_total = ctk.CTkLabel(
            scrub_frame,
            text="00:00",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.time_lbl_total.pack(side="left", padx=(8, 0))

        # Bottom line: Play buttons, speed, loop, snapshot
        btn_row = ctk.CTkFrame(self.ctrl_bar, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(2, 8))

        # Play / Pause
        self.btn_play = ctk.CTkButton(
            btn_row,
            text="▶ Play",
            command=self.toggle_play_pause,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            width=70,
            height=28,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.btn_play.pack(side="left", padx=(0, 6))

        # Step back 1 sec
        btn_back = ctk.CTkButton(
            btn_row,
            text="⏪ -1s",
            command=lambda: self.step_seconds(-1.0),
            fg_color="#1e293b",
            hover_color="#334155",
            width=50,
            height=28,
            font=ctk.CTkFont(size=10)
        )
        btn_back.pack(side="left", padx=2)

        # Step forward 1 sec
        btn_fwd = ctk.CTkButton(
            btn_row,
            text="+1s ⏩",
            command=lambda: self.step_seconds(1.0),
            fg_color="#1e293b",
            hover_color="#334155",
            width=50,
            height=28,
            font=ctk.CTkFont(size=10)
        )
        btn_fwd.pack(side="left", padx=2)

        # Loop checkbox
        self.check_loop = ctk.CTkCheckBox(
            btn_row,
            text="Loop",
            font=ctk.CTkFont(size=11),
            checkbox_height=16,
            checkbox_width=16,
            command=self._on_toggle_loop
        )
        self.check_loop.select()
        self.check_loop.pack(side="left", padx=10)

        # Speed Menu
        lbl_spd = ctk.CTkLabel(btn_row, text="Speed:", font=ctk.CTkFont(size=10), text_color="#94a3b8")
        lbl_spd.pack(side="left", padx=(6, 2))

        self.speed_menu = ctk.CTkOptionMenu(
            btn_row,
            values=["0.5x", "1.0x", "1.25x", "1.5x", "2.0x"],
            command=self._on_speed_change,
            width=70,
            height=26,
            font=ctk.CTkFont(size=10)
        )
        self.speed_menu.set("1.0x")
        self.speed_menu.pack(side="left", padx=2)

        # Right side: Frame extraction buttons
        btn_edit_frame = ctk.CTkButton(
            btn_row,
            text="✏️ Edit Frame in Studio",
            command=self._handle_edit_frame,
            fg_color="#059669",
            hover_color="#047857",
            height=28,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        btn_edit_frame.pack(side="right", padx=(4, 0))

        btn_save_frame = ctk.CTkButton(
            btn_row,
            text="📸 Save Frame",
            command=self._handle_save_frame,
            fg_color="#1e293b",
            hover_color="#334155",
            height=28,
            font=ctk.CTkFont(size=11)
        )
        btn_save_frame.pack(side="right", padx=4)

    def load_video_file(self, file_path: str) -> Tuple[bool, str]:
        """Loads video file into player."""
        self.stop()
        ok, msg = self.engine.load_video(file_path)
        if not ok:
            return False, msg

        self.time_lbl_curr.configure(text="00:00")
        self.time_lbl_total.configure(text=self.engine.formatted_total_time)
        self.scrub_slider.set(0.0)
        self._render_current_frame()
        return True, msg

    def _render_current_frame(self):
        """Draws the active video frame on the canvas preserving aspect ratio."""
        self.canvas.delete("all")
        frame = self.engine.current_pil_frame
        if not frame:
            return

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 10 or ch <= 10:
            return

        img_w, img_h = frame.size
        scale = min((cw - 20) / img_w, (ch - 20) / img_h)
        disp_w = max(1, int(img_w * scale))
        disp_h = max(1, int(img_h * scale))

        resized = frame.resize((disp_w, disp_h), Image.Resampling.BILINEAR)
        self.current_tk_img = ImageTk.PhotoImage(resized)

        pos_x = (cw - disp_w) // 2
        pos_y = (ch - disp_h) // 2

        self.canvas.create_image(pos_x, pos_y, anchor=tk.NW, image=self.current_tk_img)

    def _on_canvas_resize(self, event):
        self._render_current_frame()

    def toggle_play_pause(self):
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def play(self):
        if not self.engine.cap or not self.engine.cap.isOpened():
            return
        self.is_playing = True
        self.btn_play.configure(text="⏸ Pause", fg_color="#e11d48", hover_color="#be123c")
        self._schedule_next_frame()

    def pause(self):
        self.is_playing = False
        self.btn_play.configure(text="▶ Play", fg_color="#4f46e5", hover_color="#4338ca")
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None

    def stop(self):
        self.pause()
        self.engine.close()

    def _schedule_next_frame(self):
        if not self.is_playing:
            return

        frame = self.engine.read_next_frame()
        if frame is None:
            # End of video reached
            if self.loop:
                self.engine.seek_to_frame(0)
                self._render_current_frame()
            else:
                self.pause()
                return
        else:
            self._render_current_frame()

        # Update time indicators
        if not self.is_scrubbing and self.engine.total_frames > 0:
            ratio = self.engine.current_frame_idx / self.engine.total_frames
            self.scrub_slider.set(ratio)
            self.time_lbl_curr.configure(text=self.engine.formatted_current_time)

        # Interval calculation based on FPS and speed multiplier
        delay_ms = int(max(5, (1000.0 / (self.engine.fps * self.speed_factor))))
        self._timer_id = self.after(delay_ms, self._schedule_next_frame)

    def _on_scrub(self, val):
        self.is_scrubbing = True
        self.engine.seek_to_ratio(float(val))
        self.time_lbl_curr.configure(text=self.engine.formatted_current_time)
        self._render_current_frame()

    def _on_scrub_release(self, event):
        self.is_scrubbing = False

    def step_seconds(self, delta_sec: float):
        target_sec = max(0.0, min(self.engine.duration_seconds, self.engine.current_time_seconds + delta_sec))
        if self.engine.duration_seconds > 0:
            ratio = target_sec / self.engine.duration_seconds
            self.scrub_slider.set(ratio)
            self.engine.seek_to_ratio(ratio)
            self.time_lbl_curr.configure(text=self.engine.formatted_current_time)
            self._render_current_frame()

    def _on_toggle_loop(self):
        self.loop = bool(self.check_loop.get())

    def _on_speed_change(self, choice: str):
        val = choice.replace("x", "")
        try:
            self.speed_factor = float(val)
        except Exception:
            self.speed_factor = 1.0

    def _handle_save_frame(self):
        frame = self.engine.current_pil_frame
        if not frame:
            messagebox.showinfo("No Frame", "No active video frame available.")
            return

        out_path = filedialog.asksaveasfilename(
            title="Save Video Snapshot Frame",
            initialfile="video_frame.png",
            filetypes=[("PNG Image", "*.png"), ("JPEG Photo", "*.jpg")]
        )
        if out_path:
            frame.save(out_path)
            messagebox.showinfo("Frame Saved", f"Saved video frame snapshot to:\n{out_path}")

    def _handle_edit_frame(self):
        frame = self.engine.current_pil_frame
        if not frame:
            messagebox.showinfo("No Frame", "No active video frame available.")
            return
        if self.on_edit_frame:
            sec_str = self.engine.formatted_current_time.replace(":", "m") + "s"
            frame_title = f"{os.path.basename(self.engine.file_path or 'video')}_frame_{sec_str}"
            self.on_edit_frame(frame, frame_title)

