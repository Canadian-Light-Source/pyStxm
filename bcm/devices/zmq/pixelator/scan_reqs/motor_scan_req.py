scanRequest = {
    "scanType": "Motor"
    , "spatialType": "Point"
    , "meander": 'VAR_MEANDER'
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
                    "nPoints": 'VAR_X_NPOINTS'
                    , "trajectories": [
                    {
                        "start": 'VAR_X_START'
                        , "end": 'VAR_X_STOP'
                        , "range": 'VAR_X_RANGE'
                        , "step": 'VAR_X_STEP'
                        , "positionerName": 'VAR_X_POSITIONER'
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
            , "index": 0
        }
        , "y": {
            "region": "none"
        }
    }
}

