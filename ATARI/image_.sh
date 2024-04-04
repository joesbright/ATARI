#####../data/sn2024ehs_spw0/sn2024ehs_spw0.ms#####
wsclean -niter 1000 -size 1024 1024 -scale 22.10187764090027asec -field 2 -reorder -name ../data/sn2024ehs_spw0/IMAGES/2_automask -data-column CORRECTED_DATA ../data/sn2024ehs_spw0/sn2024ehs_spw0.ms
wsclean -niter 1000 -size 1024 1024 -scale 22.10187764090027asec -field 0 -reorder -name ../data/sn2024ehs_spw0/IMAGES/0_automask -data-column CORRECTED_DATA ../data/sn2024ehs_spw0/sn2024ehs_spw0.ms
wsclean -niter 1000 -size 1024 1024 -scale 22.10187764090027asec -field 1 -reorder -name ../data/sn2024ehs_spw0/IMAGES/1_automask -data-column CORRECTED_DATA ../data/sn2024ehs_spw0/sn2024ehs_spw0.ms
#####../data/sn2024ehs_spw1/sn2024ehs_spw1.ms#####
wsclean -niter 1000 -size 1024 1024 -scale 9.665296393089932asec -field 2 -reorder -name ../data/sn2024ehs_spw1/IMAGES/2_automask -data-column CORRECTED_DATA ../data/sn2024ehs_spw1/sn2024ehs_spw1.ms
wsclean -niter 1000 -size 1024 1024 -scale 9.665296393089932asec -field 0 -reorder -name ../data/sn2024ehs_spw1/IMAGES/0_automask -data-column CORRECTED_DATA ../data/sn2024ehs_spw1/sn2024ehs_spw1.ms
wsclean -niter 1000 -size 1024 1024 -scale 9.665296393089932asec -field 1 -reorder -name ../data/sn2024ehs_spw1/IMAGES/1_automask -data-column CORRECTED_DATA ../data/sn2024ehs_spw1/sn2024ehs_spw1.ms
wsclean -niter 1000 -size 1024 1024 -scale 9.665296393089932asec -field 2 -reorder -name ../data/sn2024ehs_spw1/IMAGES/2_automask_deep -data-column CORRECTED_DATA ../data/sn2024ehs_spw0/sn2024ehs_spw0.ms ../data/sn2024ehs_spw1/sn2024ehs_spw1.ms
