# test a XS run



from config import MASKDIR

from SciAnalysis.interfaces.databroker import dbtools as source_dbtools 
from SciAnalysis.interfaces.file import reading as source_file
from SciAnalysis.interfaces.detectors import detectors2D

from SciAnalysis.analyses.XSAnalysis.Protocols import LoadSAXSImage, LoadCalibration, CircularAverage
from SciAnalysis.analyses.XSAnalysis.Data import MasterMask


detector = detectors2D['pilatus300']

load_saxs = LoadSAXSImage()
load_calib = LoadCalibration()
load_calib.set_keymap("cms")
circavg = CircularAverage()

blemish_filename = MASKDIR + "/Pilatus300k_main_gaps-mask.png"
blemish = source_file.FileDesc(blemish_filename).get_raw()[:,:,0] > 1
blemish = blemish.astype(int)



# prepare master mask
master_mask_name = "pilatus300_mastermask.npz"
master_mask_filename = MASKDIR + "/" + master_mask_name

master_mask = MasterMask(datafile=master_mask_filename, blemish=blemish)

# read in data
start_time = "2017-03-01"
stop_time = "2017-03-02"
scires_gen = source_dbtools.pull("cms:data", start_time=start_time, stop_time=stop_time)

detector_key = 'pilatus300_image'
scires = scires_gen
cnt = 0
nobins = 1000
for scires in scires_gen:
    img = scires(detector_key).get()
    attributes = scires['attributes']
    calibration = load_calib(calibration=attributes).get()
    beamx0, beamy0 = calibration['beamx0']['value'], calibration['beamy0']['value']
    origin = beamy0, beamx0

    mask = master_mask.generate(detector['shape']['value'], origin)

    scires_sq = circavg(image=img, calibration=calibration, mask=mask, bins=nobins).compute()

    cnt += 1
    if cnt > 0:
        break


sqx, sqy = scires_sq(['sqx', 'sqy']).get()
