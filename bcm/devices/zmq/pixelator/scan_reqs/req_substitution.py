import simplejson as json
from bcm.devices.zmq.pixelator.app_dcs_devnames import app_to_dcs_devname_map
# assuming


def do_substitutions(scan_request_dct, parent):
    x_nm = parent.x['POSITIONER']
    y_nm = parent.y['POSITIONER']
    z_nm = parent.z['POSITIONER']
    if x_nm in ['None', None]:
        x_posner_nm = '"NO_NAME_SPECIFIED"'
    else:
        x_nm = app_to_dcs_devname_map[x_nm]
        x_posner_nm = f'"{x_nm}"'

    if y_nm in ['None', None]:
        y_posner_nm = '"NO_NAME_SPECIFIED"'
    else:
        y_nm = app_to_dcs_devname_map[y_nm]
        y_posner_nm = f'"{y_nm}"'

    if z_nm in ['None', None]:
        z_posner_nm = '"NO_NAME_SPECIFIED"'
    else:
        z_nm = app_to_dcs_devname_map[z_nm]
        z_posner_nm = f'"{z_nm}"'

    replace_map = {'VAR_MEANDER': 1 if parent.wdg_scan_req['meander'] else 0,
                   'VAR_Y_AXIS_FAST': 1 if parent.wdg_scan_req['y_axis_fast'] else 0,
                   'VAR_DWELL': parent.dwell_ms * 0.001,

                   'VAR_Z_NPOINTS': parent.zp['Z']['NPOINTS'],
                   'VAR_Z_CENTER': parent.zp['Z']['CENTER'],
                   'VAR_Z_RANGE': parent.zp['Z']['RANGE'],
                   'VAR_Z_STEP': parent.zp['Z']['STEP'],
                   'VAR_Z_START': parent.zp['Z']['START'],
                   'VAR_Z_STOP': parent.zp['Z']['STOP'],
                   'VAR_Z_POSITIONER': z_posner_nm,

                   'VAR_X_NPOINTS': parent.x['NPOINTS'],
                   'VAR_X_CENTER': parent.x['CENTER'],
                   'VAR_X_RANGE': parent.x['RANGE'],
                   'VAR_X_STEP': parent.x['STEP'],
                   'VAR_X_START': parent.x['START'],
                   'VAR_X_STOP': parent.x['STOP'],
                   'VAR_X_POSITIONER': x_posner_nm,

                   'VAR_Y_NPOINTS': parent.y['NPOINTS'],
                   'VAR_Y_CENTER': parent.y['CENTER'],
                   'VAR_Y_RANGE': parent.y['RANGE'],
                   'VAR_Y_STEP': parent.y['STEP'],
                   'VAR_Y_START': parent.y['START'],
                   'VAR_Y_STOP': parent.y['STOP'],
                   'VAR_Y_POSITIONER': y_posner_nm,

                   }

    scan_req_str = json.dumps(scan_request_dct)

    for k, v in replace_map.items():
        scan_req_str = scan_req_str.replace(f'"{k}"', str(v))

    #return to a dict
    sr_dct = json.loads(scan_req_str)
    return sr_dct



