#!/bin/bash
# Stage 2b tail orchestrator: wait for A-1, then run approved A-2 group.
cd /home/mfukush/AI_agent_crowding
log() { echo "$(date -u +%F/%T) $*"; }
RELAUNCH=0
while true; do
  n=$(ls data/stage2/episodes 2>/dev/null | grep -c '^S2b_A1')
  if [ "$n" -ge 288 ]; then log "A1 complete ($n)"; break; fi
  if ! ps aux | grep -q "28_s2b_group.py --set A[1]"; then
    if [ "$RELAUNCH" -ge 3 ]; then log "A1 driver died too often at $n"; break; fi
    log "A1 driver dead at $n, relaunching"; RELAUNCH=$((RELAUNCH+1))
    rm -f data/stage2/episodes/*.tmp
    setsid nohup python3 scripts/28_s2b_group.py --set A1 >> data/stage2b/driver_a1.log 2>&1 < /dev/null &
    sleep 60
  fi
  sleep 120
done
log "starting A2 group (user-approved 2026-08-25)"
python3 scripts/28_s2b_group.py --set A2 --approved >> data/stage2b/driver_a2.log 2>&1
log "A2 done ($(ls data/stage2/episodes | grep -c '^S2b_A2'))"
touch data/stage2b/GROUPS_DONE
log "ALL GROUP RUNS DONE"
