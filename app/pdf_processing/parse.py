import re

def split_blocks(text):
    raw_blocks = re.split(r"(Question\s+\d+)", text)
    blocks = []
    for i in range(1, len(raw_blocks), 2):
        block = raw_blocks[i] + "\n" + raw_blocks[i+1] if i+1 < len(raw_blocks) else raw_blocks[i]
        blocks.append(block.strip())
    return blocks 