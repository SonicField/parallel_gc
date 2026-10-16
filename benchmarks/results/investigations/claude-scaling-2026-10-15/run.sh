#!/bin/bash
# usage: run.sh N  -> JSON lines on stdout; alternates base/patch per cell
N=$1
for shape in graph tree lists chain; do
  for mode in serial 2 4 8 16; do
    for rep in 1 2; do
      for b in base patch; do
        out=$(cd /tmp && taskset -c 0-31 timeout 300 /tmp/gcscale/build-$b/python -I /tmp/gcscale/scale.py $shape $N $mode)
        echo "{\"build\":\"$b\",\"rep\":$rep,${out#\{}"
      done
    done
  done
done
