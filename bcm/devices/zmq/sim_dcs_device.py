from PyQt5.QtCore import pyqtSignal, QObject, QTimer
class sim_dcs_fbk_dev(QObject):
    changed = pyqtSignal(str, str, object, bool) # name, dcs_name, value, moving

    def __init__(self, name, dcs_name):
        super().__init__(None)
        self.name = name
        self.dcs_name = dcs_name
        self.user_readback = 0
        self.user_setpoint = 0
        self.velocity = 10
        self._cur_velo = 0
        self.acceleration = 0.1
        self._cur_accel = 0
        self.dir = 1
        self.status = 0 # stopped
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_fbk)
        self.timer.start(10)
        self.is_moving = False
        self._low_limit = 0
        self._high_limit = 0

    def get_position(self):
        return self.user_readback

    def set_low_limit(self, val):
        self._low_limit = val

    def set_high_limit(self, val):
        self._high_limit = val

    def get_low_limit(self):
        return self._low_limit_val

    def get_high_limit(self):
        return self.high_limit_val

    def update_fbk(self):
        self._cur_velo = self.velocity
        if self.user_setpoint < self.user_readback:
            self.user_readback += self.velocity * self.dir
            if self.user_readback < self.user_setpoint:
                self.user_readback = self.user_setpoint
            # name, dcs_name, value
            self.is_moving = True
            self.changed.emit(self.name, self.dcs_name, self.user_readback, self.is_moving)

        elif self.user_setpoint > self.user_readback:
            self.user_readback += self.velocity * self.dir
            if self.user_readback > self.user_setpoint:
                self.user_readback = self.user_setpoint
            self.is_moving = True
            self.changed.emit(self.name, self.dcs_name, self.user_readback, self.is_moving)
        elif self.user_setpoint > self.user_readback and self._cur_velo > 0:
            self.is_moving = True
            self.changed.emit(self.name, self.dcs_name, self.user_readback, self.is_moving)
        else:
            #we are at the setpoint
            self._cur_velo = 0
            if self.is_moving:
                self.is_moving = False
                self.changed.emit(self.name, self.dcs_name, self.user_readback, self.is_moving)


    def stop(self):
        """
        force a stop wherever the device is
        """
        self.user_setpoint = self.user_readback

    def move(self, value):
        self.user_setpoint = value
        if self.user_setpoint < self.user_readback:
            self.dir = -1
        else:
            self.dir = 1

        # print(f"sim_fbk_dev: move called with value={value}, direction={self.dir}")