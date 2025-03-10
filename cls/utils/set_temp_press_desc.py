from epics import caput, caget

# these should have been set in the respective databases but were not
caput("TM1610-3-I12-01.DESC", "Turbo cooling water")
caput("TM1610-3-I12-30.DESC", "Sample Coarse Y")
caput("TM1610-3-I12-32.DESC", "Detector Y")
caput("TM1610-3-I12-21.DESC", "Chamber temp #1")
caput("TM1610-3-I12-22.DESC", "Chamber temp #2")
caput("TM1610-3-I12-23.DESC", "Chamber temp #3")
caput("TM1610-3-I12-24.DESC", "Chamber temp #4")
caput("CCTL1610-I10:temp:fbk.DESC", "Gatan rod temp")
caput("CCTL1610-I10:temp:fbk.EGU", "deg C")

# pressures
caput("FRG1610-3-I12-01:vac:p.DESC", "Chamber pressure")
caput("TCG1610-3-I12-03:vac:p.DESC", "Turbo backing pressure")
caput("TCG1610-3-I12-04:vac:p.DESC", "Load lock pressure")
caput("TCG1610-3-I12-05:vac:p.DESC", "Rough line pressure")

caput("CCG1410-01:vac:p.DESC", "Sec. 1")
caput("CCG1410-I00-01:vac:p.DESC", "Sec. 2")
caput("CCG1410-I00-02:vac:p.DESC", "Sec. 4")
caput("CCG1610-1-I00-02:vac:p.DESC", "Sec. 6")
caput("HCG1610-1-I00-01:vac:p.DESC", "Sec. 7")
caput("CCG1610-1-I00-03:vac:p.DESC", "Sec. 8")
caput("CCG1610-I10-01:vac:p.DESC", "Sec. 10")
caput("CCG1610-I10-02:vac:p.DESC", "Sec. 11")
caput("CCG1610-I10-03:vac:p.DESC", "Sec. 12")
caput("CCG1610-I10-04:vac:p.DESC", "Sec. 13")
caput("CCG1610-I12-01:vac:p.DESC", "Sec. 14")
caput("CCG1610-I12-02:vac:p.DESC", "Sec. 15")
caput("CCG1610-3-I12-01:vac:p.DESC", "Sec. 16")
