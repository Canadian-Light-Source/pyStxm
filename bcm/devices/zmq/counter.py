import copy
from PyQt5 import QtCore

from bcm.devices.zmq.zmq_device import ZMQBaseDevice
from cls.utils.prog_dict_utils import make_progress_dict, set_prog_dict
from cls.plotWidgets.utils import make_counter_to_plotter_com_dct, gen_complete_spec_chan_name


class ZMQCounter(ZMQBaseDevice):
    """
    Simple counter device that can emit new_plot_data
    """
    new_plot_data = QtCore.pyqtSignal(object)
    def __init__(self, base_signal_name, name=None, **kwargs):
        super().__init__(base_signal_name, name=name, **kwargs)
        self.is_staged = True
        self.is_pxp_scan = True
        self.is_point_spec_scan = False
        self.is_line_spec_scan = False
        self._prog_dct = make_progress_dict(sp_id=0, percent=0, cur_img_idx=0)
        self.enable_progress_emit = True
        self.rawData = None
        self.row = 0
        self.col = 0
        self.is_tiled = False
        self.seq_map = {}
        self.x_data = []
        self.return_all_spec = False #flag to return entire line of spec data with x_data instead of single point or line

        # self.changed.connect(self.on_waveform_changed)

    def reset(self):
        """
        reset to default values
        """
        self.is_staged = True
        self.is_pxp_scan = True
        self.is_point_spec_scan = False
        self.is_line_spec_scan = False

        self.rawData = None
        self.row = 0
        self.col = 0
        self.is_tiled = False
        self.seq_map = {}
        self.x_data = []
        self.return_all_spec = False


    def set_return_all_spec_at_once(self, val):
        """
        set the flag
        mainly used by the POSITIONER or Motor scan as Pixelator doesnt return data until scan is complete,
        why it is different than all other scans I dont know
        """
        self.return_all_spec = val

    def set_seq_map(self, map):
        """
        this map contains the sequence of the event and the X axis values to use for col

        seq_map is {sequence_idx, (sp_id, x value),:
            {0: (5, -200.0),
             1: (5, -197.31543624161074),
             2: (5, -194.63087248322148),
             3: (5, -191.94630872483222),
             4: (5, -189.26174496644296),
             ...}
        """
        self.seq_map = map
        #now init x_data
        for k, dct in self.seq_map.items():
            self.x_data.append(dct['x_pos'])

    def set_spec_scan(self):
        """
        force member vars into correct settings for a spectroscopy scan
        """
        self.is_pxp_scan = True
        self.is_point_spec_scan = True
        self.is_line_spec_scan = False

    def set_line_scan(self):
        """
        force member vars into correct settings for a spectroscopy scan
        """
        self.is_pxp_scan = False
        self.is_point_spec_scan = False
        self.is_line_spec_scan = False

    def set_line_spec_scan(self):
        """
        force member vars into correct settings for a spectroscopy scan
        """
        self.is_pxp_scan = False
        self.is_point_spec_scan = False
        self.is_line_spec_scan = True

    def waveform_changed(self, dct) -> None:
        """ when this function is connected to the `changed` signal it receives
        an EPICS style callback dict:
        {   'old_value': 20.989,
            'value': 20.104,
            'timestamp': 1729700056.3274262,
            'status': 0,
            'severity': 0,
            'precision': 5,
            'lower_ctrl_limit': 0,
            'upper_ctrl_limit': 0,
            'units': '',
            'sub_type': 'value',
            'obj': <bcm.devices.zmq.counter.ZMQCounter object at 0x000001EB5B95B5B0>
        }

        """
        if self.is_staged:
            self.rawData = copy.copy(dct["value"])
            self.process_data(dct)

    def process_data(self, dct: dict) -> None:
        """
        kwargs is an dict used for callbacks and emits `new_plot_data`
        """
        #print(f"ZMQCounter: process_data: dct={dct}")

        data = dct["value"]
        self.row = dct["row"]
        self.col = dct["col"]
        app_devname = dct["app_devname"]

        # Preserve existing behavior: point if scalar-like, not point if array-like
        self.is_pxp_scan = len(data) <= 1

        try:
            # Default detector naming/path
            det_name = app_devname

            # NOTE only 1 SP_id supported at the moment
            # currently the pixelator-nh crashes if multi spatial scanRequests are submitted through their GUI also
            # so this will need to get sorted
            if self.return_all_spec:
                seq_num = dct["col"]
                seq_dct = self.seq_map[seq_num]
                sp_id = seq_dct["sp_id"]
                self.col = seq_dct["x_pos"]
                #print(f"1 seq_map[{seq_num}]={seq_dct}  dct={dct}")

                det_name = gen_complete_spec_chan_name(app_devname, sp_id=sp_id, prefix="spid-")
                # Assign all x_data so plotter can use full x axis
                self.col = self.x_data

            elif self.is_point_spec_scan and not self.return_all_spec:
                seq_num = dct["col"]
                seq_dct = self.seq_map[seq_num]
                sp_id = seq_dct["sp_id"]
                self.col = seq_dct["x_pos"]
                #print(f"2 seq_map[{seq_num}]={seq_dct}  dct={dct}")

                det_name = gen_complete_spec_chan_name(app_devname, sp_id=sp_id, prefix="spid-")

            else:
                self.col = dct["col"]

            # Conform to SIS3820-style channel dict contract
            chan_dct = {det_name: data}

            if self.enable_progress_emit:
                set_prog_dict(
                    self._prog_dct,
                    sp_id=0,
                    percent=dct["prog"],
                    cur_img_idx=dct["img_idx"],
                    ev_idx=dct["ev_idx"],
                    pol_idx=dct["pol_idx"],
                )
                prog_dct = self._prog_dct
            else:
                prog_dct = {}

            plot_dct = make_counter_to_plotter_com_dct(
                self.row,
                self.col,
                chan_dct,
                is_point=self.is_pxp_scan,
                det_name=det_name,
                is_tiled=dct["is_tiled"],
                prog_dct=prog_dct,
            )
            self.new_plot_data.emit(plot_dct)

        except Exception as e:
            raise f"process_data: EXception: emitting: {e}"

    def get_name(self):
        return self.name

    def get_position(self):
        return self.get("VAL")

    def get(self, _attr='None'):
        if hasattr(self, _attr):
            obj = getattr(self, _attr)
            return obj.get()
        else:
            return self._readback

    def put(self, val=None):
        obj = getattr(self, "VAL")
        # restrict value to 0 thru 7
        val = val % 7
        return obj.set(val)

    def is_chan_enabled(self, chan_name=None):
        return True
