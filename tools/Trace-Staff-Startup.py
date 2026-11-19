"""Bounded debugger for an isolated test-server startup; no memory dump or secrets."""
import ctypes as c
from ctypes import wintypes as w
import importlib.util
from pathlib import Path
import struct
import subprocess
import time
import threading

ROOT = Path(__file__).resolve().parents[1]
k = c.WinDLL('kernel32', use_last_error=True)
d = c.WinDLL('dbghelp', use_last_error=True)

class Event(c.Structure):
    _fields_ = [('code', w.DWORD), ('pid', w.DWORD), ('tid', w.DWORD),
                ('alignment', w.DWORD), ('data', c.c_ubyte * 160)]

class Address(c.Structure):
    _fields_ = [('offset', c.c_uint64), ('segment', w.WORD), ('mode', w.DWORD)]

class Stack(c.Structure):
    _fields_ = [('pc', Address), ('ret', Address), ('frame', Address),
                ('stack', Address), ('backing', Address), ('rest', c.c_ubyte * 512)]

k.WaitForDebugEvent.argtypes = [c.POINTER(Event), w.DWORD]
k.ContinueDebugEvent.argtypes = [w.DWORD, w.DWORD, w.DWORD]
k.OpenThread.argtypes = [w.DWORD, w.BOOL, w.DWORD]
k.OpenThread.restype = w.HANDLE
k.GetThreadContext.argtypes = [w.HANDLE, c.c_void_p]
k.CloseHandle.argtypes = [w.HANDLE]
d.SymInitialize.argtypes = [w.HANDLE, c.c_char_p, w.BOOL]
d.SymRefreshModuleList.argtypes = [w.HANDLE]
d.SymFromAddr.argtypes = [w.HANDLE, c.c_uint64, c.POINTER(c.c_uint64), c.c_void_p]
d.StackWalk64.argtypes = [w.DWORD, w.HANDLE, w.HANDLE, c.POINTER(Stack), c.c_void_p,
                         c.c_void_p, c.c_void_p, c.c_void_p, c.c_void_p]
d.SymCleanup.argtypes = [w.HANDLE]

def trace(process, log):
    handle = w.HANDLE(int(process._handle))
    d.SymInitialize(handle, None, True)
    deadline = time.monotonic() + 25
    try:
        while time.monotonic() < deadline:
            event = Event()
            if not k.WaitForDebugEvent(c.byref(event), 500):
                continue
            status = 0x10002
            if event.code == 1:
                data = bytes(event.data)
                code, = struct.unpack_from('<I', data)
                if code == 0xc0000005:
                    address, = struct.unpack_from('<Q', data, 16)
                    log.write(f'Access violation at {address:#x}\n')
                    thread = k.OpenThread(0x1fffff, False, event.tid)
                    context = c.create_string_buffer(4096)
                    struct.pack_into('<I', context, 48, 0x10000b)
                    if not k.GetThreadContext(thread, context):
                        raise c.WinError(c.get_last_error())
                    stack = Stack()
                    stack.pc.offset = struct.unpack_from('<Q', context, 248)[0]
                    stack.stack.offset = struct.unpack_from('<Q', context, 152)[0]
                    stack.frame.offset = struct.unpack_from('<Q', context, 160)[0]
                    stack.pc.mode = stack.stack.mode = stack.frame.mode = 3
                    d.SymRefreshModuleList(handle)
                    for _ in range(32):
                        if not d.StackWalk64(0x8664, handle, thread, c.byref(stack), context,
                                             None, c.cast(d.SymFunctionTableAccess64, c.c_void_p),
                                             c.cast(d.SymGetModuleBase64, c.c_void_p), None):
                            break
                        symbol = c.create_string_buffer(1100)
                        struct.pack_into('<I', symbol, 0, 88)
                        struct.pack_into('<I', symbol, 80, 1000)
                        offset = c.c_uint64()
                        if d.SymFromAddr(handle, stack.pc.offset, c.byref(offset), symbol):
                            name = symbol.raw[84:].split(b'\0')[0].decode(errors='replace')
                            log.write(f'{stack.pc.offset:#x} {name}+{offset.value:#x}\n')
                        else:
                            log.write(f'{stack.pc.offset:#x} (no symbol)\n')
                        if not stack.ret.offset:
                            break
                    k.CloseHandle(thread)
                    return
                if code != 0x80000003:
                    status = 0x80010001
            elif event.code == 6:
                file_handle, = struct.unpack_from('<Q', bytes(event.data))
                if file_handle:
                    k.CloseHandle(w.HANDLE(file_handle))
            elif event.code == 5:
                log.write('Process exited\n')
                return
            k.ContinueDebugEvent(event.pid, event.tid, status)
        log.write('No crash during bounded observation\n')
    finally:
        d.SymCleanup(handle)
        if process.poll() is None:
            process.terminate()

def main():
    spec = importlib.util.spec_from_file_location('staff_test', ROOT/'tools/Test-Staff.py')
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    native = harness.Native()
    original = subprocess.Popen
    def debug_launch(*args, **kwargs):
        kwargs['creationflags'] = 2 | 0x08000000  # DEBUG_ONLY_THIS_PROCESS, CREATE_NO_WINDOW
        kwargs['env']['_NO_DEBUG_HEAP'] = '1'
        process = original(*args, **kwargs)
        stop = threading.Event()
        def probe():
            while not stop.is_set():
                native.command('staff serverkey')
                stop.wait(.2)
        worker = threading.Thread(target=probe, daemon=True)
        worker.start()
        with (native.run/'startup-stack.txt').open('w') as log:
            trace(process, log)
        stop.set()
        worker.join(1)
        return process
    subprocess.Popen = debug_launch
    try:
        native.server()
    except AssertionError:
        print((native.run/'startup-stack.txt').read_text())
    finally:
        subprocess.Popen = original
        native.close()

if __name__ == '__main__':
    main()
