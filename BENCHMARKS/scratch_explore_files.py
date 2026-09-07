import pyewf
import pytsk3
from datetime import datetime

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
fs = pytsk3.FS_Info(img_info, offset=0)

all_files = []
all_dirs = []
deleted_entries = []

def traverse(directory, current_path=""):
    for entry in directory:
        if not entry.info.name or not entry.info.name.name:
            continue
        name = entry.info.name.name.decode("utf-8", "ignore")
        if name in [".", ".."]:
            continue

        full_path = f"{current_path}/{name}"
        is_allocated = (entry.info.name.flags == pytsk3.TSK_FS_NAME_FLAG_ALLOC)
        is_dir = (entry.info.meta and entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR)
        size = entry.info.meta.size if entry.info.meta else 0

        # MACB Timestamps
        mtime = datetime.utcfromtimestamp(entry.info.meta.mtime).isoformat() if (entry.info.meta and entry.info.meta.mtime) else None
        crtime = datetime.utcfromtimestamp(entry.info.meta.crtime).isoformat() if (entry.info.meta and entry.info.meta.crtime) else None

        item = {
            "path": full_path,
            "name": name,
            "is_dir": is_dir,
            "allocated": is_allocated,
            "size": size,
            "mtime": mtime,
            "crtime": crtime,
            "inum": entry.info.meta.addr if entry.info.meta else None
        }

        if not is_allocated:
            deleted_entries.append(item)

        if is_dir:
            all_dirs.append(item)
            try:
                sub_dir = entry.as_directory()
                traverse(sub_dir, full_path)
            except Exception as e:
                pass
        else:
            all_files.append(item)

root_dir = fs.open_dir(path="/")
traverse(root_dir)

print(f"Total directories enumerated: {len(all_dirs)}")
print(f"Total files discovered: {len(all_files)}")
print(f"Total deleted entries detected: {len(deleted_entries)}")

print("\n--- SAMPLE DISCOVERED FILES ---")
for f in all_files[:25]:
    status = "ALLOC" if f["allocated"] else "DELETED"
    print(f"[{status}] {f['path']} ({f['size']} bytes) | Modified: {f['mtime']}")

print("\n--- DELETED / UNALLOCATED ENTRIES ---")
for d in deleted_entries[:10]:
    print(f"[DELETED] {d['path']} ({d['size']} bytes) | Created: {d['crtime']}")

ewf_handle.close()
