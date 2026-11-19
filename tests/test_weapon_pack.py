from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=spec_from_file_location('weapon_pack',ROOT/'tools/Check-Weapon-Pack.py')
pack=module_from_spec(spec)
spec.loader.exec_module(pack)
MINIMUM='''weapon { version 1 id test_gun name "Test gun" baseWeapon blaster
viewModel models/st_dlc/test/view.md3 worldModel models/st_dlc/test/world.glm }'''


class WeaponPackTests(unittest.TestCase):
    def test_supported_families(self):
        for family in pack.FAMILIES:
            self.assertEqual(pack.definition(MINIMUM.replace('baseWeapon blaster','baseWeapon '+family))['baseWeapon'],family)

    def test_invalid_definitions(self):
        for text in (MINIMUM+'extra',MINIMUM.replace('version 1','version 2'),
                     MINIMUM.replace('baseWeapon blaster','baseWeapon saber'),
                     MINIMUM.replace('test_gun','../test'),MINIMUM.replace('}', 'damage 1000 }'),
                     MINIMUM.replace('}', 'version 1 }'),MINIMUM.replace('view.md3','../../view.md3')):
            with self.assertRaises(ValueError): pack.definition(text)

    def test_release_and_fallback_packs(self):
        with TemporaryDirectory() as temp:
            path=Path(temp)/'test.pk3'
            with ZipFile(path,'w') as archive:
                archive.writestr('ext_data/st_weapons/test.weapon',MINIMUM)
                archive.writestr('models/st_dlc/test/view.md3',b'fixture')
                archive.writestr('models/st_dlc/test/world.glm',b'fixture')
            errors,warnings=pack.check(path)
            self.assertFalse(errors)
            self.assertEqual(len(warnings),8)
            with ZipFile(path,'a') as archive:
                archive.writestr('models/weapons2/blaster_r/blaster.md3',b'bad override')
                archive.writestr('jampgamex86_64.dll',b'bad executable')
                archive.writestr('ext_data/st_weapons/duplicate.weapon',MINIMUM)
            errors,_=pack.check(path)
            self.assertTrue(any('Stock replacement' in error for error in errors))
            self.assertTrue(any('code/configuration' in error for error in errors))
            self.assertTrue(any('Duplicate weapon id' in error for error in errors))


if __name__=='__main__': unittest.main()
