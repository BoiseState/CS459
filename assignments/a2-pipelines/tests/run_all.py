"""`make test`: every part, then a summary. GIVEN."""

import sys
import time

from tests import part0, part1, part2, part3, part4


def main() -> int:
    t0 = time.time()
    results = []
    for mod in (part0, part1, part2, part3, part4):
        try:
            results.append(mod.run())
        except Exception as e:  # a test crashed outright; show it and keep going
            print(f"  ERROR  {type(e).__name__}: {e}")
            raise
    print("\n" + "=" * 64)
    for h in results:
        print(h.summary_line())
    n = sum(h.passed for h in results)
    print("=" * 64)
    print(f"{n} of {len(results)} parts pass  ({time.time() - t0:.0f}s)")
    if n < len(results):
        print("Run one part on its own with `make part1`, `make part2`, ... to see its full output.")
    return 0 if n == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
