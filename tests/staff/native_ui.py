"""Exercise only the owned fixture client's protected-backup dialog and media."""
import ctypes as c
from ctypes import wintypes as w
import hashlib,secrets,time

u=c.WinDLL('user32',use_last_error=True)
u.GetDlgItem.argtypes=[w.HWND,c.c_int];u.GetDlgItem.restype=w.HWND
u.SetDlgItemTextW.argtypes=[w.HWND,c.c_int,w.LPCWSTR]
u.SendMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM];u.SendMessageW.restype=w.LPARAM
u.PostMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM]
u.GetWindowLongPtrW.argtypes=[w.HWND,c.c_int];u.GetWindowLongPtrW.restype=c.c_ssize_t
u.GetWindowThreadProcessId.argtypes=[w.HWND,c.POINTER(w.DWORD)]
u.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,c.c_int]
callback=c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
u.EnumWindows.argtypes=[callback,w.LPARAM]

def dialog_for(pid):
    found=[]
    @callback
    def visit(hwnd,arg):
        owner=w.DWORD();u.GetWindowThreadProcessId(hwnd,c.byref(owner))
        if owner.value==pid:
            title=c.create_unicode_buffer(256);u.GetWindowTextW(hwnd,title,256)
            if title.value=='Saber Trials protected backup':found.append(hwnd)
        return True
    u.EnumWindows(visit,0)
    return found[0] if found else None

def answer(n,i,passphrase,confirm=False):
    n.until(lambda:dialog_for(n.clients[i].pid),8,'owned protected-backup dialog')
    hwnd=dialog_for(n.clients[i].pid)
    for control in (101,102) if confirm else (101,):
        edit=u.GetDlgItem(hwnd,control);assert edit and u.GetWindowLongPtrW(edit,-16)&0x20
        assert u.SendMessageW(edit,0xD2,0,0)!=0 # EM_GETPASSWORDCHAR
        # Drive character input; cross-process WM_SETTEXT is not reliable for these password controls.
        for character in passphrase:assert u.PostMessageW(edit,0x102,ord(character),0)
    assert u.PostMessageW(u.GetDlgItem(hwnd,1),0xF5,0,0) # BM_CLICK, owned Continue button.
    n.until(lambda:not dialog_for(n.clients[i].pid),8,'backup dialog completion')

def backup_and_media(n):
    n.client(0);n.client(1)
    backup=n.run/'portable.key';passphrase=secrets.token_urlsafe(28)
    start=len(n.log(0));n.input(0,'staff export "'+str(backup)+'"');answer(n,0,passphrase,True)
    n.until(lambda:'Staff backup: completed' in n.log(0)[start:],15,'native backup export')
    encrypted=backup.read_bytes();assert passphrase.encode() not in encrypted
    first_hash=hashlib.sha256(encrypted).hexdigest()
    start=len(n.log(0));n.input(0,'staff export "'+str(backup)+'"');answer(n,0,passphrase,True)
    n.until(lambda:'Staff backup: failed' in n.log(0)[start:],15,'backup overwrite refused')
    assert hashlib.sha256(backup.read_bytes()).hexdigest()==first_hash
    original=n.private/'client1/SaberTrialsStaff/client/identity.key';original_hash=hashlib.sha256(original.read_bytes()).hexdigest()
    start=len(n.log(1));n.input(1,'staff import "'+str(backup)+'"');answer(n,1,secrets.token_urlsafe(28))
    n.until(lambda:'Staff backup: failed' in n.log(1)[start:],15,'wrong backup passphrase refused')
    assert hashlib.sha256(original.read_bytes()).hexdigest()==original_hash
    start=len(n.log(1));n.input(1,'staff import "'+str(backup)+'"');answer(n,1,passphrase)
    n.until(lambda:'Staff backup: completed' in n.log(1)[start:],15,'identity import')
    n.action(1,'staff identity',n.ids['client0']);n.action(1,'staff login','authenticated')
    n.action(1,'staff whoami','\nOwner\n')
    n.action(1,'staff identity',n.ids['client0'])
    assert all(passphrase not in n.log(i) for i in (0,1))
    n.check('real masked export/import dialogs, no overwrite, wrong-passphrase preservation and imported Owner login')
    n.close_menus(0);n.input(0,'record staff-regression');time.sleep(.5)
    n.action(0,'staff logout','Logged out');n.action(0,'staff login','authenticated')
    n.action(0,'ghost on','completed');n.action(0,'ghost off','Ghost off')
    n.input(0,'stoprecord')
    demos=list((n.run/'client0-home/SaberTrials/demos').glob('staff-regression.*'))
    assert len(demos)==1 and demos[0].stat().st_size>1000
    data=demos[0].read_bytes()
    assert not any(keyword in data for keyword in (b'sthello ',b'stproof ',b'stsession ',b'staction ',passphrase.encode()))
    n.check('ordinary record/stoprecord creates a demo without staff authentication exchanges')
    n.input(0,'team spectator');n.close_menus(0);n.input(0,'st_photo')
    view,_=n.view(0);assert view['photo']==1,view
    n.input(0,'st_photoCapture');time.sleep(.5);n.input(0,'st_photo')
    view,_=n.view(0);assert view['photo']==0,view
    assert list((n.run/'client0-home/SaberTrials/screenshots').glob('*'))
    n.check('spectator Photo Mode still enters, captures and exits')
