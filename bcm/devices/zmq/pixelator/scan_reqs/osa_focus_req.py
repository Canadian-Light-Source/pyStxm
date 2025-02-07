scanRequest = {
    "scanType": "OSA Focus"
    , "spatialType": "Image"
    , "meander": 'VAR_MEANDER'
    , "yAxisFast": 'VAR_Y_AXIS_FAST'
    , "lineMode": "Point by Point"
    , "outerRegions": [
        {
            "dwellTime": 'VAR_DWELL'
        }
    ]
    , "innerRegions": [
        {
            "axes": [
                {
                    "nPoints": 'VAR_Z_NPOINTS'
                    , "trajectories": [
                    {
                        "center": 'VAR_Z_CENTER'
                        , "range": 'VAR_Z_RANGE'
                        , "step": 'VAR_Z_STEP'
                        , "positionerName": "Zoneplate"
                    }
                ]
                }
                , {
                    "nPoints": 'VAR_X_NPOINTS'
                    , "length": 'VAR_X_RANGE'
                    , "angle": 0.0
                    , "step": 'VAR_X_STEP'
                    , "trajectories": [
                        {
                            "center": 'VAR_X_CENTER'
                            , "positionerName": "OSAX"
                        }
                        , {
                            "center": 'VAR_Y_CENTER'
                            , "positionerName": "OSAY"
                        }
                    ]
                }
            ]
        }
    ]
    , "nOuterRegions": 1
    , "nInnerRegions": 1
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
}

