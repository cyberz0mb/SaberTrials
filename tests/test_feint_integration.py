"""Source/ABI boundaries for the isolated candidate; never starts a game."""
import json,re,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/feint-candidate-01'

class Integration(unittest.TestCase):
 def read(self,kind,file):return (OUT/kind/file).read_text()
 def test_disabled_packet_parity_with_accepted_engine(self):
  packets=[]
  for name in ('feint_protocol','feint_legacy_protocol'):
   result=subprocess.run([str(ROOT/'dist/feint-integration-tests/Release'/(name+'.exe'))],check=True,text=True,capture_output=True)
   packets.append([line for line in result.stdout.splitlines() if line.startswith('LEGACY ')])
  self.assertEqual(len(packets[0]),4);self.assertEqual(packets[0],packets[1])
 def test_shared_adapter_and_layout(self):
  for file in ('codemp/game/bg_st_feint.inc','codemp/game/bg_pmove.c','codemp/game/bg_saber.c'):
   self.assertEqual(self.read('game',file),self.read('frontend',file))
  layouts=[]
  for kind in ('engine','game','frontend'):
   s=self.read(kind,'codemp/qcommon/q_shared.h')
   layouts.append(s[s.index('typedef struct playerState_s'):s.index('} playerState_t;')])
  self.assertEqual(layouts[0],layouts[1]);self.assertEqual(layouts[0],layouts[2])
 def test_snapshot_tables(self):
  s=self.read('engine','codemp/qcommon/msg.cpp')
  tables=re.findall(r'netField_t\s+(?:playerStateFields|pilotPlayerStateFields|vehPlayerStateFields)\[\]\s*=\s*\{(.*?)\n\};',s,re.S)
  self.assertEqual(len(tables),4)
  for table in tables:
   active=re.sub(r'//[^\n]*','',table)
   self.assertEqual(len(re.findall(r'PSF\(stCombat\.',active)),16)
   self.assertIn('{ PSF(stCombatFlags), 32 }',active)
   self.assertLessEqual(len(re.findall(r'PSF\(',active)),255)
 def test_only_contact_observation_changes_damage_file(self):
  before=(ROOT/'dist/combat-foundation-01/candidate/game/codemp/game/w_saber.c').read_text()
  after=self.read('game','codemp/game/w_saber.c')
  begin=after.index('    /* Contact precedes damage/defense filtering;')
  end=after.index('\tif ( self->client->ps.saberAttackWound < level.time\n',begin)
  self.assertEqual(after[:begin]+after[end:],before)
  manifest=json.loads((OUT/'manifest.json').read_text())
  for kind,files in manifest['changes'].items():
   self.assertNotIn('codemp/game/g_combat.c',files)
   self.assertFalse(any(f.endswith(('.gla','.glm','.pk3')) for f in files))
 def test_matching_api_gates(self):
  for file,name,n in [('game/g_public.h','GAME_API_VERSION',202),('cgame/cg_public.h','CGAME_API_VERSION',203),('ui/ui_public.h','UI_API_VERSION',204)]:
   for kind in ('engine','game','frontend'):
    self.assertRegex(self.read(kind,'codemp/'+file),r'#define\s+'+name+r'\s+'+str(n)+r'\b')
  for file in ('server/sv_gameapi.cpp','client/cl_cgameapi.cpp','client/cl_uiapi.cpp'):
   s=self.read('engine','codemp/'+file)
   self.assertIn('native modules; legacy modules are not compatible.',s)
   self.assertRegex(s,r'legacy modules are not compatible\."\);\s*return;\s*\w+ = VM_CreateLegacy')
 def test_real_stopped_adapter_is_used(self):
  self.assertIn('#include "g_st_feint.inc"',self.read('game','codemp/game/g_active.c'))
  self.assertEqual(self.read('game','codemp/game/g_st_feint.inc'),(ROOT/'development-source/combat-integration/g_st_feint.inc').read_text())
 def test_default_off_and_capability_checks(self):
  self.assertIn('g_directionalFeints, "0", NULL, CVAR_SERVERINFO|CVAR_LATCH',self.read('game','codemp/game/g_xcvar.h'))
  s=self.read('game','codemp/game/g_client.c')
  self.assertEqual(s.count('strcmp(Info_ValueForKey(userinfo,"st_feintProtocol"),"1")'),2)
  self.assertIn('if(g_directionalFeints.integer && ent->s.number<MAX_CLIENTS',s)
  self.assertIn('Cvar_Get("st_feintProtocol","1",CVAR_ROM|CVAR_USERINFO)',self.read('engine','codemp/client/cl_main.cpp'))
  self.assertIn('if(!s->epoch)return qfalse;',self.read('game','codemp/game/bg_st_feint.inc'))

if __name__=='__main__':unittest.main()
