def calc_fl(energy):

    A = energy
    print("A energy = %.2f" % A)
    # "Delta zpz frm focus"
    B = 0  # self.delta_zpz_from_focus.get()
    # "scantype flag"
    C = 0  # self.scantype_flag.get()
    # "A1"
    D = -6.791682
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


# self.zpz_posner.put('user_setpoint', new_zpz)
if __name__ == "__main__":
    calc_fl(260)
    calc_fl(271.11)
    calc_fl(282.22)
    calc_fl(293.33)
    calc_fl(304.44)
    calc_fl(315.56)
    calc_fl(326.67)
    calc_fl(337.78)
    calc_fl(348.89)
    calc_fl(360.00)
