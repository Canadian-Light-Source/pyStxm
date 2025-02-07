scanRequest = {
    "scanType": "Sample",
    "spatialType": "Line",
    "meander": 'VAR_MEANDER',
    "tiling": 0,
    "yAxisFast": 'VAR_Y_AXIS_FAST',
    "osaInFocus": 0,
    "lineMode": "Point by Point",
    "accelerationDistance": 0,
    "tileDelay": 0,
    "lineDelay": 0,
    "pointDelay": 0,
    "lineRepetition": 1,
    "outerRegions": [
        {
            "dwellTime": 'VAR_DWELL',
            "axes": [
                {
                    "nPoints": 25,
                    "trajectories": [
                        {
                            "start": 650,
                            "end": 700,
                            "center": 650,
                            "range": 50,
                            "step": 2.0833333333333335,
                            "positionerName": "Energy"
                        }
                    ]
                }
            ]
        },
        {
            "dwellTime": 'VAR_DWELL',
            "axes": [
                {
                    "nPoints": 30,
                    "trajectories": [
                        {
                            "start": 700.02,
                            "end": 710,
                            "range": 9.980000000000018,
                            "step": 0.34413793103448337,
                            "positionerName": "Energy"
                        }
                    ]
                }
            ]
        }
    ],
    "innerRegions": [
        {
            "axes": [
                {
                    "nPoints": 50,
                    "length": 200,
                    "angle": 0,
                    "step": 4,
                    "trajectories": [
                        {
                            "center": 0,
                            "positionerName": "FineX"
                        },
                        {
                            "center": 0,
                            "positionerName": "FineY"
                        }
                    ]
                }
            ]
        },
        {
            "axes": [
                {
                    "nPoints": 35,
                    "length": 40,
                    "angle": 0.017453292519943295,
                    "step": 1.1428571428571428,
                    "trajectories": [
                        {
                            "center": -10,
                            "positionerName": "FineX"
                        },
                        {
                            "center": -20,
                            "positionerName": "FineY"
                        }
                    ]
                }
            ]
        },
        {
            "axes": [
                {
                    "nPoints": 75,
                    "length": 63,
                    "angle": 0.0017453292519943296,
                    "step": 0.84,
                    "trajectories": [
                        {
                            "center": 75,
                            "positionerName": "FineX"
                        },
                        {
                            "center": 73,
                            "positionerName": "FineY"
                        }
                    ]
                }
            ]
        }
    ],
    "nOuterRegions": 2,
    "nInnerRegions": 3,
    "singleOuterRegionValue": 0,
    "displayedAxes": {
        "x": {
            "region": "outer",
            "index": -1
        },
        "y": {
            "region": "inner",
            "index": 0
        }
    },
    "defocus": {
        "diameter": 0
    }
}