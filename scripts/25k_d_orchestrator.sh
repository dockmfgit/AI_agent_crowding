#!/bin/bash
# Block D orchestrator: D-1 qwen group -> D-2 70B singles -> marker.
cd /home/mfukush/AI_agent_crowding
log() { echo "$(date -u +%F/%T) $*"; }
export S2_URL=http://127.0.0.1:11435/api/generate

log "starting D-1 qwen group"
RELAUNCH=0
while true; do
  n=$(ls data/stage2/episodes 2>/dev/null | grep -c '^D1_')
  if [ "$n" -ge 480 ]; then log "D1 complete ($n)"; break; fi
  if ! ps aux | grep -q "25j_d1_[g]roup"; then
    if [ "$RELAUNCH" -ge 4 ]; then log "D1 driver died too often at $n"; break; fi
    log "launching D1 driver (attempt $RELAUNCH, at $n)"
    RELAUNCH=$((RELAUNCH+1))
    rm -f data/stage2/episodes/*.tmp
    setsid nohup env S2_MODEL=qwen3:8b S2_NOTHINK=1 \
      python3 scripts/25j_d1_group.py >> data/stage2d/driver_d1.log 2>&1 < /dev/null &
    sleep 60
  fi
  sleep 120
done

log "starting D-2 70B singles"
S2_MODEL=llama3.3:70b python3 scripts/25i_d2_70b.py \
  > data/stage2d/d2_70b.log 2>&1
log "D-2 done"
touch data/stage2d/D_DONE
log "BLOCK D DONE"
