"""Read-only Windows Restart Manager inventory for the isolated QA executable."""
import ctypes as c
from ctypes import wintypes as w
from pathlib import Path

class Unique(c.Structure):
    _fields_=[('pid',w.DWORD),('started',w.FILETIME)]
class Process(c.Structure):
    _fields_=[('process',Unique),('name',w.WCHAR*256),('service',w.WCHAR*64),
              ('type',c.c_int),('status',w.ULONG),('session',w.DWORD),('restartable',w.BOOL)]

dll=c.WinDLL('rstrtmgr');session=w.DWORD();key=c.create_unicode_buffer(33)
code=dll.RmStartSession(c.byref(session),0,key)
if code:raise OSError(code,'RmStartSession')
try:
    path=str(Path(__file__).resolve().parents[1]/'dist/staff-build-qa/Release/openjkded.x86_64.exe')
    files=(w.LPCWSTR*1)(path)
    code=dll.RmRegisterResources(session,1,files,0,None,0,None)
    if code:raise OSError(code,'RmRegisterResources')
    needed=w.UINT();count=w.UINT();reason=w.DWORD()
    code=dll.RmGetList(session,c.byref(needed),c.byref(count),None,c.byref(reason))
    if code==234:
        count.value=needed.value;items=(Process*needed.value)()
        code=dll.RmGetList(session,c.byref(needed),c.byref(count),items,c.byref(reason))
        if not code:
            for item in items[:count.value]:print(item.process.pid,item.name,item.service)
    print('Restart Manager result:',code,'owners:',needed.value,'reboot reasons:',reason.value)
finally:dll.RmEndSession(session)
