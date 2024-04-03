#####../data/sn2023mut_spw0/sn2023mut_spw0.ms#####
wsclean -niter 1000 -size 1024 1024 -scale 7.3629502537654155asec -field 2 -reorder -name ../data/sn2023mut_spw0/IMAGES/2_automask -data-column CORRECTED_DATA ../data/sn2023mut_spw0/sn2023mut_spw0.ms
wsclean -niter 1000 -size 1024 1024 -scale 7.3629502537654155asec -field 0 -reorder -name ../data/sn2023mut_spw0/IMAGES/0_automask -data-column CORRECTED_DATA ../data/sn2023mut_spw0/sn2023mut_spw0.ms
wsclean -niter 1000 -size 1024 1024 -scale 7.3629502537654155asec -field 1 -reorder -name ../data/sn2023mut_spw0/IMAGES/1_automask -data-column CORRECTED_DATA ../data/sn2023mut_spw0/sn2023mut_spw0.ms
#####../data/sn2023mut_spw1/sn2023mut_spw1.ms#####
wsclean -niter 1000 -size 1024 1024 -scale 4.4814512795885575asec -field 2 -reorder -name ../data/sn2023mut_spw1/IMAGES/2_automask -data-column CORRECTED_DATA ../data/sn2023mut_spw1/sn2023mut_spw1.ms
wsclean -niter 1000 -size 1024 1024 -scale 4.4814512795885575asec -field 0 -reorder -name ../data/sn2023mut_spw1/IMAGES/0_automask -data-column CORRECTED_DATA ../data/sn2023mut_spw1/sn2023mut_spw1.ms
wsclean -niter 1000 -size 1024 1024 -scale 4.4814512795885575asec -field 1 -reorder -name ../data/sn2023mut_spw1/IMAGES/1_automask -data-column CORRECTED_DATA ../data/sn2023mut_spw1/sn2023mut_spw1.ms
wsclean -niter 1000 -size 1024 1024 -scale 4.4814512795885575asec -field 2 -reorder -name ../data/sn2023mut_spw1/IMAGES/2_automask_deep -data-column CORRECTED_DATA ../data/sn2023mut_spw0/sn2023mut_spw0.ms ../data/sn2023mut_spw1/sn2023mut_spw1.ms
