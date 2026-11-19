"""Load the compiled game library and inspect public APIs, without starting JKA."""
import ctypes as c
import sys

class AccountAPI(c.Structure):
    _fields_=[('version',c.c_int),('size',c.c_uint),('set',c.c_void_p),('clear',c.c_void_p),('snapshot',c.c_void_p)]

class StaffAPI(c.Structure):
    _fields_=[('version',c.c_int),('size',c.c_uint),('execute',c.c_void_p),('resolve',c.c_void_p),('revoke',c.c_void_p),('reset',c.c_void_p)]

Role=c.CFUNCTYPE(c.c_int,c.c_int)
Generation=c.CFUNCTYPE(c.c_int,c.c_int,c.c_void_p)
class Imports(c.Structure):
    _fields_=[('version',c.c_int),('size',c.c_uint),('role',Role),('generation',Generation)]

game=c.CDLL(sys.argv[1])
assert game.GetModuleAPI
game.GetSaberTrialsEventAccountAPI.restype=c.POINTER(AccountAPI)
a=game.GetSaberTrialsEventAccountAPI().contents
assert a.version==1 and a.size==c.sizeof(AccountAPI) and a.set and a.clear and a.snapshot
game.GetSaberTrialsStaffAPI.restype=c.POINTER(StaffAPI)
game.GetSaberTrialsStaffAPI.argtypes=[c.POINTER(Imports)]
assert not game.GetSaberTrialsStaffAPI(None)
imports=Imports(2,c.sizeof(Imports),Role(lambda slot:0),Generation(lambda slot,output:0))
s=game.GetSaberTrialsStaffAPI(c.byref(imports)).contents
assert s.version==2 and s.size==c.sizeof(StaffAPI) and s.execute and s.resolve and s.revoke and s.reset
print('Compiled Linux game library loads and exports compatible game, staff and account APIs. No game server was started.')
