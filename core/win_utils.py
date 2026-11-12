"""
Windows Native Utilities for Gallery Cube.
Provides 64-bit memory-safe Clipboard image copying (Ctrl+C)
and Windows Recycle Bin file deletion (Delete key) using pure Windows API.
"""
import io
import ctypes
from ctypes import wintypes
from PIL import Image


def copy_image_to_clipboard(pil_img: Image.Image) -> bool:
    """Copies PIL Image to Windows Clipboard as DIB so it can be pasted anywhere."""
    try:
        output = io.BytesIO()
        pil_img.convert("RGB").save(output, "BMP")
        # Strip 14-byte BMP file header to get CF_DIB payload
        data = output.getvalue()[14:]
        output.close()

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
        kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]

        user32.OpenClipboard.argtypes = [wintypes.HWND]
        user32.SetClipboardData.restype = wintypes.HANDLE
        user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]

        CF_DIB = 8
        if not user32.OpenClipboard(None):
            return False

        try:
            user32.EmptyClipboard()
            GMEM_MOVEABLE = 0x0002
            h_glob = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if not h_glob:
                return False
            p_glob = kernel32.GlobalLock(h_glob)
            if not p_glob:
                return False
            ctypes.memmove(p_glob, data, len(data))
            kernel32.GlobalUnlock(h_glob)
            user32.SetClipboardData(CF_DIB, h_glob)
            return True
        finally:
            user32.CloseClipboard()
    except Exception:
        return False


def send_to_recycle_bin(filepath: str) -> bool:
    """Sends a file to the Windows Recycle Bin (can be undone with Ctrl+Z in Explorer)."""
    try:
        class SHFILEOPSTRUCT(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("wFunc", wintypes.UINT),
                ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR),
                ("fFlags", ctypes.c_ushort),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", wintypes.LPCWSTR)
            ]

        file_op = SHFILEOPSTRUCT()
        file_op.hwnd = None
        file_op.wFunc = 3  # FO_DELETE
        file_op.pFrom = filepath + "\0"  # Double null-terminated
        file_op.pTo = None
        file_op.fFlags = 0x0040  # FOF_ALLOWUNDO (Recycle Bin)

        res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(file_op))
        return res == 0
    except Exception:
        return False

