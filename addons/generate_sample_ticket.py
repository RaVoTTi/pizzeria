print("=" * 60)
print("  Kitchen Ticket Sample Generator")
print("=" * 60)

import importlib.util
import os

spec = importlib.util.spec_from_file_location(
    "sample", "/mnt/custom-addons/pos_kitchen_receipt/sample.py")
sample = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sample)

OUTPUT_DIR = "/tmp/kitchen_samples"

print(f"\nGenerating {len(sample.SAMPLE_TICKETS)} samples ...")
printer = env["kitchen.ticket.printer"]
sample.generate_all(printer, OUTPUT_DIR)

print(f"\n{'=' * 60}")
print(f"  {len(sample.SAMPLE_TICKETS)} samples in {OUTPUT_DIR}/")
for fname in sorted(os.listdir(OUTPUT_DIR)):
    fpath = os.path.join(OUTPUT_DIR, fname)
    size = os.path.getsize(fpath)
    print(f"  {fname} ({size} bytes)")
print(f"{'=' * 60}")
