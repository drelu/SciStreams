#!/usr/bin/python
# -*- coding: utf-8 -*-
# vi: ts=4 sw=4
'''
:mod:`SciAnalysis.XSAnalysis.Protocols` - Data analysis protocols
================================================
.. module:: SciAnalysis.XSAnalysis.Protocols
   :synopsis: Convenient protocols for data analysis.
.. moduleauthor:: Dr. Kevin G. Yager <kyager@bnl.gov>
                    Brookhaven National Laboratory
'''

################################################################################
#  Data analysis protocols.
################################################################################
# Known Bugs:
#  N/A
################################################################################
# TODO:
#  Search for "TODO" below.
################################################################################

from .Data import Data2DScattering
from ..tools import *
# databroker stuff

# import the analysis databroker
from uuid import uuid4

import hashlib

from dask import delayed
from scipy import ndimage

'''
    Notes : load should be a separate function

'''
# TODO : add pixel procesing/thresholding threshold_pixels((2**32-1)-1) # Eiger inter-module gaps
# 
# TODO : have kwargs intercepted by databroker and saved

from ..Protocol import Protocol


name = "XS:thumb"
defaults = {
    'gamma' : 0.3,
    'crop' : None,
    'blur' : 2.0,
    'resize' : 0.2,
    'ztrim' : [0.05, 0.005],
    'default_ext' : '.jpg'
}
output_names = ['thumb']
keymap = {'data' : 'data', 'output_dir' : 'output_dir'}
accepted_args = list(keymap.keys())
for name in defaults.keys():
    if name not in accepted_args:
        accepted_args.append(defaults)
@Protocol(name=name, output_names=output_names, keymap=keymap, accepted_args=accepted_args,
            defaults = defaults)
def thumb(self, data=None, output_dir=None, **run_args):
    ''' This run saves the data and outputs it to a png file.'''
    # TODO : Add documentation that we don't want functions that modify the
    # data objects BEWARE of calling outside functions that may change.  here,
    # cropping and blurring/resizing is not so big of a deal but we may want to
    # be ware of other methods
    def crop(data, size):
        '''Crop the data, centered about the q-origin. I.e. this throws away
        some of the high-q information. The size specifies the size of the new
        image (as a fraction of the original full image width).'''

        height, width = data.shape

        x0, y0 = self.get_origin()
        xi = max( int(x0 - size*width/2), 0 )
        xf = min( int(x0 + size*width/2), width )
        yi = max( int(y0 - size*height/2), 0 )
        yf = min( int(y0 + size*height/2), height )

        return data[ yi:yf, xi:xf ]

    #TODO : make mask aware
    def resize(data, zoom):
        return ndimage.interpolation.zoom(data, zoom=zoom)

    def blur(data, sigma=1.0):
        '''Apply a Gaussian smoothing/blurring to the 2D data. The sigma
        argument specifies the size (in terms of the sigma width of the
        Gaussian, in pixels).'''
        return ndimage.filters.gaussian_filter( self.data, sigma )

    if run_args['crop'] is not None:
        data = crop(data, run_args['crop'])
    if run_args['blur'] is not None:
        data = blur(data, run_args['blur'])
    if run_args['resize'] is not None:
        data = resize(data, run_args['resize']) # Shrink

    data.set_z_display([None, None, 'gamma', 0.3])
    if 'file_extension' in run_args and run_args['file_extension'] is not None:
        outfile = self.get_outfile(data.name, output_dir, ext=run_args['file_extension'])
    else:
        outfile = self.get_outfile(data.name, output_dir)

    data.plot_image(outfile, **run_args)
    datum_kwargs = {}  #kwargs for data if needed

    # this is the databroker stuff
    if run_args['db_analysis'] is not None:
        # first prep metadata for filestore
        # keep track of files saved here
        files = {
                    'thumb' : {'dtype' : 'array', 'spec' : 'PNG', 'filename'
                               : outfile},
                   }
        # 'resource_kwargs' : [], 'datum_kwargs' : [], etc
        results['_files'] = files
        results['_run_args'] = dict(**run_args)

    return results


class circular_average(Protocol):

    def __init__(self, name=None, **kwargs):

        self.name = self.__class__.__name__ if name is None else name

        self.default_ext = '.png'
        self.run_args = {}
        self.run_args.update(kwargs)

    @run_default
    def run(self, data, output_dir, **run_args):
        # update run args with internal run_args first
        for key, val in self.run_args.items():
            if key not in run_args:
                run_args[key] = val
        #data = {'object' : data, 'id' : hashlib.md5(str(data.data).encode('utf-8'))}
        #return delayed(self.run_explicit(data, output_dir, **run_args),pure=True)
        return self.run_explicit(data, output_dir, **run_args)

    def run_explicit(self, data, output_dir, **run_args):

        results = {}

        line = data.circular_average_q_bin(error=True)
        #line.smooth(2.0, bins=10)

        outfile_png = self.get_outfile(data.name, output_dir)

        try:
            line.plot(save=outfile_png, show=False, **run_args)
        except ValueError:
            pass
        outfile_dat = self.get_outfile(data.name, output_dir, ext='.dat')
        line.save_data(outfile_dat)


        # this is the databroker stuff
        if run_args['db_analysis'] is not None:
            # first prep metadata for filestore
            # keep track of files saved here
            files = {
                        'sqdat' : {'dtype' : 'array', 'spec' : 'DAT', 'filename'
                                   : outfile_dat},
                        'sqplot' : {'dtype' : 'array', 'filename' : outfile_png}
                       }
            # 'resource_kwargs' : [], 'datum_kwargs' : [], etc
            results['_files'] = files
            results['_run_args'] = dict(**run_args)

        # TODO: Fit 1D data

        return results



class circular_average_q2I(Protocol):

    def __init__(self, name=None, **kwargs):

        self.name = self.__class__.__name__ if name is None else name

        self.default_ext = '.png'
        self.run_args = {}
        self.run_args.update(kwargs)


    @run_default
    def run(self, data, output_dir, **run_args):

        results = {}

        line = data.circular_average_q_bin(error=True)

        line.y *= np.square(line.x)
        line.y_label = 'q^2*I(q)'
        line.y_rlabel = '$q^2 I(q) \, (\AA^{-2} \mathrm{counts/pixel})$'


        outfile = self.get_outfile(data.name, output_dir, ext='_q2I{}'.format(self.default_ext))
        line.plot(save=outfile, show=False, **run_args)

        outfile = self.get_outfile(data.name, output_dir, ext='_q2I.dat')
        line.save_data(outfile)

        # TODO: Fit 1D data

        return results


    def output_exists(self, name, output_dir):

        if 'file_extension' in self.run_args:
            ext = '_q2I{}'.format(self.run_args['file_extension'])
        else:
            ext = '_q2I{}'.format(self.default_ext)

        outfile = self.get_outfile(name, output_dir, ext=ext)
        return os.path.isfile(outfile)









class linecut_angle(Protocol):

    def __init__(self, name=None, **kwargs):

        self.name = self.__class__.__name__ if name is None else name

        self.default_ext = '.png'
        self.run_args = {'show_region' : False,
                         'plot_range' : [-180, 180, 0, None]
                         }
        self.run_args.update(kwargs)


    @run_default
    def run(self, data, output_dir, **run_args):

        results = {}

        #line = data.linecut_angle(q0=run_args['q0'], dq=run_args['dq'])
        line = data.linecut_angle(**run_args)

        if 'show_region' in run_args and run_args['show_region']:
            data.plot(show=True)


        #line.smooth(2.0, bins=10)

        outfile = self.get_outfile(data.name, output_dir)
        line.plot(save=outfile, **run_args)

        #outfile = self.get_outfile(data.name, output_dir, ext='_polar.png')
        #line.plot_polar(save=outfile, **run_args)

        outfile = self.get_outfile(data.name, output_dir, ext='.dat')
        line.save_data(outfile)

        return results







class calibration_check(Protocol):

    def __init__(self, name=None, **kwargs):

        self.name = self.__class__.__name__ if name is None else name

        self.default_ext = '.png'
        self.run_args = {}
        self.run_args.update(kwargs)


    @run_default
    def run(self, data, output_dir, **run_args):

        results = {}

        outfile = self.get_outfile('{}_full'.format(data.name), output_dir)
        data.plot_image(outfile, **run_args)


        data.blur(2.0)

        if 'AgBH' in run_args and run_args['AgBH']:
            q0 = 0.1076 # A^-1

            for i in range(11):
                data.overlay_ring(q0*(i+1), q0*(i+1)*0.01)

        if 'q0'  in run_args:

            q0 = run_args['q0']
            if 'num_rings' in run_args:
                num_rings = run_args['num_rings']
            else:
                num_rings = 5

            for i in range(num_rings):
                data.overlay_ring(q0*(i+1), q0*(i+1)*0.01)


        outfile = self.get_outfile(data.name, output_dir)

        data.plot(save=outfile, **run_args)

        return results








# Work in progress
################################################################################

class fit_calibration(Protocol):

    def __init__(self, name=None, **kwargs):

        self.name = self.__class__.__name__ if name is None else name

        self.default_ext = '.png'
        self.run_args = { 'material' : 'AgBH01' }
        self.run_args.update(kwargs)


    @run_default
    def run(self, data, output_dir, **run_args):

        # WARNING: This procedure doesn't work very well.

        results = {}

        if run_args['material'] is 'AgBH01':

            import lmfit
            # https://lmfit.github.io/lmfit-py/parameters.html#simple-example
            def fcn2min(params, x, data):
                '''Gaussian with linear background.'''
                v = params.valuesdict()
                model = v['prefactor']*np.exp( -np.square(x-v['x_center'])/(2*(v['sigma']**2)) ) + v['m']*x + v['b']

                return model - data

            self.lmfit = lmfit
            self._fcn2min = fcn2min

            q_peak = 0.1076 # A^-1
            dq = q_peak*0.3

            self._find_local_q_match(data, 'distance_m', 0.02, 0.002, q_peak, dq)
            self._find_local_q_match(data, 'distance_m', 0.001, 0.0005, q_peak, dq)

            #self._find_local_minimum_width(data, 'x0', 40, 2, q_peak, dq)
            #self._find_local_minimum_width(data, 'y0', 40, 2, q_peak, dq)
            #self._find_local_minimum_width(data, 'x0', 5, 0.5, q_peak, dq)
            #self._find_local_minimum_width(data, 'y0', 5, 0.5, q_peak, dq)

            self._find_local_q_match(data, 'distance_m', 0.005, 0.0002, q_peak, dq)


            print('Final values:\n    x0 = %.1f\n    y0 = %.1f\n    dist = %g'%(data.calibration.x0, data.calibration.y0, data.calibration.distance_m))


            line = data.circular_average_q_range(q_peak, dq, error=False)
            result = self._fit_peak(line)
            self.lmfit.report_fit(result.params)
            fit_data = line.y + result.residual
            fit_line = DataLine(x=line.x, y=fit_data, plot_args={'linestyle':'-', 'color':'r', 'marker':None, 'linewidth':4.0})

            outfile = self.get_outfile(data.name, output_dir)
            lines = DataLines( [line, fit_line] )
            lines.plot(save=outfile, show=False)
            outfile = self.get_outfile(data.name, output_dir, ext='.dat')
            line.save_data(outfile)


        return results


    def _fit_peak(self, line):

        params = self.lmfit.Parameters()
        params.add('prefactor', value=np.max(line.y), min=0)
        params.add('x_center', value=np.average(line.x))
        params.add('sigma', value=np.std(line.x), min=0)
        params.add('m', value=0)
        params.add('b', value=0)

        result = self.lmfit.minimize(self._fcn2min, params, args=(line.x, line.y))

        return result


    def _find_local_minimum_width(self, data, attr, spread, step, q_peak, dq):

        v_start = getattr(data.calibration, attr)
        v_min = None
        v_min_value = None

        for v_displacement in np.arange(-spread, +spread, step):

            setattr(data.calibration, attr, v_start + v_displacement)
            data.calibration.clear_maps()

            line = data.circular_average_q_range(q_peak, dq, error=False)
            result = self._fit_peak(line)
            width = result.params['sigma'].value

            print('  %s: %.1f, width: %g' % (attr, v_start+v_displacement, width))

            if v_min is None:
                v_min = v_start+v_displacement
                v_min_value = width
            elif width<v_min_value:
                v_min = v_start+v_displacement
                v_min_value = width

        # Go to the best position
        setattr(data.calibration, attr, v_min)
        data.calibration.clear_maps()


    def _find_local_q_match(self, data, attr, spread, step, q_peak, dq):

        v_start = getattr(data.calibration, attr)
        v_min = None
        v_min_value = None

        for v_displacement in np.arange(-spread, +spread, step):

            setattr(data.calibration, attr, v_start + v_displacement)
            data.calibration.clear_maps()

            line = data.circular_average_q_range(q_peak, dq, error=False)
            result = self._fit_peak(line)
            err = abs(result.params['x_center'].value - q_peak)

            print('  %s: %g, pos: %g, err: %g' % (attr, v_start+v_displacement, result.params['x_center'], err))

            if v_min is None:
                v_min = v_start+v_displacement
                v_min_value = err
            elif err<v_min_value:
                v_min = v_start+v_displacement
                v_min_value = err

        # Go to the best position
        setattr(data.calibration, attr, v_min)
        data.calibration.clear_maps()





class q_image(Protocol):

    def __init__(self, name='q_image', **kwargs):

        self.name = self.__class__.__name__ if name is None else name

        self.default_ext = '.png'
        self.run_args = {
                        'blur' : None,
                        'ztrim' : [0.05, 0.005],
                        'method' : 'nearest',
                        }
        self.run_args.update(kwargs)


    @run_default
    def run(self, data, output_dir, **run_args):

        results = {}

        if run_args['blur'] is not None:
            data.blur(run_args['blur'])

        q_data = data.remesh_q_bin(**run_args)

        if run_args['verbosity']>=5:
            # Diagnostic
            data_temp = Data2DReciprocal()

            data_temp.data = data.calibration.qx_map()
            outfile = self.get_outfile('qx-{}'.format(data.name), output_dir, ext='.png', ir=True)
            r = np.max( np.abs(data_temp.data) )
            data_temp.set_z_display([-r, +r, 'linear', 0.3])
            data_temp.plot(outfile, cmap='bwr', **run_args)

            data_temp.data = data.calibration.qy_map()
            outfile = self.get_outfile('qy-{}'.format(data.name), output_dir, ext='.png', ir=True)
            r = np.max( np.abs(data_temp.data) )
            data_temp.set_z_display([-r, +r, 'linear', 0.3])
            data_temp.plot(outfile, cmap='bwr', **run_args)

            data_temp.data = data.calibration.qz_map()
            outfile = self.get_outfile('qz-{}'.format(data.name), output_dir, ext='.png', ir=True)
            r = np.max( np.abs(data_temp.data) )
            data_temp.set_z_display([-r, +r, 'linear', 0.3])
            data_temp.plot(outfile, cmap='bwr', **run_args)



        if 'file_extension' in run_args and run_args['file_extension'] is not None:
            outfile = self.get_outfile(data.name, output_dir, ext=run_args['file_extension'])
        else:
            outfile = self.get_outfile(data.name, output_dir)

        if 'q_max' in run_args and run_args['q_max'] is not None:
            q_max = run_args['q_max']
            run_args['plot_range'] = [-q_max, +q_max, -q_max, +q_max]

        q_data.set_z_display([None, None, 'gamma', 0.3])
        q_data.plot_args = { 'rcParams': {'axes.labelsize': 55,
                                    'xtick.labelsize': 40,
                                    'ytick.labelsize': 40,
                                    },
                            }
        q_data.plot(outfile, plot_buffers=[0.30,0.05,0.25,0.05], **run_args)



        return results



class q_phi_image(Protocol):

    def __init__(self, name='q_phi_image', **kwargs):

        self.name = self.__class__.__name__ if name is None else name

        self.default_ext = '.png'
        self.run_args = {
                        'blur' : None,
                        'bins_relative' : 0.5,
                        'bins_phi' : 360.0/1.0,
                        'ztrim' : [0.05, 0.005],
                        'method' : 'nearest',
                        'yticks' : [-180, -90, 0, 90, 180],
                        }
        self.run_args.update(kwargs)


    @run_default
    def run(self, data, output_dir, **run_args):

        results = {}

        if run_args['blur'] is not None:
            data.blur(run_args['blur'])

        q_data = data.remesh_q_phi(**run_args)

        if 'file_extension' in run_args and run_args['file_extension'] is not None:
            outfile = self.get_outfile(data.name, output_dir, ext=run_args['file_extension'])
        else:
            outfile = self.get_outfile(data.name, output_dir)

        if 'q_max' in run_args and run_args['q_max'] is not None:
            run_args['plot_range'] = [0, +run_args['q_max'], -180, +180]

        q_data.set_z_display([None, None, 'gamma', 0.3])
        q_data.plot_args = { 'rcParams': {'axes.labelsize': 55,
                                    'xtick.labelsize': 40,
                                    'ytick.labelsize': 40,
                                    },
                            }
        q_data.plot(outfile, plot_buffers=[0.20,0.05,0.20,0.05], **run_args)

        if True:
            # Save Data2DQPhi() object
            import pickle
            outfile = self.get_outfile(data.name, output_dir, ext='.pkl')
            with open(outfile, 'wb') as fout:
                out_data = q_data.data, q_data.x_axis, q_data.y_axis
                pickle.dump(out_data, fout)




        return results

