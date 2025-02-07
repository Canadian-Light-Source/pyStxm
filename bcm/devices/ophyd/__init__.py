import ophyd
from cls.utils.enum_utils import Enum

trig_types = Enum(
    "DAQmx_Val_None",
    "DAQmx_Val_AnlgEdge",
    "DAQmx_Val_AnlgWin",
    "DAQmx_Val_DigEdge",
    "DAQmx_Val_DigPattern",
    "SOFT_TRIGGER",
)


class BaseDAQmxOphydDev(ophyd.Device):
    """
    a class to provide base level daqmx settings that could change scan to scan
    """

    def __init__(self, prefix, name, **kwargs):
        super(BaseDAQmxOphydDev, self).__init__(prefix, name=name, **kwargs)
        self.trig_src_pfi = None
        self.ci_clk_src_gate_pfi = None
        self.gate_clk_src_gate_pfi = None
        self.sig_src_term_pfi = None
        self.clk_src_gate_pfi = None

class BaseSimDAQmxOphydDev(ophyd.Device):
    """
    a class to provide base level daqmx settings that could change scan to scan
    """

    def __init__(self, prefix, name, **kwargs):
        super(BaseSimDAQmxOphydDev, self).__init__(prefix, name=name, **kwargs)

