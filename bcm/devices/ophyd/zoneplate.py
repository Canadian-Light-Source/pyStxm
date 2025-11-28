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


    def calc_new_zpz_pos(self):
        A = self.energy.get()
        print("A energy = %.2f:" % A)
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
        print("\tK new osa Z: %.2f" % K)
        # "FL mode0"
        L = FL_mode_0 = ((A * D) - abs(F)) + G - I
        print("\tL new FL mode0 (OSA Focused): %.2f" % L)
        # "FL mode1"
        M = FL_mode_1 = ((A * D) - E) + G - I
        print("\tM new FL mode1 (Sample Focussed): %.2f" % M)

        # "set clcd FL"
        O = new_fl = A * D
        print("\tN new FL: %.2f" % O)

        # "Zpz MTR OUT"
        if C == 0:
            N = new_zpz = L
        else:
            N = new_zpz = M
        print("\tN new ZPZ pos: %.2f\n\n" % N)
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
    # RE.subscribe(bec)
    from databroker import Broker

    db = Broker.named("pystxm_amb_bl10ID1")

    # Insert all metadata/data captured into db.
    RE.subscribe(db.insert)

    # install_kicker()

    #cz = MotorQt("SMTR1610-3-I12:47", name="DNM_COARSE_Z")
    # zpz = MotorQt("SMTR1610-3-I12:51", name="DNM_ZONEPLATE_Z")
    zpz = MotorQt("SIM_VBL1610-I12:slitX", name="DNM_ZONEPLATE_Z")
    energy = MotorQt("SIM_VBL1610-I12:ENERGY", name="SIM_VBL1610-I12:ENERGY")

    zoneplate_lst = [
        {'name': 'ZonePlate 0', 'zp_id': 0, 'a1': -4.840, 'D': 100.0, 'CsD': 45.0, 'OZone': 60.0},
        {'name': 'ZonePlate 1', 'zp_id': 1, 'a1': -6.792, 'D': 240.0, 'CsD': 90.0, 'OZone': 35.0},
        {'name': 'ZonePlate 2', 'zp_id': 2, 'a1': -7.767, 'D': 240.0, 'CsD': 90.0, 'OZone': 40.0},
        {'name': 'ZonePlate 3', 'zp_id': 3, 'a1': -4.524, 'D': 140.0, 'CsD': 60.0, 'OZone': 40.0},
        {'name': 'ZonePlate 4', 'zp_id': 4, 'a1': -4.859, 'D': 240.0, 'CsD': 95.0, 'OZone': 25.0},
        {'name': 'ZonePlate 5', 'zp_id': 5, 'a1': -4.857, 'D': 240.0, 'CsD': 95.0, 'OZone': 25.0},
        {'name': 'ZonePlate 6', 'zp_id': 6, 'a1': -5.067, 'D': 250.0, 'CsD': 100.0, 'OZone': 25.0},
        {'name': 'ZonePlate 7', 'zp_id': 7, 'a1': -6.789, 'D': 159.0, 'CsD': 111.0, 'OZone': 35.0},
        {'name': 'ZonePlate 8', 'zp_id': 8, 'a1': -35.835, 'D': 5000.0, 'CsD': 111.0, 'OZone': 35.0},
        {'name': 'ZonePlate 9', 'zp_id': 9, 'a1': -11.358981, 'D': 280.0, 'CsD': 100.0, 'OZone': 50.0},
    ]

    zp_objs = []
    for i, zp_def in enumerate(zoneplate_lst):
        zp_objs.append(Zoneplate("MYZONER", f"zp{zp_def['zp_id']}", zpz,  zp_def['a1'],  zp_def['D'],  zp_def['CsD'],  zp_def['OZone']))

    # zp1.set_energy(465)
    dets = [det1, det2, zpz]  # just one in this case, but it could be more than one
    # RE(count(dets))
    #RE(scan(dets, zp_objs[9], 395, 450, 3))
    RE(scan(dets, energy, 395, 450, 3))
