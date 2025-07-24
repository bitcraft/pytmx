import time
from pathlib import Path

from pytmx import TiledMap, decode_gid

# Optional: enable tracking cache hits
flag_cache_stats = {"hits": 0, "misses": 0}
flag_cache = {}

# TMX flag constants
GID_TRANS_FLIPX = 1 << 31
GID_TRANS_FLIPY = 1 << 30
GID_TRANS_ROT = 1 << 29
GID_MASK = GID_TRANS_FLIPX | GID_TRANS_FLIPY | GID_TRANS_ROT

DATA_DIR = Path("./apps/data/")
RUNS_PER_MAP = 3


def decode_gid_tracked(raw_gid: int):
    if raw_gid < GID_TRANS_ROT:
        return raw_gid, decode_gid(raw_gid)[1]
    if raw_gid in flag_cache:
        flag_cache_stats["hits"] += 1
        return raw_gid & ~GID_MASK, flag_cache[raw_gid]
    flag_cache_stats["misses"] += 1
    flags = decode_gid(raw_gid)[1]
    flag_cache[raw_gid] = flags
    return raw_gid & ~GID_MASK, flags


def benchmark_map(map_path: Path) -> float:
    times = []
    for _ in range(RUNS_PER_MAP):
        start = time.time()
        TiledMap(str(map_path))
        elapsed = time.time() - start
        times.append(elapsed)
    return sum(times) / RUNS_PER_MAP


def summarize_map(map_path: Path):
    try:
        tmx = TiledMap(str(map_path))
        num_layers = len(tmx.layers)
        num_tilesets = len(tmx.tilesets)
        num_tiles = sum(
            len(layer.data) for layer in tmx.layers if hasattr(layer, "data")
        )
        return num_layers, num_tilesets, num_tiles
    except Exception:
        return None, None, None


def main():
    print("TMX Load Benchmark (real maps)\n")
    print(
        f"{'Map Name':<25} | {'Avg Time (s)':>12} | {'Layers':>6} | {'Tilesets':>9} | {'Tiles':>7}"
    )
    print("-" * 70)

    for map_file in DATA_DIR.glob("*.tmx"):
        try:
            avg_time = benchmark_map(map_file)
            layers, tilesets, tiles = summarize_map(map_file)
            print(
                f"{map_file.name:<25} | {avg_time:>12.4f} | {layers:>6} | {tilesets:>9} | {tiles:>7}"
            )
        except Exception as e:
            print(f"{map_file.name:<25} | Error: {str(e)}")

    if flag_cache_stats["hits"] or flag_cache_stats["misses"]:
        print("\nGID Cache Stats")
        print(f"  Hits:   {flag_cache_stats['hits']}")
        print(f"  Misses: {flag_cache_stats['misses']}")


if __name__ == "__main__":
    main()
