

import time
from bluesky import RunEngine
from databroker import Broker
from ophyd  import Device
from ophyd import Component as Cpt
from ophyd.signal import EpicsSignal, EpicsSignalBase, EpicsSignalRO
#from ophyd.sim import det1, det2, motor
from bluesky.plans import count, scan

# class Zoneplate(Device):
#     a1 = Cpt(Signal)
#     diameter = Cpt(Signal)
#     central_stop = Cpt(Signal)
#     resolution = Cpt(Signal)
#
#     a0_focus_target = Cpt(Signal) # this is either OSA in focus, or Sample in focus
#     energy = Cpt(Signal)
#
#     def __init__(self, prefix, name, zpz_posner, a1, diam, cstop, res):
#         super(Zoneplate, self).__init__(prefix, name=name)

# class SingleROPv(Device):
#     rbv = EpicsSignalRO('.RBV')
#     def __init__(self, prefix, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, **kwargs):
#         super(SingleROPv, self).__init__(prefix, name=name, kind=kind, read_attrs=read_attrs, configuration_attrs=configuration_attrs, parent=parent, **kwargs)
#
#     def read(self):
#         return {self.name: {'value': self.rbv.get(),
#                         'timestamp': time.time(),
#                         'units': self._units}}
#
#     def describe(self):
#         '''
#         on return from super().describe() res is the following:
#         OrderedDict([('TM1610-3-I12-01_val',
#               {'source': 'PV:TM1610-3-I12-01.VAL',
#                'dtype': 'number',
#                'shape': [],
#                'units': None,
#                'lower_ctrl_limit': None,
#                'upper_ctrl_limit': None})])
#         then this describe() adds 'units' and 'category'
#         :return:
#         '''
#         # print('TestDetectorDevice: describe called')
#         res = super().describe()
#         d = res
#         k = list(res.keys())[0]
#         d[self.name] = res.pop(k)
#         for key in d:
#             d[key]['units'] = self._units
#             d[key]['category'] = self._dev_category
#             d[key]['desc'] = self._desc
#         return d


class SinglePv(Device):
    val = Cpt(EpicsSignal,'.VAL')
    def __init__(self, prefix, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, **kwargs):
        super(SinglePv, self).__init__(prefix, name=name, kind=kind, read_attrs=read_attrs, configuration_attrs=configuration_attrs, parent=parent, **kwargs)

    def read(self):
        return {self.name: {'value': self.val.get(),
                        'timestamp': time.time()
                        }}

    def set

    def describe(self):
        '''
        on return from super().describe() res is the following:
        OrderedDict([('TM1610-3-I12-01_val',
              {'source': 'PV:TM1610-3-I12-01.VAL',
               'dtype': 'number',
               'shape': [],
               'units': None,
               'lower_ctrl_limit': None,
               'upper_ctrl_limit': None})])
        then this describe() adds 'units' and 'category'
        :return:
        '''
        # print('TestDetectorDevice: describe called')
        res = super().describe()
        d = res
        k = list(res.keys())[0]
        d[k]['source'] = d[k]['source'].replace('PV:', '')
        d[self.name] = res.pop(k)
        # for key in d:
        #     d[key]['units'] = self._units
        #     d[key]['category'] = self._dev_category
        #     d[key]['desc'] = self._desc
        return d

# db = Broker.named('mongo_databroker')
# RE = RunEngine({})
#
# # Insert all metadata/data captured into db.
# RE.subscribe(db.insert)
#
# dets = [det1, det2]
#
# RE.subscribe(rr)
# RE(scan(dets, motor, -1, 1, 10))
if __name__ == '__main__':
    spv = SinglePv('TRG2400:cycles', name='PCT')
    print(spv.read())
    print(spv.describe())
    print()