"""Developer conversion of the pinned OPUS Korean model; no downloaded code runs."""
from pathlib import Path
import shutil
import sys
from ctranslate2.converters import MarianConverter

source,target=map(Path,sys.argv[1:3])
MarianConverter(str(next(source.glob('*.npz'))),[str(next(source.glob('*.vocab.yml')))]).convert(
    str(target/'model'),quantization='int8',force=True)
for original,name in [('source.spm','source.model'),('target.spm','target.model'),('README.md','README.md'),('LICENSE','LICENSE.txt')]:
    shutil.copyfile(source/original,target/name)
(target/'ATTRIBUTION.txt').write_text('OPUS-MT Korean to English, Helsinki-NLP / Language Technology Research Group, University of Helsinki.\n'
    'Source: https://object.pouta.csc.fi/OPUS-MT-models/ko-en/opus-2019-12-18.zip\n'
    'License: CC-BY-4.0; see LICENSE.txt. Converted by Saber Trials to CTranslate2 int8; model weights quantized.\n',encoding='utf8')
