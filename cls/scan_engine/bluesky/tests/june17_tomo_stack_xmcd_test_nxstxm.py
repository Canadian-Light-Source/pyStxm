from suitcase import nxstxm as suit_nxstxm

if __name__ == "__main__":
    from databroker import Broker
    from cls.scan_engine.bluesky.tests.rev_lu_dct import rev_lu_dct
    from cls.utils.file_system_tools import get_next_file_num_in_seq
    import simplejson as json

    # uids = ['ba274725-432f-4d65-8423-4c592fe37c13', 'd21c97c7-5ff2-4d9b-a975-5a712f1c772f', '206c3a4d-c76d-4b05-a29e-3f130f942cd1', '7482ddfb-0d46-45d4-9ddf-b00b2cf0c4f5', '84f4aa31-d6f9-44a5-a45b-645bac4c0a8e', '70e840d4-aa98-4f2a-bb7c-cdb7ba646ae0', '9699fe10-ebdc-4c03-b1c8-b034c4c89f8d', '94d85889-bb3c-4562-9681-2a628aaef3bf']
    uids = [
        "72a42c67-9a9a-4af0-8896-133363ea5526",
        "2bcd05f2-a99d-4a9b-a251-7a9833bd0be6",
        "7738c0c3-30ef-4698-9d06-6b0c6eea4eba",
        "836b1945-de9f-4942-9afd-55956a6452f4",
        "650fc8cb-8769-49b5-8768-8b70bdc98d9c",
        "3ddf212a-aacb-49aa-b552-210d4b57c4c6",
        "9dc67043-f129-44e1-be0b-594f6d3247d3",
        "e5a94d88-2f70-4583-bd72-7bfd6579bff0",
        "cae7b90e-6efa-41d8-b020-945eb8e6780f",
        "be4eb514-81d0-4796-9831-03ad72d5fe92",
        "eef727b6-b741-460a-a07e-5561bd6685d3",
        "52571fbc-d953-4cdd-82b1-d408549398b9",
        "36049ef9-cb03-4e52-9478-7e966fb7d686",
        "98e6f583-6a11-49fc-8752-400a1fa10f26",
        "490297a3-89b8-4939-a7f6-904816578080",
        "6aed9305-e8e9-4f11-a14a-d58c2f3a3873",
        "49127577-90ba-40f6-b57f-0df259623b23",
        "3a3d0a19-a86f-4d95-8de8-e41bd8de1a71",
        "60f40304-7886-4c50-a3be-24a3257894a2",
        "30030838-8521-4cc8-b703-7be9ac5b2596",
        "5fa37b8b-ee60-453b-ba16-dfdf6734199a",
        "903b70bf-9dba-4267-85cd-3351f18efb27",
        "db428994-6d8a-46ba-87cc-b9fceca594f6",
        "0c7ce4d1-6388-452f-8cef-83ad6dc10da1",
        "28fce7ca-56ae-4369-96b9-507e36d001cd",
        "1fc2f06a-afed-4e95-9c54-a1aab716e315",
        "71ef71a6-dc18-406a-9cf6-4e87c6cafdbd",
        "902e87d6-4cf6-4f8e-9525-0351e2295e32",
        "17c5a3b2-6099-4af9-a4de-d74194bf8ada",
        "0fa2b605-5084-4b30-bb0b-b24cec73fffc",
        "5c9cd07a-d473-4d90-a14f-b598b478e4dc",
        "512bf07d-6aa3-4dbb-ad9c-ec1f7450132e",
        "4ba135a8-a45a-41bf-996b-98c1ac3263db",
        "12119d29-079b-41cc-b55e-8ec044b4072a",
        "dd68230c-64c1-4301-8a9a-f33000865b4e",
        "5efaaec4-5351-4969-805b-b589605ce2b3",
        "f09c2722-613e-4084-b14f-777d06121dbd",
        "02a2c360-6f06-4264-8690-5f48a9b96134",
        "95c879aa-92db-4dd4-81aa-1dcddb14af00",
        "4cd48b10-651d-4600-a195-82f2050564cd",
        "1a1f2812-5201-4356-906c-09ee2ba070aa",
        "8cd2e3d8-0dd2-45e5-a9ec-7a8877aec972",
        "b2771cab-e87e-4ec5-a972-32375d8f8219",
        "132a5e46-d8c9-4001-aecf-b8acd15fd3ff",
        "9affaaa7-85fa-48b7-83b9-d3eace83c56b",
        "534e4cbf-df27-4c22-9dcc-c2d801ced5aa",
        "3a7ea47e-259e-4224-88f6-55e0c3bc9178",
        "dfac10ef-c7a8-4a6c-a42c-17f3d29f5968",
        "6060aca7-1c2e-4519-b8fa-74eacdb507b5",
        "b118fa85-e681-4058-a333-30e39afd5184",
        "99981ae8-592e-421d-b383-74f1253b726d",
        "a0142396-7aa6-4fce-8d7f-12fb19298c68",
        "aac22570-b96a-48a8-8b70-8274b9420408",
        "886e14ff-19e5-43b5-878b-c35f8fd2c2f0",
        "ebd79844-a0b5-41dc-afaa-87d13c3acabb",
        "09ef0694-cf2c-4f25-be9c-1a417107501d",
        "f4f8a02d-8dca-4307-b4be-9b767c497058",
        "77cd6f61-db50-4ac5-ac09-e29628f374bd",
        "a805e175-79eb-4377-a462-918285895db8",
        "07cbe1ae-3e4e-49ef-bb5f-6e4bafcb5a40",
        "3cb79925-7948-40b0-958a-45e2996b23af",
        "4481c47a-4f42-4717-bef5-5be6f8a1a479",
        "3b6b7f8e-9375-46b6-82a0-d3fe0311757f",
        "4dd9ae10-1407-4437-92b6-c67d49322b4f",
        "d6b1bfa7-7461-403b-a4b4-e9495a4c6163",
        "2cf8095a-d4dc-4049-bba2-1b27ede86dcc",
        "7a8b8e29-5c31-424d-9708-8576535c9441",
        "2d777bd5-972d-4982-a553-64ae77c9d87a",
        "ae087b82-68d1-4c3c-bbd3-1906ce4d3b4e",
        "e8ddea66-483d-41a6-853b-2b85427cdf5b",
        "75795365-5a09-4e04-8f72-6d818157c477",
        "75a3cd70-3017-4d6a-9883-265bf06ef4bb",
        "650df110-ca81-45f9-a532-5beb638ed294",
        "e3b48130-8255-4dfa-a93a-05b34ca37ae2",
        "d91d3ea7-3665-4612-a433-c33256b8bcf4",
        "1586729a-dd24-4a60-acff-720032d572c7",
        "002581da-58fb-47d7-848e-b540ae7911bb",
        "6e737309-5cec-4070-81ed-8c7b7d70090b",
        "45970397-3894-494d-a047-6d85f54bdd91",
        "c2ee605a-11b6-4151-9b8e-58f5a8366518",
        "4a8daff2-25ec-4506-84f8-2d4bf446cf2c",
        "47c217ee-e7c4-4657-bd6d-e1f49ac51c2e",
        "607634fb-6e1d-425e-ae33-9706be6458ac",
        "6d80faec-da17-4e7d-ac68-ab975b1fe8ff",
        "4c28fd6f-6415-469a-82e2-86defcbd269a",
        "631ec5f3-f5da-49d2-a665-025c15dd12b3",
        "f63725c2-f297-4f18-8535-39312ac57c21",
        "ad75fe39-9f1b-4870-91b4-510938f9c22a",
        "72bfc6b6-214f-4524-9ff0-590bffc6dd62",
        "4acb9b4e-ade2-4897-b1c5-43faf6cf036b",
        "a97a062b-fc20-4296-8664-4d144535cab1",
        "835495a3-e1be-4929-b44b-7f51beb195af",
        "30b5a65a-ed22-4521-a9ef-185afc733f46",
        "582dfd16-c9f8-4d43-baf5-656546e7627e",
        "ff69ad42-097b-486f-99af-d1a0e3982d9a",
        "f1d48955-e8fa-4323-8dde-8ead7eb1a05b",
        "03be1b1d-95ec-46a6-a9d9-3eeac79bcc47",
        "4a41e9b8-6c67-4def-97e1-04a53df72c56",
        "21eece36-369e-4e8a-8ae4-f7762bbcfc53",
        "a7d87caa-f02a-493e-bffe-b6d9c3d58fb1",
        "5ab49de4-e803-4009-aebc-b063e0bdc241",
        "f5ac6e18-a7ab-4c72-93b7-7f4737da3080",
        "d1c10bb7-e508-43b9-91c1-642f58985b83",
        "91f18bbc-71c9-4514-9673-e51fa99d3c00",
        "36cf6568-8244-4dc6-b000-214a4dda174b",
        "9be1c88f-2b2b-44b9-bb45-04851e13b7f0",
        "70c4c2c0-057d-43b9-aa30-744c8682a000",
        "a4035d7f-fc6c-42cc-a1ce-fead6e71f0c5",
        "44ad53db-d203-4844-9df1-3442e322a9b7",
        "34c0a4d3-ae0d-46dc-89e7-2e8239e6fcc4",
        "6e90a7d5-0bc7-4623-9693-db95755796e9",
        "2f9fe922-efae-4f64-8b7e-fc43e38b8916",
        "ff088933-1e61-4962-8942-9a40bd53590b",
        "85d8c140-55ab-46ab-9231-2cc1e150e5b3",
        "1de104ab-0f7f-4299-81f4-09f51eabe269",
        "758579dc-f767-404e-a530-94d589062d50",
        "dcb304df-6e07-407c-a644-15852cc0366c",
        "cc82e304-386a-4210-b569-c16ee7838f0d",
        "2a22477d-2ce4-47b6-ac9b-bd2b8f716d99",
        "8a821ff9-1aa0-43c5-82d7-b24b262bb773",
        "27112a05-4194-4d75-975c-3f8683a397e9",
        "ad44df5f-53fc-45dc-a44d-a6b3b62d0726",
        "d03c3450-c94a-4e68-8db1-f6c08de010f9",
        "8d270757-ebc1-480e-b7c0-d96dd4c7c9e1",
        "a31ce402-38df-4927-910a-184cbfd5a345",
        "293939a7-279b-4844-bc0c-3aee35733266",
        "8bac6fbd-b0a1-4535-9b85-9425363f7247",
        "2c33279e-23d5-49d0-9a24-9d6ccf6293d8",
        "e812ae19-7b77-4812-b5d1-90638d3c62c4",
        "fae858b9-37f3-4754-8e1a-a4314384da60",
        "4193e028-3bff-47a7-ae9a-884e25469dc4",
        "b01f1411-bda3-4e2e-b050-8f6be912a421",
        "39cede38-3766-4bfc-aa10-ad64a2237380",
        "80e6e358-5825-461d-aa74-0faa9ef74317",
        "a00bda59-13bc-4115-9aac-2b3e5665c4a5",
        "9933024e-4ac4-4610-bb37-da617315edec",
        "3cb56472-91c6-46c0-a196-5636c0adc90c",
        "d33dace5-30da-4088-9652-ab74558f63ef",
        "c6d81d06-4056-4d5e-9b37-0ed866d689a5",
        "65a4f8c8-a5dd-4558-aed5-77936128bca3",
    ]

    first_uid = uids[0]
    last_uid = uids[-1]

    data_dir = r"S:\\STXM-data\\Cryo-STXM\\2019\\guest\\0618"
    fprefix = "C" + str(
        get_next_file_num_in_seq(data_dir, prefix_char="C", extension="hdf5")
    )
    db = Broker.named("pystxm_amb_bl10ID1")
    # for uid in uids:
    #     header = db[uid]
    #     primary_docs = header.documents(fill=True)
    #     suit_nxstxm.export(primary_docs, data_dir, file_prefix=fprefix, index=0,
    #                        rev_lu_dct=rev_lu_dct, img_idx_map=img_idx_map, \
    #                        first_uid=uid, last_uid=uid)
    idx = 0
    for uid in uids:
        print("starting basic export [%s]" % uid)
        header = db[uid]
        md = json.loads(header["start"]["metadata"])
        _img_idx_map = json.loads(md["img_idx_map"])
        # img_idx_map[uid] = copy.copy(_img_idx_map['%d' % 0])
        primary_docs = header.documents(fill=True)
        suit_nxstxm.export(
            primary_docs,
            data_dir,
            file_prefix=fprefix,
            index=0,
            rev_lu_dct=rev_lu_dct,
            img_idx_map=_img_idx_map["%d" % idx],
            first_uid=first_uid,
            last_uid=last_uid,
        )
        idx += 1

    suit_nxstxm.finish_export(data_dir, fprefix, first_uid)
