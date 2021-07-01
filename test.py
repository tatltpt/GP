import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
FEATURE_DIR = os.path.join(BASE_DIR, 'static', 'files')
path = os.path.join(FEATURE_DIR, "body.h5")
print(path)
import h5py
f = h5py.File("/home/thao/Desktop/Do_an/GP/static/files/body.h5", 'r')
/home/thao/Desktop/Do_an/GP/flaskblog/static/files/body.h5
features_arr = f['features'][:]
print(path)
print(features_arr)