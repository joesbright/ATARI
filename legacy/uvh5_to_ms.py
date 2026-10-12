# convert ATA uvh5 data to casa measure set format and concat into a single measure set
import os
import glob as glob

concat_b = 'concat_all_b.py'
concat_c = 'concat_all_c.py'

for uvh5_folder in glob.glob('uvh5*'):
    os.system('python3.8 ' + concat_b + ' ' + uvh5_folder + '/' + uvh5_folder)
    os.system('python3.8 ' + concat_c + ' ' + uvh5_folder + '/' + uvh5_folder)

mymss = glob.glob('uvh5*/*.ms')

source_names = set([item.split('_')[4] for item in mymss])
outmsname = '_'.join(source_names) + '.ms'

concat(vis=mymss, concatvis=outmsname, timesort=True)