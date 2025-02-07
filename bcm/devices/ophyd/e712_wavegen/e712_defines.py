

#this is the value that if the requested dwell time is less than this value
# the system needs to produce multiple triggers so that the stages can settle in between
# actual dwell time triggers
PXP_SHORT_DWELL_REQ_MULT_TRIGS_MS = 25


SIS3820_EXTRA_PNTS = 1
NUM_TRIG_DURING_ROW_CHANGE = 1
Y_PXP_TIME_TO_MOVE_TO_NEXT_ROW = 0.18 #0.25 #sec
#Y_PXP_TIME_TO_MOVE_TO_NEXT_ROW = 0.28 #0.25 #sec
#X_PXP_END_SETTLE_TIME = 0.1 #sec
X_PXP_END_SETTLE_TIME = 0.06 #sec make factor of wave
#X_PXP_END_SETTLE_TIME = 0.15 #sec

#SHORT_DWELL_SETTLE_TIME = 0.030 #too long and no real improvemnt in spatial over 0.0075
#SHORT_DWELL_SETTLE_TIME = 0.0075 #pretty good
#SHORT_DWELL_SETTLE_TIME = 0.00175 #some slight spatial distortion on first quarter of image
SHORT_DWELL_SETTLE_TIME = 0.006 #make sure its a factor of SERVO_CYCLE_TIME = 0.00003
#SHORT_DWELL_SETTLE_TIME = 0.002

#PXP_START_DELAY = 0.001
#PXP_START_DELAY = 0.1
PXP_START_DELAY = 0.065

PXP_DWELLS_TO_WAIT_AT_START = 15

# MIN_LINE_RETURN_TIME = 0.04
MIN_LINE_RETURN_TIME = 0.006
STEP_TIME = 0.001 # default value used in funcs and calculations

