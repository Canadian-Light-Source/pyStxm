scanRequest = {
    "scanType": "Sample",
    "spatialType": "Line",
    "meander": 'VAR_MEANDER',
    "tiling": 0,
    "yAxisFast": 'VAR_Y_AXIS_FAST',
    "lineMode": "Point by Point",
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
                            "range": 50,
                            "step": 2.0833333333333335,
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
                    "nPoints": 20,
                    "length": 4,
                    "angle": 0,
                    "step": 0.2,
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
        }
    ],
    "nOuterRegions": 1,
    "nInnerRegions": 1,
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