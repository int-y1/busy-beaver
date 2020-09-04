#!/bin/bash

set -u
set -e

NUM_STATES=$1
NUM_SYMBOLS=$2
INIT_STEPS=$3
MAX_STEPS=$4
NUM_PROCESSES=$5

DATA_DIR="./data/${NUM_STATES}x${NUM_SYMBOLS}/${INIT_STEPS}/"

rm -rf $DATA_DIR
mkdir -p $DATA_DIR

make

echo
date
echo "(1) Enumerating a small number of steps to get a bunch of machines."
./lazy_beaver_enum $NUM_STATES $NUM_SYMBOLS $INIT_STEPS ${DATA_DIR}/steps_init ${DATA_DIR}/tms_init

echo
date
echo "(2) Splitting those machines into chunks."
./shuffle_split.py ${DATA_DIR}/tms_init $NUM_PROCESSES

echo
date
echo "(3) Continue enumeration on each chunk as a separate process in parallel."
for chunk_num in $(seq 0 $((NUM_PROCESSES - 1))); do
  INPUT_TMS=${DATA_DIR}/tms_init.part_${chunk_num}_of_${NUM_PROCESSES}
  ./continue_enum $INPUT_TMS $MAX_STEPS ${DATA_DIR}/steps_part_${chunk_num}_of_${NUM_PROCESSES} &
done
echo "Waiting for all the enumerations to complete."
wait

echo
date
echo "(4) Merging the results and compute the LB."
./merge_steps_examples.py ${DATA_DIR}/steps_* > ${DATA_DIR}/steps_final

echo
date
echo "Finished"
