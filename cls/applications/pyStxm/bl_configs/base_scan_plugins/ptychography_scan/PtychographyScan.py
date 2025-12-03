"""
Created on Sep 26, 2016

@author: bergr
"""
import os.path
from pathlib import Path

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp

from bcm.devices.ophyd.e712_wavegen.e712_defines import *
from bcm.devices.ophyd.ad_utils import gen_list_of_row_change_img_indexs

from cls.applications.pyStxm.main_obj_init import MAIN_OBJ
from cls.scanning.BaseScan import BaseScan
from cls.utils.roi_dict_defs import *
from cls.utils.json_utils import dict_to_json
from cls.utils.rm_remote_files import remove_remote_files, break_paths_into_send_sized_strs
from cls.scan_engine.bluesky.bluesky_defs import bs_dev_modes
from bcm.devices.ophyd.qt.daqmx_counter_output import trig_src_types
from cls.utils.log import get_module_logger
from cls.utils.dict_utils import dct_get
from cls.types.stxmTypes import (
    scan_types,
    scan_sub_types,
    sample_positioning_modes,
    sample_fine_positioning_modes,
    detector_types
)
from cls.types.stxmTypes import H5_FILE_SUFFIX, TIFF_FILE_SUFFIX

from cls.applications.pyStxm.bl_configs.base_scan_plugins.fine_image_scans.SampleFineImageWithE712WavegenScan import BaseSampleFineImageWithE712WavegenScanClass

_logger = get_module_logger(__name__)

DO_SOFTWARE_SCAN = False

class BasePtychographyScanClass(BaseSampleFineImageWithE712WavegenScanClass):

    """a scan for executing a detector point scan in X and Y, it takes an existing instance of an XYZScan class"""

    def __init__(self, main_obj=None):
        """
        __init__(): description

        :returns: None
        """
        super().__init__(main_obj=MAIN_OBJ)
        self.inner_pnts = []
        self.outer_pnts = []
        self.dwell_setpoints_ms = []
        self.inner_posner = None
        self.outer_posner = None
        self.ev_first_flg = 0  # 0 == EV then Pol, 1 == Pol then EV, a flag so that the user can decide if they want the polarization to change every ev or vice versa
        self.e712_enabled = True
        self.e712_wdg = MAIN_OBJ.device("DNM_E712_WIDGET")
        self.e712_wdg.set_main_obj(MAIN_OBJ)
        # self.total_time_seconds = 0.0
        # self.num_ttl_pnts = 0
        self.prev_point_step_time = 0.001 #default of 1ms

    def set_ev_first_flg(self, val):
        """
        set the flag, 0 == EV then Pol, 1 == Pol then EV
        :param val:
        :return:
        """
        self.ev_first_flg = val

    def go_to_scan_start(self):
        """
        an API function that will be called if it exists for all scans
        call a specific scan start for fine scans
        """
        super().fine_scan_go_to_scan_start()
        return (True)

    def stop(self):
        """

        """
        self.e712_wdg.stop_wave_generator()

        # call the parents stop
        super().stop()

    def on_scan_done(self):
        """
        calls base class on_scan_done() then does some specific stuff
        call a specific on_scan_done for fine scans
        """
        super().on_scan_done()
        super().fine_scan_on_scan_done()
        suspnd_controller_fbk = self.main_obj.device("DNM_E712_SSPND_CTRLR_FBK")
        # renable E712 controller feedback of scan was aborted
        suspnd_controller_fbk.put(0)
        cam = self.main_obj.get_default_ptycho_cam()
        cam.unstage()

        # disable datarecoder
        self.e712_wdg.enable_data_recorder(False)
        #reset point step time
        self.e712_wdg.set_point_step_time_for_ptycho(self.prev_point_step_time)

        # move motors to somewhere before the start of the scan
        mtr_dct = self.determine_samplexy_posner_pvs()
        mtr_x = self.main_obj.device(mtr_dct["fx_name"])
        mtr_y = self.main_obj.device(mtr_dct["fy_name"])
        mtr_x.move(self.x_roi[SETPOINTS][0] - 5.0)
        mtr_y.move(self.y_roi[SETPOINTS][0] - 5.0)


    def pre_flight_chk(self):
        """
        before the scan plan is configured and executed it must first pass a pre flight check,
        to be implemented by inheriting class
        :return:
        """
        mtr_x = self.main_obj.get_sample_fine_positioner("X")
        mtr_y = self.main_obj.get_sample_fine_positioner("Y")
        if hasattr(mtr_x, "servo_power"):
            # toggle power to clear any errors if there are any
            mtr_x.servo_power.put(0)
            mtr_x.servo_power.put(1)
        if hasattr(mtr_y, "servo_power"):
            # toggle power to clear any errors if there are any
            mtr_y.servo_power.put(0)
            mtr_y.servo_power.put(1)

        cam = self.main_obj.get_default_ptycho_cam()
        temp = cam.get_temperature()

        # make sure temperature is -20 before allowing scan to execute
        # if(temp > -20.0):
        if temp > 50.0:
            _logger.warn(
                "cam temperature [%.2f C] is too warm to execute scan, must be -20.0C or less"
                % temp
            )
            self.display_message(
                "cam temperature [%.2f C] is too warm to execute scan, must be -20.0C or less"
                % temp
            )
            return False
        else:
            return True

    def init_subscriptions(self, ew, func, det_lst):
        """
        over ride the base init_subscriptions because we need to use the number of rows from the self.zz_roi instead of
        self.y_roi
        :param ew:
        :param func:
        :param det_lst is a list of detector ophyd objects
        :return:
        """
        #!!!!!!!!!!!!!!!!!!!!!!!!!!!!! for now connect only the first detector, in the future though this needs to setup an emitter for each selected detector
        #so that the detectors data can be stored and plottable items can be created and built as the scan progresses
        if len(det_lst) > 0 and hasattr(det_lst[0], 'name'):
            # counter_nm = det_lst[0].name
            # d = self.main_obj.device(counter_nm)
            d = det_lst[0]
            d.new_plot_data.connect(func)
            self._det_subscription = d

    def configure_devs(self, dets):
        """
        configure_devs(): description

        :param dets: dets description
        :type dets: dets type

        :returns: None
        """
        #super().configure_devs(dets)
        for d in dets:

            if DO_SOFTWARE_SCAN:
                if hasattr(d, "set_dwell"):
                    d.set_dwell(self.dwell)
                if hasattr(d, "set_config"):
                    d.set_config(self.y_roi["NPOINTS"], self.x_roi["NPOINTS"], is_pxp_scan=self.is_pxp)
                if hasattr(d, "setup_for_software_triggered"):
                    d.setup_for_software_triggered()
                if hasattr(d, "set_sequence_map"):
                    d.set_sequence_map(self.seq_map_dct)
            else:
                #if using E712 waveform gen
                # dwell is controlled by trigger pulse so set dwell to 0.0
                if hasattr(d, "set_dwell"):
                    d.set_dwell(0.0)
                if hasattr(d, "set_config"):
                    #d.set_config(self.y_roi["NPOINTS"], self.x_roi["NPOINTS"], is_pxp_scan=self.is_pxp, is_e712_wg_scan=True, pxp_single_trig=True)
                    d.set_config(self.y_roi["NPOINTS"], self.x_roi["NPOINTS"], is_pxp_scan=False,
                                 is_e712_wg_scan=True, pxp_single_trig=True)
                if hasattr(d, "setup_for_ntrigs_per_line"):
                    d.setup_for_ntrigs_per_line()
                if hasattr(d, "set_row_change_index_points"):
                    d.set_row_change_index_points(remove_last_point=True)
                if hasattr(d, "enable_data_read_for_ptychography"):
                    d.enable_data_read_for_ptychography(True)
                if hasattr(d, "init_indexs"):
                    # new image so reset row/col indexes for data it emits to plotter
                    d.init_indexs()
                if hasattr(d, "set_sequence_map"):
                    d.set_sequence_map(self.seq_map_dct)


    def make_scan_plan(self, dets, md=None, bi_dir=False):
        """
        override the default make_scan_plan to set the scan_type,
        :param dets:
        :param gate:
        :param md:
        :param bi_dir:
        :return:
        """
        self.configure_devs(dets)

        if DO_SOFTWARE_SCAN:
            return self.make_sw_pxp_stack_scan_plan(dets, md=md, bi_dir=bi_dir)
        else:
            return self.make_pxp_stack_scan_plan(dets, md=md, bi_dir=bi_dir)



    def determine_ptycho_cam_file_dir(self):
        """
        the Stack dir contains the path for the final nexus file, this function needs to determine
        what linux path that is so that the Area Detector IOC app running on Linux can write the tiff
        files to the same directory
        """
        import os
        from cls.utils.list_utils import remove_items

        stack_dir = dct_get(self.sp_db[SPDB_ACTIVE_DATA_OBJECT], ADO_CFG_STACK_DIR)
        nxs_file_path_parts = stack_dir.split("\\")
        cam_root_dir = dct_get(self.sp_db[SPDB_ACTIVE_DATA_OBJECT], ADO_CFG_PTYCHO_CAM_DATA_DIR)
        cam_fpath_parts = cam_root_dir.split("/")
        cam_fpath_parts = remove_items(cam_fpath_parts, '')
        lastdir = cam_fpath_parts[-1]
        strt_idx = nxs_file_path_parts.index(lastdir) + 1
        end_path = "/".join(nxs_file_path_parts[strt_idx:])
        cam_fpath = "/".join([cam_root_dir, end_path])
        datarec_fname = f"{nxs_file_path_parts[-1]}"

        self.set_current_scan_data_dir(stack_dir)
        return(cam_root_dir, cam_fpath, datarec_fname)

    def ad_cam_file_plugin_info(self, file_plugin, cam_fpath):
        """
        a convienince function to enable/disable and set the file paths for the plugin
        """
        self.set_ad_file_plugin_write_path(file_plugin, cam_fpath)
        # add a windows path for the file pluggin to check for existance
        #file_plugin.windows_write_path = pystxm_write_path
        file_plugin.file_number.put(0)
        file_plugin.auto_save.put(1)
        file_plugin.create_directory.put(-3)  # this will create at least 2 levels of directories if they do not already exist
        file_plugin.file_name.put(dct_get(self.sp_db[SPDB_ACTIVE_DATA_OBJECT], ADO_CFG_PREFIX))

    def set_ad_file_plugin_write_path(self, plugin, fpath):
        """
        set the file write paths for the plugin
        """
        plugin.file_path.put(fpath)
        plugin.write_path_template = fpath

    def make_pxp_stack_scan_plan(self, dets, md=None, bi_dir=False):
        """
        creates a scan plan that at its base uses the E712 waveform generator
        """
        dev_list = self.main_obj.main_obj[DEVICES].devs_as_list()

        self._bi_dir = bi_dir
        num_ttl_imgs = (
                len(self.inner_pnts)
                * len(self.outer_pnts)
                * self.y_roi[NPOINTS]
                * self.x_roi[NPOINTS]
        )
        #num_imgs_per_inner = self.y_roi[NPOINTS] * self.x_roi[NPOINTS] + self.y_roi[NPOINTS]  # there is an extra image for each row position change
        #num_imgs_per_inner = (self.y_roi[NPOINTS] + 1) * (self.x_roi[NPOINTS] + 1)# there is an extra image for each row position change and a full extra row so SIS3820 is triggered correctly
        num_imgs_per_inner = (self.y_roi[NPOINTS]) * (self.x_roi[NPOINTS] + 1)  # there is an extra image for each row position change and a full extra row so SIS3820 is triggered correctly

        cam = self.main_obj.get_default_ptycho_cam()
        # set the output file path and configure cam
        pystxm_write_path = dct_get(self.sp_db[SPDB_ACTIVE_DATA_OBJECT], ADO_CFG_STACK_DIR)
        cam_root_dir, cam_fpath, datarec_fname = self.determine_ptycho_cam_file_dir()
        img_details = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_IMG_DETAILS)
        is_hdf5 = False
        if img_details["image.format"].find("HDF5") > -1:
            is_hdf5 = True
            self.ad_cam_file_plugin_info(cam.hdf5_file_plugin, cam_fpath)
            self.ad_cam_file_plugin_info(cam.tif_file_plugin, cam_fpath)
        else:
            self.ad_cam_file_plugin_info(cam.hdf5_file_plugin, cam_fpath)
            self.ad_cam_file_plugin_info(cam.tif_file_plugin, cam_fpath)

        # # self.file_plugin.compression.put(6)  # set to LZ4
        # # cam.file_plugin.compression.put(0)  # set to NONE

        cam.cam.image_mode.put(1)  # multiple
        cam.cam.num_images.put(num_imgs_per_inner)
        cam.cam.trigger_mode.put(1)  # standard╒
        cam.cam.array_counter.put(0)
        cam.set_dwell(self.dwell)
        cam.stage()
        # cam.file_plugin.file_template.put("%s%s_%3.3d.h5")
        #enabling a particular file plugin must come oadfter it has been staged as both
        #file plugins are enabled by default when stage() is called
        if is_hdf5:
            cam.enable_file_plugin_by_name("HDF5")  # HDF5
        else:
            cam.enable_file_plugin_by_name("TIFF")  # TIFF

        if md is None:
            _meta = self.make_standard_metadata(
                entry_name="entry0", scan_type=self.scan_type, dets=dets
            )

            _meta["dflt_ptycho_cam"] = cam.name
            if is_hdf5:
                _meta["det_data_ftype"] = H5_FILE_SUFFIX
            else:
                _meta["det_data_ftype"] = TIFF_FILE_SUFFIX

            _meta["posfbk_filepath"] = datarec_fname
            _meta["num_ttl_imgs"] = num_ttl_imgs
            _meta["img_idx_map"] = dict_to_json(self.img_idx_map)
            if is_hdf5:
                _meta["det_filepath"] = (
                        cam.hdf5_file_plugin.file_path.get()
                        + cam.hdf5_file_plugin.file_name.get()
                        + f"_%06d.{H5_FILE_SUFFIX}" % 0
                )
            else:
                _meta["det_filepath"] = (
                        cam.tif_file_plugin.file_path.get()
                        + cam.tif_file_plugin.file_name.get()
                        + f"_%06d.{TIFF_FILE_SUFFIX}" % 0
                )
            md = {"metadata": dict_to_json(_meta)}

        @bpp.baseline_decorator(dev_list)
        @bpp.run_decorator(md=md)
        def do_scan():
            pystxm_write_path = dct_get(self.sp_db[SPDB_ACTIVE_DATA_OBJECT], ADO_CFG_STACK_DIR)
            # img_cntr = 0
            # dwell_sec = self.dwell * 0.001
            outer_posner = self.main_obj.device(self.outer_posner)
            inner_posner = self.main_obj.device(self.inner_posner)
            shutter = self.main_obj.device("DNM_SHUTTER")
            e712_dev = self.main_obj.device("DNM_E712_OPHYD_DEV")
            #overide default assignment of num_cycles which adds 1
            #self.e712_wdg.set_num_cycles(self.y_roi[NPOINTS], do_extra=False)
            img_cntr = 0
            dwell_cntr = 0
            file_removal_list = []
            yield from bps.trigger(cam)
            outer_cntr = 0
            dwell_cntr = 0
            for outer_lst in self.outer_pnts:
                inner_lst = self.inner_pnts[outer_cntr]
                for dev_dct in outer_lst:
                    #{"dev": epu_pol_dev, "setpoint": pol}
                    # the virtual EPU motors sometimes do not respond with proper status if asked to move to a
                    # setpoint it is already at so skip it if it is already where we want it
                    if dev_dct["dev"].get_position() != dev_dct["setpoint"]:
                        yield from bps.mv(dev_dct["dev"], dev_dct["setpoint"], group="outer")
                yield from bps.wait("outer")

                inner_cntr = 0
                for i_lst in inner_lst:
                    #make sure stages are ready for next iteration of the wave generator
                    self.go_to_scan_start()

                    for d in dets:
                        yield from bps.trigger(d)

                        yield from bps.stage(d)
                        if hasattr(d, "kickoff"):
                            yield from bps.kickoff(d)

                    yield from bps.sleep(1.0)
                    #set camera to acquiring
                    #cam.cam.acquire.put(1)
                    yield from bps.mv(cam.cam.acquire, 1, group="CAM")
                    yield from bps.wait("CAM")

                    # adjust the filepaths for camera images and E712 datarecorder position data
                    fpath = f"{cam_fpath}/{outer_cntr:02d}_{inner_cntr:02d}"
                    if is_hdf5:
                        suffix = H5_FILE_SUFFIX
                        self.set_ad_file_plugin_write_path(cam.hdf5_file_plugin, fpath)
                    else:
                        suffix = TIFF_FILE_SUFFIX
                        self.set_ad_file_plugin_write_path(cam.tif_file_plugin, fpath)

                    _dr_fname = f"{fpath}/{datarec_fname}_{outer_cntr:02d}_{inner_cntr:02d}.dat"
                    #self.e712_wdg.set_data_recorder_fpath(f"{fpath}/{outer_cntr:02d}_{inner_cntr:02d}_{datarec_fname}" % img_cntr)
                    self.e712_wdg.set_data_recorder_fpath(_dr_fname)

                    fprefix = datarec_fname.replace("_%03d.dat","")
                    # r_idx_lst, r_fnames = gen_list_of_row_change_img_indexs(self.x_roi[NPOINTS], self.y_roi[NPOINTS], first_img_idx=img_cntr*num_imgs_per_inner,
                    #                                                         subdir=f"{pystxm_write_path}\\{outer_cntr:02d}_{inner_cntr:02d}", fprefix=fprefix, fsuffix=suffix)
                    r_idx_lst, r_fnames = gen_list_of_row_change_img_indexs(self.x_roi[NPOINTS], self.y_roi[NPOINTS], first_img_idx=img_cntr * num_imgs_per_inner,
                                                                            subdir=f"{fpath}", fprefix=fprefix, fsuffix=suffix)
                    file_removal_list.append(r_fnames)
                    # print('PtychographyScanClass: moving inner posner [%s] to [%.2f]' % (inner_posner.get_name(), ip))
                    #yield from bps.mv(inner_posner, ip)
                    for dev_dct in i_lst:
                        # {"dev": epu_pol_dev, "setpoint": pol}
                        # the virtual EPU motors sometimes do not respond with proper status if asked to move to a
                        # setpoint it is already at so skip it if it is already where we want it
                        if dev_dct["dev"].get_position() != dev_dct["setpoint"]:
                            yield from bps.mv(dev_dct["dev"], dev_dct["setpoint"], group="inner")
                    yield from bps.wait("inner")
                    # this starts the wavgen and waits for it to finish without blocking the Qt event loop
                    # create an event bundle
                    shutter.open()
                    yield from bps.mv(e712_dev.run, 1)
                    shutter.close()


                    # read the positions of the motors
                    yield from bps.create("primary")

                    for d in dets:
                        yield from bps.read(d)
                        if hasattr(d, "init_indexs"):
                            # new image so reset row/col indexes for data it emits to plotter
                            d.init_indexs()
                    for dev_dct in outer_lst:
                        yield from bps.read(dev_dct["dev"])
                    for dev_dct in i_lst:
                        yield from bps.read(dev_dct["dev"])
                    yield from bps.save()
                    img_cntr += 1
                    inner_cntr += 1

                    for d in dets:
                        yield from bps.unstage(d)

                    # add a slight delay between inner changes otherwise ADTucsen prodces incorrect number of images
                    #yield from bps.sleep(1.0)

                dwell_cntr += 1
                outer_cntr += 1


            print("PtychographyScanClass: done closing shutter")
            shutter.close()
            yield from bps.unstage(cam)

            for d in dets:
                #now disable read for ptycho
                if hasattr(d, "enable_data_read_for_ptychography"):
                    d.enable_data_read_for_ptychography(False)

            #remove these image files
            self.remove_row_change_images(file_removal_list)
            # print("PtychographyScanClass: make_scan_plan Leaving")

        return (yield from do_scan())

    # def remove_row_change_images(self, remove_lst):
    #     """
    #     takes a list of windows based paths to the image files that were produced when th erows changed
    #     by the stages during the ptycho scan
    #     """
    #     for flist in remove_lst:
    #         fstrs = break_paths_into_send_sized_strs(flist)
    #         remove_remote_files(remote_host="IOC1610-310", file_paths=fstrs, port=5066)

    def remove_row_change_images(self, data_dir, remove_lst):
        """
        takes a list of windows based paths to the image files that were produced when th erows changed
        by the stages during the ptycho scan
        """
        self.remove_files.emit(data_dir, remove_lst)



    def make_sw_pxp_stack_scan_plan(self, dets, md=None, bi_dir=False):
        """

        """
        dev_list = self.main_obj.main_obj[DEVICES].devs_as_list()

        self._bi_dir = bi_dir
        num_ttl_imgs = (
            len(self.inner_pnts)
            * len(self.outer_pnts)
            * self.y_roi[NPOINTS]
            * self.x_roi[NPOINTS]
        )
        cam = self.main_obj.get_default_ptycho_cam()
        # set the output file path and configure cam
        pystxm_write_path = dct_get(self.sp_db[SPDB_ACTIVE_DATA_OBJECT], ADO_CFG_STACK_DIR)
        cam_root_dir, cam_fpath = self.determine_ptycho_cam_file_dir()
        cam.file_plugin.read_path_template = cam_fpath
        _cur_datadir = pystxm_write_path
        cam.file_plugin.file_path.put(cam_fpath)
        #cam.file_plugin.write_path_template = cam_fpath
        cam.file_plugin.write_path_template = cam_fpath
        #add a windows path for the file pluggin to check for existance
        cam.file_plugin.windows_write_path = pystxm_write_path
        cam.file_plugin.file_number.put(0)
        cam.file_plugin.auto_save.put(1)
        cam.file_plugin.create_directory.put(-3)  # this will create at least 2 levels of directories if they do not already exist
        # self.file_plugin.compression.put(6)  # set to LZ4
        # cam.file_plugin.compression.put(0)  # set to NONE
        cam.set_dwell(self.dwell)
        cam.cam.image_mode.put(0)  # single
        cam.cam.trigger_mode.put(0)  # internal
        cam.cam.array_counter.put(0)  # reset counter to 0 for this run
        cam.stage()
        #cam.file_plugin.file_template.put("%s%s_%3.3d.h5")
        cam.file_plugin.file_name.put(dct_get(self.sp_db[SPDB_ACTIVE_DATA_OBJECT], ADO_CFG_PREFIX))
        if md is None:
            _meta = self.make_standard_metadata(
                entry_name="entry0", scan_type=self.scan_type, dets=dets
            )
            _meta["dflt_ptycho_cam"] = cam.name
            _meta["num_ttl_imgs"] = num_ttl_imgs
            _meta["img_idx_map"] = dict_to_json(self.img_idx_map)
            _meta["det_filepath"] = (
                cam.file_plugin.file_path.get()
                + cam.file_plugin.file_name.get()
                + f"_%06d.{H5_FILE_SUFFIX}" % 0
            )
            md = {"metadata": dict_to_json(_meta)}

            # md = {'metadata': dict_to_json(
            #     self.make_standard_metadata(entry_name='entry0', scan_type=self.scan_type))}

        @bpp.baseline_decorator(dev_list)
        @bpp.run_decorator(md=md)
        def do_scan():
            # img_cntr = 0
            # dwell_sec = self.dwell * 0.001
            outer_posner = self.main_obj.device(self.outer_posner)
            inner_posner = self.main_obj.device(self.inner_posner)
            mtr_x = self.main_obj.get_sample_fine_positioner("X")
            mtr_y = self.main_obj.get_sample_fine_positioner("Y")
            shutter = self.main_obj.device("DNM_SHUTTER")
            x_roi = self.sp_db["X"]
            y_roi = self.sp_db["Y"]
            shutter.open()
            img_cntr = 0
            dwell_cntr = 0
            #dets.append(mtr_x)
            #dets.append(mtr_y)
            for op in self.outer_pnts:
                # print('PtychographyScanClass: moving outter posner [%s] to [%.2f]' % (outer_posner.get_name(), op))
                dwell_ms = self.dwell_setpoints_ms[dwell_cntr]
                for d in dets:
                    if hasattr(d, "set_dwell"):
                        d.set_dwell(dwell_ms)

                yield from bps.mv(outer_posner, op)
                for ip in self.inner_pnts:
                    # print('PtychographyScanClass: moving inner posner [%s] to [%.2f]' % (inner_posner.get_name(), ip))
                    yield from bps.mv(inner_posner, ip)
                    # set aquisition time
                    for y in y_roi['SETPOINTS']:
                        yield from bps.mv(mtr_y, y)
                        # print('PtychographyScanClass: moving Y to [%.3f]' % y)
                        for x in x_roi['SETPOINTS']:
                            # print('PtychographyScanClass: moving X to [%.3f]' % x)
                            yield from bps.mv(mtr_x, x)
                            yield from bps.trigger_and_read( dets )
                            img_cntr += 1
                            print("PtychographyScanClass: img_counter = [%d]" % img_cntr)
                dwell_cntr += 1

            print("PtychographyScanClass: done closing shutter")
            shutter.close()
            yield from bps.unstage(cam)

        return (yield from do_scan())

    def configure(self, wdg_com, sp_id=0, line=False, restore=True, z_enabled=False):
        """
        configure(): description

        :param sp_db: sp_db description
        :type sp_db: sp_db type

        :param line=False: line=False description
        :type line=False: line=False type

        :param restore=True: restore=True description
        :type restore=True: restore=True type

        :param z_enabled=False: z_enabled=False description
        :type z_enabled=False: z_enabled=False type

        :returns: None
        """
        # call the base class configure so that all member vars can be initialized
        # sanity check that the scan has a camera it can work with
        cam = self.main_obj.get_default_ptycho_cam()
        if cam is None:
            _logger.error(f"There is no default ptycho camera configured in the device database")
            return (False)

        # make sure latest selections are all pushed to the controller
        self.e712_wdg.set_datarecorder_defaults_for_ptycho()
        self.prev_point_step_time = self.e712_wdg.get_point_step_time()
        self.e712_wdg.set_point_step_time_for_ptycho(0.001)
        self.e712_wdg.enable_data_recorder(True)
        ret = super().configure(wdg_com, sp_id=sp_id, line=False)
        self.config_basic_2d(wdg_com, sp_id=sp_id, z_enabled=False)
        self._current_img_idx = 0
        self.is_pxp = True


        ######################## NEW ######################################################################
        # this img_idx_map is used in teh on_counter_changed handler to put the data in the correct array
        self.inner_pnts = []
        self.outer_pnts = []
        self.dwell_setpoints_ms = []

        energy_dev = self.main_obj.device("DNM_ENERGY_DEVICE")
        epu_pol_dev = self.main_obj.device("DNM_EPU_POLARIZATION")
        epu_offset_dev = self.main_obj.device("DNM_EPU_OFFSET")
        epu_angle_dev = self.main_obj.device("DNM_EPU_ANGLE")
        self.outer_pnts = []
        self.inner_pnts = []
        if self.ev_first_flg == 0:
            # ev is on the outer loop
            outer_nm = "e_idx"
            inner_nm = "pol_idx"

            for ev_roi in self.e_rois:
                for ev_sp in ev_roi[SETPOINTS]:
                    #self.outer_pnts.append(ev_sp)
                    self.dwell_setpoints_ms.append(ev_roi[DWELL])
                    self.outer_pnts.append([{"dev": energy_dev, "setpoint":ev_sp}])#, "dwell": self.dwell})

                    self.dwell = ev_roi[DWELL]
                    # pol_setpoints = self.e_rois[0][EPU_POL_PNTS]
                    pol_setpoints = ev_roi[EPU_POL_PNTS]
                    # self.dwell = self.e_rois[0][DWELL]
                    pnt = 0
                    inner_lst = []
                    for pol in pol_setpoints:
                        # self.inner_pts.append(pol)
                        offset = ev_roi[EPU_OFF_PNTS][pnt]
                        angle = ev_roi[EPU_ANG_PNTS][pnt]
                        inner_lst.append([{"dev": epu_pol_dev, "setpoint": pol},
                                              {"dev": epu_offset_dev, "setpoint": offset},
                                              {"dev": epu_angle_dev,  "setpoint": angle}])
                        pnt += 1
                    self.inner_pnts.append(inner_lst)
            self.outer_posner = "DNM_ENERGY"
            self.inner_posner = "DNM_EPU_POLARIZATION"
        else:
            # polarization is on the outer loop
            inner_nm = "e_idx"
            outer_nm = "pol_idx"

            for ev_roi in self.e_rois:
                self.dwell = ev_roi[DWELL]
                # pol_setpoints = self.e_rois[0][EPU_POL_PNTS]
                pol_setpoints = ev_roi[EPU_POL_PNTS]
                # self.dwell = self.e_rois[0][DWELL]
                pnt = 0

                for pol in pol_setpoints:
                    # self.inner_pts.append(pol)
                    offset = ev_roi[EPU_OFF_PNTS][pnt]
                    angle = ev_roi[EPU_ANG_PNTS][pnt]
                    self.outer_pnts.append([{"dev": epu_pol_dev, "setpoint": pol},
                                      {"dev": epu_offset_dev, "setpoint": offset},
                                      {"dev": epu_angle_dev, "setpoint": angle}])
                    pnt += 1
                    inner_lst = []
                    for ev_sp in ev_roi[SETPOINTS]:
                        #self.outer_pnts.append(ev_sp)
                        self.dwell_setpoints_ms.append(ev_roi[DWELL])
                        inner_lst.append([{"dev": energy_dev, "setpoint":ev_sp}])#, "dwell": self.dwell})
                    self.inner_pnts.append(inner_lst)



            self.outer_posner = "DNM_EPU_POLARIZATION"
            self.inner_posner = "DNM_ENERGY"

        self.ev_setpoints = dct_get(wdg_com, SPDB_SINGLE_LST_EV_ROIS)
        e_roi = self.e_rois[0]
        self.numEPU = len(dct_get(e_roi, EPU_POL_PNTS))
        if self.numEPU < 1:
            self.numEPU = 1

        self.img_idx_map = {}
        indiv_img_idx = 0
        spid = list(self.sp_rois.keys())[0]
        sp_idx = 0
        offset = 0
        gt_mtr = self.main_obj.device('DNM_GONI_THETA')
        if (gt_mtr):
            gt_sp = gt_mtr.get_position()
        else:
            gt_sp = 0.0
        # for future Ptycho/Tomo
        # for gt_sp in self.gt_roi[SETPOINTS]:
        #     for i in range(len(self.outer_pnts)):
        #         for j in range(self.inner_pts):
        #             for y in self.y_roi[SETPOINTS]:
        #                 for x in self.x_roi[SETPOINTS]:
        #                     self.img_idx_map['%d' % indiv_img_idx] = {outer_nm: i, inner_nm: j, 'sp_idx': sp_idx, 'sp_id': spid,
        #                                                               'entry': 'entry%d' % (sp_idx),
        #                                                               'rotation_angle': gt_sp}
        #
        #                     indiv_img_idx += 1
        ado = dct_get(self.sp_db, SPDB_ACTIVE_DATA_OBJECT)
        fprefix = ado["CFG"]["DATA_FILE_NAME"].split(".")[0]
        for i in range(len(self.outer_pnts)):
            for j in range(len(self.inner_pnts)):
                for y in self.y_roi[SETPOINTS]:
                    for x in self.x_roi[SETPOINTS]:
                        self.img_idx_map['%d' % indiv_img_idx] = {outer_nm: i, inner_nm: j, 'sp_idx': sp_idx, 'sp_id': spid,
                                                                  'entry': 'entry%d' % (sp_idx),
                                                                  'rotation_angle': gt_sp,
                                                                  'filename': f"{fprefix}_{indiv_img_idx:06d}.{H5_FILE_SUFFIX}"}

                        indiv_img_idx += 1

        # self.img_idx_map = self.gen_spectrum_scan_seq_map(
        #     len(self.ev_setpoints), self.sp_id_list, num_pol=self.numEPU)

        self.seq_map_dct = self.generate_2d_seq_image_map(1, 1, self.y_roi[NPOINTS], self.x_roi[NPOINTS], lxl=False)

        # depending on the scan size the positioners used in the scan will be different, use a singe
        # function to find out which we are to use and return those names in a dct
        dct = self.determine_samplexy_posner_pvs(force_fine_scan=True)

        # # depending on the current samplpositioning_mode perform a different configuration
        # if self.sample_positioning_mode == sample_positioning_modes.GONIOMETER:
        #     # self.seq_map_dct = self.generate_2d_seq_image_map(
        #     #     self.numE, self.zy_roi[NPOINTS], self.zx_roi[NPOINTS], lxl=self.is_lxl
        #     # )
        #     if self.use_hdw_accel:
        #         self.config_for_goniometer_scan_hdw_accel(dct)
        #     else:
        #         self.config_for_goniometer_scan(dct)
        #
        # else:
        #     if self.sample_positioning_mode == sample_positioning_modes.GONIOMETER:
        #         # self.seq_map_dct = self.generate_2d_seq_image_map(
        #         #     self.numE,
        #         #     self.zy_roi[NPOINTS],
        #         #     self.zx_roi[NPOINTS],
        #         #     lxl=self.is_lxl,
        #         # )
        #         # goniometer_zoneplate mode
        #         self.configure_for_zxzy_fine_scan_hdw_accel(dct)
        #     elif (self.sample_positioning_mode == sample_positioning_modes.COARSE) and (
        #             self.fine_sample_positioning_mode
        #             == sample_fine_positioning_modes.ZONEPLATE
        #     ):
        #         # self.seq_map_dct = self.generate_2d_seq_image_map(
        #         #     self.numE,
        #         #     self.zy_roi[NPOINTS],
        #         #     self.zx_roi[NPOINTS],
        #         #     lxl=self.is_lxl,
        #         # )
        #         self.configure_for_coarse_zoneplate_fine_scan_hdw_accel(dct)
        #     else:
        #         # coarse_samplefine mode
        #         # self.seq_map_dct = self.generate_2d_seq_image_map(
        #         #     self.numE, self.y_roi[NPOINTS], self.x_roi[NPOINTS], lxl=self.is_lxl
        #         # )
        #         self.configure_for_samplefxfy_fine_scan_hdw_accel(dct)

        self.move_zpxy_to_its_center()

        return(ret)
        # if not ret:
        #     return(ret)
        #
        # self.is_pxp = True
        #
        # self.config_basic_2d(wdg_com, sp_id=sp_id, z_enabled=False)
        #
        # ######################## NEW ######################################################################
        # # this img_idx_map is used in teh on_counter_changed handler to put the data in the correct array
        # self.inner_pts = []
        # self.outer_pnts = []
        #
        # if self.ev_first_flg == 0:
        #     # ev is on the outer loop
        #     outer_nm = "e_idx"
        #     inner_nm = "pol_idx"
        #     self.outer_pnts = []
        #     for ev_roi in self.e_rois:
        #         for ev_sp in ev_roi[SETPOINTS]:
        #             self.outer_pnts.append(ev_sp)
        #     pol_setpoints = self.e_rois[0][EPU_POL_PNTS]
        #     self.dwell = self.e_rois[0][DWELL]
        #     for pol in pol_setpoints:
        #         self.inner_pts.append(pol)
        #     self.outer_posner = "DNM_ENERGY"
        #     self.inner_posner = "DNM_EPU_POLARIZATION"
        # else:
        #     # polarization is on the outer loop
        #     inner_nm = "e_idx"
        #     outer_nm = "pol_idx"
        #     for ev_roi in self.e_rois:
        #         for ev_sp in ev_roi[SETPOINTS]:
        #             self.inner_pts.append(ev_sp)
        #
        #     pol_setpoints = self.e_rois[0][EPU_POL_PNTS]
        #     self.dwell = self.e_rois[0][DWELL]
        #     for pol in pol_setpoints:
        #         self.outer_pnts.append(pol)
        #     self.outer_posner = "DNM_EPU_POLARIZATION"
        #     self.inner_posner = "DNM_ENERGY"
        #
        # self.img_idx_map = {}
        # indiv_img_idx = 0
        # spid = list(self.sp_rois.keys())[0]
        # sp_idx = 0
        # offset = 0
        # gt_mtr = self.main_obj.device("DNM_GONI_THETA")
        # if gt_mtr:
        #     gt_sp = gt_mtr.get_position()
        # else:
        #     gt_sp = 0.0
        #
        # # for future Ptycho/Tomo
        # # for gt_sp in self.gt_roi[SETPOINTS]:
        # #     for i in range(len(self.outer_pnts)):
        # #         for j in range(self.inner_pts):
        # #             for y in self.y_roi[SETPOINTS]:
        # #                 for x in self.x_roi[SETPOINTS]:
        # #                     self.img_idx_map['%d' % indiv_img_idx] = {outer_nm: i, inner_nm: j, 'sp_idx': sp_idx, 'sp_id': spid,
        # #                                                               'entry': 'entry%d' % (sp_idx),
        # #                                                               'rotation_angle': gt_sp}
        # #
        # #                     indiv_img_idx += 1
        #
        # finex_nm = self.main_obj.get_sample_fine_positioner("X").get_name()
        # finey_nm = self.main_obj.get_sample_fine_positioner("Y").get_name()
        # self.x_roi[POSITIONER] = finex_nm
        # self.y_roi[POSITIONER] = finey_nm
        #
        # for i in range(len(self.outer_pnts)):
        #     for j in range(len(self.inner_pts)):
        #         for y in self.y_roi[SETPOINTS]:
        #             for x in self.x_roi[SETPOINTS]:
        #                 self.img_idx_map["%d" % indiv_img_idx] = {
        #                     outer_nm: i,
        #                     inner_nm: j,
        #                     "sp_idx": sp_idx,
        #                     "sp_id": spid,
        #                     "entry": "entry%d" % (sp_idx),
        #                     "rotation_angle": gt_sp,
        #                 }
        #
        #                 indiv_img_idx += 1
        #     # if (self.numEPU is 1):
        #     #     offset += 1
        #     # else:
        #     #     offset += 2
        #
        # #####################################################################################
        #
        # self.seq_map_dct = self.,(
        #     1, self.y_roi[NPOINTS], self.x_roi[NPOINTS], lxl=False
        # )
        #
        # self.move_zpxy_to_its_center()
        # self.finish_setup()
        #
        # return(ret)

