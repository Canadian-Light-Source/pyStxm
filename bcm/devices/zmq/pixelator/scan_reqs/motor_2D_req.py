scanRequest = {
    "scanType": "Motor2D",
    "spatialType": "Image",
    "meander": 0,
    "yAxisFast": 0,
    "lineMode": "Point by Point",
    "outerRegions": [
        {
            "dwellTime": 'VAR_DWELL'
        }
    ],
    "innerRegions": [
        {
            "axes": [
                {
                    "nPoints": 'VAR_Y_NPOINTS',
                    "trajectories": [
                        {
                            "start": 'VAR_Y_START',
                            "end": 'VAR_Y_STOP',
                            "range": 'VAR_Y_RANGE',
                            "step": 'VAR_Y_STEP',
                            "positionerName": 'VAR_Y_POSITIONER'
                        }
                    ]
                },
                {
                    "nPoints":  'VAR_X_NPOINTS',
                    "trajectories": [
                        {
                            "start": 'VAR_X_START',
                            "end": 'VAR_X_STOP',
                            "range": 'VAR_X_RANGE',
                            "step": 'VAR_X_STEP',
                            "positionerName": 'VAR_X_POSITIONER'
                        }
                    ]
                }
            ]
        }
    ],
    "nOuterRegions": 1,
    "nInnerRegions": 1,
    "displayedAxes": {
        "x": {
            "region": "inner",
            "index": 1
        },
        "y": {
            "region": "inner",
            "index": 0
        }
    }
}
