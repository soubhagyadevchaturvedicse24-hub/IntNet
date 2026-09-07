import sys
from dfvfs.lib import definitions
from dfvfs.path import factory as path_spec_factory
from dfvfs.resolver import resolver

print("--- TESTING DFVFS ON E01 ---")
try:
    os_path_spec = path_spec_factory.Factory.NewPathSpec(
        definitions.TYPE_INDICATOR_OS,
        location=r"D:\Proto SIH\Images\Images_Set_1.E01"
    )

    ewf_path_spec = path_spec_factory.Factory.NewPathSpec(
        definitions.TYPE_INDICATOR_EWF,
        parent=os_path_spec
    )
    
    # Open file object representing the unified raw disk stream
    ewf_file_object = resolver.Resolver.OpenFileObject(ewf_path_spec)
    print("dfVFS opened EWF file object successfully!")
    print("Virtual disk size via dfVFS:", ewf_file_object.get_size(), f"({ewf_file_object.get_size() / (1024**2):.2f} MB)")

    # Test TSK path spec with parent = ewf_path_spec
    tsk_path_spec = path_spec_factory.Factory.NewPathSpec(
        definitions.TYPE_INDICATOR_TSK,
        parent=ewf_path_spec,
        location="/"
    )
    tsk_file_entry = resolver.Resolver.OpenFileEntry(tsk_path_spec)
    print("dfVFS opened TSK filesystem on EWF successfully!")
    
    entries = []
    for sub in tsk_file_entry.sub_file_entries:
        entries.append(sub.name)
    print(f"dfVFS enumerated {len(entries)} entries in root directory via TSK:")
    print(entries[:15])

except Exception as e:
    import traceback
    traceback.print_exc()
