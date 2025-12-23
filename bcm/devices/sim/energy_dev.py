
import time

import math
from PyQt5 import QtCore, QtGui, QtWidgets

from ophyd import Component as Cpt, Device
from ophyd.signal import Signal
from ophyd.status import DeviceStatus


ABS_MIN_A0 = 100.0  # Minimum allowable A0
ABS_MAX_A0 = 5000.0  # Maximum allowable A0


class Sigs(QtCore.QObject):
    focus_params_changed = QtCore.pyqtSignal(dict)


class FocusCalculations(object):
    """
    Class to handle focus calculations for zoneplates.
    """
    def __init__(self, prefix, name='', parent=None):
        super().__init__(parent, name=name)
        self._sigs = Sigs()
        self.focus_params_changed = self._sigs.focus_params_changed
        self.zoneplate_def = {}
        self.osa_def = {}
        self.A0 = ABS_MAX_A0
        self.delta_A0 = 0.0
        self.zpz_adjust = 0.0
        self.min_A0 = ABS_MIN_A0  # Minimum allowable A0
        self.max_A0 = ABS_MAX_A0
        self._FL = 0.0
        self.zpz_for_osa_focussed = 0.0
        self.zpz_for_sample_focussed = 0.0
        self._defocus_beam_setpoint_um = 0.0  # desired defocus beam in micrometers
        self._defocus_um = 0.0 # actual defocus calc result in micrometers

    def emit_focus_params_changed(self):
        params = {
            'zoneplate_def': self.zoneplate_def,
            'osa_def': self.osa_def,
            'FL': self._FL,
            'min_A0': self.min_A0,
            'A0': self.A0,
            'max_A0': self.max_A0,
            'delta_A0': self.delta_A0,
            'zpz_adjust': self.zpz_adjust,
            "defocus_beam_setpoint_um": self._defocus_beam_setpoint_um,
            "defocus_beam_um": self._defocus_um,
            "zpz_for_osa_focussed": self.zpz_for_osa_focussed,
            "zpz_for_sample_focussed": self.zpz_for_sample_focussed,
        }
        self.focus_params_changed.emit(params)

    def update_min_a0(self, val: float):
        """
        Update the min_A0 value
        :param val: New ,min_A0 value
        """
        if val < ABS_MIN_A0:
            _logger.warn(f"Attempted to set min_A0 to {val}, which is below absolute minimum of {ABS_MIN_A0}. Setting to {ABS_MIN_A0}.")
        else:
            self.min_A0 = val
        # self.emit_focus_params_changed()

    def calc_focal_length(self, energy):
        """
        f = A1 * E
        """

        if energy and self.zoneplate_def:
            if 'zpA1' in self.zoneplate_def:
                # ignore the sign of A1
                f = math.fabs(self.zoneplate_def["zpA1"]) * energy
                self._FL = f
                # self.emit_focus_params_changed()
                return f
            else:
                raise ValueError(
                    "Zoneplate definition does not contain 'zpA1' key and as such may not have been initialized yet with a zoneplate definition.")

    def get_focal_length_as_zpz_position(self) -> float:
        """
        Get the current focal length (FL)
        :return: Current focal length (FL)
        """
        self._FL_as_zpz_pos = 0.0 - self._FL
        if not self._FL_as_zpz_pos == 0.0:
            self.emit_focus_params_changed()
        return self._FL_as_zpz_pos

    def calc_delta_focus_position(self, energy: float, desired_focus_position: float) -> float:
        """
        Calculate the change in focal length (delta_a0) required to achieve the desired focal length for a given energy.
        :param desired_focal_length: Desired focal length
        :param energy: Energy in eV
        :return: Change in focal length (delta_a0)
        """
        current_focal_length = 0.0 - (math.fabs(self.calc_focal_length(energy)) - (self.A0 + self.delta_A0))
        delta_focus_pos = desired_focus_position - current_focal_length
        # self.update_a0_for_focus(delta_focus_pos)
        return delta_focus_pos

    def calc_new_coarse_z_pos_for_focus(self, energy: float, cur_cz_pos: float, desired_focus_position: float) -> float:
        """
        Calculate the new coarse z position needed to achieve focus at the desired focal length for a given energy.
        :param cur_cz_pos: Current coarse z position
        :param delta_a0: Change in focal length required to achieve focus
        :return: New coarse z position
        """
        delta_focus_pos = self.calc_delta_focus_position(energy, desired_focus_position)
        new_cz_pos = cur_cz_pos - delta_focus_pos
        return new_cz_pos

    def calc_new_zoneplate_z_pos_for_focus(self, energy: float) -> float:
        """
        NOTE: Focal length is equal to OSA in focus, calc new zpz position for current energy, Ao and delta_A0

        Calculate the new zoneplate z position needed to achieve focus at the desired focal length for a given energy.
        :param focal_length: Desired focal length
        :param a0: Current focal length
        :param delta_a0: Change in focal length required to achieve focus
        :return: New zoneplate z position
        """
        focal_length = self.calc_focal_length(energy)
        if focal_length:
            new_zp_z_pos = 0.0 - math.fabs((focal_length + self._defocus_um) + self.zpz_adjust) + (self.A0 + self.delta_A0)
            self.zpz_for_sample_focussed = new_zp_z_pos
            self.emit_focus_params_changed()
            return new_zp_z_pos
        else:
            return None

    def calc_new_zpz_for_osa_focussed(self, energy: float) -> float:
        """
        Calculate the new zoneplate z position needed to achieve focus at the desired focal length for a given energy when OSA is focused.
        :param energy: Energy in eV
        :return: New zoneplate z position
        """
        focal_length = self.calc_focal_length(energy)
        if focal_length:
            #new_zp_z_pos = 0.0 - (math.fabs(focal_length) - (self.zpz_adjust + self.delta_A0))
            new_zp_z_pos = 0.0 - math.fabs(focal_length + self._defocus_um)
            self.zpz_for_osa_focussed = new_zp_z_pos
            self.emit_focus_params_changed()
            return new_zp_z_pos
        else:
            return None



class EnergyDevice(FocusCalculations, Device):
    """"
    energy_dev_dict = {
                "a0_dev": a0_dev,
                "delta_a0_dev": delta_a0_dev,
                "zpz_adjust_dev": zpz_adjust_dev,
                "defocus_beam_dev": defocus_beam_dev,
                "energy_posner": energy_posner,
                "zpz_posner": zpz_posner,
                "cz_posner": cz_posner
    }
    """

    def __init__(self, prefix, name, energy_dev_dict=None):
        super(EnergyDevice, self).__init__(prefix, name=name)
        self.dcs_name = prefix + "_EnergyDevice"

        self.energy_posner = energy_dev_dict['energy_posner']
        self.zpz_posner = energy_dev_dict['zpz_posner']
        self.cz_posner = energy_dev_dict['cz_posner']

        self.a0_dev = energy_dev_dict['a0_dev']
        self.delta_a0_dev = energy_dev_dict['delta_a0_dev']
        self.zpz_adjust_dev = energy_dev_dict['zpz_adjust_dev']
        self.defocus_beam_dev = energy_dev_dict['defocus_beam_dev']
        self.focal_len_dev = energy_dev_dict['focal_len_dev']
        self.zp_a1_dev = energy_dev_dict['zp_a1_dev']
        self.a0_max_dev = energy_dev_dict['a0_max_dev']
        self.calcd_zpz_dev = energy_dev_dict['calcd_zpz_dev']
        self.zp_focus_mode_dev = energy_dev_dict["zp_focus_mode_dev"]

        self._enable_fl_change_on_energy_change = True
        self.focus_mode = 'OSA'  # or 'SAMPLE'
        self.FLMode_0 = 0.0
        self.FLMode_1 = 0.0

        skip_lst = ['OphydAttrList', 'move', 'put', 'set', 'stop']
        for attr in dir(self.energy_posner):
            if attr.startswith('_') or (attr in skip_lst):
                continue
            val = getattr(self.energy_posner, attr)
            if attr.find("parent") > -1:
                continue
            if callable(val):
                setattr(self, attr, val)


    def get_name(self):
        return self.name

    def update_focus_calcs(self):
        """
        a function that can be called to make sure all relevant focus calcs are executed when a param changes
        """
        energy = self.energy_posner.get_position()
        self.calculate_focal_length(energy)
        self.calc_new_zoneplate_z_pos_for_focus(energy)
        self.update_cacld_zpz_pos()
        self.calc_new_zpz_for_osa_focussed(energy)


    def update_zp_def(self, zp_def: dict):
        """
        Update the zoneplate definition
        :param zp_def: New zoneplate definition
        """
        self.zoneplate_def = zp_def
        self.emit_focus_params_changed()

    def update_osa_def(self, osa_def: dict):
        """
        Update the OSA definition
        :param osa_def: New OSA definition
        """
        self.osa_def = osa_def
        self.emit_focus_params_changed()

    def get_a0(self) -> float:
        """
        Get the current focal length (A0)
        :return: Current focal length (A0)
        """
        self.update_a0(self.a0_dev.get())
        return self.A0

    def get_delta_a0(self) -> float:
        """
        Get the current change in focal length (delta_a0)
        :return: Current change in focal length (delta_a0)
        """
        delta_a0 = self.delta_a0_dev.get()
        self.update_delta_a0(delta_a0)
        return delta_a0

    def get_focal_length(self) -> float:
        """
        Get the current focal length (FL)
        :return: Current focal length (FL)
        """
        return math.fabs(self._FL)

    def update_a0(self, a0: float):
        """
        Update the a0 value
        :param a0: New a0 value
        """
        self.A0 = a0
        self.a0_dev.put(a0)
        self.update_delta_a0(0.0)
        self.update_focus_calcs()

    def update_delta_a0(self, delta_a0: float):
        """
        Update the delta_a0 value
        :param delta_a0: New delta_a0 value
        """
        self.delta_A0 = delta_a0
        self.delta_a0_dev.put(delta_a0)
        self.update_focus_calcs()

    def update_a0_for_focus(self, new_a0: float):
        """
        Update the focal length (A0) to a new value, ensuring it is within allowable limits.
        :param new_a0: New focal length (A0)
        """

        new_a0 = self.A0 + new_a0
        self.update_a0(new_a0)
        self.update_focus_calcs()

    def update_cacld_zpz_pos(self):
        """
        Update the calculated zpz position
        :param val: New calculated zpz position
        """
        new_zpz_pos = self.calc_new_zpz_pos("SAMPLE")
        self.calcd_zpz_dev.put(new_zpz_pos)


    def adjust_zpz(self, adjust: float):
        """
        Adjust the zpz position offset
        :param adjust: Adjustment value
        """
        self.zpz_adjust = adjust
        self.zpz_adjust_dev.put(adjust)
        self.update_focus_calcs()

    def enable_fl_change_with_energy_change(self, enable: bool):
        """
        Enable or disable automatic focal length change when energy changes.
        :param enable: True to enable, False to disable
        """
        self._enable_fl_change_on_energy_change = enable


    def defocus_beam(self, defocus_um: float):
        """
        Defocus the beam by a specified amount in micrometers.
        :param defocus_um: Amount to defocus the beam in micrometers.
        """
        self._defocus_beam_setpoint_um = defocus_um
        zp_res = self.zoneplate_def['zpOZone']
        energy_val = self.energy_posner.get_position()

        # calc the actual defocus in um from the desired setpoint
        self._defocus_um = (defocus_um * zp_res * energy_val) / 1239.8
        self.defocus_beam_dev.put(self._defocus_um)
        # self.emit_focus_params_changed()
        #self.calc_new_zpz_pos()
        if self.focus_mode == 'OSA':
            self.move_to_osa_focussed()
        else:
            self.move_to_sample_focussed()
        self.update_focus_calcs()

    def calculate_focal_length(self, energy: float=None) -> float:
        """
        Calculate and return the focal length for the given energy.
        If no energy is provided, use the current energy from the energy positioner.
        :param energy: Energy in eV
        :return: Calculated focal length
        """
        if energy is None:
            energy = self.energy_posner.get()

        fl = self.calc_focal_length(energy)
        self.focal_len_dev.put(fl)
        return fl

    def set_focus_mode(self, mode: str):
        """
        set focus mode to either 'OSA' or 'SAMPLE'
        """
        if mode in ['OSA', 'SAMPLE']:
            self.focus_mode = mode

            if mode == 'OSA':
                self.zp_focus_mode_dev.put(0)
                self.move_to_osa_focussed()
            else:
                self.zp_focus_mode_dev.put(1)
                self.move_to_sample_focussed()

            self.update_focus_calcs()
        else:
            raise ValueError("Focus mode must be either 'OSA' or 'SAMPLE'")


    def set_zp_def(self, zp_def: dict):
        """
        set zoneplate definition from dict
        """
        self.update_zp_def(zp_def)
        zp_a1 = zp_def['zpA1']
        self.zp_a1_dev.put(zp_a1)
        # update max_a0
        max_a0 = self.calc_max_a0()
        self.a0_max_dev.put(max_a0)

        #update calcd zpz pos
        self.update_cacld_zpz_pos()

    def set_osa_def(self, osa_def: dict):
        """
        set osa definition from dict
        """
        self.update_osa_def(osa_def)
        max_a0 = self.calc_max_a0()
        self.a0_max_dev.put(max_a0)
        # update calcd zpz pos
        self.update_cacld_zpz_pos()

    def get_new_zpz_for_osa_focussed(self, energy: float=None) -> float:
        if energy is None:
            energy = self.energy_posner.get()

        return  self.calc_new_zpz_for_osa_focussed(energy)

    def report(self):
        print("name = %s, type = %s" % (str(self.__class__), self.name))

    def trigger(self):
        st = super().trigger()
        # #this put doesnt return until it is complete (the waveform generator is done)
        # self.run.put(1, callback=st._finished)
        return st

    def unstage(self):
        st = super().unstage()
        # self.run.put(0)
        st = DeviceStatus(self)
        st.set_finished()
        return st

    def calc_max_a0(self) -> float:
        """
        Defocus the beam by a specified amount in micrometers.
        :param defocus_um: Amount to defocus the beam in micrometers.
        """
        if isinstance(self.osa_def, dict) and isinstance(self.zoneplate_def, dict):
            if 'D' in self.osa_def:
                osa_D = self.osa_def['D']
                zp_diam = self.zoneplate_def['zpD']
                fl = self.calc_focal_length(self.energy_posner.get())
                self.max_A0 = float((osa_D * fl) / zp_diam)
                return self.max_A0
        return None

    def calc_new_zpz_pos(self, focus_mode=None):
        # self.report_params()
        if focus_mode is None:
            focus_mode = self.focus_mode

        energy_val = self.energy_posner.get()
        FL = self.calc_focal_length(energy_val)
        B = 0  # self.delta_zpz_from_focus.get()
        C = 0  # self.scantype_flag.get()
        defocus_um = self._defocus_um
        A0 = self.A0
        delta_A0 = self.delta_A0
        new_zpz_for_osa_focussed = self.calc_new_zpz_for_osa_focussed(energy_val)
        new_zpz_for_sample_focussed = self.calc_new_zoneplate_z_pos_for_focus(energy_val)
        self.FLMode_1 = new_zpz_for_sample_focussed

        if focus_mode == 'OSA':
            new_zpz = new_zpz_for_osa_focussed
        else:
            new_zpz = new_zpz_for_sample_focussed

        # print(f"Calculated new ZPZ position: {new_zpz:.2f} based on focus mode: {self.focus_mode}\n")
        return new_zpz


    def move_to_osa_focussed(self, energy_sp=None):
        """
        Move the zpz positioner to the calculated position for OSA focused mode.
        """
        if energy_sp is not None:
            energy_val = energy_sp
        else:
            energy_val = self.energy_posner.get()

        new_zpz = self.calc_new_zpz_for_osa_focussed(energy_val)
        # print(f"Moving ZPZ to OSA focused position: {new_zpz:.2f}\n")
        #self.zpz_posner.put("user_setpoint", new_zpz)
        self.zpz_posner.call_emit_move(new_zpz, wait=False)

    def move_to_sample_focussed(self, energy_sp=None):
        """
        Move the zpz positioner to the calculated position for Sample focused mode.
        """
        if energy_sp is not None:
            energy_val = energy_sp
        else:
            energy_val = self.energy_posner.get()
        new_zpz = self.calc_new_zoneplate_z_pos_for_focus(energy_val)
        # print(f"Moving ZPZ to Sample focused position: {new_zpz:.2f}\n")
        # self.zpz_posner.put("user_setpoint", new_zpz)
        self.zpz_posner.call_emit_move(new_zpz, wait=False)

    def move(self, val: float, wait=True):
        # print("EnergyDevice [move] called with val: ", val)
        self.energy_posner.move(val, wait=wait)
        if self._enable_fl_change_on_energy_change:
            if self.focus_mode == 'OSA':
                self.move_to_osa_focussed(energy_sp=val)
            else:
                self.move_to_sample_focussed(energy_sp=val)

    def put(self, energy_sp):
        # print("EnergyDevice [put] called with val: ", val)
        # move the zoneplate z positioner to the correct position based on focus mode
        if self._enable_fl_change_on_energy_change:
            if self.focus_mode == 'OSA':
                self.move_to_osa_focussed(energy_sp)
            else:
                self.move_to_sample_focussed(energy_sp)
        # now move energy
        self.energy_posner.move(energy_sp)


    def set(self, val):
        """
        part of the API required to execute from a scan plan
        :param val:
        :return:
        """
        # print("EnergyDevice [set] called with val: ", val)
        self.put(val)
        st = DeviceStatus(self, timeout=5.0)
        st.set_finished()
        return st

    def stop(self, *, success):
        # self.close()
        # self.is_open = False
        pass





if __name__ == "__main__":
    from bcm.devices import MotorQt
    from bluesky import RunEngine
    from bluesky.plans import scan, count
    from ophyd.sim import det1, det2
    from epics import PV
    from cls.applications.pyStxm.bl_configs.utils import make_basedevice, make_base_simdevice

    # Make plots update live while scans run.
    from bluesky.utils import install_kicker

    def on_focus_parms_changed(params):
        # print("Focus parameters changed:")
        # for key, value in params.items():
        #     print(f"\t{key}: {value}")
        # print("")
        pass

    def mdev(dcs_name, name):
        d = make_base_simdevice(
            cat="PVS",
            sig_nm=dcs_name,
            name=name,
            desc="",
            units="",
            rd_only=False,
            backend="epics",
            devcfg=None,
        )
        return d

    RE = RunEngine({})
    from bluesky.callbacks.best_effort import BestEffortCallback

    bec = BestEffortCallback()

    # Send all metadata/data captured to the BestEffortCallback.
    # RE.subscribe(bec)
    from databroker import Broker

    db = Broker.named("pystxm_amb_bl10ID1")

    # Insert all metadata/data captured into db.
    RE.subscribe(db.insert)

    # install_kicker()

    cz_mtr = MotorQt("SMTR1610-3-I12-47", name="DNM_COARSE_Z")
    zpz_mtr = MotorQt("SMTR1610-3-I12-51", name="DNM_ZONEPLATE_Z")
    energy_mtr = MotorQt("SIM_VBL1610-I12:ENERGY", name="SIM_VBL1610-I12:ENERGY")

    time.sleep(1.0)  # give motors time to connect

    edct = {}
    edct["energy_posner"] = energy_mtr
    edct["zpz_posner"] = zpz_mtr
    edct["cz_posner"] = cz_mtr

    edct["a0_dev"] = mdev("DNM_A0", "DNM_A0")
    edct["delta_a0_dev"] = mdev("DNM_DELTA_A0", "DNM_DELTA_A0")
    edct["zpz_adjust_dev"] = mdev("DNM_ZPZ_ADJUST", "DNM_ZPZ_ADJUST")
    edct["defocus_beam_dev"] = mdev("DNM_BEAM_DEFOCUS", "DNM_BEAM_DEFOCUS")
    edct["focal_len_dev"] = mdev("DNM_FOCAL_LENGTH", "DNM_FOCAL_LENGTH")
    edct["zp_a1_dev"] = mdev("DNM_ZP_A1", "DNM_ZP_A1")
    edct["a0_max_dev"] = mdev("DNM_A0MAX", "DNM_A0MAX")
    edct["calcd_zpz_dev"] = mdev("DNM_CALCD_ZPZ", "DNM_CALCD_ZPZ")
    edct["zp_focus_mode_dev"] = mdev("DNM_ZONEPLATE_FOCUS_MODE", "DNM_ZONEPLATE_FOCUS_MODE")

    edct["a0_dev"].put(1000.0)
    edct["delta_a0_dev"].put(0.0)
    edct["zpz_adjust_dev"].put(0.0)
    edct["defocus_beam_dev"].put(0.0)
    edct["zp_a1_dev"].put(11.358981)
    edct["a0_max_dev"].put(500)
    #edct["calcd_zpz_dev"].put(0.0)
    edct["zp_focus_mode_dev"].put(1)

    energy_device = EnergyDevice("SIM_VBL1610-I12:ENERGY", name="ENERGY_DEVICE", energy_dev_dict=edct)
    energy_device.focus_params_changed.connect(on_focus_parms_changed)

    zp0 = {'name': 'ZonePlate 0', 'zp_id': 0, 'zpA1': 4.840, 'zpD': 100.0, 'CsD': 45.0, 'zpOZone': 60.0}
    zp1 = {'name': 'ZonePlate 1', 'zp_id': 1, 'zpA1': 6.792, 'zpD': 240.0, 'CsD': 90.0, 'zpOZone': 35.0}
    zp2 = {'name': 'ZonePlate 2', 'zp_id': 2, 'zpA1': 7.767, 'zpD': 240.0, 'CsD': 90.0, 'zpOZone': 40.0}
    zp3 = {'name': 'ZonePlate 3', 'zp_id': 3, 'zpA1': 4.524, 'zpD': 140.0, 'CsD': 60.0, 'zpOZone': 40.0}
    zp4 = {'name': 'ZonePlate 4', 'zp_id': 4, 'zpA1': 4.859, 'zpD': 240.0, 'CsD': 95.0, 'zpOZone': 25.0}
    zp5 = {'name': 'ZonePlate 5', 'zp_id': 5, 'zpA1': 4.857, 'zpD': 240.0, 'CsD': 95.0, 'zpOZone': 25.0}
    zp6 = {'name': 'ZonePlate 6', 'zp_id': 6, 'zpA1': 5.067, 'zpD': 250.0, 'CsD': 100.0, 'zpOZone': 25.0}
    zp7 = {'name': 'ZonePlate 7', 'zp_id': 7, 'zpA1': 6.789, 'zpD': 159.0, 'CsD': 111.0, 'zpOZone': 35.0}
    zp8 = {'name': 'ZonePlate 8', 'zp_id': 8, 'zpA1': 35.835, 'zpD': 5000.0, 'CsD': 111.0, 'zpOZone': 35.0}
    zp9 = {'name': 'ZonePlate 9', 'zp_id': 9, 'zpA1': 11.358981, 'zpD': 280.0, 'CsD': 100.0, 'zpOZone': 50.0}

    osa0 = {'name': 'OSA 0', 'osa_id': 0, 'D': 30.0}
    osa1 = {'name': 'OSA 1', 'osa_id': 1, 'D': 50.0}
    osa2 = {'name': 'OSA 2', 'osa_id': 2, 'D': 40.0}
    osa3 = {'name': 'OSA 3', 'osa_id': 3, 'D': 60.0}
    osa4 = {'name': 'OSA 4', 'osa_id': 4, 'D': 70.0}
    osa5 = {'name': 'OSA 5', 'osa_id': 5, 'D': 51.0}
    osa6 = {'name': 'OSA 6', 'osa_id': 6, 'D': 42.0}
    osa7 = {'name': 'OSA 7', 'osa_id': 7, 'D': 63.0}
    osa8 = {'name': 'OSA 8', 'osa_id': 8, 'D': 74.0}

    dets = [det1]  # just one in this case, but it could be more than one
    # RE(count(dets))

    energy_val = energy_mtr.get_position()
    # delta_a0_val = PV("ASTXM1610:bl_api:delta_A0").get()
    # a0_val = PV("ASTXM1610:bl_api:A0").get()
    # defocus_val = PV("ASTXM1610:bl_api:zp:defocus").get()
    # adjust_val = PV("ASTXM1610:bl_api:zp:adjust_zpz").get()
    #
    # FLMode0_val = PV("ASTXM1610:bl_api:zp:mode:setter.L").get()
    # FLMode1_val = PV("ASTXM1610:bl_api:zp:mode:setter.M").get()



    # run calcs based in current pv values
    energy_device.set_zp_def(zp9)
    energy_device.calc_focal_length(energy_val)
    energy_device.set_osa_def(osa1)
    energy_device.update_a0(1000)
    energy_device.update_delta_a0(0)
    energy_device.adjust_zpz(0)
    energy_device.defocus_beam(0)
    energy_device.set_focus_mode("SAMPLE")

    # if energy_device.FLMode_0 != FLMode0_val:
    #     print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!FLMode_0 mismatch: calc={energy_device.FLMode_0:.2f}, pv={FLMode0_val:.2f}")
    # else:
    #     print(f"BOOM! FLMode_0 match: calc={energy_device.FLMode_0:.2f}, pv={FLMode0_val:.2f}")
    #
    # if energy_device.FLMode_1 != FLMode1_val:
    #     print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!FLMode_1 mismatch: calc={energy_device.FLMode_1:.2f}, pv={FLMode1_val:.2f}")
    # else:
    #     print(f"BOOM! FLMode_1 match: calc={energy_device.FLMode_1:.2f}, pv={FLMode1_val:.2f}")

    # print(f"-----Starting scan with energy device... using zoneplate zp9 and osa1----OSA FOCUSSED")
    # RE(scan(dets, energy_device, 395, 425, 3))

    # energy_device.set_zp_def(zp2)
    # energy_device.set_osa_def(osa1)
    energy_device.set_focus_mode("SAMPLE")
    print(f"-----Starting scan with energy device... using zoneplate zp2 and osa1---- SAMPLE FOCUSSED")
    RE(scan(dets, energy_device, 395.0, 450.0, 10))

    energy_device.move_to_osa_focussed()
    energy_device.move_to_sample_focussed()
    energy_device.move_to_osa_focussed()

    # At the end of your script, before exiting
    RE.stop()  # Stop the RunEngine if running

    # If using ophyd devices, unstage them
    energy_device.unstage()


