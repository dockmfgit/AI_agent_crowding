#!/bin/bash
cd /home/mfukush/AI_agent_crowding
log() { echo "$(date -u +%F/%T) $*"; }
R=0
while true; do
  n=$(ls data/stage2/episodes 2>/dev/null | grep -c '^B3c_')
  if [ "$n" -ge 256 ]; then log "B3c complete ($n)"; break; fi
  if ! ps aux | grep -q "44_b_[g]roup"; then
    if [ "$R" -ge 4 ]; then log "driver died too often at $n"; break; fi
    log "launching B3c driver (attempt $R, at $n)"; R=$((R+1))
    rm -f data/stage2/episodes/*.tmp
    setsid nohup env S2_MODEL=qwen3:8b S2_NOTHINK=1 \
      python3 scripts/44_b_group.py >> data/stage2c/driver_b3c.log 2>&1 < /dev/null &
    sleep 60
  fi
  sleep 120
done
touch data/stage2c/B3C_DONE
log "DONE"
