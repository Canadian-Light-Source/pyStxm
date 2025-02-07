#from suitcase import nxstxm as suit_nxstxm
from cls.data_io import nxstxm as suit_nxstxm
import simplejson as json

if __name__ == "__main__":
    from databroker import Broker
    #from cls.scan_engine.bluesky.tests.rev_lu_dct import rev_lu_dct, img_idx_map

    #Coarse Image
    uid = "46a14353-2663-432e-80f7-fbdd4c07e474"
    #not sure
    uid = "1a7b46ee-4047-4e20-9015-1ad1936d5801"

    #fine image scan 300x300
    uid = "e76c9c7c-810f-49b8-ad2d-153c1e30c440"

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
