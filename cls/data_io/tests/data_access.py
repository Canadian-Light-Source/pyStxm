
from databroker import Broker
import cls.data_io.nxstxm as suit_nxstxm

def dump_docs(docs):
    for d in docs:
        print(d)

db = Broker.named("pystxm_amb_bl10ID1")

#this scan has all flyers selected and only a single dev in baseline
#uid = '07651366-0b42-4e12-ab94-f520f4a01e0d'
#this scan has all flyers and all devs
#uid = 'b9280b61-3791-49d2-9f8a-01ee01acae9f'
#uid = 'e968be87-524c-4407-8bf2-6ba095b39a08'
uid = '47a20703-52aa-4d01-83b1-810e906452e3' # focus scan
uid = 'ac52f634-aee2-4f40-b13f-2ff5d076d435' # ptycho
uid = 'ac6fbc60-2865-42fa-bfa4-eab52514d97f'
uid = 'd9efdb6f-9321-45ac-bae1-bc646792a64a' # coarse image
header = db[uid]
primary_docs = header.documents(fill=True)
#dump_docs(primary_docs)



data_dir = "c:/test_data"
file_prefix = "new"
first_uid = uid
suit_nxstxm.export(primary_docs, data_dir, file_prefix=file_prefix, first_uid=uid)
# suit_nxstxm.finish_export(data_dir, fprefix, first_uid, is_stack_dir=is_stack)
suit_nxstxm.finish_export(data_dir, file_prefix, first_uid)
