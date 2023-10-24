from astropy import units as u
from astropy.coordinates import SkyCoord
import numpy as np
import pandas as pd
from itertools import groupby


def split_condition(x):
    return x in {''}

class Person:
  def __init__(self, name, ra, dec, ):
    self.name = name
    self.ra = ra
    self.dec = dec


# should take as input astropy coordinates for the target of interest
def find_phase_calibrator(source_coordinates, band):

    cal_database = open('../data/VLA_Calibratorlist.dat', 'r')
    cal_lines = cal_database.readlines()
    cal_lines = [s.strip() for s in cal_lines]
    grouper = groupby(cal_lines, key=split_condition)
    # convert to dictionary via enumerate
    grouped_cal_lines = dict(enumerate((list(j) for i, j in grouper if not i), 0))

    separation = np.inf
    for key in grouped_cal_lines:
        source_meta = grouped_cal_lines[key][0].split()
        name = source_meta[0]
        RA = source_meta[3].replace('m', 'h').replace('s', '').split('h')
        Dec = source_meta[4].replace('\'', 'd').replace('\"', '').split('d')
        source_skycoords = SkyCoord(' '.join(RA) + ' ' + ' '.join(Dec), unit=(u.hourangle, u.deg))
        body = [line for line in grouped_cal_lines[key][5:] if '=' not in line]
        body = [line.split() for line in body]
        body = pd.DataFrame(body)
        if body.empty: continue
        body = body.rename(columns={0:'band', 1:'band_id', 2:'A', 3:'B', 4:'C', 5:'D', 6:'flux'})
        body = body.astype({'band':str, 'band_id':str, 'A':str, 'B':str, 'C':str, 'D':str, 'flux':float})
        body.attrs['name'] = name
        body.attrs['source_skycoords'] = source_skycoords
        print(body)
        if (source_coordinates.separation(body.attrs['source_skycoords']) < separation) & (band in body['band_id'].values) & (('S' in body['D'][body['band_id'] == band].values) or ('P' in body['D'][body['band_id'] == band].values) and (body['flux'][body['band_id'] == band].values > 1)):
            separation = source_coordinates.separation(body.attrs['source_skycoords'])
            print(body.attrs['name'], source_coordinates.separation(body.attrs['source_skycoords']).deg, body['flux'].values[body['band_id'] == band])

    return(None)

test_source = SkyCoord('17 27 43.31 -16 12 19.23', unit=(u.hourangle, u.deg))
band = 'L'
find_phase_calibrator(test_source, band)
