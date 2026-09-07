import os
import sys
from pathlib import Path
import pyewf

img_path = r"D:\Proto SIH\Images\Images_Set_1.E01"
print("pyewf version:", pyewf.get_version())

filenames = pyewf.glob(img_path)
print("pyewf.glob returned filenames:", filenames)

handle = pyewf.handle()
handle.open(filenames)

print("Segment count:", handle.number_of_segments)
print("Media size (bytes):", handle.get_media_size())
print("Media size (MB):", handle.get_media_size() / (1024 * 1024))
print("Bytes per sector:", handle.bytes_per_sector)
print("Sectors per chunk:", handle.sectors_per_chunk)
print("Chunk size:", handle.chunk_size)
print("Error granularity:", handle.error_granularity)
print("Format:", handle.format)

# Read first 512 bytes (MBR/VBR)
header = handle.read(512)
print("Read first 512 bytes:", len(header))
print("Hex signature at end of 512:", header[510:512].hex())

# Seek beyond E01 boundary into E02 (E01 is 1,572,708,706 bytes)
e02_offset = 1572708706 + 1024
handle.seek(e02_offset)
chunk_e02 = handle.read(512)
print(f"Read from offset {e02_offset} (inside E02): {len(chunk_e02)} bytes read successfully!")

handle.close()
print("EWF test finished cleanly.")
