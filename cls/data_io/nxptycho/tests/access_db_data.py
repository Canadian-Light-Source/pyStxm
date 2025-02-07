import os.path

from databroker import Broker
import cls.data_io.nxptycho as suit_ptycho

def dump_docs(docs):
    for d in docs:
        print(d)

db = Broker.named("pystxm_amb_bl10ID1")

uid = 'a4f0f240-358a-493e-8669-7191a9a27171'
uid = '629f3d84-e9b5-40f5-a78f-1741c4f03be7'
uid = 'd2ce3ed1-30cd-495e-ad54-1bae0de7ceed'
header = db[uid]
primary_docs = header.documents(fill=True)
#dump_docs(primary_docs)



data_dir = "c:\\test_data"
file_prefix = "new"
first_uid = uid

if os.path.exists(os.path.join(data_dir,str(uid) + "-new")):
    os.remove(os.path.join(data_dir,str(uid) + "-new"))

if os.path.exists(os.path.join(data_dir,"new.hdf5")):
    os.remove(os.path.join(data_dir,"new.hdf5"))


suit_ptycho.export(primary_docs, data_dir, file_prefix=file_prefix, first_uid=uid)
# suit_nxstxm.finish_export(data_dir, fprefix, first_uid, is_stack_dir=is_stack)
suit_ptycho.finish_export(data_dir, file_prefix, first_uid)
