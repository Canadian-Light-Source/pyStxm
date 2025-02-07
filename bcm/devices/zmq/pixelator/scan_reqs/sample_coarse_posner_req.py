scanRequest = {
    "scanType": "Sample"
    , "spatialType": "Image"
    , "meander": 0
    , "tiling": 0
    , "yAxisFast": 0
    , "lineMode": "Point by Point"
    , "outerRegions": [
        {
            "dwellTime": 0.012500000000000001
            , "axes": [
            {
                "nPoints": 10
                , "trajectories": [
                {
                    "start": 650.0
                    , "end": 680.0
                    , "range": 30.0
                    , "step": 3.3333333333333335
                    , "positionerName": "Energy"
                }
            ]
            }
        ]
        }
        , {
            "dwellTime": 0.012500000000000001
            , "axes": [
                {
                    "nPoints": 3
                    , "trajectories": [
                    {
                        "start": 680.20000000000005
                        , "end": 700.0
                        , "range": 19.799999999999955
                        , "step": 9.8999999999999773
                        , "positionerName": "Energy"
                    }
                ]
                }
            ]
        }
        , {
            "dwellTime": 0.012500000000000001
            , "axes": [
                {
                    "nPoints": 4
                    , "trajectories": [
                    {
                        "start": 700.20000000000005
                        , "end": 710.0
                        , "range": 9.7999999999999545
                        , "step": 3.2666666666666515
                        , "positionerName": "Energy"
                    }
                ]
                }
            ]
        }
    ]
    , "innerRegions": [
        {
            "axes": [
                {
                    "nPoints": 25
                    , "trajectories": [
                    {
                        "center": 0.0
                        , "range": 50.0
                        , "step": 2.0
                        , "positionerName": "CoarseY"
                    }
                ]
                }
                , {
                    "nPoints": 25
                    , "trajectories": [
                        {
                            "center": 0.0
                            , "range": 50.0
                            , "step": 2.0
                            , "positionerName": "CoarseX"
                        }
                    ]
                }
            ]
        }
    ]
    , "nOuterRegions": 1
    , "nInnerRegions": 1
    , "singleOuterRegionValue": 0
    , "displayedAxes": {
        "x": {
            "region": "inner"
            , "index": 1
        }
        , "y": {
            "region": "inner"
            , "index": 0
        }
    }
    , "defocus": {
        "diameter": 0.0
    }
}

A
