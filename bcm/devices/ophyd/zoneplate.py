"""
record(transform, "$(bl):$(stxm):zp:mode:setter")
{
	field(PINI, "0")
	field(PREC, "7")
	field(DISV, "0")
  field(SDIS, "$(bl):$(stxm):enabled.VAL")
  #if the scanselflag is 0 (mode 0) then disable this record
  field(DISV, "0")

  field(CMTA, "new energy")						field(INPA, "$(blEnergy) CP")

	field(CMTB, "Delta zpz frm focus")	field(INPB, "$(bl):$(stxm):delta_A0 CP")
	field(CMTC, "scantype flag")				field(INPC, "$(bl):$(stxm):zp:scanselflag CP")
	field(CMTD, "A1")										field(INPD, "$(bl):$(stxm):zp:def.A NPP NMS")
	field(CMTE, "Defocus (um)")					field(INPE, "$(bl):$(stxm):zp:dfcus:clc CP")
	field(CMTF, "A0 setpoint")					field(INPF, "$(bl):$(stxm):A0.VAL CP")
	field(CMTG, "delta A0")							field(INPG, "$(bl):$(stxm):delta_A0.VAL CP")
	field(CMTH, "theo FL")							field(INPH, "$(bl):$(stxm):zp:FL.VAL NPP NMS")
	field(CMTI, "adjust zpz")						field(INPI, "$(bl):$(stxm):zp:adjust_zpz CP")

	field(CMTJ, "")											field(CLCJ, "")								field(OUTJ, "")
	field(CMTK, "new osaz")							field(CLCK, "((-1.0*F)-E)+G")	field(OUTK, "IOC:m106C:check_tr.A PP NMS")

	field(CMTL, "FL mode0")							field(CLCL, "((A*D)-ABS(F))+G-I")	field(OUTL, "")
	field(CMTM, "FL mode1")							field(CLCM, "((A*D)-E)+G-I")			field(OUTM, "")

	field(CMTN, "Zpz MTR OUT")					field(CLCN, "(C=0)?L:M")		field(OUTN, "$(zp_zMtr) PP NMS")
	field(CMTO, "set clcd FL")					field(CLCO, "A*D")						field(OUTO, "$(bl):$(stxm):zp:FL.VAL PP")

}

record(transform, "$(bl):$(stxm):zp:fbk:tr")
{
  field(DESC, "$(stxm) energy")
  field(PREC, "7")
  field(SCAN, ".1 second")

  field(CMTA, "new energy")												field(INPA, "$(blEnergy).RBV")
  field(CMTB, "Zone plate diameter")							field(INPB, "$(bl):$(stxm):zp:def.B")
  #field(CMTC, "Outer most zone width")						field(INPC, "$(bl):$(stxm):zp_outr_wd")
  #field(CMTD, "Central stop diameter")						field(INPD, "$(bl):$(stxm):zp:def.C")
  field(CMTE, "Order sorting aperture diameter")	field(INPE, "$(bl):$(stxm):osa:def.A ")
  #field(CMTF, "Order sorting aperture thickness")	field(INPF, "$(stxm):osa_aprtr_thick")

  field(CMTG, "A1")	field(INPG, "$(bl):$(stxm):zp:def.A ")
  field(CMTH, "")		field(INPH, "")

	field(CMTI, "focal length")	field(INPI, "$(bl):$(stxm):zp:FL")
	field(CMTJ, "A0Max")				field(CLCJ, "(E*(-1.0*I)/B)")		field(OUTJ, "$(bl):$(stxm):A0Max PP")
  field(CMTK, "ideal Osaz(A0)") field(CLCK, "J-15")
  field(CMTL, "Calcd ZpZ") 		field(CLCL, "I+K")
  field(CMTM, "") 						field(CLCM, "")
  field(CMTN, "") 						field(CLCN, "")

}


"""
import time

from ophyd import Component as Cpt, Device
from ophyd.signal import Signal
from ophyd.status import DeviceStatus


class Zoneplate(Device):
    a1 = Cpt(Signal)
    diameter = Cpt(Signal)
    central_stop = Cpt(Signal)
    resolution = Cpt(Signal)

    a0_focus_target = Cpt(Signal)  # this is either OSA in focus, or Sample in focus
    energy = Cpt(Signal)

    def __init__(self, prefix, name, zpz_posner, a1, diam, cstop, res):
        super(Zoneplate, self).__init__(prefix, name=name)
        self.a1.set(a1)
        self.diameter.put(diam)
        self.central_stop.put(cstop)
        self.resolution.put(res)
        self.zpz_posner = zpz_posner
        # I need to add the zoneplate motor device here so that it can be moved under 'set'

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

    # def calc_new_zpz_pos(self):
    #     A = self.energy.get()
    #     # "Delta zpz frm focus"
    #     B = 0 #self.delta_zpz_from_focus.get()
    #     #"scantype flag"
    #     C = 1 #self.scantype_flag.get()
    #     # "A1"
    #     D = self.a1.get()
    #     #"Defocus (um)"
    #     E = 0 #self.defocus.get()
    #     # "A0 setpoint"
    #     F = 1000 #self.ao_setpoint.get()
    #     # "delta A0"
    #     G = 0 #self.delta_a0.get()
    #     # "theo FL"
    #     H = 0 #self.theoretical_fl.get()
    #     # "adjust zpz"
    #     I = 0 #self.adjust_zpz.get()
    #
    #     # "new osaz"
    #     K = new_osa_z = ((-1.0*F)-E)+G
    #     # "FL mode0"
    #     L = FL_mode_0 = ((A*D)-abs(F))+G-I
    #     # "FL mode1"
    #     M = FL_mode_1 = ((A*D)-E)+G-I
    #
    #     # "Zpz MTR OUT"
    #     if C == 0:
    #         N = new_zpz = L
    #     else:
    #         N = new_zpz = M
    #     # "set clcd FL"
    #     O = new_fl = A*D
    #
    #     self.zpz_posner.put('user_setpoint', new_zpz)

    def calc_new_zpz_pos(self):
        A = self.energy.get()
        print("A energy = %.2f" % A)
        # "Delta zpz frm focus"
        B = 0  # self.delta_zpz_from_focus.get()
        # "scantype flag"
        C = 0  # self.scantype_flag.get()
        # "A1"
        D = self.a1.get()
        # "Defocus (um)"
        E = 0  # self.defocus.get()
        # "A0 setpoint"
        F = 1000.0  # self.ao_setpoint.get()
        # "delta A0"
        G = 0  # self.delta_a0.get()
        # "theo FL"
        H = 0  # self.theoretical_fl.get()
        # "adjust zpz"
        I = 0  # self.adjust_zpz.get()

        # "new osaz"
        K = new_osa_z = ((-1.0 * F) - E) + G
        print("K new osa Z: %.2f" % K)
        # "FL mode0"
        L = FL_mode_0 = ((A * D) - abs(F)) + G - I
        print("L new FL mode0: %.2f" % L)
        # "FL mode1"
        M = FL_mode_1 = ((A * D) - E) + G - I
        print("M new FL mode1: %.2f" % M)

        # "set clcd FL"
        O = new_fl = A * D
        print("N new FL: %.2f" % O)

        # "Zpz MTR OUT"
        if C == 0:
            N = new_zpz = L
        else:
            N = new_zpz = M
        print("N new ZPZ pos: %.2f" % N)
        self.zpz_posner.put("user_setpoint", new_zpz)

    def put(self, val):
        self.energy.put(val)
        self.calc_new_zpz_pos()

    def set(self, val):
        """
        part of the API required to execute from a scan plan
        :param val:
        :return:
        """
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

    # Make plots update live while scans run.
    from bluesky.utils import install_kicker

    RE = RunEngine({})
    from bluesky.callbacks.best_effort import BestEffortCallback

    bec = BestEffortCallback()

    # Send all metadata/data captured to the BestEffortCallback.
    RE.subscribe(bec)
    from databroker import Broker

    db = Broker.named("pystxm_amb_bl10ID1")

    # Insert all metadata/data captured into db.
    RE.subscribe(db.insert)

    # install_kicker()

    zpz = MotorQt("SIM_IOC:m704", name="SIM_IOC:m704")
    energy = MotorQt("SIM_VBL1610-I10:AMB:ENERGY", name="SIM_VBL1610-I10:AMB:ENERGY")

    zp1 = Zoneplate("MYZONER", "zp1", zpz, -4.839514, 100, 45, 60)
    zp2 = Zoneplate("MYZONER", "zp2", zpz, -6.791682, 240, 90, 35)
    zp3 = Zoneplate("MYZONER", "zp3", zpz, -7.76662, 240, 90, 40)
    zp4 = Zoneplate("MYZONER", "zp4", zpz, -4.524239, 140, 60, 40)
    zp5 = Zoneplate("MYZONER", "zp5", zpz, -4.85874, 240, 95, 25)
    zp6 = Zoneplate("MYZONER", "zp6", zpz, -4.85874, 240, 95, 25)
    zp7 = Zoneplate("MYZONER", "zp7", zpz, -5.0665680, 250, 100, 25)
    zp8 = Zoneplate("MYZONER", "zp8", zpz, 0, 240, 100, 63.79)

    # zp1.set_energy(465)
    dets = [det1, det2, zpz]  # just one in this case, but it could be more than one
    RE(count(dets))
    RE(scan(dets, zp2, 260, 360, 10))
