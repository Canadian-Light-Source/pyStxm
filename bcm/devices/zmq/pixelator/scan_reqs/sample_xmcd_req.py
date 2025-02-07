scanRequest = {
    "scanType": "Sample",
    "spatialType": "Image",
    "meander": 1,
    "tiling": 1,
    "yAxisFast": 1,
    "osaInFocus": 0,
    "lineMode": "Point by Point",
    "accelerationDistance": 13,
    "tileDelay": 2,
    "lineDelay": 3,
    "pointDelay": 0,
    "lineRepetition": 2,
    "outerRegions": [
        {
            "dwellTime": 0.1,
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
                    "nPoints": 100,
                    "trajectories": [
                        {
                            "start": -250,
                            "end": 250,
                            "range": 500,
                            "step": 5.05050505050505,
                            "positionerName": "FineY"
                        }
                    ]
                },
                {
                    "nPoints": 100,
                    "trajectories": [
                        {
                            "start": -250,
                            "end": 250,
                            "range": 500,
                            "step": 5.05050505050505,
                            "positionerName": "FineX"
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
    "defocus": {
        "diameter": 0
    },
    "polarization": {
        "active": 1,
        "types": [
            "circ. right"
        ],
        "stokes": [
            "[0,0,1]"
        ]
    }
}