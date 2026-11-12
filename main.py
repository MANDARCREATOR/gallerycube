"""
Gallery Cube 🧊 — Universal Media Studio (Photos & Videos)
Entry point for Windows Desktop Application.
Supports direct double-click launch from Windows File Explorer.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow


def main():
    # Enable Windows High-DPI Awareness
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = MainWindow()

    # If launched by double-clicking a file in Windows File Explorer
    if len(sys.argv) > 1:
        initial_file = os.path.abspath(sys.argv[1])
        if os.path.exists(initial_file):
            directory = os.path.dirname(initial_file)
            def _open_startup_file():
                # 1. Load active file FIRST so it displays instantly on screen (<50ms)
                app.load_media_path(initial_file)
                # 2. Fast non-blocking folder indexing
                app.after(30, lambda: app._load_album_from_dir(directory, active_file=initial_file))
            app.after(50, _open_startup_file)
    else:
        # If launched directly without file arguments on first run
        from core.config_manager import is_first_run
        if is_first_run():
            app.after(400, app.open_first_run_dialog)

    app.mainloop()


if __name__ == "__main__":
    main()
