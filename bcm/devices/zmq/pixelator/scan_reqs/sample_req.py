scanRequest = {
    "scanType": "Sample",
    "spatialType": "Image",
    "meander": 1,
    "tiling": 1,
    "yAxisFast": 1,
    "osaInFocus": 0,
    "lineMode": "Point by Point",
    "accelerationDistance": 1,
    "tileDelay": 0.002,
    "lineDelay": 0.003,
    "pointDelay": 0.004,
    "lineRepetition": 5,
    "outerRegions": [
        {
            "dwellTime": 0.01,
            "axes": [
                {
                    "nPoints": 1,
                    "trajectories": [
                        {
                            "start": 650,
                            "end": 650,
                            "range": 0,
                            "step": 0,
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
                    "nPoints": 25,
                    "trajectories": [
                        {
                            "start": -750,
                            "end": 750,
                            "center": 0,
                            "range": 1500,
                            "step": 60,
                            "positionerName": "CoarseY"
                        }
                    ]
                },
                {
                    "nPoints": 25,
                    "trajectories": [
                        {
                            "start": -750,
                            "end": 750,
                            "center": 0,
                            "range": 1500,
                            "step": 60,
                            "positionerName": "CoarseX"
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
    },
    "positionPrecision": {
        "precision": 6
    },
    "defocus": {
        "diameter": 0
    },
    "polarization": {
        "active": 1
    }
}