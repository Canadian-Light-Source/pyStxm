
import numpy as np
from pathlib import Path
import datetime

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp

from ophyd.status import DeviceStatus, SubscriptionStatus

from ophyd.areadetector.trigger_mixins import SingleTrigger
from ophyd.areadetector.detectors import DetectorBase
from ophyd.areadetector.cam import CamBase
from ophyd.signal import (EpicsSignalRO, EpicsSignal)
from ophyd.areadetector.base import (ADComponent as ADCpt,
                   EpicsSignalWithRBV as SignalWithRBV)
from ophyd.areadetector.plugins import (ImagePlugin, StatsPlugin,
                                            ColorConvPlugin, ProcessPlugin,
                                            OverlayPlugin, ROIPlugin,
                                            TransformPlugin, NetCDFPlugin,
                                            TIFFPlugin, JPEGPlugin, HDF5Plugin,
        # FilePlugin
                                            )
from ophyd.areadetector.filestore_mixins import (
    FileStoreTIFFIterativeWrite,
    FileStoreHDF5SingleIterativeWrite,
)
from ophyd.areadetector.plugins import register_plugin, FilePlugin_V22, HDF5Plugin_V22
from ophyd.utils import set_and_wait
from ophyd.areadetector.filestore_mixins import FileStoreBase, new_short_uid, FileStoreTIFF, FileStoreIterativeWrite

IMG_FTYPE_HDF5 = 0
IMG_FTYPE_TIFF = 1


class TUCSEN_FileStorePluginBase(FileStoreBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, "create_directory"):
            self.stage_sigs.update({"create_directory": -3})
        self.stage_sigs.update([('auto_increment', 'Yes'),
                                ('array_counter', 0),
                                ('auto_save', 'Yes'),
                                ('num_capture', 0),
                                ])
        self._fn = None
        self._fp = None

    def make_filename(self):
        '''Make a filename.

        This is a hook so that the read and write paths can either be modified
        or created on disk prior to configuring the areaDetector plugin.

        Returns
        -------
        filename : str
            The start of the filename
        read_path : str
            Path that ophyd can read from
        write_path : str
            Path that the IOC can write to
        ('a9b3ed47-bd2e-47af-ab20',
             '\\home\\bergr\\SM\\test_data\\C167092\\',
             '/opt/test_data/C167092')
        '''
        #dont over ride what was previously set to these signals likely from the scan plan
        filename = self.file_name.get()
        read_path = self.read_path_template
        write_path = self.write_path_template
        return filename, read_path, write_path

    def stage(self):
        # Make a filename.
        filename, read_path, write_path = self.make_filename()

        # Ensure we do not have an old file open.
        if self.file_write_mode != 'Single':
            self.capture.set(0).wait()
        # These must be set before parent is staged (specifically
        # before capture mode is turned on. They will not be reset
        # on 'unstage' anyway.
        self.file_path.set(write_path).wait()
        self.file_name.set(filename).wait()
        self.file_number.set(0).wait()
        super().stage()

        # AD does this same templating in C, but we can't access it
        # so we do it redundantly here in Python.
        self._fn = self.file_template.get() % (read_path,
                                               filename,
                                               # file_number is *next* iteration
                                               self.file_number.get() - 1)
        self._fp = read_path
        # if not self.file_path_exists.get():
        #     raise IOError("Path %s does not exist on IOC."
        #                   "" % self.file_path.get())

class FileStoreTIFF(TUCSEN_FileStorePluginBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filestore_spec = 'AD_TIFF'  # spec name stored in resource doc
        self.stage_sigs.update([('enable', 0),
                                ('file_template', '%s%s_%6.6d.tiff'),
                                ('file_write_mode', 'Single'),
                                ])
        # 'Single' file_write_mode means one image : one file.
        # It does NOT mean that 'num_images' is ignored.

    def get_frames_per_point(self):
        return self.parent.cam.num_images.get()

class TUCSEN_FileStoreTIFFIterativeWrite(FileStoreTIFF, FileStoreIterativeWrite):
    pass

@register_plugin
class TUCSEN_TIFFPlugin(FilePlugin_V22, version=(1, 9, 1), version_type='ADCore'):
    _default_suffix = 'TIFF1:'
    _suffix_re = r'TIFF\d:'
    _html_docs = ['NDFileTIFF.html']
    _plugin_type = 'NDFileTIFF'

class TUCSEN_TIFFPluginWithFileStore(TUCSEN_TIFFPlugin, TUCSEN_FileStoreTIFFIterativeWrite):
    """Add this as a component to detectors that write TIFFs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.windows_write_path = ""

    def make_filename(self):
        '''Make a filename.

        This is a hook so that the read and write paths can either be modified
        or created on disk prior to configuring the areaDetector plugin.

        Returns
        -------
        filename : str
            The start of the filename
        read_path : str
            Path that ophyd can read from
        write_path : str
            Path that the IOC can write to or is it the path that this application can write to?

            ('a9b3ed47-bd2e-47af-ab20',
             '\/opt/test_data/C167092/',
             '/opt/test_data/C167092')
        '''
        #dont over ride what was previously set to these signals likely from the scan plan
        filename = self.file_name.get()
        read_path = self.read_path_template
        write_path = self.write_path_template
        return filename, read_path, write_path

    # def stage(self):
    #     # Make a filename.
    #     filename, read_path, write_path = self.make_filename()
    #
    #     # Ensure we do not have an old file open.
    #     if self.file_write_mode != 'Single':
    #         set_and_wait(self.capture, 0)
    #     # These must be set before parent is staged (specifically
    #     # before capture mode is turned on. They will not be reset
    #     # on 'unstage' anyway.
    #     self.file_path.set(write_path).wait()
    #     set_and_wait(self.file_name, filename)
    #     set_and_wait(self.file_number, 0)
    #     super().stage()
    #
    #     # AD does this same templating in C, but we can't access it
    #     # so we do it redundantly here in Python.
    #     self._fn = self.file_template.get() % (read_path,
    #                                            filename,
    #                                            # file_number is *next* iteration
    #                                            self.file_number.get() - 1)
    #     self._fp = read_path
    #     # if not self.file_path_exists.get():
    #     #     raise IOError("Path %s does not exist on IOC."
    #     #                   "" % self.file_path.get())
    #     # if not Path(self.windows_write_path).exists():
    #     #     raise IOError(f"Path [{self.self.windows_write_path}] does not exist as seen by this application.")

class TucsenDetectorCam(CamBase):
    _html_docs = []
    serial_number = ADCpt(EpicsSignalRO, 'SerialNumber_RBV')
    firmware_version = ADCpt(EpicsSignalRO, 'FirmwareVersion_RBV')
    sdk_version = ADCpt(EpicsSignalRO, 'SDKVersion_RBV')
    bus = ADCpt(EpicsSignalRO, 'Bus_RBV')
    driver_version = ADCpt(EpicsSignalRO, 'DriverVersion_RBV')
    adcore_version = ADCpt(EpicsSignalRO, 'ADCoreVersion_RBV')

    fan_gear = ADCpt(SignalWithRBV, 'FanGear')
    auto_exposure = ADCpt(SignalWithRBV, 'AutoExposure')
    histogram = ADCpt(SignalWithRBV, 'Histogram')
    defect_correction = ADCpt(SignalWithRBV, 'DefectCorrection')
    auto_levels = ADCpt(SignalWithRBV, 'AutoLevels')
    enhance = ADCpt(SignalWithRBV, 'Enhance')
    enable_denoise = ADCpt(SignalWithRBV, 'EnableDenoise')
    dyn_rge_correction = ADCpt(SignalWithRBV, 'DynRgeCorrection')
    gamma = ADCpt(SignalWithRBV, 'Gamma')
    contrast = ADCpt(SignalWithRBV, 'Contrast')
    hdrk = ADCpt(SignalWithRBV, 'HDRK')
    left_levels = ADCpt(SignalWithRBV, 'LeftLevels')
    right_levels = ADCpt(SignalWithRBV, 'RightLevels')
    black_level = ADCpt(SignalWithRBV, 'BlackLevel')
    brightness = ADCpt(SignalWithRBV, 'Brightness')
    sharpness = ADCpt(SignalWithRBV, 'Sharpness')
    noise_level = ADCpt(SignalWithRBV, 'NoiseLevel')

    trigger_exposure = ADCpt(SignalWithRBV, 'TriggerExposure')
    trigger_edge = ADCpt(SignalWithRBV, 'TriggerEdge')
    trigger_delay = ADCpt(SignalWithRBV, 'TriggerDelay')

    trigger_out_1_mode = ADCpt(SignalWithRBV, 'TriggerOut1Mode')
    trigger_out_1_edge = ADCpt(SignalWithRBV, 'TriggerOut1Edge')
    trigger_out_1_delay = ADCpt(SignalWithRBV, 'TriggerOut1Delay')
    trigger_out_1_width = ADCpt(SignalWithRBV, 'TriggerOut1Width')

    trigger_out_2_mode = ADCpt(SignalWithRBV, 'TriggerOut2Mode')
    trigger_out_2_edge = ADCpt(SignalWithRBV, 'TriggerOut2Edge')
    trigger_out_2_delay = ADCpt(SignalWithRBV, 'TriggerOut2Delay')
    trigger_out_2_width = ADCpt(SignalWithRBV, 'TriggerOut2Width')

    trigger_out_3_mode = ADCpt(SignalWithRBV, 'TriggerOut3Mode')
    trigger_out_3_edge = ADCpt(SignalWithRBV, 'TriggerOut3Edge')
    trigger_out_3_delay = ADCpt(SignalWithRBV, 'TriggerOut3Delay')
    trigger_out_3_width = ADCpt(SignalWithRBV, 'TriggerOut3Width')


    def dump_report(self):
        """
        a function to display the connection information to the camera
        """

        print(f"Manufacturer: {self.manufacturer.get()}")
        print(f"Model: {self.model.get()}")
        print(f"Serial Number: {self.serial_number.get()}")
        print(f"Firmware Version: {self.firmware_version.get()}")
        print(f"SDK Version: {self.sdk_version.get()}")
        print(f"Bus: {self.bus.get()}")
        print(f"Driver Version: {self.driver_version.get()}")
        print(f"ADCore Version: {self.adcore_version.get()}")


        for attribute in dir(self):
            # print(attribute, getattr(tucsen.cam, attribute))
            attr = getattr(self, attribute)
            if hasattr(attr, "_read_pvname"):
                # print(attribute, getattr(tucsen.cam, attribute))
                print(f"\t{attribute} = {attr.get()}")

class TUCSEN_HDF5_Plugin(HDF5Plugin_V22, FileStoreHDF5SingleIterativeWrite):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def make_filename(self):
        '''Make a filename.

        This is a hook so that the read and write paths can either be modified
        or created on disk prior to configuring the areaDetector plugin.

        Returns
        -------
        filename : str
            The start of the filename
        read_path : str
            Path that ophyd can read from
        write_path : str
            Path that the IOC can write to or is it the path that this application can write to?

            ('a9b3ed47-bd2e-47af-ab20',
             '\directory\\test_data\\C167092\\',
             '/opt/test_data/C167092')
        '''
        #dont over ride what was previously set to these signals likely from the scan plan
        filename = self.file_name.get()
        read_path = self.read_path_template
        write_path = self.write_path_template
        return filename, read_path, write_path

rootdir = "/opt/"
dest = "/opt/test_data/guest/0623/"

class TucsenDetector(DetectorBase):
    _html_docs = []  # the documentation is not public
    cam = ADCpt(TucsenDetectorCam, 'cam1:')
    image = ADCpt(ImagePlugin, "image1:")
    tif_file_plugin = ADCpt(
        TUCSEN_TIFFPluginWithFileStore,
        "TIFF1:",
        write_path_template=dest,
        read_path_template=dest,
        read_attrs=[],
        root=rootdir,
    )
    hdf5_file_plugin = ADCpt(
        TUCSEN_HDF5_Plugin,
        suffix="HDF1:",
        write_path_template=dest,
        read_path_template=dest,
        root=rootdir,
    )

    def __init__(self, prefix, name):
        super(TucsenDetector, self).__init__(prefix=prefix, name=name)
        # these will appear in databroker documents
        # self.read_attrs = ['file_plugin', 'stats1.total']
        #default is hdf5
        self.read_attrs = ["hdf5_file_plugin"]

    def enable_file_plugin_by_name(self, nm="HDF5"):
        """
        enable/disable the file plgins by name, mutually exclusive
        so specifying one disables the other
        This function is needed because stage() will enable both under the hood
        """
        if nm.find("HDF5") > -1:
            self.hdf5_file_plugin.enable.put(1)
            self.tif_file_plugin.enable.put(0)
            self.read_attrs = ["hdf5_file_plugin"]
        else:
            self.hdf5_file_plugin.enable.put(0)
            self.tif_file_plugin.enable.put(1)
            self.read_attrs = ["tif_file_plugin"]

    def stage(self, *args, **kwargs):
        # init some settings
        self.hdf5_file_plugin.array_counter.put(0)
        self.tif_file_plugin.array_counter.put(0)

        return super().stage(*args, **kwargs)

    def set_dwell(self, dwell_ms):
        """
        a function used by higher level scans to set the dwell
        """
        dwell_sec = dwell_ms * 0.001
        self.cam.acquire_time.put(dwell_sec)
        # Ru says the acquire period should be a tad longer than exposer time
        self.cam.acquire_period.put(dwell_sec + .002)


    def get_name(self):
        return self.name

    def get_position(self):
        return 0.0

    def get_temperature(self):
        val = self.cam.temperature_actual.get()
        return val

    def set_trigger_mode_hdw_trig(self):
        """
        for the Tucsen Dhyana 95 V2 the trigger modes are
         0 = Free Run -> for software single image acquisitions
         1 = Standard -> for hardware trigger
         2 = Synchronous -> not used
         3 = Global -> not used
         4 = Software -> not used

        """
        self.set_trigger_signal(1)

    def set_trigger_signal(self, mode):
        """
        calls the signal to set the value
        """
        self.cam.trigger_mode.put(mode)

    def set_file_output_path(self, cam_root_dir, fpath):
        """
        set all of the relevant attributes so that the tiff files save to the correct location
        """
        #update the hdf5 plugin paths
        self.hdf5_file_plugin.file_path.put(fpath)
        self.hdf5_file_plugin.reg_root = cam_root_dir
        self.hdf5_file_plugin.write_path_template = fpath
        self.hdf5_file_plugin.read_path_template = fpath

        #update the tif plugin paths
        self.tif_file_plugin.file_path.put(fpath)
        self.tif_file_plugin.reg_root = cam_root_dir
        self.tif_file_plugin.write_path_template = fpath
        self.tif_file_plugin.read_path_template = fpath

    def trigger(self):
        super(TucsenDetector, self).trigger()
        def check_value(*, old_value, value, **kwargs):
            "Return True when the acquisition is complete, False otherwise."
            return (old_value == 1 and value == 0)

        status = SubscriptionStatus(self.cam.acquire, check_value)

        #print("ad_tucsen: trigger: calling run(1)")
        self.cam.acquire.put(1)

        return status



def make_scan_plan(motor1, motor2, motor3, motor4, noisy_det, tucsen, md={}):
    # tucsen = SimGreatEyestucsen('SIM_tucsen1610-I10-02:', name='SIM_GE_tucsen')
    # _rpath = dct_get(self.sp_db[SPDB_ACTIVE_DATA_OBJECT], ADO_CFG_STACK_DIR)
    base_data_dir = dest
    data_dir = "C" + str(random.randint(100000, 999999))
    tucsen.hdf5_file_plugin.read_path_template = base_data_dir + "/" + data_dir
    # _cur_datadir = _rpath.replace("/", "")
    # _cur_datadir = _cur_datadir.replace("\\", "/")
    _cur_datadir = base_data_dir + "/" + data_dir
    # tucsen.hdf5_file_plugin.reg_root.put('/opt')
    tucsen.hdf5_file_plugin.file_path.put(_cur_datadir)
    # tucsen.hdf5_file_plugin.read_path_template = tucsen.hdf5_file_plugin.write_path_template = _cur_datadir
    tucsen.hdf5_file_plugin.write_path_template = _cur_datadir
    tucsen.hdf5_file_plugin.file_template.put("%s_%d.tif")

    # tucsen.hdf5_file_plugin.file_path.put('/opt/test_data/')
    tucsen.hdf5_file_plugin.file_name.put('Ctest_')
    tucsen.hdf5_file_plugin.file_number.put(0)
    tucsen.hdf5_file_plugin.auto_save.put(1)
    tucsen.hdf5_file_plugin.create_directory.put(-2) # this will create at least 2 levels of directories if they do not already exist
    # self.hdf5_file_plugin.compression.put(6)  # set to LZ4
    # tucsen.hdf5_file_plugin.compression.put(0)  # set to NONE
    dwell_sec = 0.3
    tucsen.cam.image_mode.put(0)  # single
    tucsen.cam.trigger_mode.put(0)  # internal
    tucsen.cam.array_counter.put(0)  # reset counter to 0 for this run
    tucsen.cam.acquire_time.put(dwell_sec)
    # Ru says the acquire period should be a tad longer than exposer time
    tucsen.cam.acquire_period.put(dwell_sec + 0.002)

    tucsen.stage()
    tucsen.hdf5_file_plugin.file_template.put("%s%s_%3.3d.tif")

    #@bpp.baseline_decorator(dev_list)
    @bpp.run_decorator(md=md)
    def do_scan():
        # img_cntr = 0
        # dwell_sec = self.dwell * 0.001
        mtr_y = motor2
        mtr_x = motor1
        outer_posner = motor3
        inner_posner = motor4

        # #Ru says the acquire period should be a tad longer than exposer time
        # ccd.cam.acquire_period.put(dwell_sec + 0.002)

        # yield from bps.stage(gate)
        outer_pnts = np.linspace(0,10,2)
        inner_pts = np.linspace(-15,15,3)
        y_setpoints = np.linspace(-5, 5, 4)
        x_setpoints = np.linspace(-5, 5, 4)

        #shutter.open()
        img_cntr = 0
        for op in outer_pnts:
            # print('PtychographyScanClass: moving outter posner [%s] to [%.2f]' % (outer_posner.get_name(), op))
            yield from bps.mv(outer_posner, op)

            for ip in inner_pts:
                # print('PtychographyScanClass: moving inner posner [%s] to [%.2f]' % (inner_posner.get_name(), ip))
                yield from bps.mv(inner_posner, ip)

                for y in y_setpoints:
                    yield from bps.mv(mtr_y, y)
                    # print('PtychographyScanClass: moving Y to [%.3f]' % y)
                    for x in x_setpoints:
                        # print('PtychographyScanClass: moving X to [%.3f]' % x)
                        yield from bps.mv(mtr_x, x)
                        yield from bps.trigger_and_read(
                            [tucsen, noisy_det, mtr_y, mtr_x]
                        )
                        img_cntr += 1
                        print("PtychographyScanClass: img_counter = [%d]" % img_cntr )

        print("PtychographyScanClass: done closing shutter")
        #shutter.close()
        # yield from bps.wait(group='e712_wavgen')
        # yield from bps.unstage(gate)
        yield from bps.unstage(tucsen)

        print("PtychographyScanClass: make_scan_plan Leaving")

    return (yield from do_scan())




if __name__ == '__main__':
    from bluesky import RunEngine
    import bluesky.plans as bp
    from databroker import Broker
    import random
    from ophyd.sim import motor, motor1, motor2, motor3, noisy_det


    tucsen = TucsenDetector("SCMOS1610-310:",name="TucsenAD")
    #tucsen.cam.fan_gear.put(2)
    #tucsen.cam.defect_correction.put(1)
    #tucsen.cam.dump_report()
    tucsen.hdf5_file_plugin.file_template.put("%s_%d.h5")

    db = Broker.named("pystxm_amb_bl10ID1")
    RE = RunEngine({})
    RE.subscribe(db.insert)

    tucsen.stage()

    tucsen.enable_file_plugin_by_name("HDF5")
    #tucsen.set_trigger_signal()
    print(tucsen.summary())
    # tucsen.read_attrs = ['file_plugin']
    ptycho_plan = make_scan_plan(motor, motor1, motor2, motor3, noisy_det, tucsen, md={"user": "bergr"})
    plan = lambda: ptycho_plan
    #(uid,) = RE(bp.count([tucsen]))

    (uid,) = RE(ptycho_plan)

    hdr = db[uid]
    docs = hdr.documents()
    # next(docs)  # repeat it until the end of iterator
    # hdr = db['<your uid>']
    docs = hdr.documents()
    for name, doc in docs:
        if name in ["resource", "datum"]:
            print(name, doc)

    tucsen.unstage()


