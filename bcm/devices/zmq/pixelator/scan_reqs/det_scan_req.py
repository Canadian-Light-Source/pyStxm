scanRequest = {
    "scanType": "Detector"
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
                    "nPoints": 'VAR_Y_NPOINTS'
                    , "trajectories": [
                    {
                        "center": 'VAR_Y_CENTER'
                        , "range": 'VAR_Y_RANGE'
                        , "step": 'VAR_Y_STEP'
                        , "positionerName": "DetectorY"
                    }
                ]
                }
                , {
                    "nPoints": 'VAR_X_NPOINTS'
                    , "trajectories": [
                        {
                            "center": 'VAR_X_CENTER'
                            , "range": 'VAR_X_RANGE'
                            , "step": 'VAR_X_STEP'
                            , "positionerName": "DetectorX"
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
