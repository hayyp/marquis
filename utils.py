from typing import List, Union, BinaryIO

def list_to_bytes(
    lst: List[str]
) -> Union[bytes, BinaryIO, None]:
    with open ("tmp.txt", "w", encoding="utf-8") as tmp_file:
        for chapter in lst:
            tmp_file.write(chapter)
    with open ("tmp.txt", "rb") as tmp_file:
        file_data = tmp_file.read()
        return file_data