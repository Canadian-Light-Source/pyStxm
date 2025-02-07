scanRequest = {
    "scanType": "Sample",
    "spatialType": "Point",
    "meander": 0,
    "tiling": 0,
    "yAxisFast": 0,
    "lineMode": "Point by Point",
    "outerRegions": [
        {
            "dwellTime": 0.012,
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
        },
        {
            "dwellTime": 0.012,
            "axes": [
                {
                    "nPoints": 26,
                    "trajectories": [
                        {
                            "start": 701,
                            "end": 710,
                            "range": 9,
                            "step": 0.36,
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
                    "nPoints": 1,
                    "trajectories": [
                        {
                            "center": 1,
                            "range": 0.7071067811865476,
                            "positionerName": "FineX"
                        },
                        {
                            "center": 1,
                            "range": 0.7071067811865476,
                            "positionerName": "FineY"
                        }
                    ]
                }
            ]
        },
        {
            "axes": [
                {
                    "nPoints": 1,
                    "trajectories": [
                        {
                            "center": 2,
                            "range": 0.7071067811865476,
                            "positionerName": "FineX"
                        },
                        {
                            "center": 2,
                            "range": 0.7071067811865476,
                            "positionerName": "FineY"
                        }
                    ]
                }
            ]
        },
        {
            "axes": [
                {
                    "nPoints": 1,
                    "trajectories": [
                        {
                            "range": 0.7071067811865476,
                            "positionerName": "FineX"
                        },
                        {
                            "range": 0.7071067811865476,
                            "positionerName": "FineY"
                        }
                    ]
                }
            ]
        }
    ],
    "nOuterRegions": 2,
    "nInnerRegions": 2,
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