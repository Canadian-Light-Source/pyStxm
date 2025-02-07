scanRequest = {
    "scanType": "Focus"
    , "spatialType": "Image"
    , "meander": 0
    , "yAxisFast": 0
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
                            "center": 0.0
                            , "positionerName": "FineX"
                        }
                        , {
                            "center": 0.0
                            , "positionerName": "FineY"
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

