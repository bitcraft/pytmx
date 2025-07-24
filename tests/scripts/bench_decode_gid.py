import timeit

from pytmx import TileFlags, decode_gid

# Constants
GID_TRANS_FLIPX = 1 << 31
GID_TRANS_FLIPY = 1 << 30
GID_TRANS_ROT = 1 << 29
GID_MASK = GID_TRANS_FLIPX | GID_TRANS_FLIPY | GID_TRANS_ROT


def decode_no_cache(raw_gid: int) -> tuple[int, TileFlags]:
    if raw_gid < GID_TRANS_ROT:
        return raw_gid, TileFlags(False, False, False)
    return (
        raw_gid & ~GID_MASK,
        TileFlags(
            raw_gid & GID_TRANS_FLIPX == GID_TRANS_FLIPX,
            raw_gid & GID_TRANS_FLIPY == GID_TRANS_FLIPY,
            raw_gid & GID_TRANS_ROT == GID_TRANS_ROT,
        ),
    )


def run_benchmark(size: int) -> tuple[float, float]:
    raw_gids = [GID_TRANS_FLIPX | GID_TRANS_FLIPY | (i % 1000 + 1) for i in range(size)]

    def run_no_cache():
        for gid in raw_gids:
            decode_no_cache(gid)

    def run_with_cache():
        for gid in raw_gids:
            decode_gid(gid)

    time_no_cache = timeit.timeit(run_no_cache, number=1)
    time_cache = timeit.timeit(run_with_cache, number=1)
    return time_no_cache, time_cache


def main():
    print("Running decode_gid benchmarks...\n")
    gid_sizes = [1_000, 5_000, 10_000, 50_000, 100_000, 250_000, 500_000, 1_000_000]

    print(f"{'GID Count':>10} | {'No Cache':>10} | {'With Cache':>11} | {'Speedup':>8}")
    print("-" * 50)

    for size in gid_sizes:
        no_cache, cache = run_benchmark(size)
        speedup = no_cache / cache if cache > 0 else float("inf")
        print(f"{size:>10} | {no_cache:.4f}s | {cache:.4f}s | {speedup:>7.2f}x")


if __name__ == "__main__":
    main()
