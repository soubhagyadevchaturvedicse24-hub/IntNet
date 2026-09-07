import pyewf
import pytsk3

class EwfImgInfo(pytsk3.Img_Info):
    def __init__(self, ewf_handle):
        self._ewf_handle = ewf_handle
        super().__init__()

    def read(self, offset, size):
        self._ewf_handle.seek(offset)
        return self._ewf_handle.read(size)

    def get_size(self):
        return self._ewf_handle.get_media_size()

filenames = pyewf.glob(r"D:\Proto SIH\Images\Images_Set_1.E01")
ewf_handle = pyewf.handle()
ewf_handle.open(filenames)

img_info = EwfImgInfo(ewf_handle)

print("--- TESTING VOLUME / PARTITION TABLE ---")
has_volume = False
try:
    vs = pytsk3.Volume_Info(img_info)
    has_volume = True
    print("Volume System Type:", vs.info.vstype)
    print("Block size:", vs.info.block_size)
    print("Partition count:", vs.info.part_count)
    for part in vs:
        desc = part.desc.decode("utf-8", "ignore") if hasattr(part.desc, "decode") else str(part.desc)
        print(f"Partition #{part.addr}: {desc}, start_sector={part.start}, len_sectors={part.len}, byte_offset={part.start * 512}")
except Exception as e:
    print("Volume_Info returned:", e)

print("\n--- TESTING FILESYSTEM IDENTIFICATION ---")
offsets_to_test = [0]
if has_volume:
    for part in vs:
        if part.len > 0 and part.flags == pytsk3.TSK_VS_PART_FLAG_ALLOC:
            offsets_to_test.append(part.start * 512)

for offset in sorted(list(set(offsets_to_test))):
    print(f"\nTesting offset: {offset} (sector {offset // 512})")
    try:
        fs = pytsk3.FS_Info(img_info, offset=offset)
        print("  -> Filesystem detected! Type:", fs.info.ftype)
        print("  -> Block size:", fs.info.block_size)
        print("  -> Block count:", fs.info.block_count)
        print("  -> Root inum:", fs.info.root_inum)
        print("  -> FS ID:", getattr(fs.info, "fs_id", None))

        # Enumerate root dir
        print("  -> Attempting root directory enumeration:")
        root_dir = fs.open_dir(path="/")
        entry_count = 0
        for entry in root_dir:
            name = entry.info.name.name.decode("utf-8", "ignore") if entry.info.name and entry.info.name.name else "unnamed"
            flags = "ALLOC" if (entry.info.name and entry.info.name.flags == pytsk3.TSK_FS_NAME_FLAG_ALLOC) else "UNALLOC"
            entry_type = "DIR" if (entry.info.meta and entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR) else "FILE"
            size = entry.info.meta.size if entry.info.meta else 0
            print(f"     [{flags}] {entry_type}: {name} (size: {size} bytes, inum: {entry.info.meta.addr if entry.info.meta else 'N/A'})")
            entry_count += 1
        print(f"  -> Total root directory entries: {entry_count}")

    except Exception as e:
        print(f"  -> No filesystem at offset {offset}: {e}")

ewf_handle.close()
print("\nTSK test finished.")
