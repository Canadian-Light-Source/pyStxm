
import math
from PyQt5 import QtCore, QtGui, QtWidgets

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

    def update_a0(self, a0: float):
        """
        Update the a0 value
        :param a0: New a0 value
        """
        self.A0 = a0

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
        current_focal_length = self.focal_length(energy)
        delta_a0 = desired_focus_position - current_focal_length
        return delta_a0

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

    def calc_new_zoneplate_z_pos_for_focus(self, energy: float, a0: float, desired_focus_position: float) -> float:
        """
        NOTE: Focal length is equal to OSA in focus

        Calculate the new zoneplate z position needed to achieve focus at the desired focal length for a given energy.
        :param focal_length: Desired focal length
        :param a0: Current focal length
        :param delta_a0: Change in focal length required to achieve focus
        :return: New zoneplate z position
        """
        focal_length = self.focal_length(energy)
        delta_focus_pos = self.calc_delta_focus_position(energy, desired_focus_position)
        new_zp_z_pos = 0.0 - ((math.fabs(focal_length) - a0) - (delta_focus_pos) + self.delta_A0)
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

    for des_focus_pos in desired_focus_position:
        print(f"[des_focus_pos: {des_focus_pos}] Cz = {fclass.calc_new_coarse_z_pos_for_focus(energy, cz, des_focus_pos):.2f} um")
    print()
    for des_focus_pos in desired_focus_position:
        print(f"[des_focus_pos: {des_focus_pos}] ZPz = {fclass.calc_new_zoneplate_z_pos_for_focus(energy, a0, des_focus_pos):.2f} um")








