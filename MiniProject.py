"""
Usage:
    python huffman.py compress   input.txt  output.huf
    python huffman.py decompress output.huf restored.txt
"""
import heapq
import sys
from collections import Counter


def build_codes(freq):
    """Build {byte: bit-string} from {byte: frequency}."""
    heap = [(f, i, sym) for i, (sym, f) in enumerate(freq.items())]
    heapq.heapify(heap)
    next_id = len(heap)

    while len(heap) > 1:
        f1, _, left = heapq.heappop(heap)
        f2, _, right = heapq.heappop(heap)
        heapq.heappush(heap, (f1 + f2, next_id, (left, right)))
        next_id += 1

    codes = {}

    def walk(node, code):
        if isinstance(node, tuple):
            walk(node[0], code + "0")
            walk(node[1], code + "1")
        else:
            codes[node] = code or "0"

    walk(heap[0][2], "")
    return codes

def format_size(num_bytes):
    """Convert byte count into a human-readable string (B, KB, MB, GB)."""
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.2f} {unit}" if unit != "B" else f"{num_bytes} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.2f} TB"

def compress(src, dst):
    with open(src, "rb") as f:
        data = f.read()

    if not data:
        open(dst, "wb").close()
        return

    freq = Counter(data)
    codes = build_codes(freq)

    header = bytearray([len(freq) - 1, 0])  # pad placeholder
    for sym, count in freq.items():
        header.append(sym)
        header += count.to_bytes(4, "big")

    packed = bytearray()
    buffer = 0
    bit_count = 0

    for b in data:
        for c in codes[b]:
            buffer = (buffer << 1) | (1 if c == "1" else 0)
            bit_count += 1
            if bit_count == 8:
                packed.append(buffer)
                buffer = 0
                bit_count = 0

    pad = 0
    if bit_count > 0:
        pad = 8 - bit_count
        buffer <<= pad
        packed.append(buffer)

    header[1] = pad
    out = header + packed

    with open(dst, "wb") as f:
        f.write(out)

    old, new = len(data), len(out)
    print(f"{format_size(old)} -> {format_size(new)} ({new / old:.1%} of original)")

def decompress(src, dst):
    with open(src, "rb") as f:
        data = f.read()

    if not data:
        open(dst, "wb").close()
        return

    count, pad = data[0] + 1, data[1]
    freq, pos = {}, 2
    for _ in range(count):
        freq[data[pos]] = int.from_bytes(data[pos + 1:pos + 5], "big")
        pos += 5

    lookup = {code: sym for sym, code in build_codes(freq).items()}
    total_symbols = sum(freq.values())

    payload = data[pos:]
    total_bits = len(payload) * 8 - pad

    out = bytearray()
    code = ""
    bit_index = 0

    for byte in payload:
        for shift in range(7, -1, -1):
            if bit_index >= total_bits or len(out) >= total_symbols:
                break
            bit = (byte >> shift) & 1
            code += "1" if bit else "0"
            bit_index += 1
            if code in lookup:
                out.append(lookup[code])
                code = ""
        if len(out) >= total_symbols:
            break

    with open(dst, "wb") as f:
        f.write(out)
    print(f"Restored {format_size(len(out))}")

if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] not in ("compress", "decompress"):
        sys.exit("Usage: python huffman.py compress|decompress <input> <output>")
    action = compress if sys.argv[1] == "compress" else decompress
    action(sys.argv[2], sys.argv[3])