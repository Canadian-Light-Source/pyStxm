#from suitcase import nxstxm as suit_nxstxm
from cls.data_io import nxstxm as suit_nxstxm
import simplejson as json

if __name__ == "__main__":
    from databroker import Broker

    #OSA focus
    uid = "7aa2682a-fccc-4cd9-85cc-4cc092df9bb5"

    data_dir = r"G:\\nexus\\nexusformat\\stxm_test\\export_tsts"
    fprefix = "Ctester"
    db = Broker.named("pystxm_amb_bl10ID1")
    header = db[uid]
    docs_lst = list(header.documents(fill=True))
    md_str = docs_lst[0][1]['metadata']
    md = json.loads(md_str)
    primary_docs = header.documents(fill=True)
    suit_nxstxm.export(
        primary_docs,
        data_dir,
        file_prefix=fprefix,
        index=0,
        rev_lu_dct=md['rev_lu_dct'],
        img_idx_map=md['img_idx_map'],
        first_uid=uid,
        last_uid=uid,
    )
