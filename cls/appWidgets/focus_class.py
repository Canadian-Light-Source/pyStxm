
import math
from PyQt5 import QtCore, QtGui, QtWidgets

from cls.utils.log import get_module_logger

_logger = get_module_logger(__name__)

ABS_MIN_A0 = 100.0  # Minimum allowable A0
ABS_MAX_A0 = 5000.0  # Maximum allowable A0


class FocusCalculations(QtCore.QObject):
    """
    Class to handle focus calculations for zoneplates.
    """
    def __init__(self, zoneplate_def: dict, A0: float, delta_A0: float=0.0, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.zoneplate_def = zoneplate_def
        self.A0 = A0
        self.delta_A0 = delta_A0
        self.min_A0 = ABS_MIN_A0  # Minimum allowable A0

    def update_min_a0(self, val: float):
        """
        Update the min_A0 value
        :param val: New ,min_A0 value
        """
        if val < ABS_MIN_A0:
            _logger.warn(f"Attempted to set min_A0 to {val}, which is below absolute minimum of {ABS_MIN_A0}. Setting to {ABS_MIN_A0}.")
        else:
            self.min_A0 = val

    def update_a0(self, a0: float):
        """
        Update the a0 value
        :param a0: New a0 value
        """
        self.A0 = a0
        self.update_delta_a0(0.0)

    def update_delta_a0(self, delta_a0: float):
        """
        Update the delta_a0 value
        :param delta_a0: New delta_a0 value
        """
        self.delta_A0 = delta_a0


    def focal_length(self, energy):
        """
        f = A1 * E
        """
        f = self.zoneplate_def["zpA1"] * energy

        return f

    def get_a0(self) -> float:
        """
        Get the current focal length (A0)
        :return: Current focal length (A0)
        """
        return self.A0

    def get_delta_a0(self) -> float:
        """
        Get the current change in focal length (delta_a0)
        :return: Current change in focal length (delta_a0)
        """
        return self.delta_A0

    def calc_delta_focus_position(self, energy: float, desired_focus_position: float) -> float:
        """
        Calculate the change in focal length (delta_a0) required to achieve the desired focal length for a given energy.
        :param desired_focal_length: Desired focal length
        :param energy: Energy in eV
        :return: Change in focal length (delta_a0)
        """
        current_focal_length = 0.0 - (math.fabs(self.focal_length(energy)) - (self.A0 + self.delta_A0))
        delta_focus_pos = desired_focus_position - current_focal_length
        self.update_a0_for_focus(delta_focus_pos)
        return delta_focus_pos

    def update_a0_for_focus(self, new_a0: float):
        """
        Update the focal length (A0) to a new value, ensuring it is within allowable limits.
        :param new_a0: New focal length (A0)
        """
        self.A0 += new_a0

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
        focal_length = self.focal_length(energy)
        new_zp_z_pos = 0.0 - (math.fabs(focal_length) - (self.A0 + self.delta_A0))
        # new_zp_z_pos = 0.0 - ((math.fabs(focal_length) - self.A0) - (delta_focus_pos) + self.delta_A0)
        return new_zp_z_pos



if __name__ == '__main__':
    import sys

    energy = 395.0  # eV
    a1 = -11.0
    a0 = 1000
    desired_focus_position = [-3386, -3286, -3486, -3586, -3586, -3686, -3786, -3886, -3986]
    cz = 3000
    zpz = -3486

    zp_def = {"D": 280.0, "CsD": 100, "OZone": 50, "zpA1": -11.359}

    fclass = FocusCalculations(zp_def, a0)

    fl = fclass.focal_length(energy)
    print(f"[a0={a0:.2f}] Focal length at {energy} eV: {fl} um")
    print("-----------------------------------------------")

    # for des_focus_pos in desired_focus_position:
    #     print(f"[des_focus_pos: {des_focus_pos}] Cz = {fclass.calc_new_coarse_z_pos_for_focus(energy, cz, des_focus_pos):.2f} um")
    # print()
    # for des_focus_pos in desired_focus_position:
    #     print(f"[des_focus_pos: {des_focus_pos}] ZPz = {fclass.calc_new_zoneplate_z_pos_for_focus(energy, a0, des_focus_pos):.2f} um")

    new_a0_offset = fclass.calc_delta_focus_position(395, -3476.8)
    fclass.update_a0_for_focus(new_a0_offset)
    fclass.calc_new_zoneplate_z_pos_for_focus(energy)






