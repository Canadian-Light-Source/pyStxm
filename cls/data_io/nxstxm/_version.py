# This file was generated by 'versioneer.py' (0.18) from
# revision-control system data, or from the parent directory name of an
# unpacked source archive. Distribution tarballs contain a pre-generated copy
# of this file.

import json

version_json = """
{
 "date": "2019-07-25T11:22:11-0600",
 "dirty": true,
 "error": null,
 "full-revisionid": "eda68350b03d2617d7b0e71133ab41ecc60060cc",
 "version": "0.post1.dev0+geda6835"
}
"""  # END VERSION_JSON


def get_versions():
    return json.loads(version_json)
