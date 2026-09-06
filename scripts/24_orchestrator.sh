#!/bin/bash
# Stage 2 tail orchestrator: wait for B6, run B5 fidelity, run final analysis.
# Runs detached; progress in data/stage2/orchestrator.log; marker file on done.
cd /home/mfukush/AI_agent_crowding
log() { echo "$(date -u +%F/%T) $*"; }

# 1. wait for second pass (relaunch once if its driver died mid-way)
RELAUNCHED=0
while true; do
  n=$(ls data/stage2/episodes 2>/dev/null | grep -c '^B6')
  if [ "$n" -ge 432 ]; then log "B6 complete ($n)"; break; fi
  if ! ps aux | grep -q "23_second_[p]ass"; then
    if [ "$RELAUNCHED" -ge 3 ]; then log "B6 driver died too often, giving up at $n"; break; fi
    log "second-pass driver dead at $n, relaunching"
    RELAUNCHED=$((RELAUNCHED+1))
    rm -f data/stage2/episodes/*.tmp
    setsid nohup python3 scripts/23_second_pass.py >> data/stage2/driver_b6.log 2>&1 < /dev/null &
    sleep 60
  fi
  sleep 120
done

# 2. fidelity block B5 (10 episodes, 5-sample spins)
log "starting B5 fidelity"
python3 scripts/22_stage2_driver.py --blocks B5 >> data/stage2/driver_b5.log 2>&1
log "B5 done ($(ls data/stage2/episodes | grep -c '^B5'))"

# 3. final analysis
log "running final analysis"
python3 scripts/29_stage2_analysis.py > results/stage2_final_analysis.log 2>&1
log "analysis done"
touch data/stage2/PIPELINE_DONE
log "ALL DONE"
