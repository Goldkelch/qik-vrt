#!/usr/bin/env bash
# Full profile; compilers/runtimes are provisioned by the enclosing workflow.
set -euo pipefail
repository_root="$(git rev-parse --show-toplevel)"
cd "$repository_root"
profile=conformance/effect_ack/core-invariant-v1/full
evidence_directory="$1"
mkdir -p "$evidence_directory"
cc -std=c90 -pedantic -Wall -Wextra -Werror -Iinclude "$profile/c90.c" "$profile/harness.c" src/effect_ack_core.c -o /tmp/full-c90
/tmp/full-c90 > "$evidence_directory/c90.out"
m68k-linux-gnu-gcc -m68000 -c "$profile/m68000.s" -o /tmp/full-m68k.o
m68k-linux-gnu-gcc -m68000 -std=c90 -pedantic -Wall -Wextra -Werror -static "$profile/harness.c" /tmp/full-m68k.o -o /tmp/full-m68k
qemu-m68k /tmp/full-m68k > "$evidence_directory/m68000.out"
set -a
. "$RUNNER_TEMP/core-invariant/pharo.env"
set +a
"/tmp/core-pharo/vm/$PHARO_VM_FILE" --headless "/tmp/core-pharo/image/$PHARO_IMAGE_FILE" st "$profile/smalltalk.st" > "$evidence_directory/pharo.log" 2>&1 || { cat "$evidence_directory/pharo.log"; exit 1; }
mv full-smalltalk.out "$evidence_directory/smalltalk.out"
python3 -B "$profile/temdd_profile.py" "$profile/full.temdd" "$evidence_directory/temdd.out" "$evidence_directory/temdd-ir.json"
(
  cd formalization/QIKVRT_Formalization_v2.0
  lake env lean "../../$profile/Full.lean" | tee "$evidence_directory/lean.log"
  lake env lean --run "../../$profile/Full.lean" > "$evidence_directory/lean-execution.log"
  mv full-lean.out "$evidence_directory/lean.out"
)
printf '%s\n' QIKVRT_FULL_LEAN_PASS > "$evidence_directory/lean.marker"
export PATH="/tmp/gnatprove-x86_64-linux-15.1.0-1/bin:$PATH"
gprbuild -P "$profile/ada/full.gpr"
"$profile/ada/bin/full_main"
mv full-ada.out "$evidence_directory/ada_spark.out"
gnatprove -P "$profile/ada/full_spark.gpr" --level=2 --checks-as-errors=on --warnings=error --report=all | tee "$evidence_directory/spark.log"
cat "$profile/ada/obj-spark/gnatprove/gnatprove.out" | tee -a "$evidence_directory/spark.log"
printf '%s\n' QIKVRT_FULL_SPARK_PASS > "$evidence_directory/spark.marker"
python3 -B -m unittest discover -s "$profile" -p test_full.py -v 2>&1 | tee "$evidence_directory/negative-controls.log"
python3 -B "$profile/check.py" --contract "$profile/contract.json" --directory "$evidence_directory" --head "$(git rev-parse HEAD)" --tree "$(git rev-parse 'HEAD^{tree}')" --output "$evidence_directory/report.json"
git diff --exit-code
