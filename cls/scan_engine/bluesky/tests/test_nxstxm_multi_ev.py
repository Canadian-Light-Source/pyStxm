#from suitcase import nxstxm as suit_nxstxm
from cls.data_io import nxstxm as suit_nxstxm
import simplejson as json

if __name__ == "__main__":
    from databroker import Broker

    #fine image scan 300x300
    uids = ['b35d81d6-0cf5-4dd3-9f0d-dc19578fe365', 'ac2f37ab-4cff-49c1-97c8-401e62b08e33', '68aec20a-31cb-4674-88c4-dcfc193c9bde']
    first_uid = uids[0]
    last_uid = uids[-1]
    data_dir = r"G:\\nexus\\nexusformat\\stxm_test\\export_tsts"
    fprefix = "Ctester"
    db = Broker.named("pystxm_amb_bl10ID1")
    for uid in uids:
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
            first_uid=first_uid,
            last_uid=uid,
        )

    suit_nxstxm.finish_export(data_dir, fprefix, first_uid)
