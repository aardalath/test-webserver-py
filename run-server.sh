#!/bin/bash
docker run -t -i \
    --expose=8080 \
    -v $(pwd):/ws \
    -w /ws/www \
    qpf-debian:a \
    python /ws/test-dataserver.py -H 0.0.0.0 -p 8080 -l debug --no-dirlist -r /ws/www \
    | tee out.loh
