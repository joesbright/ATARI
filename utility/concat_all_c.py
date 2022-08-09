from pyuvdata import UVData
import sys

base = sys.argv[1]

uv1, uv2, uv3, uv4, uv5, uv6, uv7 = UVData(), UVData(), UVData(), UVData(), UVData(), UVData(), UVData()

uv1.read("seti-node5/"+base+"_0.uvh5", fix_old_proj=False)
uv2.read("seti-node5/"+base+"_1.uvh5", fix_old_proj=False)
uv3.read("seti-node6/"+base+"_0.uvh5", fix_old_proj=False)
uv4.read("seti-node6/"+base+"_1.uvh5", fix_old_proj=False)
uv5.read("seti-node7/"+base+"_0.uvh5", fix_old_proj=False)
uv6.read("seti-node7/"+base+"_1.uvh5", fix_old_proj=False)
uv7.read("seti-node8/"+base+"_0.uvh5", fix_old_proj=False)

uvd = uv1 + uv2 + uv3 + uv4 + uv5 + uv6 + uv7

uvd.write_ms(base + '_b.ms')
uvd.write_uvh5(base + '_b.uvh5')
